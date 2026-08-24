"""Immutable evidence-only contracts for G2.4.18 destination contract assessment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from eag.governed_destination_contract.canonical import (
    DESTINATION_CONTRACT_ASSESSMENT_SCHEMA_VERSION,
    DESTINATION_CONTRACT_SCHEMA_VERSION,
    DestinationContractEvidenceError,
    canonical_digest,
    canonical_timestamp,
    require_identifier,
    require_non_empty,
    require_sha256,
)
from eag.governed_promotion import PromotionEligibilityAssessment, PromotionEligibilityRequest
from eag.governed_transition_authorization import (
    ExternalTransitionAuthorizationReceipt,
    ExternalTransitionIntentEvidence,
    TransitionAuthorizationAssessment,
)
from eag.governed_transition_control import TransitionControlDecision


class DestinationContractProfile(StrEnum):
    """The supported declared profile, bound exactly to G2.4.16 transition evidence."""

    EXTERNAL_ARTIFACT_TRANSITION_V1 = "external_artifact_transition_v1"


class DestinationOperationProfile(StrEnum):
    """A declaration only; it does not create an executable operation."""

    EXTERNAL_ARTIFACT_TRANSFER_V1 = "external_artifact_transfer_v1"


class DestinationRequestSchema(StrEnum):
    """Non-executable identifier for a future external request schema."""

    EXTERNAL_ARTIFACT_REQUEST_V1 = "external_artifact_request_v1"


class DestinationReceiptSchema(StrEnum):
    """Non-executable identifier for a future external receipt schema."""

    EXTERNAL_ARTIFACT_RECEIPT_V1 = "external_artifact_receipt_v1"


class DestinationIdempotencyProfile(StrEnum):
    """Declared future destination idempotency capability; never a live guarantee."""

    DESTINATION_IDEMPOTENCY_DECLARATION_V1 = "destination_idempotency_declaration_v1"


class DestinationContractDisposition(StrEnum):
    """Evidence-only outcomes that neither authorize nor execute an operation."""

    CONTRACT_ATTESTED = "contract_attested"
    NOT_ATTESTED = "not_attested"
    UNSUPPORTED_DESTINATION_CONTRACT = "unsupported_destination_contract"


class DestinationContractFindingCode(StrEnum):
    """Typed deterministic findings with no destination or provider output."""

    CONTRACT_MISSING = "contract_missing"
    CONTRACT_EVIDENCE_INVALID = "contract_evidence_invalid"
    CONTRACT_EXPIRED = "contract_expired"
    CONTRACT_DESTINATION_MISMATCH = "contract_destination_mismatch"
    CONTRACT_POLICY_MISMATCH = "contract_policy_mismatch"
    ELIGIBILITY_EVIDENCE_INVALID = "eligibility_evidence_invalid"
    ELIGIBILITY_BINDING_MISMATCH = "eligibility_binding_mismatch"
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_EVIDENCE_INVALID = "authorization_evidence_invalid"
    AUTHORIZATION_DENIED = "authorization_denied"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    AUTHORIZATION_BINDING_MISMATCH = "authorization_binding_mismatch"
    TRANSITION_BINDING_MISMATCH = "transition_binding_mismatch"
    ARTIFACT_IDENTITY_MISMATCH = "artifact_identity_mismatch"
    EXECUTION_RUN_BINDING_MISMATCH = "execution_run_binding_mismatch"
    ASSESSMENT_BINDING_MISMATCH = "assessment_binding_mismatch"
    ISSUER_REFERENCE_INVALID = "issuer_reference_invalid"
    TRANSITION_CONTROL_AMBIGUOUS = "transition_control_ambiguous"
    UNSUPPORTED_PROFILE = "unsupported_profile"


def _ordered_unique_strings(
    values: tuple[str, ...], field_name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise DestinationContractEvidenceError(f"{field_name} must be a tuple")
    normalized = tuple(require_non_empty(value, field_name) for value in values)
    if not allow_empty and not normalized:
        raise DestinationContractEvidenceError(f"{field_name} cannot be empty")
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise DestinationContractEvidenceError(f"{field_name} must be strictly ordered and unique")
    return normalized


def _profile_value(value: StrEnum | str, field_name: str) -> str:
    if not isinstance(value, (StrEnum, str)):
        raise DestinationContractEvidenceError(f"{field_name} must be a declaration identifier")
    return require_identifier(value.value if isinstance(value, StrEnum) else value, field_name)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalDestinationContractEvidence:
    """Immutable non-secret declaration for a future destination-facing contract.

    It neither asserts live destination truth nor exposes a client, endpoint, account,
    secret, credential, request payload, release state, or external receipt.
    """

    destination_contract_id: str
    destination_identity: str
    artifact_id: str
    artifact_fingerprint: str
    promotion_assessment_id: str
    promotion_assessment_digest: str
    transition_intent_id: str
    authorization_id: str
    authorization_binding_digest: str
    authorization_assessment_id: str
    authorization_assessment_digest: str
    promotion_policy_digest: str
    authorization_policy_digest: str
    execution_id: str | None
    run_id: str | None
    transition_profile: DestinationContractProfile | str
    operation_profile: DestinationOperationProfile | str
    external_request_schema_id: DestinationRequestSchema | str
    external_receipt_schema_id: DestinationReceiptSchema | str
    destination_idempotency_profile: DestinationIdempotencyProfile | str
    destination_policy_digest: str
    attestation_issuer_identity: str
    attestation_reference: str
    issued_at: datetime
    expires_at: datetime
    contract_digest: str
    schema_version: str = DESTINATION_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "destination_contract_id",
            "destination_identity",
            "artifact_id",
            "promotion_assessment_id",
            "transition_intent_id",
            "authorization_id",
            "authorization_assessment_id",
            "attestation_issuer_identity",
            "attestation_reference",
        ):
            object.__setattr__(self, field_name, require_identifier(getattr(self, field_name), field_name))
        for field_name in (
            "transition_profile",
            "operation_profile",
            "external_request_schema_id",
            "external_receipt_schema_id",
            "destination_idempotency_profile",
        ):
            object.__setattr__(self, field_name, _profile_value(getattr(self, field_name), field_name))
        for field_name in (
            "artifact_fingerprint",
            "promotion_assessment_digest",
            "authorization_binding_digest",
            "authorization_assessment_digest",
            "promotion_policy_digest",
            "authorization_policy_digest",
            "destination_policy_digest",
        ):
            object.__setattr__(self, field_name, require_sha256(getattr(self, field_name), field_name))
        for field_name in ("execution_id", "run_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_identifier(value, field_name))
        object.__setattr__(self, "issued_at", canonical_timestamp(self.issued_at, "issued_at"))
        object.__setattr__(self, "expires_at", canonical_timestamp(self.expires_at, "expires_at"))
        if self.expires_at <= self.issued_at:
            raise DestinationContractEvidenceError("expires_at must be after issued_at")
        if self.schema_version != DESTINATION_CONTRACT_SCHEMA_VERSION:
            raise DestinationContractEvidenceError("unsupported destination contract schema_version")
        object.__setattr__(self, "contract_digest", require_sha256(self.contract_digest, "contract_digest"))
        if self.contract_digest != self.calculate_digest():
            raise DestinationContractEvidenceError("contract_digest does not match canonical contract evidence")

    @classmethod
    def issue(
        cls,
        *,
        destination_contract_id: str,
        destination_identity: str,
        artifact_id: str,
        artifact_fingerprint: str,
        promotion_assessment_id: str,
        promotion_assessment_digest: str,
        transition_intent_id: str,
        authorization_id: str,
        authorization_binding_digest: str,
        authorization_assessment_id: str,
        authorization_assessment_digest: str,
        promotion_policy_digest: str,
        authorization_policy_digest: str,
        execution_id: str | None,
        run_id: str | None,
        transition_profile: DestinationContractProfile | str,
        operation_profile: DestinationOperationProfile | str,
        external_request_schema_id: DestinationRequestSchema | str,
        external_receipt_schema_id: DestinationReceiptSchema | str,
        destination_idempotency_profile: DestinationIdempotencyProfile | str,
        destination_policy_digest: str,
        attestation_issuer_identity: str,
        attestation_reference: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> ExternalDestinationContractEvidence:
        canonical_issued = canonical_timestamp(issued_at, "issued_at")
        canonical_expires = canonical_timestamp(expires_at, "expires_at")
        payload = _contract_payload(
            destination_contract_id=destination_contract_id,
            destination_identity=destination_identity,
            artifact_id=artifact_id,
            artifact_fingerprint=artifact_fingerprint,
            promotion_assessment_id=promotion_assessment_id,
            promotion_assessment_digest=promotion_assessment_digest,
            transition_intent_id=transition_intent_id,
            authorization_id=authorization_id,
            authorization_binding_digest=authorization_binding_digest,
            authorization_assessment_id=authorization_assessment_id,
            authorization_assessment_digest=authorization_assessment_digest,
            promotion_policy_digest=promotion_policy_digest,
            authorization_policy_digest=authorization_policy_digest,
            execution_id=execution_id,
            run_id=run_id,
            transition_profile=transition_profile,
            operation_profile=operation_profile,
            external_request_schema_id=external_request_schema_id,
            external_receipt_schema_id=external_receipt_schema_id,
            destination_idempotency_profile=destination_idempotency_profile,
            destination_policy_digest=destination_policy_digest,
            attestation_issuer_identity=attestation_issuer_identity,
            attestation_reference=attestation_reference,
            issued_at=canonical_issued,
            expires_at=canonical_expires,
            schema_version=DESTINATION_CONTRACT_SCHEMA_VERSION,
        )
        return cls(
            destination_contract_id=destination_contract_id,
            destination_identity=destination_identity,
            artifact_id=artifact_id,
            artifact_fingerprint=artifact_fingerprint,
            promotion_assessment_id=promotion_assessment_id,
            promotion_assessment_digest=promotion_assessment_digest,
            transition_intent_id=transition_intent_id,
            authorization_id=authorization_id,
            authorization_binding_digest=authorization_binding_digest,
            authorization_assessment_id=authorization_assessment_id,
            authorization_assessment_digest=authorization_assessment_digest,
            promotion_policy_digest=promotion_policy_digest,
            authorization_policy_digest=authorization_policy_digest,
            execution_id=execution_id,
            run_id=run_id,
            transition_profile=transition_profile,
            operation_profile=operation_profile,
            external_request_schema_id=external_request_schema_id,
            external_receipt_schema_id=external_receipt_schema_id,
            destination_idempotency_profile=destination_idempotency_profile,
            destination_policy_digest=destination_policy_digest,
            attestation_issuer_identity=attestation_issuer_identity,
            attestation_reference=attestation_reference,
            issued_at=canonical_issued,
            expires_at=canonical_expires,
            contract_digest=canonical_digest(payload),
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            _contract_payload(
                destination_contract_id=self.destination_contract_id,
                destination_identity=self.destination_identity,
                artifact_id=self.artifact_id,
                artifact_fingerprint=self.artifact_fingerprint,
                promotion_assessment_id=self.promotion_assessment_id,
                promotion_assessment_digest=self.promotion_assessment_digest,
                transition_intent_id=self.transition_intent_id,
                authorization_id=self.authorization_id,
                authorization_binding_digest=self.authorization_binding_digest,
                authorization_assessment_id=self.authorization_assessment_id,
                authorization_assessment_digest=self.authorization_assessment_digest,
                promotion_policy_digest=self.promotion_policy_digest,
                authorization_policy_digest=self.authorization_policy_digest,
                execution_id=self.execution_id,
                run_id=self.run_id,
                transition_profile=self.transition_profile,
                operation_profile=self.operation_profile,
                external_request_schema_id=self.external_request_schema_id,
                external_receipt_schema_id=self.external_receipt_schema_id,
                destination_idempotency_profile=self.destination_idempotency_profile,
                destination_policy_digest=self.destination_policy_digest,
                attestation_issuer_identity=self.attestation_issuer_identity,
                attestation_reference=self.attestation_reference,
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                schema_version=self.schema_version,
            )
        )

    def to_payload(self) -> dict[str, str | None]:
        """Return exact redacted durable-form evidence without operational material."""
        return {
            **_contract_payload(
                destination_contract_id=self.destination_contract_id,
                destination_identity=self.destination_identity,
                artifact_id=self.artifact_id,
                artifact_fingerprint=self.artifact_fingerprint,
                promotion_assessment_id=self.promotion_assessment_id,
                promotion_assessment_digest=self.promotion_assessment_digest,
                transition_intent_id=self.transition_intent_id,
                authorization_id=self.authorization_id,
                authorization_binding_digest=self.authorization_binding_digest,
                authorization_assessment_id=self.authorization_assessment_id,
                authorization_assessment_digest=self.authorization_assessment_digest,
                promotion_policy_digest=self.promotion_policy_digest,
                authorization_policy_digest=self.authorization_policy_digest,
                execution_id=self.execution_id,
                run_id=self.run_id,
                transition_profile=self.transition_profile,
                operation_profile=self.operation_profile,
                external_request_schema_id=self.external_request_schema_id,
                external_receipt_schema_id=self.external_receipt_schema_id,
                destination_idempotency_profile=self.destination_idempotency_profile,
                destination_policy_digest=self.destination_policy_digest,
                attestation_issuer_identity=self.attestation_issuer_identity,
                attestation_reference=self.attestation_reference,
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                schema_version=self.schema_version,
            ),
            "contract_digest": self.contract_digest,
        }

    @classmethod
    def from_payload(cls, payload: object) -> ExternalDestinationContractEvidence:
        """Parse only exact complete destination-contract evidence."""
        required = {
            "artifact_fingerprint",
            "artifact_id",
            "attestation_issuer_identity",
            "attestation_reference",
            "authorization_assessment_digest",
            "authorization_assessment_id",
            "authorization_binding_digest",
            "authorization_id",
            "authorization_policy_digest",
            "contract_digest",
            "destination_contract_id",
            "destination_idempotency_profile",
            "destination_identity",
            "destination_policy_digest",
            "execution_id",
            "expires_at",
            "external_receipt_schema_id",
            "external_request_schema_id",
            "issued_at",
            "operation_profile",
            "promotion_assessment_digest",
            "promotion_assessment_id",
            "promotion_policy_digest",
            "run_id",
            "schema_version",
            "transition_intent_id",
            "transition_profile",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise DestinationContractEvidenceError("destination contract payload has unexpected fields")
        try:
            return cls(
                destination_contract_id=payload["destination_contract_id"],
                destination_identity=payload["destination_identity"],
                artifact_id=payload["artifact_id"],
                artifact_fingerprint=payload["artifact_fingerprint"],
                promotion_assessment_id=payload["promotion_assessment_id"],
                promotion_assessment_digest=payload["promotion_assessment_digest"],
                transition_intent_id=payload["transition_intent_id"],
                authorization_id=payload["authorization_id"],
                authorization_binding_digest=payload["authorization_binding_digest"],
                authorization_assessment_id=payload["authorization_assessment_id"],
                authorization_assessment_digest=payload["authorization_assessment_digest"],
                promotion_policy_digest=payload["promotion_policy_digest"],
                authorization_policy_digest=payload["authorization_policy_digest"],
                execution_id=payload["execution_id"],
                run_id=payload["run_id"],
                transition_profile=payload["transition_profile"],
                operation_profile=payload["operation_profile"],
                external_request_schema_id=payload["external_request_schema_id"],
                external_receipt_schema_id=payload["external_receipt_schema_id"],
                destination_idempotency_profile=payload["destination_idempotency_profile"],
                destination_policy_digest=payload["destination_policy_digest"],
                attestation_issuer_identity=payload["attestation_issuer_identity"],
                attestation_reference=payload["attestation_reference"],
                issued_at=datetime.fromisoformat(payload["issued_at"]),
                expires_at=datetime.fromisoformat(payload["expires_at"]),
                contract_digest=payload["contract_digest"],
                schema_version=payload["schema_version"],
            )
        except (KeyError, TypeError, ValueError, DestinationContractEvidenceError) as error:
            raise DestinationContractEvidenceError("invalid destination contract payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class DestinationContractAssessmentRequest:
    """Self-validating immutable bundle of exact public evidence contracts only.

    Raw mappings and arbitrary objects are intentionally excluded. This contract binds
    published G2.4.15–G2.4.17 evidence without reparsing or recreating their semantics.
    """

    assessment_request_id: str
    promotion_request: PromotionEligibilityRequest
    promotion_assessment: PromotionEligibilityAssessment
    transition_intent: ExternalTransitionIntentEvidence
    authorization: ExternalTransitionAuthorizationReceipt
    authorization_assessment: TransitionAuthorizationAssessment
    contract: ExternalDestinationContractEvidence
    timestamp: datetime
    transition_control_evidence: TransitionControlDecision | None = None
    request_digest: str | None = None
    schema_version: str = DESTINATION_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "assessment_request_id", require_identifier(self.assessment_request_id, "assessment_request_id"))
        for field_name, expected_type in (
            ("promotion_request", PromotionEligibilityRequest),
            ("promotion_assessment", PromotionEligibilityAssessment),
            ("transition_intent", ExternalTransitionIntentEvidence),
            ("authorization", ExternalTransitionAuthorizationReceipt),
            ("authorization_assessment", TransitionAuthorizationAssessment),
            ("contract", ExternalDestinationContractEvidence),
        ):
            if not isinstance(getattr(self, field_name), expected_type):
                raise TypeError(f"{field_name} must be an immutable {expected_type.__name__}")
        if self.transition_control_evidence is not None and not isinstance(
            self.transition_control_evidence, TransitionControlDecision
        ):
            raise TypeError("transition_control_evidence must be a TransitionControlDecision or None")
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != DESTINATION_CONTRACT_SCHEMA_VERSION:
            raise DestinationContractEvidenceError("unsupported destination contract request schema_version")
        calculated_digest = self.calculate_digest()
        if self.request_digest is None:
            object.__setattr__(self, "request_digest", calculated_digest)
        else:
            object.__setattr__(self, "request_digest", require_sha256(self.request_digest, "request_digest"))
            if self.request_digest != calculated_digest:
                raise DestinationContractEvidenceError(
                    "request_digest does not match canonical destination contract request"
                )

    def calculate_digest(self) -> str:
        return canonical_digest(_request_payload(self))

    def to_payload(self) -> dict[str, object]:
        """Return exact canonical evidence references without raw mappings or handles."""
        return {**_request_payload(self), "request_digest": self.request_digest}


def _declaration_value(value: StrEnum | str) -> str:
    return value.value if isinstance(value, StrEnum) else value


def _request_payload(request: DestinationContractAssessmentRequest) -> dict[str, object]:
    """Canonical reference-only representation of all authoritative request inputs."""
    promotion_request = request.promotion_request
    promotion_assessment = request.promotion_assessment
    intent = request.transition_intent
    authorization = request.authorization
    authorization_assessment = request.authorization_assessment
    contract = request.contract
    control = request.transition_control_evidence
    return {
        "authorization": {
            "authorization_binding_digest": authorization.binding_digest,
            "authorization_id": authorization.authorization_id,
            "schema_version": authorization.schema_version,
        },
        "authorization_assessment": {
            "assessment_digest": authorization_assessment.assessment_digest,
            "assessment_id": authorization_assessment.assessment_id,
            "schema_version": authorization_assessment.schema_version,
        },
        "contract": {
            "contract_digest": contract.contract_digest,
            "destination_contract_id": contract.destination_contract_id,
            "schema_version": contract.schema_version,
        },
        "promotion_assessment": {
            "assessment_digest": promotion_assessment.assessment_digest,
            "assessment_id": promotion_assessment.assessment_id,
            "schema_version": promotion_assessment.schema_version,
        },
        "promotion_request": {
            "artifact_fingerprint": promotion_request.artifact_fingerprint,
            "artifact_id": promotion_request.artifact_id,
            "destination_identity": promotion_request.destination_identity,
            "intent_id": promotion_request.intent_id,
            "lineage_reference": promotion_request.lineage_reference,
            "promotion_policy_digest": promotion_request.promotion_policy_digest,
            "promotion_profile": _declaration_value(promotion_request.promotion_profile),
            "readiness_evidence_reference": promotion_request.readiness_evidence_reference,
            "schema_version": promotion_request.schema_version,
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
        "transition_intent": {
            "artifact_fingerprint": intent.artifact_fingerprint,
            "artifact_id": intent.artifact_id,
            "authorization_policy_digest": intent.authorization_policy_digest,
            "destination_identity": intent.destination_identity,
            "eligibility_assessment_digest": intent.eligibility_assessment_digest,
            "eligibility_assessment_id": intent.eligibility_assessment_id,
            "execution_id": intent.execution_id,
            "promotion_policy_digest": intent.promotion_policy_digest,
            "run_id": intent.run_id,
            "schema_version": intent.schema_version,
            "transition_intent_id": intent.transition_intent_id,
            "transition_profile": _declaration_value(intent.transition_profile),
        },
    }


@dataclass(frozen=True, slots=True, kw_only=True)
class DestinationContractFinding:
    """One typed non-sensitive refusal or evidence observation."""

    code: DestinationContractFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, DestinationContractFindingCode):
            raise TypeError("code must be a DestinationContractFindingCode")
        object.__setattr__(self, "evidence_reference", require_non_empty(self.evidence_reference, "evidence_reference"))

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class DestinationContractAssessment:
    """Immutable destination-contract assessment with exact typed parent-request provenance."""

    assessment_id: str
    assessed_request_id: str
    assessed_request_digest: str
    destination_identity: str
    contract_id: str | None
    disposition: DestinationContractDisposition
    findings: tuple[DestinationContractFinding, ...]
    evidence_refs: tuple[str, ...]
    recommendations: tuple[str, ...]
    assessment_digest: str
    timestamp: datetime
    schema_version: str = DESTINATION_CONTRACT_ASSESSMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "assessment_id", require_identifier(self.assessment_id, "assessment_id"))
        object.__setattr__(
            self,
            "assessed_request_id",
            require_identifier(self.assessed_request_id, "assessed_request_id"),
        )
        object.__setattr__(
            self,
            "assessed_request_digest",
            require_sha256(self.assessed_request_digest, "assessed_request_digest"),
        )
        object.__setattr__(self, "destination_identity", require_identifier(self.destination_identity, "destination_identity"))
        if self.contract_id is not None:
            object.__setattr__(self, "contract_id", require_identifier(self.contract_id, "contract_id"))
        if not isinstance(self.disposition, DestinationContractDisposition):
            raise TypeError("disposition must be a DestinationContractDisposition")
        if any(not isinstance(finding, DestinationContractFinding) for finding in self.findings):
            raise TypeError("findings must contain DestinationContractFinding values")
        finding_keys = tuple((finding.code.value, finding.evidence_reference) for finding in self.findings)
        if finding_keys != tuple(sorted(finding_keys)) or len(set(finding_keys)) != len(finding_keys):
            raise DestinationContractEvidenceError("findings must be strictly ordered and unique")
        object.__setattr__(self, "evidence_refs", _ordered_unique_strings(self.evidence_refs, "evidence_refs", allow_empty=True))
        object.__setattr__(self, "recommendations", _ordered_unique_strings(self.recommendations, "recommendations", allow_empty=True))
        object.__setattr__(self, "assessment_digest", require_sha256(self.assessment_digest, "assessment_digest"))
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != DESTINATION_CONTRACT_ASSESSMENT_SCHEMA_VERSION:
            raise DestinationContractEvidenceError("unsupported destination contract assessment schema_version")
        if self.assessment_digest != self.calculate_digest():
            raise DestinationContractEvidenceError("assessment_digest does not match canonical destination contract assessment")

    @classmethod
    def issue(
        cls,
        *,
        assessment_id: str,
        request: DestinationContractAssessmentRequest,
        destination_identity: str,
        contract_id: str | None,
        disposition: DestinationContractDisposition,
        findings: tuple[DestinationContractFinding, ...],
        evidence_refs: tuple[str, ...],
        recommendations: tuple[str, ...],
        timestamp: datetime,
    ) -> DestinationContractAssessment:
        if not isinstance(request, DestinationContractAssessmentRequest):
            raise TypeError("request must be a DestinationContractAssessmentRequest")
        request_digest = request.request_digest
        if request_digest is None:
            raise DestinationContractEvidenceError("request_digest must be self-validating")
        canonical_time = canonical_timestamp(timestamp, "timestamp")
        payload = _assessment_payload(
            assessment_id=assessment_id,
            assessed_request_id=request.assessment_request_id,
            assessed_request_digest=request_digest,
            destination_identity=destination_identity,
            contract_id=contract_id,
            disposition=disposition,
            findings=findings,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            timestamp=canonical_time,
            schema_version=DESTINATION_CONTRACT_ASSESSMENT_SCHEMA_VERSION,
        )
        return cls(
            assessment_id=assessment_id,
            assessed_request_id=request.assessment_request_id,
            assessed_request_digest=request_digest,
            destination_identity=destination_identity,
            contract_id=contract_id,
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
                assessed_request_id=self.assessed_request_id,
                assessed_request_digest=self.assessed_request_digest,
                destination_identity=self.destination_identity,
                contract_id=self.contract_id,
                disposition=self.disposition,
                findings=self.findings,
                evidence_refs=self.evidence_refs,
                recommendations=self.recommendations,
                timestamp=self.timestamp,
                schema_version=self.schema_version,
            )
        )


def _contract_payload(
    *,
    destination_contract_id: str,
    destination_identity: str,
    artifact_id: str,
    artifact_fingerprint: str,
    promotion_assessment_id: str,
    promotion_assessment_digest: str,
    transition_intent_id: str,
    authorization_id: str,
    authorization_binding_digest: str,
    authorization_assessment_id: str,
    authorization_assessment_digest: str,
    promotion_policy_digest: str,
    authorization_policy_digest: str,
    execution_id: str | None,
    run_id: str | None,
    transition_profile: DestinationContractProfile | str,
    operation_profile: DestinationOperationProfile | str,
    external_request_schema_id: DestinationRequestSchema | str,
    external_receipt_schema_id: DestinationReceiptSchema | str,
    destination_idempotency_profile: DestinationIdempotencyProfile | str,
    destination_policy_digest: str,
    attestation_issuer_identity: str,
    attestation_reference: str,
    issued_at: datetime,
    expires_at: datetime,
    schema_version: str,
) -> dict[str, str | None]:
    return {
        "artifact_fingerprint": require_sha256(artifact_fingerprint, "artifact_fingerprint"),
        "artifact_id": _profile_value(artifact_id, "artifact_id"),
        "attestation_issuer_identity": _profile_value(attestation_issuer_identity, "attestation_issuer_identity"),
        "attestation_reference": _profile_value(attestation_reference, "attestation_reference"),
        "authorization_assessment_digest": require_sha256(
            authorization_assessment_digest, "authorization_assessment_digest"
        ),
        "authorization_assessment_id": _profile_value(
            authorization_assessment_id, "authorization_assessment_id"
        ),
        "authorization_binding_digest": require_sha256(
            authorization_binding_digest, "authorization_binding_digest"
        ),
        "authorization_id": _profile_value(authorization_id, "authorization_id"),
        "authorization_policy_digest": require_sha256(
            authorization_policy_digest, "authorization_policy_digest"
        ),
        "destination_contract_id": _profile_value(destination_contract_id, "destination_contract_id"),
        "destination_idempotency_profile": _profile_value(
            destination_idempotency_profile, "destination_idempotency_profile"
        ),
        "destination_identity": _profile_value(destination_identity, "destination_identity"),
        "destination_policy_digest": require_sha256(destination_policy_digest, "destination_policy_digest"),
        "execution_id": None if execution_id is None else _profile_value(execution_id, "execution_id"),
        "expires_at": canonical_timestamp(expires_at, "expires_at").isoformat(),
        "external_receipt_schema_id": _profile_value(external_receipt_schema_id, "external_receipt_schema_id"),
        "external_request_schema_id": _profile_value(external_request_schema_id, "external_request_schema_id"),
        "issued_at": canonical_timestamp(issued_at, "issued_at").isoformat(),
        "operation_profile": _profile_value(operation_profile, "operation_profile"),
        "promotion_assessment_digest": require_sha256(promotion_assessment_digest, "promotion_assessment_digest"),
        "promotion_assessment_id": _profile_value(promotion_assessment_id, "promotion_assessment_id"),
        "promotion_policy_digest": require_sha256(promotion_policy_digest, "promotion_policy_digest"),
        "run_id": None if run_id is None else _profile_value(run_id, "run_id"),
        "schema_version": schema_version,
        "transition_intent_id": _profile_value(transition_intent_id, "transition_intent_id"),
        "transition_profile": _profile_value(transition_profile, "transition_profile"),
    }


def _assessment_payload(
    *,
    assessment_id: str,
    assessed_request_id: str,
    assessed_request_digest: str,
    destination_identity: str,
    contract_id: str | None,
    disposition: DestinationContractDisposition,
    findings: tuple[DestinationContractFinding, ...],
    evidence_refs: tuple[str, ...],
    recommendations: tuple[str, ...],
    timestamp: datetime,
    schema_version: str,
) -> dict[str, object]:
    return {
        "assessment_id": assessment_id,
        "assessed_request_digest": require_sha256(assessed_request_digest, "assessed_request_digest"),
        "assessed_request_id": require_identifier(assessed_request_id, "assessed_request_id"),
        "contract_id": contract_id,
        "destination_identity": destination_identity,
        "disposition": disposition.value,
        "evidence_refs": list(evidence_refs),
        "findings": [finding.to_payload() for finding in findings],
        "recommendations": list(recommendations),
        "schema_version": schema_version,
        "timestamp": canonical_timestamp(timestamp, "timestamp").isoformat(),
    }


__all__ = [
    "DestinationContractAssessment",
    "DestinationContractAssessmentRequest",
    "DestinationContractDisposition",
    "DestinationContractEvidenceError",
    "DestinationContractFinding",
    "DestinationContractFindingCode",
    "DestinationContractProfile",
    "DestinationIdempotencyProfile",
    "DestinationOperationProfile",
    "DestinationReceiptSchema",
    "DestinationRequestSchema",
    "ExternalDestinationContractEvidence",
]
