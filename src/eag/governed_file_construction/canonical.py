"""Canonical serialization helpers for the bounded G2.4.22 file-construction boundary."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

CONSTRUCTION_ACTION_PLAN_SCHEMA_VERSION = "g2.4.22.construction-action-plan.v1"
CONSTRUCTION_AUTHORIZATION_SCHEMA_VERSION = "g2.4.22.construction-authorization.v1"
CONSTRUCTION_RECEIPT_SCHEMA_VERSION = "g2.4.22.construction-receipt.v1"
CONSTRUCTION_PROFILE = "attested_empty_workspace_create_only_v1"


class ConstructionEvidenceError(ValueError):
    """Raised when a construction contract is not strict canonical evidence."""


def canonical_digest(payload: dict[str, object]) -> str:
    """Return the deterministic SHA-256 identity of one JSON-compatible payload."""
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def require_identifier(value: str, field_name: str) -> str:
    """Require a stable non-empty textual identity."""
    if not isinstance(value, str) or not value.strip():
        raise ConstructionEvidenceError(f"{field_name} must be a non-empty string")
    return value


def require_sha256(value: str, field_name: str) -> str:
    """Require a lowercase SHA-256 digest."""
    if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ConstructionEvidenceError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def canonical_timestamp(value: datetime, field_name: str) -> datetime:
    """Require and normalize a timezone-aware timestamp to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ConstructionEvidenceError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def utf8_bytes(value: str, field_name: str) -> bytes:
    """Return strict UTF-8 bytes for an immutable literal content field."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a str")
    try:
        return value.encode("utf-8", "strict")
    except UnicodeError as error:
        raise ConstructionEvidenceError(f"{field_name} must be strict UTF-8") from error


__all__ = [
    "CONSTRUCTION_ACTION_PLAN_SCHEMA_VERSION",
    "CONSTRUCTION_AUTHORIZATION_SCHEMA_VERSION",
    "CONSTRUCTION_PROFILE",
    "CONSTRUCTION_RECEIPT_SCHEMA_VERSION",
    "ConstructionEvidenceError",
    "canonical_digest",
    "canonical_timestamp",
    "require_identifier",
    "require_sha256",
    "utf8_bytes",
]
