"""Immutable evidence-only contracts for G2.4.19 outcome-semantics policy assessment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from eag.governed_destination_contract import (
    DestinationContractAssessment,
    DestinationContractAssessmentRequest,
    DestinationIdempotencyProfile,
    DestinationOperationProfile,
    DestinationReceiptSchema,
)
from eag.governed_outcome_policy.canonical import (
    OUTCOME_POLICY_SCHEMA_VERSION,
    OutcomePolicyEvidenceError,
    canonical_digest,
    canonical_timestamp,
    require_identifier,
    require_non_empty,
    require_sha256,
)
from eag.governed_transition_control import TransitionControlDecision


class OutcomePolicyProfile(StrEnum):
    """Supported declaration profile; never an outcome or execution capability."""

    EXTERNAL_ARTIFACT_OUTCOME_POLICY_V1 = "external_artifact_outcome_policy_v1"


class FutureReceiptClass(StrEnum):
    """Declared vocabulary for a future verifier; this is not receipt evidence."""

    REJECTED_BEFORE_EFFECT_V1 = "rejected_before_effect_v1"
    EFFECT_REPORTED_UNVERIFIED_V1 = "effect_reported_unverified_v1"
    EFFECT_VERIFIED_V1 = "effect_verified_v1"
    OUTCOME_UNKNOWN_V1 = "outcome_unknown_v1"


class UnknownOutcomeDisposition(StrEnum):
    """Required safety treatment for a future unknown external outcome."""

    STOP_AND_RECONCILIATION_REQUIRED = "stop_and_reconciliation_required"


class AutomaticRetryDisposition(StrEnum):
    """G2.4.19 forbids automatic retry semantics."""

    FORBIDDEN = "forbidden"


class AutomaticRollbackDisposition(StrEnum):
    """G2.4.19 forbids automatic rollback semantics."""

    FORBIDDEN = "forbidden"


class CompletionVerificationRequirement(StrEnum):
    """Completion requires a separately designed future receipt verifier."""

    FUTURE_RECEIPT_VERIFICATION_REQUIRED = "future_receipt_verification_required"


class OutcomePolicyDisposition(StrEnum):
    """Evidence-only policy assessment outcomes."""

    OUTCOME_POLICY_ATTESTED = "outcome_policy_attested"
    NOT_ATTESTED = "not_attested"
    UNSUPPORTED_OUTCOME_POLICY = "unsupported_outcome_policy"


class OutcomePolicyFindingCode(StrEnum):
    """Typed deterministic findings without external outcome claims."""

    POLICY_EVIDENCE_INVALID = "policy_evidence_invalid"
    POLICY_EXPIRED = "policy_expired"
    CONTRACT_ASSESSMENT_INVALID = "contract_assessment_invalid"
    CONTRACT_BINDING_MISMATCH = "contract_binding_mismatch"
    DESTINATION_BINDING_MISMATCH = "destination_binding_mismatch"
    PROFILE_BINDING_MISMATCH = "profile_binding_mismatch"
    UNSUPPORTED_OUTCOME_PROFILE = "unsupported_outcome_profile"
    UNSAFE_UNKNOWN_OUTCOME_SEMANTICS = "unsafe_unknown_outcome_semantics"
    AUTOMATIC_RETRY_FORBIDDEN = "automatic_retry_forbidden"
    AUTOMATIC_ROLLBACK_FORBIDDEN = "automatic_rollback_forbidden"
    UNVERIFIED_COMPLETION_FORBIDDEN = "unverified_completion_forbidden"
    TRANSITION_CONTROL_AMBIGUOUS = "transition_control_ambiguous"


_EXPECTED_RECEIPT_CLASSES = tuple(sorted(item.value for item in FutureReceiptClass))


def _enum_value(value: StrEnum | str, field_name: str) -> str:
    if not isinstance(value, (StrEnum, str)):
        raise OutcomePolicyEvidenceError(f"{field_name} must be a declaration identifier")
    return require_identifier(value.value if isinstance(value, StrEnum) else value, field_name)


def _ordered_unique_values(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise OutcomePolicyEvidenceError(f"{field_name} must be a tuple")
    normalized = tuple(_enum_value(value, field_name) for value in values)
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise OutcomePolicyEvidenceError(f"{field_name} must be strictly ordered and unique")
    return normalized


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalOutcomeSemanticsPolicyEvidence:
    """Immutable declaration of safe future outcome semantics, never outcome evidence."""

    outcome_policy_id: str
    destination_contract_id: str
    destination_contract_digest: str
    destination_contract_assessment_id: str
    destination_contract_assessment_digest: str
    destination_identity: str
    operation_profile: OutcomePolicyProfile | str
    destination_operation_profile: DestinationOperationProfile | str
    external_receipt_schema_id: DestinationReceiptSchema | str
    destination_idempotency_profile: DestinationIdempotencyProfile | str
    future_receipt_classes: tuple[FutureReceiptClass | str, ...]
    unknown_outcome_disposition: UnknownOutcomeDisposition | str
    automatic_retry_disposition: AutomaticRetryDisposition | str
    automatic_rollback_disposition: AutomaticRollbackDisposition | str
    completion_verification_requirement: CompletionVerificationRequirement | str
    issued_at: datetime
    expires_at: datetime
    policy_digest: str
    schema_version: str = OUTCOME_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "outcome_policy_id",
            "destination_contract_id",
            "destination_contract_assessment_id",
            "destination_identity",
        ):
            object.__setattr__(self, field_name, require_identifier(getattr(self, field_name), field_name))
        for field_name in (
            "operation_profile",
            "destination_operation_profile",
            "external_receipt_schema_id",
            "destination_idempotency_profile",
            "unknown_outcome_disposition",
            "automatic_retry_disposition",
            "automatic_rollback_disposition",
            "completion_verification_requirement",
        ):
            object.__setattr__(self, field_name, _enum_value(getattr(self, field_name), field_name))
        object.__setattr__(
            self, "future_receipt_classes", _ordered_unique_values(self.future_receipt_classes, "future_receipt_classes")
        )
        for field_name in (
            "destination_contract_digest",
            "destination_contract_assessment_digest",
        ):
            object.__setattr__(self, field_name, require_sha256(getattr(self, field_name), field_name))
        object.__setattr__(self, "issued_at", canonical_timestamp(self.issued_at, "issued_at"))
        object.__setattr__(self, "expires_at", canonical_timestamp(self.expires_at, "expires_at"))
        if self.expires_at <= self.issued_at:
            raise OutcomePolicyEvidenceError("expires_at must be after issued_at")
        if self.schema_version != OUTCOME_POLICY_SCHEMA_VERSION:
            raise OutcomePolicyEvidenceError("unsupported outcome policy schema_version")
        object.__setattr__(self, "policy_digest", require_sha256(self.policy_digest, "policy_digest"))
        if self.policy_digest != self.calculate_digest():
            raise OutcomePolicyEvidenceError("policy_digest does not match canonical outcome policy evidence")

    @classmethod
    def issue(
        cls,
        *,
        outcome_policy_id: str,
        destination_contract_id: str,
        destination_contract_digest: str,
        destination_contract_assessment_id: str,
        destination_contract_assessment_digest: str,
        destination_identity: str,
        operation_profile: OutcomePolicyProfile | str,
        destination_operation_profile: DestinationOperationProfile | str,
        external_receipt_schema_id: DestinationReceiptSchema | str,
        destination_idempotency_profile: DestinationIdempotencyProfile | str,
        future_receipt_classes: tuple[FutureReceiptClass | str, ...],
        unknown_outcome_disposition: UnknownOutcomeDisposition | str,
        automatic_retry_disposition: AutomaticRetryDisposition | str,
        automatic_rollback_disposition: AutomaticRollbackDisposition | str,
        completion_verification_requirement: CompletionVerificationRequirement | str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> ExternalOutcomeSemanticsPolicyEvidence:
        canonical_issued = canonical_timestamp(issued_at, "issued_at")
        canonical_expires = canonical_timestamp(expires_at, "expires_at")
        payload = _policy_payload(
            outcome_policy_id=outcome_policy_id,
            destination_contract_id=destination_contract_id,
            destination_contract_digest=destination_contract_digest,
            destination_contract_assessment_id=destination_contract_assessment_id,
            destination_contract_assessment_digest=destination_contract_assessment_digest,
            destination_identity=destination_identity,
            operation_profile=operation_profile,
            destination_operation_profile=destination_operation_profile,
            external_receipt_schema_id=external_receipt_schema_id,
            destination_idempotency_profile=destination_idempotency_profile,
            future_receipt_classes=future_receipt_classes,
            unknown_outcome_disposition=unknown_outcome_disposition,
            automatic_retry_disposition=automatic_retry_disposition,
            automatic_rollback_disposition=automatic_rollback_disposition,
            completion_verification_requirement=completion_verification_requirement,
            issued_at=canonical_issued,
            expires_at=canonical_expires,
            schema_version=OUTCOME_POLICY_SCHEMA_VERSION,
        )
        return cls(
            outcome_policy_id=outcome_policy_id,
            destination_contract_id=destination_contract_id,
            destination_contract_digest=destination_contract_digest,
            destination_contract_assessment_id=destination_contract_assessment_id,
            destination_contract_assessment_digest=destination_contract_assessment_digest,
            destination_identity=destination_identity,
            operation_profile=operation_profile,
            destination_operation_profile=destination_operation_profile,
            external_receipt_schema_id=external_receipt_schema_id,
            destination_idempotency_profile=destination_idempotency_profile,
            future_receipt_classes=future_receipt_classes,
            unknown_outcome_disposition=unknown_outcome_disposition,
            automatic_retry_disposition=automatic_retry_disposition,
            automatic_rollback_disposition=automatic_rollback_disposition,
            completion_verification_requirement=completion_verification_requirement,
            issued_at=canonical_issued,
            expires_at=canonical_expires,
            policy_digest=canonical_digest(payload),
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            _policy_payload(
                outcome_policy_id=self.outcome_policy_id,
                destination_contract_id=self.destination_contract_id,
                destination_contract_digest=self.destination_contract_digest,
                destination_contract_assessment_id=self.destination_contract_assessment_id,
                destination_contract_assessment_digest=self.destination_contract_assessment_digest,
                destination_identity=self.destination_identity,
                operation_profile=self.operation_profile,
                destination_operation_profile=self.destination_operation_profile,
                external_receipt_schema_id=self.external_receipt_schema_id,
                destination_idempotency_profile=self.destination_idempotency_profile,
                future_receipt_classes=self.future_receipt_classes,
                unknown_outcome_disposition=self.unknown_outcome_disposition,
                automatic_retry_disposition=self.automatic_retry_disposition,
                automatic_rollback_disposition=self.automatic_rollback_disposition,
                completion_verification_requirement=self.completion_verification_requirement,
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                schema_version=self.schema_version,
            )
        )

    def to_payload(self) -> dict[str, str | list[str]]:
        return {
            **_policy_payload(
                outcome_policy_id=self.outcome_policy_id,
                destination_contract_id=self.destination_contract_id,
                destination_contract_digest=self.destination_contract_digest,
                destination_contract_assessment_id=self.destination_contract_assessment_id,
                destination_contract_assessment_digest=self.destination_contract_assessment_digest,
                destination_identity=self.destination_identity,
                operation_profile=self.operation_profile,
                destination_operation_profile=self.destination_operation_profile,
                external_receipt_schema_id=self.external_receipt_schema_id,
                destination_idempotency_profile=self.destination_idempotency_profile,
                future_receipt_classes=self.future_receipt_classes,
                unknown_outcome_disposition=self.unknown_outcome_disposition,
                automatic_retry_disposition=self.automatic_retry_disposition,
                automatic_rollback_disposition=self.automatic_rollback_disposition,
                completion_verification_requirement=self.completion_verification_requirement,
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                schema_version=self.schema_version,
            ),
            "policy_digest": self.policy_digest,
        }

    @classmethod
    def from_payload(cls, payload: object) -> ExternalOutcomeSemanticsPolicyEvidence:
        required = {
            "automatic_retry_disposition",
            "automatic_rollback_disposition",
            "completion_verification_requirement",
            "destination_contract_assessment_digest",
            "destination_contract_assessment_id",
            "destination_contract_digest",
            "destination_contract_id",
            "destination_idempotency_profile",
            "destination_identity",
            "destination_operation_profile",
            "expires_at",
            "external_receipt_schema_id",
            "future_receipt_classes",
            "issued_at",
            "operation_profile",
            "outcome_policy_id",
            "policy_digest",
            "schema_version",
            "unknown_outcome_disposition",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise OutcomePolicyEvidenceError("outcome policy payload has unexpected fields")
        try:
            classes = payload["future_receipt_classes"]
            if not isinstance(classes, list):
                raise OutcomePolicyEvidenceError("future_receipt_classes must be a list")
            return cls(
                outcome_policy_id=payload["outcome_policy_id"],
                destination_contract_id=payload["destination_contract_id"],
                destination_contract_digest=payload["destination_contract_digest"],
                destination_contract_assessment_id=payload["destination_contract_assessment_id"],
                destination_contract_assessment_digest=payload["destination_contract_assessment_digest"],
                destination_identity=payload["destination_identity"],
                operation_profile=payload["operation_profile"],
                destination_operation_profile=payload["destination_operation_profile"],
                external_receipt_schema_id=payload["external_receipt_schema_id"],
                destination_idempotency_profile=payload["destination_idempotency_profile"],
                future_receipt_classes=tuple(classes),
                unknown_outcome_disposition=payload["unknown_outcome_disposition"],
                automatic_retry_disposition=payload["automatic_retry_disposition"],
                automatic_rollback_disposition=payload["automatic_rollback_disposition"],
                completion_verification_requirement=payload["completion_verification_requirement"],
                issued_at=datetime.fromisoformat(payload["issued_at"]),
                expires_at=datetime.fromisoformat(payload["expires_at"]),
                policy_digest=payload["policy_digest"],
                schema_version=payload["schema_version"],
            )
        except (KeyError, TypeError, ValueError, OutcomePolicyEvidenceError) as error:
            raise OutcomePolicyEvidenceError("invalid outcome policy payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class OutcomeSemanticsAssessmentRequest:
    """Exact immutable G2.4.18 evidence plus one policy declaration only."""

    assessment_request_id: str
    destination_contract_request: DestinationContractAssessmentRequest
    destination_contract_assessment: DestinationContractAssessment
    policy: ExternalOutcomeSemanticsPolicyEvidence
    timestamp: datetime
    transition_control_evidence: TransitionControlDecision | None = None
    request_digest: str | None = None
    schema_version: str = OUTCOME_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "assessment_request_id", require_identifier(self.assessment_request_id, "assessment_request_id"))
        for field_name, expected_type in (
            ("destination_contract_request", DestinationContractAssessmentRequest),
            ("destination_contract_assessment", DestinationContractAssessment),
            ("policy", ExternalOutcomeSemanticsPolicyEvidence),
        ):
            if not isinstance(getattr(self, field_name), expected_type):
                raise TypeError(f"{field_name} must be an immutable {expected_type.__name__}")
        if self.transition_control_evidence is not None and not isinstance(
            self.transition_control_evidence, TransitionControlDecision
        ):
            raise TypeError("transition_control_evidence must be a TransitionControlDecision or None")
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != OUTCOME_POLICY_SCHEMA_VERSION:
            raise OutcomePolicyEvidenceError("unsupported outcome policy request schema_version")
        calculated = self.calculate_digest()
        if self.request_digest is None:
            object.__setattr__(self, "request_digest", calculated)
        else:
            object.__setattr__(self, "request_digest", require_sha256(self.request_digest, "request_digest"))
            if self.request_digest != calculated:
                raise OutcomePolicyEvidenceError("request_digest does not match canonical outcome policy request")

    def calculate_digest(self) -> str:
        return canonical_digest(_request_payload(self))

    def to_payload(self) -> dict[str, Any]:
        return {**_request_payload(self), "request_digest": self.request_digest}


@dataclass(frozen=True, slots=True, kw_only=True)
class OutcomeSemanticsFinding:
    """One typed policy/evidence finding with no operational remediation."""

    code: OutcomePolicyFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, OutcomePolicyFindingCode):
            raise TypeError("code must be an OutcomePolicyFindingCode")
        object.__setattr__(self, "evidence_reference", require_non_empty(self.evidence_reference, "evidence_reference"))

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class OutcomeSemanticsAssessment:
    """Immutable policy-only assessment; never an outcome, receipt, or completion record."""

    assessment_id: str
    destination_identity: str
    policy_id: str | None
    disposition: OutcomePolicyDisposition
    findings: tuple[OutcomeSemanticsFinding, ...]
    evidence_refs: tuple[str, ...]
    recommendations: tuple[str, ...]
    assessment_digest: str
    timestamp: datetime
    schema_version: str = OUTCOME_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "assessment_id", require_identifier(self.assessment_id, "assessment_id"))
        object.__setattr__(self, "destination_identity", require_identifier(self.destination_identity, "destination_identity"))
        if self.policy_id is not None:
            object.__setattr__(self, "policy_id", require_identifier(self.policy_id, "policy_id"))
        if not isinstance(self.disposition, OutcomePolicyDisposition):
            raise TypeError("disposition must be an OutcomePolicyDisposition")
        if any(not isinstance(item, OutcomeSemanticsFinding) for item in self.findings):
            raise TypeError("findings must contain OutcomeSemanticsFinding values")
        finding_keys = tuple((item.code.value, item.evidence_reference) for item in self.findings)
        if finding_keys != tuple(sorted(finding_keys)) or len(set(finding_keys)) != len(finding_keys):
            raise OutcomePolicyEvidenceError("findings must be strictly ordered and unique")
        object.__setattr__(self, "evidence_refs", _ordered_unique_values(self.evidence_refs, "evidence_refs"))
        object.__setattr__(self, "recommendations", _ordered_unique_values(self.recommendations, "recommendations"))
        object.__setattr__(self, "assessment_digest", require_sha256(self.assessment_digest, "assessment_digest"))
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != OUTCOME_POLICY_SCHEMA_VERSION:
            raise OutcomePolicyEvidenceError("unsupported outcome policy assessment schema_version")
        if self.assessment_digest != self.calculate_digest():
            raise OutcomePolicyEvidenceError("assessment_digest does not match canonical outcome policy assessment")

    @classmethod
    def issue(
        cls,
        *,
        assessment_id: str,
        destination_identity: str,
        policy_id: str | None,
        disposition: OutcomePolicyDisposition,
        findings: tuple[OutcomeSemanticsFinding, ...],
        evidence_refs: tuple[str, ...],
        recommendations: tuple[str, ...],
        timestamp: datetime,
    ) -> OutcomeSemanticsAssessment:
        canonical_time = canonical_timestamp(timestamp, "timestamp")
        payload = _assessment_payload(
            assessment_id=assessment_id,
            destination_identity=destination_identity,
            policy_id=policy_id,
            disposition=disposition,
            findings=findings,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            timestamp=canonical_time,
            schema_version=OUTCOME_POLICY_SCHEMA_VERSION,
        )
        return cls(
            assessment_id=assessment_id,
            destination_identity=destination_identity,
            policy_id=policy_id,
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
                destination_identity=self.destination_identity,
                policy_id=self.policy_id,
                disposition=self.disposition,
                findings=self.findings,
                evidence_refs=self.evidence_refs,
                recommendations=self.recommendations,
                timestamp=self.timestamp,
                schema_version=self.schema_version,
            )
        )


def _policy_payload(
    *,
    outcome_policy_id: str,
    destination_contract_id: str,
    destination_contract_digest: str,
    destination_contract_assessment_id: str,
    destination_contract_assessment_digest: str,
    destination_identity: str,
    operation_profile: OutcomePolicyProfile | str,
    destination_operation_profile: DestinationOperationProfile | str,
    external_receipt_schema_id: DestinationReceiptSchema | str,
    destination_idempotency_profile: DestinationIdempotencyProfile | str,
    future_receipt_classes: tuple[FutureReceiptClass | str, ...],
    unknown_outcome_disposition: UnknownOutcomeDisposition | str,
    automatic_retry_disposition: AutomaticRetryDisposition | str,
    automatic_rollback_disposition: AutomaticRollbackDisposition | str,
    completion_verification_requirement: CompletionVerificationRequirement | str,
    issued_at: datetime,
    expires_at: datetime,
    schema_version: str,
) -> dict[str, Any]:
    return {
        "automatic_retry_disposition": _enum_value(automatic_retry_disposition, "automatic_retry_disposition"),
        "automatic_rollback_disposition": _enum_value(automatic_rollback_disposition, "automatic_rollback_disposition"),
        "completion_verification_requirement": _enum_value(
            completion_verification_requirement, "completion_verification_requirement"
        ),
        "destination_contract_assessment_digest": require_sha256(
            destination_contract_assessment_digest, "destination_contract_assessment_digest"
        ),
        "destination_contract_assessment_id": require_identifier(
            destination_contract_assessment_id, "destination_contract_assessment_id"
        ),
        "destination_contract_digest": require_sha256(destination_contract_digest, "destination_contract_digest"),
        "destination_contract_id": require_identifier(destination_contract_id, "destination_contract_id"),
        "destination_idempotency_profile": _enum_value(
            destination_idempotency_profile, "destination_idempotency_profile"
        ),
        "destination_identity": require_identifier(destination_identity, "destination_identity"),
        "destination_operation_profile": _enum_value(destination_operation_profile, "destination_operation_profile"),
        "expires_at": canonical_timestamp(expires_at, "expires_at").isoformat(),
        "external_receipt_schema_id": _enum_value(external_receipt_schema_id, "external_receipt_schema_id"),
        "future_receipt_classes": list(_ordered_unique_values(future_receipt_classes, "future_receipt_classes")),
        "issued_at": canonical_timestamp(issued_at, "issued_at").isoformat(),
        "operation_profile": _enum_value(operation_profile, "operation_profile"),
        "outcome_policy_id": require_identifier(outcome_policy_id, "outcome_policy_id"),
        "schema_version": schema_version,
        "unknown_outcome_disposition": _enum_value(unknown_outcome_disposition, "unknown_outcome_disposition"),
    }


def _request_payload(request: OutcomeSemanticsAssessmentRequest) -> dict[str, Any]:
    contract_request = request.destination_contract_request
    contract_assessment = request.destination_contract_assessment
    policy = request.policy
    control = request.transition_control_evidence
    return {
        "destination_contract_assessment": {
            "assessment_digest": contract_assessment.assessment_digest,
            "assessment_id": contract_assessment.assessment_id,
            "disposition": contract_assessment.disposition.value,
            "schema_version": contract_assessment.schema_version,
        },
        "destination_contract_request": {
            "request_digest": contract_request.request_digest,
            "schema_version": contract_request.schema_version,
        },
        "policy": {
            "outcome_policy_id": policy.outcome_policy_id,
            "policy_digest": policy.policy_digest,
            "schema_version": policy.schema_version,
        },
        "schema_version": request.schema_version,
        "timestamp": request.timestamp.isoformat(),
        "transition_control_evidence": None
        if control is None
        else {
            "control_key": control.control_key,
            "decision_digest": control.decision_digest,
            "decision_id": control.decision_id,
            "schema_version": control.schema_version,
        },
    }


def _assessment_payload(
    *,
    assessment_id: str,
    destination_identity: str,
    policy_id: str | None,
    disposition: OutcomePolicyDisposition,
    findings: tuple[OutcomeSemanticsFinding, ...],
    evidence_refs: tuple[str, ...],
    recommendations: tuple[str, ...],
    timestamp: datetime,
    schema_version: str,
) -> dict[str, Any]:
    return {
        "assessment_id": assessment_id,
        "destination_identity": destination_identity,
        "disposition": disposition.value,
        "evidence_refs": list(evidence_refs),
        "findings": [item.to_payload() for item in findings],
        "policy_id": policy_id,
        "recommendations": list(recommendations),
        "schema_version": schema_version,
        "timestamp": canonical_timestamp(timestamp, "timestamp").isoformat(),
    }


__all__ = [
    "AutomaticRetryDisposition",
    "AutomaticRollbackDisposition",
    "CompletionVerificationRequirement",
    "ExternalOutcomeSemanticsPolicyEvidence",
    "FutureReceiptClass",
    "OutcomePolicyDisposition",
    "OutcomePolicyEvidenceError",
    "OutcomePolicyFindingCode",
    "OutcomePolicyProfile",
    "OutcomeSemanticsAssessment",
    "OutcomeSemanticsAssessmentRequest",
    "OutcomeSemanticsFinding",
    "UnknownOutcomeDisposition",
]
