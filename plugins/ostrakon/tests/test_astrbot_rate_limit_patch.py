from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import timedelta
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


class DummyRateLimitStrategy(Enum):
    STALL = "stall"
    DISCARD = "discard"


class DummyStage:
    pass


def register_stage(cls: type[Any]) -> type[Any]:
    return cls


def load_patch(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    modules: dict[str, ModuleType] = {}

    for name in (
        "astrbot",
        "astrbot.core",
        "astrbot.core.config",
        "astrbot.core.config.astrbot_config",
        "astrbot.core.platform",
        "astrbot.core.platform.astr_message_event",
        "astrbot.core.pipeline",
        "astrbot.core.pipeline.context",
        "astrbot.core.pipeline.stage",
        "astrbot.core.pipeline.rate_limit_check",
    ):
        module = ModuleType(name)
        if name in {
            "astrbot",
            "astrbot.core",
            "astrbot.core.config",
            "astrbot.core.platform",
            "astrbot.core.pipeline",
            "astrbot.core.pipeline.rate_limit_check",
        }:
            module.__path__ = []  # type: ignore[attr-defined]
        modules[name] = module
        monkeypatch.setitem(sys.modules, name, module)

    modules["astrbot.core"].logger = logging.getLogger("ostrakon-rate-limit-test")
    modules["astrbot.core.config.astrbot_config"].RateLimitStrategy = DummyRateLimitStrategy
    modules["astrbot.core.platform.astr_message_event"].AstrMessageEvent = object
    modules["astrbot.core.pipeline.context"].PipelineContext = object
    modules["astrbot.core.pipeline.stage"].Stage = DummyStage
    modules["astrbot.core.pipeline.stage"].register_stage = register_stage

    patch_path = (
        Path(__file__).resolve().parents[1] / "deploy" / "astrbot" / "rate_limit_stage.py"
    )
    module_name = "astrbot.core.pipeline.rate_limit_check.ostrakon_patch"
    spec = importlib.util.spec_from_file_location(module_name, patch_path)
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


class FakeEvent:
    def __init__(
        self,
        *,
        text: str = "",
        raw: dict[str, Any] | None = None,
        session_id: str = "group-1",
    ) -> None:
        self.session_id = session_id
        self.message_obj = SimpleNamespace(raw_message=raw or {})
        self._text = text
        self.stopped = False

    def get_message_str(self) -> str:
        return self._text

    def stop_event(self) -> None:
        self.stopped = True


@pytest.mark.asyncio
async def test_ostrakon_control_events_bypass_chat_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_patch(monkeypatch)
    stage = module.RateLimitStage()
    stage.rate_limit_count = 1
    stage.rate_limit_time = timedelta(seconds=60)
    stage.rl_strategy = DummyRateLimitStrategy.DISCARD.value

    status = FakeEvent(text="/ostrakon status")
    reset = FakeEvent(text="/ostrakon reset")
    reaction = FakeEvent(
        raw={"post_type": "notice", "notice_type": "group_msg_emoji_like"}
    )
    normal_first = FakeEvent(text="hello")
    normal_second = FakeEvent(text="world")

    for event in (status, reset, reaction, normal_first, normal_second):
        await stage.process(event)

    assert status.stopped is False
    assert reset.stopped is False
    assert reaction.stopped is False
    assert normal_first.stopped is False
    assert normal_second.stopped is True


def test_ostrakon_command_bypass_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_patch(monkeypatch)

    assert module._is_ostrakon_control_command(FakeEvent(text=" /ostrakon status ")) is True
    assert module._is_ostrakon_control_command(FakeEvent(text="/ostrakon reset")) is True
    assert module._is_ostrakon_control_command(FakeEvent(text="/ostrakon status now")) is False
    assert module._is_ostrakon_control_command(FakeEvent(text="/status")) is False
