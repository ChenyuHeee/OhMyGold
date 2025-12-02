"""Common agent construction helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from autogen import AssistantAgent, UserProxyAgent

from ..config.settings import Settings


def build_llm_config(settings: Settings, *, agent_name: str) -> Dict[str, Any]:
    """Return the AutoGen llm_config dictionary with optional local overrides."""

    config_list: List[Dict[str, Any]] = []
    local_agents = set(settings.local_model_agents)

    if (
        settings.local_model_enabled
        and settings.local_model_name
        and agent_name in local_agents
    ):
        local_config: Dict[str, Any] = {
            "model": settings.local_model_name,
        }
        if settings.local_model_base_url:
            local_config["base_url"] = settings.local_model_base_url
        if settings.local_model_api_key:
            local_config["api_key"] = settings.local_model_api_key
        config_list.append(local_config)

    config_list.append(
        {
            "model": settings.deepseek_model,
            "api_key": settings.deepseek_api_key,
            "base_url": settings.deepseek_base_url,
        }
    )

    return {"config_list": config_list}


def create_llm_agent(name: str, system_prompt: str, settings: Settings) -> AssistantAgent:
    """Create an AutoGen AssistantAgent bound to DeepSeek."""

    return AssistantAgent(
        name=name,
        system_message=system_prompt,
        llm_config=build_llm_config(settings, agent_name=name),
    )


def create_user_proxy(name: str, code_execution_config: Dict[str, Any] | None = None) -> UserProxyAgent:
    """Create a UserProxyAgent for running Python tools on behalf of LLM agents."""

    return UserProxyAgent(
        name=name,
        system_message="You are an orchestration proxy that executes Python helpers when requested.",
        code_execution_config=code_execution_config or {"use_docker": False},
    )
