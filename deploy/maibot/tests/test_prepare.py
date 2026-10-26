"""Check deployment boundaries without credentials, Docker or network access."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import tomllib

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("maibot_prepare", HERE / "prepare.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def test_render_escapes_credentials():
    key = 'fake-"quote\\slash\nline\tend'
    rendered = prepare.render('api_key = "${DEEPSEEK_API_KEY}"', {"DEEPSEEK_API_KEY": key})
    assert tomllib.loads(rendered)["api_key"] == key


def test_fresh_directory_and_refuse_overwrite(tmp_path):
    output = tmp_path / "runtime"
    env = {**os.environ, "DEEPSEEK_API_KEY": "test-placeholder", "NAPCAT_TOKEN": "test-token"}
    args = [sys.executable, str(HERE / "prepare.py"), str(output), "--bot-qq", "123456789",
            "--group-id", "987654321", "--config-only"]
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "test-placeholder" not in result.stdout + result.stderr
    configs = {}
    for name, relative in prepare.FILES.items():
        path = output / relative
        configs[name] = tomllib.loads(path.read_text())
        assert path.stat().st_mode & 0o777 == 0o600
    bot = configs["bot_config.toml"]
    assert bot["bot"]["qq_account"] == "123456789"
    assert bot["a_memorix"]["global_memory_sharing_enabled"] is False
    assert bot["a_memorix"]["integration"]["heuristic_memory_cross_chat_enabled"] is False
    policy = configs["adapter_policy.toml"]
    assert policy["defaults"]["group"] == {"default_action": "block", "allow_ids": ["987654321"]}
    assert policy["defaults"]["private"] == {"default_action": "block", "allow_ids": []}
    model = configs["model_config.toml"]
    assert model["api_providers"][0]["api_key"] == "test-placeholder"
    assert model["web"]["services"]["deepseek-search"]["api_key"] == "test-placeholder"
    assert model["models"][0]["visual"] is True
    assert configs["adapter_config.toml"]["client"]["token"] == "test-token"
    assert "127.0.0.1:18001:8001" in (output / "compose.yaml").read_text()
    sentinel = output / "config/bot_config.toml"
    before = sentinel.read_bytes()
    retry = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    assert retry.returncode != 0
    assert "refusing to overwrite" in retry.stderr
    assert sentinel.read_bytes() == before


def test_templates_contain_only_placeholder_credentials():
    def check(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"api_key", "token", "access_token", "password", "secret"}:
                    assert child in ("", "${DEEPSEEK_API_KEY}", "${NAPCAT_TOKEN}")
                elif key in {"auth_token", "api_server_allowed_api_keys"}:
                    assert child == []
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    for path in (HERE / "templates").glob("*.example"):
        check(tomllib.loads(path.read_text()))
