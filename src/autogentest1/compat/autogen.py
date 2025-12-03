"""Compatibility helpers for AutoGen agent imports."""

from __future__ import annotations

# NOTE: pyautogen 0.10.0 re-exports symbols via autogen_agentchat/autogen_ext.
# The try/except blocks keep the project working on both legacy and modern
# release trains without forcing callers to pin a specific package.
try:  # pragma: no cover - exercised when legacy package is present
    from autogen import AssistantAgent, UserProxyAgent  # type: ignore
except ImportError:  # pragma: no cover - default path in recent releases
    from autogen_agentchat.agents import AssistantAgent, UserProxyAgent  # type: ignore

try:  # pragma: no cover - legacy shim
    from autogen.coding import LocalCommandLineCodeExecutor  # type: ignore
except ImportError:  # pragma: no cover - modern package layout
    from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor  # type: ignore

__all__ = [
    "AssistantAgent",
    "LocalCommandLineCodeExecutor",
    "UserProxyAgent",
]
