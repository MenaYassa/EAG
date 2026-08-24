"""Immutable G2.4.21 local construction work-order evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from eag.governed_composition import RuntimeCompositionAttestation
from eag.governed_construction_work_order.canonical import (
    CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION,
    ConstructionWorkOrderEvidenceError,
    canonical_digest,
    canonical_timestamp,
    require_identifier,
    require_nonnegative_int,
    require_positive_int,
    require_sha256,
)
from eag.governed_destination_contract import (
    DestinationContractAssessment,
    DestinationContractAssessmentRequest,
)
from eag.governed_outcome_policy import (
    OutcomeSemanticsAssessment,
    OutcomeSemanticsAssessmentRequest,
)
from eag.governed_workspace import WorkspaceCustodyAttestation


class ConstructionWorkOrderProfile(StrEnum):
    """The sole static profile for non-executing local construction intent evidence."""

    DISPOSABLE_LOCAL_CONSTRUCTION_WORK_ORDER_V1 = "disposable_local_construction_work_order_v1"


class ConstructionWorkOrderDisposition(StrEnum):
    """Evidence-only outcomes that never grant construction execution authority."""

    CONSTRUCTION_WORK_ORDER_ATTESTED = "construction_work_order_attested"
    NOT_ATTESTED = "not_attested"
    UNSUPPORTED_CONSTRUCTION_PROFILE = "unsupported_construction_profile"


class ConstructionWorkOrderFindingCode(StrEnum):
    """Typed policy/evidence findings with no effect, process, or completion claim."""

    WORK_ORDER_EXPIRED = "work_order_expired"
    WORKSPACE_CUSTODY_INVALID = "workspace_custody_invalid"
    WORKSPACE_CUSTODY_BINDING_MISMATCH = "workspace_custody_binding_mismatch"
    RUNTIME_COMPOSITION_INVALID = "runtime_composition_invalid"
    RUNTIME_COMPOSITION_BINDING_MISMATCH = "runtime_composition_binding_mismatch"
    CONTRACT_ASSESSMENT_INVALID = "contract_assessment_invalid"
    CONTRACT_BINDING_MISMATCH = "contract_binding_mismatch"
    OUTCOME_POLICY_ASSESSMENT_INVALID = "outcome_policy_assessment_invalid"
    OUTCOME_POLICY_BINDING_MISMATCH = "outcome_policy_binding_mismatch"
    WORKSPACE_BINDING_MISMATCH = "workspace_binding_mismatch"
    UNSUPPORTED_CAPABILITY_DECLARATION = "unsupported_capability_declaration"
    INVALID_STATIC_LIMITS = "invalid_static_limits"
    UNSUPPORTED_CONSTRUCTION_PROFILE = "unsupported_construction_profile"


_SUPPORTED_CAPABILITIES = (
    "construction_architecture_declaration",
    "construction_requirements_declaration",
    "construction_work_order_evidence",
)


def _enum_value(value: ConstructionWorkOrderProfile | str, field_name: str) -> str:
    if not isinstance(value, (ConstructionWorkOrderProfile, str)):
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a construction profile")
    return require_identifier(value.value if isinstance(value, ConstructionWorkOrderProfile) else value, field_name)


def _ordered_unique_identifiers(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a non-empty tuple")
    normalized = tuple(require_identifier(value, field_name) for value in values)
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be strictly ordered and unique")
    return normalized


def _ordered_unique_values(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be a tuple")
    normalized = tuple(require_identifier(value, field_name) for value in values)
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise ConstructionWorkOrderEvidenceError(f"{field_name} must be strictly ordered and unique")
    return normalized


@dataclass(frozen=True, slots=True, kw_only=True)
class LocalConstructionWorkOrderEvidence:
    """Immutable local-construction intent evidence, never a workspace, file, or command authority.

    The declaration is static policy vocabulary for a future separately governed effect
    owner. It neither creates nor leases a workspace, changes files, starts a process,
    authorizes a command, obtains a dependency, or determines application correctness.
    """

    work_order_id: str
    execution_id: str
    run_id: str
    workspace_id: str
    workspace_root_identity: str
    workspace_custody_attestation_id: str
    workspace_custody_binding_digest: str
    runtime_composition_attestation_id: str
    runtime_composition_binding_digest: str
    destination_contract_id: str
    destination_contract_digest: str
    destination_contract_assessment_id: str
    destination_contract_assessment_digest: str
    outcome_policy_id: str
    outcome_policy_digest: str
    outcome_policy_assessment_id: str
    outcome_policy_assessment_digest: str
    construction_requirements_digest: str
    architecture_specification_digest: str
    action_plan_digest: str
    declared_capability_ids: tuple[str, ...]
    max_file_actions: int
    max_total_bytes: int
    max_command_actions: int
    construction_profile: ConstructionWorkOrderProfile | str
    issued_at: datetime
    expires_at: datetime
    work_order_digest: str
    schema_version: str = CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "work_order_id",
            "execution_id",
            "run_id",
            "workspace_id",
            "workspace_custody_attestation_id",
            "runtime_composition_attestation_id",
        ):
            object.__setattr__(self, field_name, require_identifier(getattr(self, field_name), field_name))
        for field_name in (
            "workspace_root_identity",
            "workspace_custody_binding_digest",
            "runtime_composition_binding_digest",
            "destination_contract_digest",
            "destination_contract_assessment_digest",
            "outcome_policy_digest",
            "outcome_policy_assessment_digest",
            "construction_requirements_digest",
            "architecture_specification_digest",
            "action_plan_digest",
            "work_order_digest",
        ):
            object.__setattr__(self, field_name, require_sha256(getattr(self, field_name), field_name))
        for field_name in (
            "destination_contract_id",
            "destination_contract_assessment_id",
            "outcome_policy_id",
            "outcome_policy_assessment_id",
        ):
            object.__setattr__(self, field_name, require_identifier(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "declared_capability_ids",
            _ordered_unique_identifiers(self.declared_capability_ids, "declared_capability_ids"),
        )
        object.__setattr__(self, "max_file_actions", require_positive_int(self.max_file_actions, "max_file_actions"))
        object.__setattr__(self, "max_total_bytes", require_positive_int(self.max_total_bytes, "max_total_bytes"))
        object.__setattr__(
            self,
            "max_command_actions",
            require_nonnegative_int(self.max_command_actions, "max_command_actions"),
        )
        object.__setattr__(
            self,
            "construction_profile",
            _enum_value(self.construction_profile, "construction_profile"),
        )
        object.__setattr__(self, "issued_at", canonical_timestamp(self.issued_at, "issued_at"))
        object.__setattr__(self, "expires_at", canonical_timestamp(self.expires_at, "expires_at"))
        if self.expires_at <= self.issued_at:
            raise ConstructionWorkOrderEvidenceError("expires_at must be after issued_at")
        if self.schema_version != CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION:
            raise ConstructionWorkOrderEvidenceError("unsupported construction work-order schema_version")
        if self.work_order_digest != self.calculate_digest():
            raise ConstructionWorkOrderEvidenceError(
                "work_order_digest does not match canonical construction work-order evidence"
            )

    @classmethod
    def issue(
        cls,
        *,
        work_order_id: str,
        execution_id: str,
        run_id: str,
        workspace_id: str,
        workspace_root_identity: str,
        workspace_custody_attestation_id: str,
        workspace_custody_binding_digest: str,
        runtime_composition_attestation_id: str,
        runtime_composition_binding_digest: str,
        destination_contract_id: str,
        destination_contract_digest: str,
        destination_contract_assessment_id: str,
        destination_contract_assessment_digest: str,
        outcome_policy_id: str,
        outcome_policy_digest: str,
        outcome_policy_assessment_id: str,
        outcome_policy_assessment_digest: str,
        construction_requirements_digest: str,
        architecture_specification_digest: str,
        action_plan_digest: str,
        declared_capability_ids: tuple[str, ...],
        max_file_actions: int,
        max_total_bytes: int,
        max_command_actions: int,
        construction_profile: ConstructionWorkOrderProfile | str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> LocalConstructionWorkOrderEvidence:
        canonical_issued = canonical_timestamp(issued_at, "issued_at")
        canonical_expires = canonical_timestamp(expires_at, "expires_at")
        payload = _work_order_payload(
            work_order_id=work_order_id,
            execution_id=execution_id,
            run_id=run_id,
            workspace_id=workspace_id,
            workspace_root_identity=workspace_root_identity,
            workspace_custody_attestation_id=workspace_custody_attestation_id,
            workspace_custody_binding_digest=workspace_custody_binding_digest,
            runtime_composition_attestation_id=runtime_composition_attestation_id,
            runtime_composition_binding_digest=runtime_composition_binding_digest,
            destination_contract_id=destination_contract_id,
            destination_contract_digest=destination_contract_digest,
            destination_contract_assessment_id=destination_contract_assessment_id,
            destination_contract_assessment_digest=destination_contract_assessment_digest,
            outcome_policy_id=outcome_policy_id,
            outcome_policy_digest=outcome_policy_digest,
            outcome_policy_assessment_id=outcome_policy_assessment_id,
            outcome_policy_assessment_digest=outcome_policy_assessment_digest,
            construction_requirements_digest=construction_requirements_digest,
            architecture_specification_digest=architecture_specification_digest,
            action_plan_digest=action_plan_digest,
            declared_capability_ids=declared_capability_ids,
            max_file_actions=max_file_actions,
            max_total_bytes=max_total_bytes,
            max_command_actions=max_command_actions,
            construction_profile=construction_profile,
            issued_at=canonical_issued,
            expires_at=canonical_expires,
            schema_version=CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION,
        )
        return cls(
            work_order_id=work_order_id,
            execution_id=execution_id,
            run_id=run_id,
            workspace_id=workspace_id,
            workspace_root_identity=workspace_root_identity,
            workspace_custody_attestation_id=workspace_custody_attestation_id,
            workspace_custody_binding_digest=workspace_custody_binding_digest,
            runtime_composition_attestation_id=runtime_composition_attestation_id,
            runtime_composition_binding_digest=runtime_composition_binding_digest,
            destination_contract_id=destination_contract_id,
            destination_contract_digest=destination_contract_digest,
            destination_contract_assessment_id=destination_contract_assessment_id,
            destination_contract_assessment_digest=destination_contract_assessment_digest,
            outcome_policy_id=outcome_policy_id,
            outcome_policy_digest=outcome_policy_digest,
            outcome_policy_assessment_id=outcome_policy_assessment_id,
            outcome_policy_assessment_digest=outcome_policy_assessment_digest,
            construction_requirements_digest=construction_requirements_digest,
            architecture_specification_digest=architecture_specification_digest,
            action_plan_digest=action_plan_digest,
            declared_capability_ids=declared_capability_ids,
            max_file_actions=max_file_actions,
            max_total_bytes=max_total_bytes,
            max_command_actions=max_command_actions,
            construction_profile=construction_profile,
            issued_at=canonical_issued,
            expires_at=canonical_expires,
            work_order_digest=canonical_digest(payload),
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            _work_order_payload(
                work_order_id=self.work_order_id,
                execution_id=self.execution_id,
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                workspace_root_identity=self.workspace_root_identity,
                workspace_custody_attestation_id=self.workspace_custody_attestation_id,
                workspace_custody_binding_digest=self.workspace_custody_binding_digest,
                runtime_composition_attestation_id=self.runtime_composition_attestation_id,
                runtime_composition_binding_digest=self.runtime_composition_binding_digest,
                destination_contract_id=self.destination_contract_id,
                destination_contract_digest=self.destination_contract_digest,
                destination_contract_assessment_id=self.destination_contract_assessment_id,
                destination_contract_assessment_digest=self.destination_contract_assessment_digest,
                outcome_policy_id=self.outcome_policy_id,
                outcome_policy_digest=self.outcome_policy_digest,
                outcome_policy_assessment_id=self.outcome_policy_assessment_id,
                outcome_policy_assessment_digest=self.outcome_policy_assessment_digest,
                construction_requirements_digest=self.construction_requirements_digest,
                architecture_specification_digest=self.architecture_specification_digest,
                action_plan_digest=self.action_plan_digest,
                declared_capability_ids=self.declared_capability_ids,
                max_file_actions=self.max_file_actions,
                max_total_bytes=self.max_total_bytes,
                max_command_actions=self.max_command_actions,
                construction_profile=self.construction_profile,
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                schema_version=self.schema_version,
            )
        )

    def to_payload(self) -> dict[str, object]:
        return {
            **_work_order_payload(
                work_order_id=self.work_order_id,
                execution_id=self.execution_id,
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                workspace_root_identity=self.workspace_root_identity,
                workspace_custody_attestation_id=self.workspace_custody_attestation_id,
                workspace_custody_binding_digest=self.workspace_custody_binding_digest,
                runtime_composition_attestation_id=self.runtime_composition_attestation_id,
                runtime_composition_binding_digest=self.runtime_composition_binding_digest,
                destination_contract_id=self.destination_contract_id,
                destination_contract_digest=self.destination_contract_digest,
                destination_contract_assessment_id=self.destination_contract_assessment_id,
                destination_contract_assessment_digest=self.destination_contract_assessment_digest,
                outcome_policy_id=self.outcome_policy_id,
                outcome_policy_digest=self.outcome_policy_digest,
                outcome_policy_assessment_id=self.outcome_policy_assessment_id,
                outcome_policy_assessment_digest=self.outcome_policy_assessment_digest,
                construction_requirements_digest=self.construction_requirements_digest,
                architecture_specification_digest=self.architecture_specification_digest,
                action_plan_digest=self.action_plan_digest,
                declared_capability_ids=self.declared_capability_ids,
                max_file_actions=self.max_file_actions,
                max_total_bytes=self.max_total_bytes,
                max_command_actions=self.max_command_actions,
                construction_profile=self.construction_profile,
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                schema_version=self.schema_version,
            ),
            "work_order_digest": self.work_order_digest,
        }

    @classmethod
    def from_payload(cls, payload: object) -> LocalConstructionWorkOrderEvidence:
        required = set(_WORK_ORDER_FIELDS) | {"work_order_digest"}
        if not isinstance(payload, dict) or set(payload) != required:
            raise ConstructionWorkOrderEvidenceError("construction work-order payload has unexpected fields")
        try:
            capability_values = payload["declared_capability_ids"]
            if not isinstance(capability_values, list):
                raise ConstructionWorkOrderEvidenceError("declared_capability_ids payload must be a list")
            return cls(
                work_order_id=payload["work_order_id"],
                execution_id=payload["execution_id"],
                run_id=payload["run_id"],
                workspace_id=payload["workspace_id"],
                workspace_root_identity=payload["workspace_root_identity"],
                workspace_custody_attestation_id=payload["workspace_custody_attestation_id"],
                workspace_custody_binding_digest=payload["workspace_custody_binding_digest"],
                runtime_composition_attestation_id=payload["runtime_composition_attestation_id"],
                runtime_composition_binding_digest=payload["runtime_composition_binding_digest"],
                destination_contract_id=payload["destination_contract_id"],
                destination_contract_digest=payload["destination_contract_digest"],
                destination_contract_assessment_id=payload["destination_contract_assessment_id"],
                destination_contract_assessment_digest=payload["destination_contract_assessment_digest"],
                outcome_policy_id=payload["outcome_policy_id"],
                outcome_policy_digest=payload["outcome_policy_digest"],
                outcome_policy_assessment_id=payload["outcome_policy_assessment_id"],
                outcome_policy_assessment_digest=payload["outcome_policy_assessment_digest"],
                construction_requirements_digest=payload["construction_requirements_digest"],
                architecture_specification_digest=payload["architecture_specification_digest"],
                action_plan_digest=payload["action_plan_digest"],
                declared_capability_ids=tuple(capability_values),
                max_file_actions=payload["max_file_actions"],
                max_total_bytes=payload["max_total_bytes"],
                max_command_actions=payload["max_command_actions"],
                construction_profile=payload["construction_profile"],
                issued_at=datetime.fromisoformat(payload["issued_at"]),
                expires_at=datetime.fromisoformat(payload["expires_at"]),
                work_order_digest=payload["work_order_digest"],
                schema_version=payload["schema_version"],
            )
        except (KeyError, TypeError, ValueError, ConstructionWorkOrderEvidenceError) as error:
            raise ConstructionWorkOrderEvidenceError("invalid construction work-order payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionWorkOrderAssessmentRequest:
    """Exact immutable upstream evidence and one construction work-order declaration only."""

    assessment_request_id: str
    workspace_custody_attestation: WorkspaceCustodyAttestation
    runtime_composition_attestation: RuntimeCompositionAttestation
    destination_contract_request: DestinationContractAssessmentRequest
    destination_contract_assessment: DestinationContractAssessment
    outcome_policy_request: OutcomeSemanticsAssessmentRequest
    outcome_policy_assessment: OutcomeSemanticsAssessment
    work_order: LocalConstructionWorkOrderEvidence
    timestamp: datetime
    request_digest: str | None = None
    schema_version: str = CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assessment_request_id",
            require_identifier(self.assessment_request_id, "assessment_request_id"),
        )
        for field_name, expected_type in (
            ("workspace_custody_attestation", WorkspaceCustodyAttestation),
            ("runtime_composition_attestation", RuntimeCompositionAttestation),
            ("destination_contract_request", DestinationContractAssessmentRequest),
            ("destination_contract_assessment", DestinationContractAssessment),
            ("outcome_policy_request", OutcomeSemanticsAssessmentRequest),
            ("outcome_policy_assessment", OutcomeSemanticsAssessment),
            ("work_order", LocalConstructionWorkOrderEvidence),
        ):
            if not isinstance(getattr(self, field_name), expected_type):
                raise TypeError(f"{field_name} must be an immutable {expected_type.__name__}")
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION:
            raise ConstructionWorkOrderEvidenceError("unsupported work-order assessment request schema_version")
        calculated = self.calculate_digest()
        if self.request_digest is None:
            object.__setattr__(self, "request_digest", calculated)
        else:
            object.__setattr__(self, "request_digest", require_sha256(self.request_digest, "request_digest"))
            if self.request_digest != calculated:
                raise ConstructionWorkOrderEvidenceError(
                    "request_digest does not match canonical construction work-order request"
                )

    def calculate_digest(self) -> str:
        return canonical_digest(_request_payload(self))

    def to_payload(self) -> dict[str, object]:
        return {**_request_payload(self), "request_digest": self.request_digest}


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionWorkOrderFinding:
    """One typed evidence-only finding with no workspace, command, or recovery instruction."""

    code: ConstructionWorkOrderFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, ConstructionWorkOrderFindingCode):
            raise TypeError("code must be a ConstructionWorkOrderFindingCode")
        object.__setattr__(
            self,
            "evidence_reference",
            require_identifier(self.evidence_reference, "evidence_reference"),
        )

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionWorkOrderAssessment:
    """Immutable work-order policy evidence; it never reports local or external execution facts."""

    assessment_id: str
    workspace_id: str
    work_order_id: str | None
    disposition: ConstructionWorkOrderDisposition
    findings: tuple[ConstructionWorkOrderFinding, ...]
    evidence_refs: tuple[str, ...]
    recommendations: tuple[str, ...]
    assessment_digest: str
    timestamp: datetime
    schema_version: str = CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "assessment_id", require_identifier(self.assessment_id, "assessment_id"))
        object.__setattr__(self, "workspace_id", require_identifier(self.workspace_id, "workspace_id"))
        if self.work_order_id is not None:
            object.__setattr__(self, "work_order_id", require_identifier(self.work_order_id, "work_order_id"))
        if not isinstance(self.disposition, ConstructionWorkOrderDisposition):
            raise TypeError("disposition must be a ConstructionWorkOrderDisposition")
        if any(not isinstance(item, ConstructionWorkOrderFinding) for item in self.findings):
            raise TypeError("findings must contain ConstructionWorkOrderFinding values")
        finding_keys = tuple((item.code.value, item.evidence_reference) for item in self.findings)
        if finding_keys != tuple(sorted(finding_keys)) or len(set(finding_keys)) != len(finding_keys):
            raise ConstructionWorkOrderEvidenceError("findings must be strictly ordered and unique")
        object.__setattr__(self, "evidence_refs", _ordered_unique_values(self.evidence_refs, "evidence_refs"))
        object.__setattr__(self, "recommendations", _ordered_unique_values(self.recommendations, "recommendations"))
        object.__setattr__(self, "assessment_digest", require_sha256(self.assessment_digest, "assessment_digest"))
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION:
            raise ConstructionWorkOrderEvidenceError("unsupported construction work-order assessment schema_version")
        if self.assessment_digest != self.calculate_digest():
            raise ConstructionWorkOrderEvidenceError(
                "assessment_digest does not match canonical construction work-order assessment"
            )

    @classmethod
    def issue(
        cls,
        *,
        assessment_id: str,
        workspace_id: str,
        work_order_id: str | None,
        disposition: ConstructionWorkOrderDisposition,
        findings: tuple[ConstructionWorkOrderFinding, ...],
        evidence_refs: tuple[str, ...],
        recommendations: tuple[str, ...],
        timestamp: datetime,
    ) -> ConstructionWorkOrderAssessment:
        canonical_time = canonical_timestamp(timestamp, "timestamp")
        payload = _assessment_payload(
            assessment_id=assessment_id,
            workspace_id=workspace_id,
            work_order_id=work_order_id,
            disposition=disposition,
            findings=findings,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            timestamp=canonical_time,
            schema_version=CONSTRUCTION_WORK_ORDER_SCHEMA_VERSION,
        )
        return cls(
            assessment_id=assessment_id,
            workspace_id=workspace_id,
            work_order_id=work_order_id,
            disposition=disposition,
            findings=findings,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            assessment_digest=canonical_digest(payload),
            timestamp=canonical_time,
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            _assessment_payload(
                assessment_id=self.assessment_id,
                workspace_id=self.workspace_id,
                work_order_id=self.work_order_id,
                disposition=self.disposition,
                findings=self.findings,
                evidence_refs=self.evidence_refs,
                recommendations=self.recommendations,
                timestamp=self.timestamp,
                schema_version=self.schema_version,
            )
        )


_WORK_ORDER_FIELDS = (
    "action_plan_digest",
    "architecture_specification_digest",
    "construction_profile",
    "construction_requirements_digest",
    "declared_capability_ids",
    "destination_contract_assessment_digest",
    "destination_contract_assessment_id",
    "destination_contract_digest",
    "destination_contract_id",
    "execution_id",
    "expires_at",
    "issued_at",
    "max_command_actions",
    "max_file_actions",
    "max_total_bytes",
    "outcome_policy_assessment_digest",
    "outcome_policy_assessment_id",
    "outcome_policy_digest",
    "outcome_policy_id",
    "run_id",
    "runtime_composition_attestation_id",
    "runtime_composition_binding_digest",
    "schema_version",
    "work_order_id",
    "workspace_custody_attestation_id",
    "workspace_custody_binding_digest",
    "workspace_id",
    "workspace_root_identity",
)


def _work_order_payload(
    *,
    work_order_id: str,
    execution_id: str,
    run_id: str,
    workspace_id: str,
    workspace_root_identity: str,
    workspace_custody_attestation_id: str,
    workspace_custody_binding_digest: str,
    runtime_composition_attestation_id: str,
    runtime_composition_binding_digest: str,
    destination_contract_id: str,
    destination_contract_digest: str,
    destination_contract_assessment_id: str,
    destination_contract_assessment_digest: str,
    outcome_policy_id: str,
    outcome_policy_digest: str,
    outcome_policy_assessment_id: str,
    outcome_policy_assessment_digest: str,
    construction_requirements_digest: str,
    architecture_specification_digest: str,
    action_plan_digest: str,
    declared_capability_ids: tuple[str, ...],
    max_file_actions: int,
    max_total_bytes: int,
    max_command_actions: int,
    construction_profile: ConstructionWorkOrderProfile | str,
    issued_at: datetime,
    expires_at: datetime,
    schema_version: str,
) -> dict[str, object]:
    return {
        "action_plan_digest": require_sha256(action_plan_digest, "action_plan_digest"),
        "architecture_specification_digest": require_sha256(
            architecture_specification_digest,
            "architecture_specification_digest",
        ),
        "construction_profile": _enum_value(construction_profile, "construction_profile"),
        "construction_requirements_digest": require_sha256(
            construction_requirements_digest,
            "construction_requirements_digest",
        ),
        "declared_capability_ids": list(_ordered_unique_identifiers(declared_capability_ids, "declared_capability_ids")),
        "destination_contract_assessment_digest": require_sha256(
            destination_contract_assessment_digest,
            "destination_contract_assessment_digest",
        ),
        "destination_contract_assessment_id": require_identifier(
            destination_contract_assessment_id,
            "destination_contract_assessment_id",
        ),
        "destination_contract_digest": require_sha256(destination_contract_digest, "destination_contract_digest"),
        "destination_contract_id": require_identifier(destination_contract_id, "destination_contract_id"),
        "execution_id": require_identifier(execution_id, "execution_id"),
        "expires_at": canonical_timestamp(expires_at, "expires_at").isoformat(),
        "issued_at": canonical_timestamp(issued_at, "issued_at").isoformat(),
        "max_command_actions": require_nonnegative_int(max_command_actions, "max_command_actions"),
        "max_file_actions": require_positive_int(max_file_actions, "max_file_actions"),
        "max_total_bytes": require_positive_int(max_total_bytes, "max_total_bytes"),
        "outcome_policy_assessment_digest": require_sha256(
            outcome_policy_assessment_digest,
            "outcome_policy_assessment_digest",
        ),
        "outcome_policy_assessment_id": require_identifier(
            outcome_policy_assessment_id,
            "outcome_policy_assessment_id",
        ),
        "outcome_policy_digest": require_sha256(outcome_policy_digest, "outcome_policy_digest"),
        "outcome_policy_id": require_identifier(outcome_policy_id, "outcome_policy_id"),
        "run_id": require_identifier(run_id, "run_id"),
        "runtime_composition_attestation_id": require_identifier(
            runtime_composition_attestation_id,
            "runtime_composition_attestation_id",
        ),
        "runtime_composition_binding_digest": require_sha256(
            runtime_composition_binding_digest,
            "runtime_composition_binding_digest",
        ),
        "schema_version": schema_version,
        "work_order_id": require_identifier(work_order_id, "work_order_id"),
        "workspace_custody_attestation_id": require_identifier(
            workspace_custody_attestation_id,
            "workspace_custody_attestation_id",
        ),
        "workspace_custody_binding_digest": require_sha256(
            workspace_custody_binding_digest,
            "workspace_custody_binding_digest",
        ),
        "workspace_id": require_identifier(workspace_id, "workspace_id"),
        "workspace_root_identity": require_sha256(workspace_root_identity, "workspace_root_identity"),
    }


def _request_payload(request: ConstructionWorkOrderAssessmentRequest) -> dict[str, object]:
    custody = request.workspace_custody_attestation
    composition = request.runtime_composition_attestation
    contract_assessment = request.destination_contract_assessment
    outcome_assessment = request.outcome_policy_assessment
    work_order = request.work_order
    return {
        "assessment_request_id": request.assessment_request_id,
        "destination_contract_assessment": {
            "assessment_digest": contract_assessment.assessment_digest,
            "assessment_id": contract_assessment.assessment_id,
            "disposition": contract_assessment.disposition.value,
            "schema_version": contract_assessment.schema_version,
        },
        "destination_contract_request": {
            "request_digest": request.destination_contract_request.request_digest,
            "schema_version": request.destination_contract_request.schema_version,
        },
        "outcome_policy_assessment": {
            "assessment_digest": outcome_assessment.assessment_digest,
            "assessment_id": outcome_assessment.assessment_id,
            "disposition": outcome_assessment.disposition.value,
            "schema_version": outcome_assessment.schema_version,
        },
        "outcome_policy_request": {
            "request_digest": request.outcome_policy_request.request_digest,
            "schema_version": request.outcome_policy_request.schema_version,
        },
        "runtime_composition_attestation": {
            "attestation_id": composition.attestation_id,
            "binding_digest": composition.binding_digest,
            "manifest_digest": composition.manifest.digest,
        },
        "schema_version": request.schema_version,
        "timestamp": request.timestamp.isoformat(),
        "work_order": {
            "work_order_digest": work_order.work_order_digest,
            "work_order_id": work_order.work_order_id,
        },
        "workspace_custody_attestation": {
            "attestation_id": custody.attestation_id,
            "binding_digest": custody.binding_digest,
            "workspace_root_identity": custody.workspace_root_identity,
        },
    }


def _assessment_payload(
    *,
    assessment_id: str,
    workspace_id: str,
    work_order_id: str | None,
    disposition: ConstructionWorkOrderDisposition,
    findings: tuple[ConstructionWorkOrderFinding, ...],
    evidence_refs: tuple[str, ...],
    recommendations: tuple[str, ...],
    timestamp: datetime,
    schema_version: str,
) -> dict[str, object]:
    return {
        "assessment_id": assessment_id,
        "disposition": disposition.value,
        "evidence_refs": list(evidence_refs),
        "findings": [item.to_payload() for item in findings],
        "recommendations": list(recommendations),
        "schema_version": schema_version,
        "timestamp": canonical_timestamp(timestamp, "timestamp").isoformat(),
        "work_order_id": work_order_id,
        "workspace_id": workspace_id,
    }


__all__ = [
    "ConstructionWorkOrderAssessment",
    "ConstructionWorkOrderAssessmentRequest",
    "ConstructionWorkOrderDisposition",
    "ConstructionWorkOrderEvidenceError",
    "ConstructionWorkOrderFinding",
    "ConstructionWorkOrderFindingCode",
    "ConstructionWorkOrderProfile",
    "LocalConstructionWorkOrderEvidence",
]
