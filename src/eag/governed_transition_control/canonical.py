"""Canonical immutable-evidence utilities for G2.4.17 transition control."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

TRANSITION_CONTROL_SCHEMA_VERSION = "g2.4.17.transition-control.v1"


class TransitionControlEvidenceError(ValueError):
    """Raised when transition-control evidence cannot be canonicalized safely."""


def require_non_empty(value: object, field_name: str) -> str:
    """Require a non-empty string without transforming semantic identity."""
    if not isinstance(value, str) or not value.strip():
        raise TransitionControlEvidenceError(f"{field_name} must be a non-empty string")
    return value


def require_sha256(value: object, field_name: str) -> str:
    """Require a lower-case SHA-256 hexadecimal digest."""
    value = require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise TransitionControlEvidenceError(f"{field_name} must be a lower-case SHA-256 digest")
    return value


def canonical_timestamp(value: object, field_name: str) -> datetime:
    """Normalize one aware timestamp to UTC with no external clock access."""
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise TransitionControlEvidenceError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def canonical_digest(payload: object) -> str:
    """Return a deterministic SHA-256 digest for JSON-compatible evidence only."""
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise TransitionControlEvidenceError("evidence payload is not canonical JSON") from error
    return hashlib.sha256(encoded).hexdigest()


def control_key_digest(*, transition_identity: object) -> str:
    """Derive the durable key from exact canonical authorized transition identity.

    Caller-supplied idempotency text is deliberately excluded from this authority.
    It may remain in full request evidence for traceability, but it cannot create a
    second durable identity for the same authorized transition.
    """
    if not isinstance(transition_identity, dict):
        raise TransitionControlEvidenceError("transition_identity must be a mapping")
    return canonical_digest(
        {
            "schema_version": TRANSITION_CONTROL_SCHEMA_VERSION,
            "transition_identity": transition_identity,
        }
    )


def canonical_json_mapping(payload: object) -> dict[str, Any]:
    """Validate a durable JSON object before contract-level parsing."""
    if not isinstance(payload, dict):
        raise TransitionControlEvidenceError("durable payload must be a JSON object")
    return payload
