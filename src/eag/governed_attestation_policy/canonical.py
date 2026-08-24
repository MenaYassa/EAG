"""Canonical immutable-evidence utilities for G2.4.20 attestation policy."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

ATTESTATION_POLICY_SCHEMA_VERSION = "g2.4.20.destination-contract-attestation-policy.v1"


class AttestationPolicyEvidenceError(ValueError):
    """Raised when attestation-policy evidence is structurally unsafe or inconsistent."""


def require_non_empty(value: object, field_name: str) -> str:
    """Require one non-empty text value without accepting operational handles."""
    if not isinstance(value, str) or not value.strip():
        raise AttestationPolicyEvidenceError(f"{field_name} must be a non-empty string")
    return value


def require_identifier(value: object, field_name: str) -> str:
    """Require a deterministic identifier free of whitespace and endpoint syntax."""
    text = require_non_empty(value, field_name)
    if any(character.isspace() for character in text) or "://" in text or "/" in text:
        raise AttestationPolicyEvidenceError(f"{field_name} must be a compact identifier")
    return text


def require_sha256(value: object, field_name: str) -> str:
    """Require one lowercase SHA-256 digest."""
    text = require_non_empty(value, field_name)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise AttestationPolicyEvidenceError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def canonical_timestamp(value: object, field_name: str) -> datetime:
    """Return a timezone-aware UTC timestamp."""
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise AttestationPolicyEvidenceError(f"{field_name} must be a timezone-aware datetime")
    return value.astimezone(UTC)


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize exact evidence deterministically."""
    try:
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as error:
        raise AttestationPolicyEvidenceError("evidence payload is not canonical JSON") from error


def canonical_digest(payload: dict[str, Any]) -> str:
    """Return the SHA-256 digest of canonical evidence JSON."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


__all__ = [
    "ATTESTATION_POLICY_SCHEMA_VERSION",
    "AttestationPolicyEvidenceError",
    "canonical_digest",
    "canonical_json",
    "canonical_timestamp",
    "require_identifier",
    "require_non_empty",
    "require_sha256",
]
