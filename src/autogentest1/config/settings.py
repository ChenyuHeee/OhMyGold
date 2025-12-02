"""Application settings loaded from environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, List

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


def _lenient_json_loads(value: str) -> Any:
    """Parse JSON values for settings while tolerating plain strings."""

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


class Settings(BaseSettings):
    """Central configuration for the AutoGen agents and services."""

    deepseek_api_key: str = Field(...)
    deepseek_model: str = Field("deepseek-chat")
    deepseek_base_url: str = Field("https://api.deepseek.com/v1")
    data_provider: str = Field("yfinance")
    default_symbol: str = Field("XAUUSD")
    default_days: int = Field(14)
    log_level: str = Field("INFO")
    max_position_oz: float = Field(5000.0)
    stress_var_millions: float = Field(3.0)
    daily_drawdown_pct: float = Field(3.0)
    default_position_oz: float = Field(0.0)
    pnl_today_millions: float = Field(0.0)
    local_model_enabled: bool = Field(False)
    local_model_name: str | None = Field("qwen2.5-14b-instruct")
    local_model_base_url: str | None = Field("http://127.0.0.1:11434/v1")
    local_model_api_key: str | None = Field(None)
    local_model_agents: List[str] = Field(default_factory=list)
    alpha_vantage_api_key: str | None = Field(
        None,
        validation_alias=AliasChoices("alpha_vantage_api_key", "alphavantage_api_key", "ALPHAVANTAGE_API_KEY"),
    )
    news_api_key: str | None = Field(None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @classmethod
    def settings_json_loads(cls, value: str) -> Any:
        """Decode JSON values from env while tolerating plain comma-separated lists."""

        return _lenient_json_loads(value)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Disable strict JSON decoding for environment-backed sources."""

        for source in (env_settings, dotenv_settings):
            if hasattr(source, "config"):
                source.config["enable_decoding"] = False

        return init_settings, env_settings, dotenv_settings, file_secret_settings

    @field_validator("local_model_agents", mode="before")
    @classmethod
    def _parse_local_model_agents(cls, value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str) and item.strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @model_validator(mode="before")
    @classmethod
    def _map_legacy_env_keys(cls, data: Any) -> Any:
        if isinstance(data, dict) and "alphavantage_api_key" in data and "alpha_vantage_api_key" not in data:
            data = dict(data)
            data["alpha_vantage_api_key"] = data.pop("alphavantage_api_key")
        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once and cache the instance for reuse."""

    return Settings()  # type: ignore[call-arg]
