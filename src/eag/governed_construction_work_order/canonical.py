"""Canonical immutable-evidence utilities for G2.4.21 construction work orders."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION = "g2.4.21.local-construction-work-order.v1"
CONSTRUCTION_WORK_ORDER_ASSESSMENT_SCHEMA_VERSION = "g2.4.21.construction-work-order-assessment.v2"


class ConstructionWorkOrderEvidenceError(ValueError):
    """Raised when construction work-order evidence is malformed or inconsistent."""


def require_non_empty(value: object, field_name: str) -> str:
    """Require non-empty declaration text without accepting operational handles."""
    if not isinstance(value, str) or not value.strip():
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a non-empty string")
    return value


def require_identifier(value: object, field_name: str) -> str:
    """Require a compact deterministic identifier free of endpoint syntax."""
    text = require_non_empty(value, field_name)
    if any(character.isspace() for character in text) or "://" in text or "/" in text:
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a compact identifier")
    return text


def require_sha256(value: object, field_name: str) -> str:
    """Require one lowercase SHA-256 digest."""
    text = require_non_empty(value, field_name)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def require_positive_int(value: object, field_name: str) -> int:
    """Require one positive static limit; zero and booleans are invalid."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a positive integer")
    return value


def require_nonnegative_int(value: object, field_name: str) -> int:
    """Require one nonnegative static declaration limit."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a nonnegative integer")
    return value


def canonical_timestamp(value: object, field_name: str) -> datetime:
    """Return one timezone-aware UTC timestamp."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a timezone-aware datetime")
    return value.astimezone(UTC)


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize exact evidence deterministically."""
    try:
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as error:
        raise ConstructionWorkOrderEvidenceError("evidence payload is not canonical JSON") from error


def canonical_digest(payload: dict[str, Any]) -> str:
    """Return the SHA-256 digest of canonical evidence JSON."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


__all__ = [
    "CONSTRUCTION_WORK_ORDER_ASSESSMENT_SCHEMA_VERSION",
    "CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION",
    "ConstructionWorkOrderEvidenceError",
    "canonical_digest",
    "canonical_json",
    "canonical_timestamp",
    "require_identifier",
    "require_non_empty",
    "require_nonnegative_int",
    "require_positive_int",
    "require_sha256",
]
