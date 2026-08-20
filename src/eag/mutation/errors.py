"""Typed, sanitized errors for deterministic governed mutation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MutationViolationCode(StrEnum):
    """Stable reasons for deterministic mutation rejection or failure."""

    MALFORMED_PROPOSAL = "malformed_proposal"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    ABSOLUTE_PATH = "absolute_path"
    PATH_TRAVERSAL = "path_traversal"
    PATH_ESCAPE = "path_escape"
    SYMLINK_PATH = "symlink_path"
    SENSITIVE_PATH = "sensitive_path"
    SENSITIVE_CONTENT = "sensitive_content"
    PARENT_MISSING = "parent_missing"
    TARGET_NOT_REGULAR_FILE = "target_not_regular_file"
    CONTENT_TOO_LARGE = "content_too_large"
    TARGET_TOO_LARGE = "target_too_large"
    CREATE_TARGET_EXISTS = "create_target_exists"
    MODIFY_TARGET_MISSING = "modify_target_missing"
    PRECONDITION_STALE = "precondition_stale"
    PRECONDITION_MISMATCH = "precondition_mismatch"
    AUTHORIZATION_REJECTED = "authorization_rejected"
    AUTHORIZATION_MISMATCH = "authorization_mismatch"
    AUTHORIZATION_REUSED = "authorization_reused"
    POSTCONDITION_MISMATCH = "postcondition_mismatch"
    WRITE_FAILED = "write_failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationViolation:
    """Redacted deterministic violation without source content, host paths, or secrets."""

    code: MutationViolationCode
    stage: str
    message: str
    target_path: str | None = None
    policy_version: str = "1.0"


class MutationError(ValueError):
    """Base class for expected governed mutation errors."""


class MutationPolicyError(MutationError):
    """Raised when an untrusted proposal violates deterministic mutation policy."""

    def __init__(self, violation: MutationViolation) -> None:
        super().__init__(violation.message)
        self.violation = violation


class MutationAuthorizationError(MutationError):
    """Raised when one-time proposal-bound authorization is absent, stale, or mismatched."""

    def __init__(self, violation: MutationViolation) -> None:
        super().__init__(violation.message)
        self.violation = violation
