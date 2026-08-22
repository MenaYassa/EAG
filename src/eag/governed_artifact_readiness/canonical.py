"""Canonical serialization and validation utilities for artifact readiness evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
from typing import Any

ARTIFACT_READINESS_SCHEMA_VERSION = "g2.4.14"


class ArtifactReadinessCanonicalError(ValueError):
    """Raised when canonical artifact readiness evidence is malformed."""


def require_non_empty(value: str, field_name: str) -> str:
    """Return one required non-empty string without coercion."""
    if not isinstance(value, str) or not value.strip():
        raise ArtifactReadinessCanonicalError(f"{field_name} cannot be empty")
    return value


def require_sha256(value: str, field_name: str) -> str:
    """Return one lowercase SHA-256 digest or raise a deterministic contract error."""
    require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ArtifactReadinessCanonicalError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def require_relative_path(value: str, field_name: str) -> str:
    """Reject absolute, empty, traversal, and platform-ambiguous evidence paths."""
    require_non_empty(value, field_name)
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or value.startswith("./"):
        raise ArtifactReadinessCanonicalError(f"{field_name} must be a safe relative POSIX path")
    if str(candidate) in {".", ""} or "\\" in value:
        raise ArtifactReadinessCanonicalError(f"{field_name} must be a safe relative POSIX path")
    return value


def canonical_digest(payload: dict[str, Any]) -> str:
    """Return the SHA-256 digest of an exact canonical JSON payload."""
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ARTIFACT_READINESS_SCHEMA_VERSION",
    "ArtifactReadinessCanonicalError",
    "canonical_digest",
    "require_non_empty",
    "require_relative_path",
    "require_sha256",
]
