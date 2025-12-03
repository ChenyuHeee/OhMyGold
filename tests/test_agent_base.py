"""Tests for agent base helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from autogentest1.agents.base import _build_code_execution_config
from autogentest1.config.settings import Settings


def _make_settings(tmp_path: Path, **overrides) -> Settings:
    base = Settings.model_validate(
        {
            "code_execution_enabled": True,
            "code_execution_agents": ["QuantResearchAgent", "TechAnalystAgent"],
            "code_execution_timeout": 123,
            "code_execution_workdir": str(tmp_path / "sandbox"),
        }
    )
    if overrides:
        base = base.model_copy(update=overrides)
    return base


def test_build_code_execution_config_creates_executor(monkeypatch, tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)

    captured: dict[str, SimpleNamespace] = {}

    def fake_executor(*, timeout: int, work_dir, **_: object):
        obj = SimpleNamespace(timeout=timeout, work_dir=Path(work_dir))
        captured["executor"] = obj
        return obj

    monkeypatch.setattr("autogentest1.agents.base.LocalCommandLineCodeExecutor", fake_executor)

    config = _build_code_execution_config(settings, "QuantResearchAgent")
    assert config is not None
    assert config["timeout"] == settings.code_execution_timeout
    assert captured["executor"].timeout == settings.code_execution_timeout
    assert captured["executor"].work_dir.exists()


def test_build_code_execution_config_respects_disabled_agent(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path, code_execution_agents=["TechAnalystAgent"])

    config = _build_code_execution_config(settings, "QuantResearchAgent")
    assert config is None


def test_build_code_execution_config_uses_default_dir(monkeypatch, tmp_path: Path) -> None:
    settings = _make_settings(tmp_path, code_execution_workdir=None)

    created_paths: list[Path] = []

    def fake_executor(*, timeout: int, work_dir, **_: object):
        path = Path(work_dir)
        created_paths.append(path)
        return SimpleNamespace(timeout=timeout, work_dir=path)

    monkeypatch.setattr("autogentest1.agents.base.LocalCommandLineCodeExecutor", fake_executor)

    config = _build_code_execution_config(settings, "TechAnalystAgent")
    assert config is not None
    assert created_paths and created_paths[0].exists()
