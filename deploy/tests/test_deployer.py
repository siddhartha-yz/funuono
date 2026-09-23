from pathlib import Path

import pytest

from deploy.deployer import PLUGINS, DeploymentError, install_plugins


def make_layout(root: Path) -> tuple[Path, Path, Path]:
    stage = root / "stage"
    live = root / "live"
    backup = root / "backup"
    for name in PLUGINS:
        (stage / "plugins" / name).mkdir(parents=True)
        (stage / "plugins" / name / "marker").write_text("new")
        (live / name).mkdir(parents=True)
        (live / name / "marker").write_text("old")
    return stage, live, backup


def test_success_swaps_both_plugins(tmp_path: Path) -> None:
    stage, live, backup = make_layout(tmp_path)
    reloaded = []
    install_plugins(stage, live, backup, reloaded.append)
    assert reloaded == list(PLUGINS)
    assert all((live / name / "marker").read_text() == "new" for name in PLUGINS)
    assert all((backup / name / "marker").read_text() == "old" for name in PLUGINS)


def test_reload_failure_restores_both_plugins(tmp_path: Path) -> None:
    stage, live, backup = make_layout(tmp_path)
    calls = []

    def reload(name: str) -> None:
        calls.append(name)
        if name == PLUGINS[1] and calls.count(name) == 1:
            raise RuntimeError("simulated reload failure")

    with pytest.raises(DeploymentError, match="rolled back"):
        install_plugins(stage, live, backup, reload)
    assert all((live / name / "marker").read_text() == "old" for name in PLUGINS)
    assert all((backup / "failed-new" / name / "marker").read_text() == "new" for name in PLUGINS)
    assert calls == [*PLUGINS, *PLUGINS]
