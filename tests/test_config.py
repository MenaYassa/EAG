"""Tests for EAG configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from eag.config import Settings


def test_default_settings() -> None:
    settings = Settings()

    assert settings.kernel.name == "EAG"
    assert settings.kernel.environment == "development"
    assert settings.logging.level == "INFO"
    assert settings.logging.json_output is False


def test_nested_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "EAG_KERNEL__ENVIRONMENT",
        "production",
    )
    monkeypatch.setenv(
        "EAG_LOGGING__LEVEL",
        "DEBUG",
    )
    monkeypatch.setenv(
        "EAG_LOGGING__JSON_OUTPUT",
        "true",
    )

    settings = Settings()

    assert settings.kernel.environment == "production"
    assert settings.logging.level == "DEBUG"
    assert settings.logging.json_output is True


def test_settings_are_immutable() -> None:
    settings = Settings()

    with pytest.raises(ValidationError):
        settings.logging.level = "DEBUG"  # type: ignore[misc]


def test_workspace_accepts_path() -> None:
    workspace = Path("/tmp/eag-test")

    settings = Settings(
        kernel={
            "workspace": workspace,
        }
    )

    assert settings.kernel.workspace == workspace
