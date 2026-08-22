"""Canonical serialization utilities for G2.4.15 promotion eligibility evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

PROMOTION_SCHEMA_VERSION = "g2.4.15"


class PromotionCanonicalError(ValueError):
    """Raised when promotion evidence is structurally non-canonical."""


def require_non_empty(value: str, field_name: str) -> str:
    """Require one non-empty string without coercion."""
    if not isinstance(value, str) or not value.strip():
        raise PromotionCanonicalError(f"{field_name} cannot be empty")
    return value


def require_sha256(value: str, field_name: str) -> str:
    """Require one lowercase SHA-256 digest."""
    require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise PromotionCanonicalError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def canonical_timestamp(value: datetime, field_name: str) -> datetime:
    """Normalize one timezone-aware timestamp to UTC."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PromotionCanonicalError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def canonical_digest(payload: dict[str, Any]) -> str:
    """Calculate one deterministic SHA-256 digest over canonical JSON."""
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


__all__ = [
    "PROMOTION_SCHEMA_VERSION",
    "PromotionCanonicalError",
    "canonical_digest",
    "canonical_timestamp",
    "require_non_empty",
    "require_sha256",
]
