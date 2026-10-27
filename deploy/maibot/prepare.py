"""Prepare a fresh deployment directory; never modify a running deployment."""

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import tomllib

HERE = Path(__file__).resolve().parent
FILES = {
    "bot_config.toml": "config/bot_config.toml",
    "model_config.toml": "config/model_config.toml",
    "adapter_policy.toml": "config/adapter_policy.toml",
    "adapter_config.toml": "plugins/MaiBot-SnowLuma-Adapter/config.toml",
}
PLACEHOLDER = re.compile(r"\$\{([A-Z_]+)\}")


def render(text: str, values: dict[str, str]) -> str:
    """Substitute inside TOML strings, escaping quotes and backslashes."""
    def replace(match: re.Match) -> str:
        return json.dumps(values[match[1]], ensure_ascii=False)[1:-1]

    result = PLACEHOLDER.sub(replace, text)
    tomllib.loads(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--bot-qq", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--config-only", action="store_true",
                        help="Skip the adapter checkout (offline validation only).")
    args = parser.parse_args()
    if not re.fullmatch(r"[1-9][0-9]{4,11}", args.bot_qq):
        parser.error("Invalid bot QQ number")
    if not re.fullmatch(r"[1-9][0-9]{4,11}", args.group_id):
        parser.error("Invalid group number")
    destination = args.destination.resolve()
    if destination.exists():
        parser.error("Destination already exists; refusing to overwrite")
    key = os.environ.get("DEEPSEEK_API_KEY") or getpass.getpass("DeepSeek API key: ")
    if not key.strip():
        parser.error("DeepSeek API key is required")
    values = {"BOT_QQ": args.bot_qq, "GROUP_ID": args.group_id,
              "DEEPSEEK_API_KEY": key, "NAPCAT_TOKEN": os.environ.get("NAPCAT_TOKEN", "")}
    rendered = {target: render((HERE / "templates" / (name + ".example")).read_text(), values)
                for name, target in FILES.items()}
    os.umask(0o077)
    destination.mkdir(parents=True, mode=0o700)
    provenance = json.loads((HERE / "PROVENANCE.json").read_text())
    if not args.config_only:
        adapter = destination / "plugins/MaiBot-SnowLuma-Adapter"
        subprocess.run(["git", "clone", "--no-checkout", provenance["adapter_repository"],
                        str(adapter)], check=True)
        subprocess.run(["git", "-C", str(adapter), "checkout", "--detach",
                        provenance["adapter_commit"]], check=True)
    for relative, text in rendered.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(text)
        path.chmod(0o600)
    for name in ("Dockerfile", "compose.yaml", "PROVENANCE.json"):
        shutil.copyfile(HERE / name, destination / name)
    for name in ("data", "logs"):
        (destination / name).mkdir(mode=0o700)
    print(f"Prepared {destination}; no containers started")


if __name__ == "__main__":
    main()
