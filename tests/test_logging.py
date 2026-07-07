"""Tests for EAG structured logging."""

import json

import pytest

from eag.config import LoggingSettings
from eag.logging import configure_logging, get_logger


def test_console_logging(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(
        LoggingSettings(
            level="INFO",
            json_output=False,
        )
    )

    logger = get_logger(component="test")
    logger.info("test_event", value=42)

    captured = capsys.readouterr()

    assert "test_event" in captured.out
    assert "component" in captured.out
    assert "test" in captured.out


def test_json_logging(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(
        LoggingSettings(
            level="INFO",
            json_output=True,
        )
    )

    logger = get_logger(component="test")
    logger.info("test_event", value=42)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["event"] == "test_event"
    assert payload["component"] == "test"
    assert payload["value"] == 42
    assert payload["level"] == "info"


def test_log_level_filtering(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(
        LoggingSettings(
            level="WARNING",
            json_output=True,
        )
    )

    logger = get_logger(component="test")

    logger.info("hidden_event")
    logger.warning("visible_event")

    captured = capsys.readouterr()

    assert "hidden_event" not in captured.out
    assert "visible_event" in captured.out