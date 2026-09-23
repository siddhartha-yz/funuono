"""Deploy CI-approved plugin commits without restarting AstrBot or NapCat."""

from __future__ import annotations

import argparse
import fcntl
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

REPO = "siddhartha-yz/funuono"
GIT_URL = f"git@github.com:{REPO}.git"
PLUGINS = ("nju_join_verifier", "ostrakon")
STATE_DIR = Path("/home/ubuntu/.local/share/funuono")
GIT_DIR = STATE_DIR / "repo.git"
LIVE_DIR = Path("/home/ubuntu/workspace/astrbot/data/plugins")
KEY_FILE = Path("/home/ubuntu/.config/funuono/astrbot-plugin.key")
API_BASE = "http://127.0.0.1:6185/api/v1"


class DeploymentError(RuntimeError):
    pass


def run(*args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        args,
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise DeploymentError(f"{' '.join(args[:2])} failed: {message[-1000:]}")
    return result.stdout


def fetch_main() -> str:
    if not GIT_DIR.exists():
        run("git", "init", "--bare", str(GIT_DIR))
        run("git", "--git-dir", str(GIT_DIR), "remote", "add", "origin", GIT_URL)
    run(
        "git", "--git-dir", str(GIT_DIR), "fetch", "--quiet", "origin",
        "+refs/heads/main:refs/remotes/origin/main",
    )
    sha = run("git", "--git-dir", str(GIT_DIR), "rev-parse", "refs/remotes/origin/main")
    return sha.decode().strip()


def ci_succeeded(sha: str) -> bool:
    endpoint = (
        f"repos/{REPO}/actions/workflows/ci.yml/runs"
        f"?head_sha={sha}&branch=main&per_page=20"
    )
    payload = json.loads(run("gh", "api", endpoint))
    return any(
        item.get("head_sha") == sha
        and item.get("event") == "push"
        and item.get("status") == "completed"
        and item.get("conclusion") == "success"
        for item in payload.get("workflow_runs", [])
    )


def merged_pull_request(sha: str) -> bool:
    """Only a squash-merged PR targeting main may become a production release."""
    payload = json.loads(run("gh", "api", f"repos/{REPO}/commits/{sha}/pulls"))
    return any(
        item.get("merged_at")
        and item.get("merge_commit_sha") == sha
        and item.get("base", {}).get("ref") == "main"
        for item in payload
    )


def stage_plugins(sha: str, stage: Path) -> None:
    archive = run(
        "git", "--git-dir", str(GIT_DIR), "archive", sha,
        *(f"plugins/{name}" for name in PLUGINS),
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(stage, filter="data")
    for name in PLUGINS:
        plugin = stage / "plugins" / name
        if not (plugin / "main.py").is_file() or not (plugin / "metadata.yaml").is_file():
            raise DeploymentError(f"missing required files for {name}")
        run(sys.executable, "-m", "compileall", "-q", str(plugin))


def read_plugin_key() -> str:
    mode = KEY_FILE.stat().st_mode
    if mode & 0o077:
        raise DeploymentError(f"plugin API key file is not private: {KEY_FILE}")
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key.startswith("abk_"):
        raise DeploymentError("invalid plugin API key file")
    return key


def reload_plugin(name: str, key: str) -> None:
    url = f"{API_BASE}/plugins/{name}/reload"
    request = urllib.request.Request(
        url, data=b"{}", method="POST",
        headers={"X-API-Key": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
    except (urllib.error.URLError, ValueError) as exc:
        raise DeploymentError(f"reload request failed for {name}: {exc}") from exc
    if payload.get("status") != "ok":
        raise DeploymentError(f"AstrBot rejected reload for {name}: {payload.get('message')}")


def install_plugins(
    stage: Path,
    live_dir: Path,
    backup: Path,
    reload_fn: Callable[[str], None],
) -> None:
    """Swap both plugin trees and restore the old trees if either reload fails."""
    backup.mkdir(parents=True, exist_ok=False)
    if os.stat(stage).st_dev != os.stat(live_dir).st_dev:
        raise DeploymentError("staging and live plugin directories are on different filesystems")
    moved_old: set[str] = set()
    installed_new: set[str] = set()
    try:
        for name in PLUGINS:
            live = live_dir / name
            if live.exists():
                os.replace(live, backup / name)
                moved_old.add(name)
            os.replace(stage / "plugins" / name, live)
            installed_new.add(name)
        for name in PLUGINS:
            reload_fn(name)
    except Exception as exc:
        failed_dir = backup / "failed-new"
        failed_dir.mkdir(exist_ok=True)
        for name in reversed(PLUGINS):
            live = live_dir / name
            if name in installed_new and live.exists():
                os.replace(live, failed_dir / name)
            if name in moved_old:
                os.replace(backup / name, live)
        rollback_errors = []
        for name in PLUGINS:
            if name in moved_old:
                try:
                    reload_fn(name)
                except Exception as rollback_exc:  # noqa: BLE001 - continue restoring both plugins
                    rollback_errors.append(f"{name}: {rollback_exc}")
        detail = f"; rollback reload errors: {', '.join(rollback_errors)}" if rollback_errors else ""
        raise DeploymentError(f"deployment rolled back: {exc}{detail}") from exc


def sync() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with (STATE_DIR / "deploy.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        sha = fetch_main()
        deployed_file = STATE_DIR / "deployed.sha"
        if deployed_file.exists() and deployed_file.read_text().strip() == sha:
            return
        if not ci_succeeded(sha):
            print(f"{sha[:12]}: waiting for successful CI", flush=True)
            return
        if not merged_pull_request(sha):
            print(f"{sha[:12]}: no merged pull request; deployment skipped", flush=True)
            return
        key = read_plugin_key()
        with tempfile.TemporaryDirectory(prefix="stage-", dir=STATE_DIR) as temp:
            stage = Path(temp)
            stage_plugins(sha, stage)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = STATE_DIR / "backups" / f"{stamp}-{sha[:12]}"
            backup.parent.mkdir(exist_ok=True)
            install_plugins(stage, LIVE_DIR, backup, lambda name: reload_plugin(name, key))
        temp_state = STATE_DIR / "deployed.sha.tmp"
        temp_state.write_text(sha + "\n", encoding="utf-8")
        os.replace(temp_state, deployed_file)
        print(f"deployed {sha}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("sync",))
    args = parser.parse_args()
    try:
        if args.command == "sync":
            sync()
    except (DeploymentError, OSError, subprocess.SubprocessError) as exc:
        print(f"deployment error: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
