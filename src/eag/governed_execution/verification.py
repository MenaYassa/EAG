"""Trusted deterministic G2.4.2 verification boundary.

This module is intentionally read-only.  It evaluates one trusted specification
against one confined workspace target and never executes commands, mutates a
workspace, calls a provider, or changes mutation authority.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eag.governed_execution.enums import ExecutionEvidenceKind
from eag.governed_execution.models import (
    ExecutionEvidenceRef,
    GovernedExecutionContext,
)

if TYPE_CHECKING:
    from eag.mutation.models import MutationReceipt

VERIFICATION_CONTRACT_VERSION = "1.0"


class VerificationCheck(StrEnum):
    """The only bounded, trusted assertions supported in G2.4.2."""

    EXACT_CONTENT = "exact_content"
    FILE_EXISTS = "file_exists"
    FILE_ABSENT = "file_absent"
    EXPECTED_FINGERPRINT = "expected_fingerprint"


class VerificationStatus(StrEnum):
    """Outcome of a trusted verification attempt, distinct from mutation outcome."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


class VerificationFailureCode(StrEnum):
    """Safe stable result reasons with no provider-controlled wording."""

    MUTATION_NOT_SUCCESSFUL = "mutation_not_successful"
    TARGET_PATH_MISMATCH = "target_path_mismatch"
    TARGET_OUTSIDE_WORKSPACE = "target_outside_workspace"
    TARGET_SYMLINK = "target_symlink"
    TARGET_TOO_LARGE = "target_too_large"
    TARGET_READ_FAILED = "target_read_failed"
    ASSERTION_FAILED = "assertion_failed"


class ObjectiveStatus(StrEnum):
    """Deterministic completion-policy assessment independent of verifier status."""

    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"


class ObjectiveFailureCode(StrEnum):
    """Typed reasons why verified evidence cannot establish objective success."""

    MUTATION_NOT_SUCCESSFUL = "mutation_not_successful"
    VERIFICATION_NOT_PASSED = "verification_not_passed"


class VerificationRequestError(ValueError):
    """Raised for malformed or unsupported trusted verification requests."""


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationSpecification:
    """Trusted bounded assertion selected outside all provider output."""

    specification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_path: str
    check: VerificationCheck
    expected_content: str | None = None
    expected_fingerprint: str | None = None
    max_bytes: int = 65_536
    version: str = VERIFICATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.specification_id.strip():
            raise VerificationRequestError("specification_id cannot be empty")
        _validate_relative_path(self.target_path)
        if not isinstance(self.check, VerificationCheck):
            raise VerificationRequestError("unsupported verification check")
        if not isinstance(self.max_bytes, int) or isinstance(self.max_bytes, bool) or self.max_bytes < 1:
            raise VerificationRequestError("max_bytes must be a positive integer")
        if self.version != VERIFICATION_CONTRACT_VERSION:
            raise VerificationRequestError("unsupported verification contract version")
        if self.check is VerificationCheck.EXACT_CONTENT:
            if not isinstance(self.expected_content, str):
                raise VerificationRequestError("exact_content requires expected_content")
            if len(self.expected_content.encode("utf-8")) > self.max_bytes:
                raise VerificationRequestError("expected_content exceeds max_bytes")
            if self.expected_fingerprint is not None:
                raise VerificationRequestError("exact_content cannot declare expected_fingerprint")
        elif self.check is VerificationCheck.EXPECTED_FINGERPRINT:
            if not self.expected_fingerprint:
                raise VerificationRequestError("expected_fingerprint requires expected_fingerprint")
            if self.expected_content is not None:
                raise VerificationRequestError("expected_fingerprint cannot declare expected_content")
        elif self.expected_content is not None or self.expected_fingerprint is not None:
            raise VerificationRequestError("existence checks cannot declare expected content or fingerprint")


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationRequest:
    """One trusted request binding a completed receipt to one specification."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    receipt: MutationReceipt
    specification: VerificationSpecification
    execution_context: GovernedExecutionContext | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip() or not self.run_id.strip():
            raise VerificationRequestError("request_id and run_id cannot be empty")
        if not _is_receipt_evidence(self.receipt):
            raise VerificationRequestError("receipt must provide immutable mutation receipt evidence")
        if not isinstance(self.specification, VerificationSpecification):
            raise VerificationRequestError("specification must be a VerificationSpecification")
        if self.run_id != self.receipt.run_id:
            raise VerificationRequestError("request run_id must match receipt run_id")
        if self.specification.target_path != self.receipt.target_path:
            raise VerificationRequestError("specification target_path must match receipt target_path")
        if self.execution_context is not None:
            if not isinstance(self.execution_context, GovernedExecutionContext):
                raise VerificationRequestError("execution_context must be a GovernedExecutionContext")
            if self.execution_context.run_id != self.run_id:
                raise VerificationRequestError("execution context run_id must match request run_id")


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationEvidence:
    """Redacted observation of one deterministic read-only assertion."""

    target_path: str
    check: VerificationCheck
    observed_exists: bool
    observed_fingerprint: str | None
    observed_bytes: int

    def __post_init__(self) -> None:
        _validate_relative_path(self.target_path)
        if not isinstance(self.check, VerificationCheck):
            raise TypeError("check must be a VerificationCheck")
        if self.observed_fingerprint is not None and len(self.observed_fingerprint) != 64:
            raise ValueError("observed_fingerprint must be a SHA-256 digest")
        if not isinstance(self.observed_bytes, int) or self.observed_bytes < 0:
            raise ValueError("observed_bytes must be a non-negative integer")


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationResult:
    """Immutable trusted outcome, separate from mutation receipt and objective success."""

    verification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    run_id: str
    receipt_id: str
    specification_id: str
    status: VerificationStatus
    evidence: VerificationEvidence | None
    failure_code: VerificationFailureCode | None = None
    version: str = VERIFICATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for field_name in ("verification_id", "request_id", "run_id", "receipt_id", "specification_id"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty")
        if not isinstance(self.status, VerificationStatus):
            raise TypeError("status must be a VerificationStatus")
        if self.evidence is not None and not isinstance(self.evidence, VerificationEvidence):
            raise TypeError("evidence must be a VerificationEvidence or None")
        if self.failure_code is not None and not isinstance(self.failure_code, VerificationFailureCode):
            raise TypeError("failure_code must be a VerificationFailureCode or None")
        if self.status is VerificationStatus.PASSED and self.failure_code is not None:
            raise ValueError("passed verification cannot carry failure_code")
        if self.status is VerificationStatus.FAILED and self.failure_code is None:
            raise ValueError("failed verification requires failure_code")
        if self.status is VerificationStatus.NOT_RUN and self.failure_code is None:
            raise ValueError("not_run verification requires failure_code")
        if self.version != VERIFICATION_CONTRACT_VERSION:
            raise ValueError("unsupported verification contract version")

    @property
    def evidence_ref(self) -> ExecutionEvidenceRef:
        """Return a redacted G2.4.1 ledger reference without raw content."""
        metadata = {"status": self.status.value}
        if self.failure_code is not None:
            metadata["failure_code"] = self.failure_code.value
        return ExecutionEvidenceRef(
            kind=ExecutionEvidenceKind.VERIFICATION,
            reference_id=self.verification_id,
            digest=(
                self.evidence.observed_fingerprint
                if self.evidence is not None and self.evidence.observed_fingerprint is not None
                else ""
            ),
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ObjectiveAssessment:
    """Pure completion-policy evidence; this object never changes state."""

    status: ObjectiveStatus
    verification_id: str
    receipt_id: str
    failure_code: ObjectiveFailureCode | None = None

    def __post_init__(self) -> None:
        if not self.verification_id.strip() or not self.receipt_id.strip():
            raise ValueError("verification_id and receipt_id cannot be empty")
        if self.status is ObjectiveStatus.SATISFIED and self.failure_code is not None:
            raise ValueError("satisfied objective cannot have failure_code")
        if self.status is ObjectiveStatus.NOT_SATISFIED and self.failure_code is None:
            raise ValueError("unsatisfied objective requires failure_code")


class DeterministicVerifier:
    """Evaluate exactly one trusted specification using confined read-only file access."""

    def __init__(self, *, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=True)
        if not self._workspace_root.is_dir():
            raise VerificationRequestError("workspace_root must be a directory")

    def verify(self, request: VerificationRequest) -> VerificationResult:
        """Return immutable pass, fail, or not-run evidence without raising operational effects."""
        if not _mutation_succeeded(request.receipt):
            return self._result(
                request,
                status=VerificationStatus.NOT_RUN,
                failure_code=VerificationFailureCode.MUTATION_NOT_SUCCESSFUL,
                evidence=None,
            )
        target, path_error = self._confined_target(request.specification.target_path)
        if path_error is not None:
            return self._result(
                request,
                status=VerificationStatus.FAILED,
                failure_code=path_error,
                evidence=None,
            )
        assert target is not None
        evidence, read_error = self._observe(target, request.specification)
        if read_error is not None:
            return self._result(
                request,
                status=VerificationStatus.FAILED,
                failure_code=read_error,
                evidence=evidence,
            )
        assert evidence is not None
        passed = _evaluate(request.specification, target, evidence)
        return self._result(
            request,
            status=VerificationStatus.PASSED if passed else VerificationStatus.FAILED,
            failure_code=None if passed else VerificationFailureCode.ASSERTION_FAILED,
            evidence=evidence,
        )

    def _confined_target(
        self,
        target_path: str,
    ) -> tuple[Path | None, VerificationFailureCode | None]:
        try:
            _validate_relative_path(target_path)
        except VerificationRequestError:
            return None, VerificationFailureCode.TARGET_OUTSIDE_WORKSPACE
        current = self._workspace_root
        for part in Path(target_path).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                return None, VerificationFailureCode.TARGET_SYMLINK
        resolved = current.resolve(strict=False)
        if resolved != self._workspace_root and self._workspace_root not in resolved.parents:
            return None, VerificationFailureCode.TARGET_OUTSIDE_WORKSPACE
        return current, None

    @staticmethod
    def _observe(
        target: Path,
        specification: VerificationSpecification,
    ) -> tuple[VerificationEvidence | None, VerificationFailureCode | None]:
        exists = target.exists()
        if specification.check is VerificationCheck.FILE_ABSENT:
            return (
                VerificationEvidence(
                    target_path=specification.target_path,
                    check=specification.check,
                    observed_exists=exists,
                    observed_fingerprint=None,
                    observed_bytes=0,
                ),
                None,
            )
        if not exists:
            return (
                VerificationEvidence(
                    target_path=specification.target_path,
                    check=specification.check,
                    observed_exists=False,
                    observed_fingerprint=None,
                    observed_bytes=0,
                ),
                None,
            )
        if not target.is_file():
            return None, VerificationFailureCode.TARGET_READ_FAILED
        try:
            size = target.stat().st_size
            if size > specification.max_bytes:
                return None, VerificationFailureCode.TARGET_TOO_LARGE
            content = target.read_bytes()
        except OSError:
            return None, VerificationFailureCode.TARGET_READ_FAILED
        return (
            VerificationEvidence(
                target_path=specification.target_path,
                check=specification.check,
                observed_exists=True,
                observed_fingerprint=hashlib.sha256(content).hexdigest(),
                observed_bytes=len(content),
            ),
            None,
        )

    @staticmethod
    def _result(
        request: VerificationRequest,
        *,
        status: VerificationStatus,
        failure_code: VerificationFailureCode | None,
        evidence: VerificationEvidence | None,
    ) -> VerificationResult:
        return VerificationResult(
            request_id=request.request_id,
            run_id=request.run_id,
            receipt_id=request.receipt.mutation_id,
            specification_id=request.specification.specification_id,
            status=status,
            evidence=evidence,
            failure_code=failure_code,
        )


class ObjectiveCompletionPolicy:
    """Accept objective success only from successful mutation and trusted pass evidence."""

    @staticmethod
    def assess(
        receipt: MutationReceipt,
        verification: VerificationResult,
    ) -> ObjectiveAssessment:
        if receipt.mutation_id != verification.receipt_id:
            raise VerificationRequestError("verification receipt_id must match supplied receipt")
        if not _mutation_succeeded(receipt):
            return ObjectiveAssessment(
                status=ObjectiveStatus.NOT_SATISFIED,
                verification_id=verification.verification_id,
                receipt_id=receipt.mutation_id,
                failure_code=ObjectiveFailureCode.MUTATION_NOT_SUCCESSFUL,
            )
        if verification.status is not VerificationStatus.PASSED:
            return ObjectiveAssessment(
                status=ObjectiveStatus.NOT_SATISFIED,
                verification_id=verification.verification_id,
                receipt_id=receipt.mutation_id,
                failure_code=ObjectiveFailureCode.VERIFICATION_NOT_PASSED,
            )
        return ObjectiveAssessment(
            status=ObjectiveStatus.SATISFIED,
            verification_id=verification.verification_id,
            receipt_id=receipt.mutation_id,
        )


def _is_receipt_evidence(value: Any) -> bool:
    """Validate the fixed redacted evidence surface of a G2.3.1 receipt."""
    required = ("mutation_id", "run_id", "target_path", "result", "verification_passed")
    if any(not hasattr(value, field_name) for field_name in required):
        return False
    if not isinstance(value.mutation_id, str) or not value.mutation_id.strip():
        return False
    if not isinstance(value.run_id, str) or not value.run_id.strip():
        return False
    if not isinstance(value.target_path, str) or not value.target_path.strip():
        return False
    return isinstance(value.verification_passed, bool) and getattr(value.result, "value", None) in {
        "completed",
        "rejected",
        "failed",
    }


def _mutation_succeeded(receipt: MutationReceipt) -> bool:
    """Recognize only the existing receipt's completed postcondition outcome."""
    return getattr(receipt.result, "value", None) == "completed" and receipt.verification_passed


def _evaluate(
    specification: VerificationSpecification,
    target: Path,
    evidence: VerificationEvidence,
) -> bool:
    if specification.check is VerificationCheck.FILE_EXISTS:
        return evidence.observed_exists
    if specification.check is VerificationCheck.FILE_ABSENT:
        return not evidence.observed_exists
    if not evidence.observed_exists:
        return False
    if specification.check is VerificationCheck.EXPECTED_FINGERPRINT:
        return evidence.observed_fingerprint == specification.expected_fingerprint
    if specification.check is VerificationCheck.EXACT_CONTENT:
        try:
            return target.read_text(encoding="utf-8") == specification.expected_content
        except (OSError, UnicodeDecodeError):
            return False
    raise AssertionError("validated verification check was not evaluated")


def _validate_relative_path(target_path: str) -> None:
    if not isinstance(target_path, str) or not target_path.strip():
        raise VerificationRequestError("target_path cannot be empty")
    path = Path(target_path)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise VerificationRequestError("target_path must be a confined relative path")


__all__ = [
    "DeterministicVerifier",
    "ObjectiveAssessment",
    "ObjectiveCompletionPolicy",
    "ObjectiveFailureCode",
    "ObjectiveStatus",
    "VERIFICATION_CONTRACT_VERSION",
    "VerificationCheck",
    "VerificationEvidence",
    "VerificationFailureCode",
    "VerificationRequest",
    "VerificationRequestError",
    "VerificationResult",
    "VerificationSpecification",
    "VerificationStatus",
]
