"""Immutable contracts for G2.4.22 bounded descriptor-relative file construction."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath

from eag.governed_construction_work_order import (
    ConstructionWorkOrderAssessment,
    ConstructionWorkOrderAssessmentRequest,
)
from eag.governed_file_construction.canonical import (
    CONSTRUCTION_ACTION_PLAN_SCHEMA_VERSION,
    CONSTRUCTION_AUTHORIZATION_SCHEMA_VERSION,
    CONSTRUCTION_PROFILE,
    CONSTRUCTION_RECEIPT_SCHEMA_VERSION,
    ConstructionEvidenceError,
    canonical_digest,
    canonical_timestamp,
    require_identifier,
    require_sha256,
    utf8_bytes,
)
from eag.governed_workspace import (
    WorkspaceCustodyAttestation,
    WorkspaceCustodyRequest,
    WorkspaceCustodyRootBinding,
)


class ConstructionActionKind(StrEnum):
    """The sole G2.4.22 action kind."""

    CREATE_TEXT_FILE = "create_text_file"


class ConstructionAuthorizationDisposition(StrEnum):
    """Pre-effect construction decision; not a session, permit, or generic capability."""

    ATTESTED = "attested"
    REFUSED = "refused"


class ConstructionFindingCode(StrEnum):
    """Typed fail-closed construction findings."""

    ASSESSMENT_INVALID = "construction_work_order_assessment_invalid"
    REQUEST_PROVENANCE_MISMATCH = "construction_work_order_request_provenance_mismatch"
    ASSESSMENT_NOT_ATTESTED = "construction_work_order_assessment_not_attested"
    WORK_ORDER_BINDING_MISMATCH = "work_order_binding_mismatch"
    PLAN_BINDING_MISMATCH = "plan_binding_mismatch"
    PLAN_LIMIT_EXCEEDED = "plan_limit_exceeded"
    CUSTODY_HANDOFF_MISMATCH = "custody_handoff_mismatch"
    HANDLE_REJECTED = "custody_root_handle_rejected"
    CONSTRUCTION_CAPABILITY_UNSUPPORTED = "construction_capability_unsupported"
    PATH_UNSAFE = "path_unsafe"
    TARGET_EXISTS = "target_exists"
    FILESYSTEM_FAILURE = "filesystem_failure"
    POSTWRITE_VERIFICATION_FAILED = "postwrite_verification_failed"


class ConstructionBatchDisposition(StrEnum):
    """Terminal local construction state; no value asserts application readiness."""

    CONSTRUCTION_FILES_CREATED = "construction_files_created"
    CONSTRUCTION_REFUSED = "construction_refused"
    PARTIAL_CONSTRUCTION_STOPPED = "partial_construction_stopped"


class ConstructionActionDisposition(StrEnum):
    """One receipt disposition for an actual attempted effect."""

    CREATED = "created"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionFileAction:
    """One declared create-only UTF-8 regular-file effect."""

    sequence: int
    relative_path: str
    content: str
    content_digest: str | None = None
    byte_count: int | None = None
    kind: ConstructionActionKind = ConstructionActionKind.CREATE_TEXT_FILE

    def __post_init__(self) -> None:
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 1:
            raise ConstructionEvidenceError("sequence must be a positive int")
        if self.kind is not ConstructionActionKind.CREATE_TEXT_FILE:
            raise ConstructionEvidenceError("only create_text_file actions are supported")
        object.__setattr__(self, "relative_path", _normalized_relative_path(self.relative_path))
        encoded = utf8_bytes(self.content, "content")
        digest = hashlib.sha256(encoded).hexdigest()
        if self.content_digest is None:
            object.__setattr__(self, "content_digest", digest)
        else:
            object.__setattr__(self, "content_digest", require_sha256(self.content_digest, "content_digest"))
            if self.content_digest != digest:
                raise ConstructionEvidenceError("content_digest does not match literal UTF-8 content")
        if self.byte_count is None:
            object.__setattr__(self, "byte_count", len(encoded))
        elif not isinstance(self.byte_count, int) or isinstance(self.byte_count, bool) or self.byte_count < 0:
            raise ConstructionEvidenceError("byte_count must be a non-negative int")
        elif self.byte_count != len(encoded):
            raise ConstructionEvidenceError("byte_count does not match literal UTF-8 content")

    def to_payload(self) -> dict[str, object]:
        return {
            "byte_count": self.byte_count,
            "content": self.content,
            "content_digest": self.content_digest,
            "kind": self.kind.value,
            "relative_path": self.relative_path,
            "sequence": self.sequence,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionActionPlan:
    """Canonical ordered action plan with digest-derived sole identity."""

    actions: tuple[ConstructionFileAction, ...]
    plan_digest: str | None = None
    schema_version: str = CONSTRUCTION_ACTION_PLAN_SCHEMA_VERSION
    profile: str = CONSTRUCTION_PROFILE

    def __post_init__(self) -> None:
        if self.schema_version != CONSTRUCTION_ACTION_PLAN_SCHEMA_VERSION:
            raise ConstructionEvidenceError("unsupported construction action-plan schema_version")
        if self.profile != CONSTRUCTION_PROFILE:
            raise ConstructionEvidenceError("unsupported construction action-plan profile")
        if not self.actions or any(not isinstance(item, ConstructionFileAction) for item in self.actions):
            raise ConstructionEvidenceError("actions must be a non-empty tuple of ConstructionFileAction")
        if tuple(item.sequence for item in self.actions) != tuple(range(1, len(self.actions) + 1)):
            raise ConstructionEvidenceError("action sequences must be contiguous and start at one")
        paths = tuple(item.relative_path for item in self.actions)
        if len(set(paths)) != len(paths):
            raise ConstructionEvidenceError("action paths must be unique")
        if any(len(PurePosixPath(item.relative_path).parts) > 8 for item in self.actions):
            raise ConstructionEvidenceError("action path depth exceeds the supported profile")
        calculated = self.calculate_digest()
        if self.plan_digest is None:
            object.__setattr__(self, "plan_digest", calculated)
        else:
            object.__setattr__(self, "plan_digest", require_sha256(self.plan_digest, "plan_digest"))
            if self.plan_digest != calculated:
                raise ConstructionEvidenceError("plan_digest does not match canonical action plan")

    @property
    def file_count(self) -> int:
        return len(self.actions)

    @property
    def total_bytes(self) -> int:
        return sum(_action_byte_count(action) for action in self.actions)

    def calculate_digest(self) -> str:
        return canonical_digest(self._payload_without_digest())

    def _payload_without_digest(self) -> dict[str, object]:
        return {
            "actions": [action.to_payload() for action in self.actions],
            "file_count": self.file_count,
            "profile": self.profile,
            "schema_version": self.schema_version,
            "total_bytes": self.total_bytes,
        }

    def to_payload(self) -> dict[str, object]:
        return {**self._payload_without_digest(), "plan_digest": self.plan_digest}


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionAuthorizationRequest:
    """Immutable, canonical evidence only; the live custody handle is explicitly excluded."""

    authorization_id: str
    assessment_request: ConstructionWorkOrderAssessmentRequest
    assessment: ConstructionWorkOrderAssessment
    custody_request: WorkspaceCustodyRequest
    custody_attestation: WorkspaceCustodyAttestation
    custody_root_binding: WorkspaceCustodyRootBinding
    plan: ConstructionActionPlan
    timestamp: datetime
    authorization_digest: str | None = None
    schema_version: str = CONSTRUCTION_AUTHORIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "authorization_id", require_identifier(self.authorization_id, "authorization_id"))
        if not isinstance(self.assessment_request, ConstructionWorkOrderAssessmentRequest):
            raise TypeError("assessment_request must be ConstructionWorkOrderAssessmentRequest")
        if not isinstance(self.assessment, ConstructionWorkOrderAssessment):
            raise TypeError("assessment must be ConstructionWorkOrderAssessment")
        if not isinstance(self.custody_request, WorkspaceCustodyRequest):
            raise TypeError("custody_request must be WorkspaceCustodyRequest")
        if not isinstance(self.custody_attestation, WorkspaceCustodyAttestation):
            raise TypeError("custody_attestation must be WorkspaceCustodyAttestation")
        if not isinstance(self.custody_root_binding, WorkspaceCustodyRootBinding):
            raise TypeError("custody_root_binding must be WorkspaceCustodyRootBinding")
        if not isinstance(self.plan, ConstructionActionPlan):
            raise TypeError("plan must be ConstructionActionPlan")
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != CONSTRUCTION_AUTHORIZATION_SCHEMA_VERSION:
            raise ConstructionEvidenceError("unsupported construction authorization schema_version")
        calculated = self.calculate_digest()
        if self.authorization_digest is None:
            object.__setattr__(self, "authorization_digest", calculated)
        else:
            object.__setattr__(
                self,
                "authorization_digest",
                require_sha256(self.authorization_digest, "authorization_digest"),
            )
            if self.authorization_digest != calculated:
                raise ConstructionEvidenceError("authorization_digest does not match canonical authorization request")

    def _payload_without_digest(self) -> dict[str, object]:
        work_order = self.assessment_request.work_order
        return {
            "assessment_digest": self.assessment.assessment_digest,
            "assessment_id": self.assessment.assessment_id,
            "assessment_request_digest": self.assessment_request.request_digest,
            "assessment_request_id": self.assessment_request.assessment_request_id,
            "authorization_id": self.authorization_id,
            "custody_attestation_binding_digest": self.custody_attestation.binding_digest,
            "custody_attestation_id": self.custody_attestation.attestation_id,
            "custody_request_digest": self.custody_request.request_digest,
            "custody_request_id": self.custody_request.custody_request_id,
            "custody_root_binding_digest": self.custody_root_binding.binding_digest,
            "custody_root_binding_id": self.custody_root_binding.binding_id,
            "plan_digest": self.plan.plan_digest,
            "schema_version": self.schema_version,
            "timestamp": self.timestamp.isoformat(),
            "work_order_digest": work_order.work_order_digest,
            "work_order_id": work_order.work_order_id,
        }

    def calculate_digest(self) -> str:
        return canonical_digest(self._payload_without_digest())

    def to_payload(self) -> dict[str, object]:
        return {**self._payload_without_digest(), "authorization_digest": self.authorization_digest}


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionFinding:
    """One deterministic construction finding with no recovery instruction."""

    code: ConstructionFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, ConstructionFindingCode):
            raise TypeError("code must be ConstructionFindingCode")
        object.__setattr__(self, "evidence_reference", require_identifier(self.evidence_reference, "evidence_reference"))

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionAuthorizationDecision:
    """Immutable pre-effect decision; it is not a permit or live-handle wrapper."""

    disposition: ConstructionAuthorizationDisposition
    findings: tuple[ConstructionFinding, ...]
    authorization_id: str
    authorization_digest: str
    plan_digest: str
    work_order_digest: str
    assessment_digest: str
    custody_attestation_binding_digest: str
    custody_root_binding_digest: str
    decision_digest: str | None = None
    schema_version: str = CONSTRUCTION_AUTHORIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ConstructionAuthorizationDisposition):
            raise TypeError("disposition must be ConstructionAuthorizationDisposition")
        if any(not isinstance(item, ConstructionFinding) for item in self.findings):
            raise TypeError("findings must contain ConstructionFinding values")
        keys = tuple((item.code.value, item.evidence_reference) for item in self.findings)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise ConstructionEvidenceError("findings must be strictly ordered and unique")
        object.__setattr__(self, "authorization_id", require_identifier(self.authorization_id, "authorization_id"))
        for name in (
            "authorization_digest",
            "plan_digest",
            "work_order_digest",
            "assessment_digest",
            "custody_attestation_binding_digest",
            "custody_root_binding_digest",
        ):
            object.__setattr__(self, name, require_sha256(getattr(self, name), name))
        if self.schema_version != CONSTRUCTION_AUTHORIZATION_SCHEMA_VERSION:
            raise ConstructionEvidenceError("unsupported construction authorization decision schema_version")
        if self.disposition is ConstructionAuthorizationDisposition.ATTESTED and self.findings:
            raise ConstructionEvidenceError("attested construction decision cannot carry findings")
        if self.disposition is ConstructionAuthorizationDisposition.REFUSED and not self.findings:
            raise ConstructionEvidenceError("refused construction decision requires findings")
        calculated = self.calculate_digest()
        if self.decision_digest is None:
            object.__setattr__(self, "decision_digest", calculated)
        else:
            object.__setattr__(self, "decision_digest", require_sha256(self.decision_digest, "decision_digest"))
            if self.decision_digest != calculated:
                raise ConstructionEvidenceError("decision_digest does not match canonical decision")

    def calculate_digest(self) -> str:
        return canonical_digest(
            {
                "assessment_digest": self.assessment_digest,
                "authorization_digest": self.authorization_digest,
                "authorization_id": self.authorization_id,
                "custody_attestation_binding_digest": self.custody_attestation_binding_digest,
                "custody_root_binding_digest": self.custody_root_binding_digest,
                "findings": [item.to_payload() for item in self.findings],
                "plan_digest": self.plan_digest,
                "schema_version": self.schema_version,
                "disposition": self.disposition.value,
                "work_order_digest": self.work_order_digest,
            }
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionActionReceipt:
    """Direct immutable proof of one successfully created declared regular file."""

    sequence: int
    relative_path: str
    content_digest: str
    byte_count: int
    occurred_at: datetime
    receipt_digest: str | None = None
    schema_version: str = CONSTRUCTION_RECEIPT_SCHEMA_VERSION
    disposition: ConstructionActionDisposition = ConstructionActionDisposition.CREATED

    def __post_init__(self) -> None:
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 1:
            raise ConstructionEvidenceError("sequence must be a positive int")
        object.__setattr__(self, "relative_path", _normalized_relative_path(self.relative_path))
        object.__setattr__(self, "content_digest", require_sha256(self.content_digest, "content_digest"))
        if not isinstance(self.byte_count, int) or isinstance(self.byte_count, bool) or self.byte_count < 0:
            raise ConstructionEvidenceError("byte_count must be a non-negative int")
        if self.disposition is not ConstructionActionDisposition.CREATED:
            raise ConstructionEvidenceError("G2.4.22 action receipts record only successful prefix effects")
        object.__setattr__(self, "occurred_at", canonical_timestamp(self.occurred_at, "occurred_at"))
        if self.schema_version != CONSTRUCTION_RECEIPT_SCHEMA_VERSION:
            raise ConstructionEvidenceError("unsupported construction receipt schema_version")
        calculated = self.calculate_digest()
        if self.receipt_digest is None:
            object.__setattr__(self, "receipt_digest", calculated)
        else:
            object.__setattr__(self, "receipt_digest", require_sha256(self.receipt_digest, "receipt_digest"))
            if self.receipt_digest != calculated:
                raise ConstructionEvidenceError("receipt_digest does not match canonical action receipt")

    def calculate_digest(self) -> str:
        return canonical_digest(
            {
                "byte_count": self.byte_count,
                "content_digest": self.content_digest,
                "disposition": self.disposition.value,
                "occurred_at": self.occurred_at.isoformat(),
                "relative_path": self.relative_path,
                "schema_version": self.schema_version,
                "sequence": self.sequence,
            }
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionBatchReceipt:
    """Immutable direct state evidence of a created prefix or a pre-effect refusal."""

    disposition: ConstructionBatchDisposition
    authorization_id: str
    authorization_digest: str
    plan_digest: str
    work_order_digest: str
    assessment_digest: str
    custody_attestation_binding_digest: str
    custody_root_binding_digest: str
    action_receipts: tuple[ConstructionActionReceipt, ...]
    occurred_at: datetime
    first_failure: ConstructionFindingCode | None = None
    batch_digest: str | None = None
    schema_version: str = CONSTRUCTION_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ConstructionBatchDisposition):
            raise TypeError("disposition must be ConstructionBatchDisposition")
        object.__setattr__(self, "authorization_id", require_identifier(self.authorization_id, "authorization_id"))
        for name in (
            "authorization_digest",
            "plan_digest",
            "work_order_digest",
            "assessment_digest",
            "custody_attestation_binding_digest",
            "custody_root_binding_digest",
        ):
            object.__setattr__(self, name, require_sha256(getattr(self, name), name))
        if any(not isinstance(item, ConstructionActionReceipt) for item in self.action_receipts):
            raise TypeError("action_receipts must contain ConstructionActionReceipt values")
        if tuple(item.sequence for item in self.action_receipts) != tuple(range(1, len(self.action_receipts) + 1)):
            raise ConstructionEvidenceError("action receipt sequences must be a contiguous successful prefix")
        object.__setattr__(self, "occurred_at", canonical_timestamp(self.occurred_at, "occurred_at"))
        if self.first_failure is not None and not isinstance(self.first_failure, ConstructionFindingCode):
            raise TypeError("first_failure must be ConstructionFindingCode or None")
        if self.disposition is ConstructionBatchDisposition.CONSTRUCTION_FILES_CREATED:
            if self.first_failure is not None:
                raise ConstructionEvidenceError("completed construction receipt cannot carry a failure")
        elif self.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED:
            if self.action_receipts or self.first_failure is None:
                raise ConstructionEvidenceError("pre-effect refusal requires no action receipt and one failure")
        elif self.disposition is ConstructionBatchDisposition.PARTIAL_CONSTRUCTION_STOPPED:
            if self.first_failure is None:
                raise ConstructionEvidenceError("partial construction requires a first failure")
        if self.schema_version != CONSTRUCTION_RECEIPT_SCHEMA_VERSION:
            raise ConstructionEvidenceError("unsupported construction receipt schema_version")
        calculated = self.calculate_digest()
        if self.batch_digest is None:
            object.__setattr__(self, "batch_digest", calculated)
        else:
            object.__setattr__(self, "batch_digest", require_sha256(self.batch_digest, "batch_digest"))
            if self.batch_digest != calculated:
                raise ConstructionEvidenceError("batch_digest does not match canonical batch receipt")

    def calculate_digest(self) -> str:
        return canonical_digest(
            {
                "action_receipts": [
                    {"receipt_digest": item.receipt_digest, "sequence": item.sequence}
                    for item in self.action_receipts
                ],
                "assessment_digest": self.assessment_digest,
                "authorization_digest": self.authorization_digest,
                "authorization_id": self.authorization_id,
                "custody_attestation_binding_digest": self.custody_attestation_binding_digest,
                "custody_root_binding_digest": self.custody_root_binding_digest,
                "disposition": self.disposition.value,
                "first_failure": None if self.first_failure is None else self.first_failure.value,
                "occurred_at": self.occurred_at.isoformat(),
                "plan_digest": self.plan_digest,
                "schema_version": self.schema_version,
                "work_order_digest": self.work_order_digest,
            }
        )


def _action_byte_count(action: ConstructionFileAction) -> int:
    if action.byte_count is None:
        raise ConstructionEvidenceError("validated action is missing byte_count")
    return action.byte_count


def _normalized_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConstructionEvidenceError("relative_path must be a non-empty string")
    if "\\" in value or value.startswith("/") or value.endswith("/"):
        raise ConstructionEvidenceError("relative_path must be normalized POSIX-relative text")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ConstructionEvidenceError("relative_path must not escape the workspace root")
    if str(path) != value:
        raise ConstructionEvidenceError("relative_path must be canonical POSIX-relative text")
    return value


__all__ = [
    "CONSTRUCTION_PROFILE",
    "ConstructionActionDisposition",
    "ConstructionActionKind",
    "ConstructionActionPlan",
    "ConstructionActionReceipt",
    "ConstructionAuthorizationDecision",
    "ConstructionAuthorizationDisposition",
    "ConstructionAuthorizationRequest",
    "ConstructionBatchDisposition",
    "ConstructionBatchReceipt",
    "ConstructionEvidenceError",
    "ConstructionFileAction",
    "ConstructionFinding",
    "ConstructionFindingCode",
]
