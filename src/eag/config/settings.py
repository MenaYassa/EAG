"""Typed configuration models for EAG."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(frozen=True)

    level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    json_output: bool = False


class KernelSettings(BaseModel):
    """Kernel configuration."""

    model_config = ConfigDict(frozen=True)

    name: str = "EAG"
    environment: Literal[
        "development",
        "testing",
        "production",
    ] = "development"

    workspace: Path = Field(
        default_factory=Path.cwd,
    )


class GatewaySettings(BaseModel):
    """Configuration for an explicitly enabled governed LLM gateway."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    provider_id: str = "litellm"
    model_id: str = "gpt-5-mini"
    api_key: SecretStr | None = None
    api_base: str | None = None
    timeout_ms: int = 30_000
    max_attempts: int = 2
    max_total_tokens: int = 8_000
    max_estimated_cost: float = 1.0
    allow_fallback: bool = True


class Settings(BaseSettings):
    """Root EAG application settings."""

    model_config = SettingsConfigDict(
        env_prefix="EAG_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    kernel: KernelSettings = Field(
        default_factory=KernelSettings,
    )

    logging: LoggingSettings = Field(
        default_factory=LoggingSettings,
    )

    gateway: GatewaySettings = Field(
        default_factory=GatewaySettings,
    )
