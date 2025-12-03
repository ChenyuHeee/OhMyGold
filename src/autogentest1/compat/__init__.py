"""Compatibility layer for third-party interfaces."""

from .autogen import AssistantAgent, LocalCommandLineCodeExecutor, UserProxyAgent

__all__ = [
    "AssistantAgent",
    "LocalCommandLineCodeExecutor",
    "UserProxyAgent",
]
