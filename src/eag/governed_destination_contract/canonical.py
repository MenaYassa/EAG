"""Canonical immutable-evidence utilities for G2.4.18 destination contracts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime

DESTINATION_CONTRACT_SCHEMA_VERSION = "g2.4.18.destination-contract.v1"


class DestinationContractEvidenceError(ValueError):
    """Raised when destination-contract evidence is structurally unsafe."""


def require_non_empty(value: object, field_name: str) -> str:
    """Require one non-empty string without changing its semantic identity."""
    if not isinstance(value, str) or not value.strip():
        raise DestinationContractEvidenceError(f"{field_name} must be a non-empty string")
    return value


def require_identifier(value: object, field_name: str) -> str:
    """Require one bounded declaration identifier with no URL or secret syntax."""
    value = require_non_empty(value, field_name)
    if len(value) > 160 or re.fullmatch(r"[a-z0-9][a-z0-9._:-]{2,159}", value) is None:
        raise DestinationContractEvidenceError(f"{field_name} must be a canonical declaration identifier")
    lowered = value.lower()
    forbidden = ("://", "@", "token", "secret", "password", "credential", "bearer", "header")
    if any(marker in lowered for marker in forbidden):
        raise DestinationContractEvidenceError(f"{field_name} must not contain endpoint or secret material")
    return value


def require_sha256(value: object, field_name: str) -> str:
    """Require one lower-case SHA-256 hexadecimal digest."""
    value = require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise DestinationContractEvidenceError(f"{field_name} must be a lower-case SHA-256 digest")
    return value


def canonical_timestamp(value: object, field_name: str) -> datetime:
    """Normalize one timezone-aware timestamp to UTC without reading a clock."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise DestinationContractEvidenceError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def canonical_digest(payload: object) -> str:
    """Return a deterministic SHA-256 digest for canonical JSON evidence."""
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise DestinationContractEvidenceError("evidence payload is not canonical JSON") from error
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "DESTINATION_CONTRACT_SCHEMA_VERSION",
    "DestinationContractEvidenceError",
    "canonical_digest",
    "canonical_timestamp",
    "require_identifier",
    "require_non_empty",
    "require_sha256",
]
