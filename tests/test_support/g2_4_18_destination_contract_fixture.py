"""Deterministic immutable fixture and observation support for G2.4.18 tests only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from eag.governed_destination_contract import (
    DestinationContractAssessment,
    DestinationContractAssessmentRequest,
    DestinationContractAssessor,
    DestinationContractProfile,
    DestinationIdempotencyProfile,
    DestinationOperationProfile,
    DestinationReceiptSchema,
    DestinationRequestSchema,
    ExternalDestinationContractEvidence,
)
from eag.governed_promotion import PromotionEligibilityAssessment, PromotionEligibilityRequest
from eag.governed_transition_authorization import (
    ExternalTransitionAuthorizationReceipt,
    ExternalTransitionIntentEvidence,
    TransitionAuthorizationAssessment,
    TransitionAuthorizationDisposition,
)
from eag.governed_transition_control import (
    ExternalTransitionControlRequest,
    TransitionControlDecision,
    TransitionControlDisposition,
    TransitionControlFinding,
    TransitionControlFindingCode,
    TransitionControlProfile,
)
from test_support.g2_4_16_transition_authorization_fixture import authorization_fixture


@dataclass(frozen=True, slots=True)
class DestinationContractFixture:
    """Exact published evidence plus one non-secret supplied contract declaration."""

    promotion_request: PromotionEligibilityRequest
    promotion_assessment: PromotionEligibilityAssessment
    transition_intent: ExternalTransitionIntentEvidence
    authorization: ExternalTransitionAuthorizationReceipt
    authorization_assessment: TransitionAuthorizationAssessment
    contract: ExternalDestinationContractEvidence
    ambiguous_control_evidence: TransitionControlDecision
    timestamp: datetime


@dataclass(slots=True)
class EffectSentinel:
    """Test-only counters for forbidden effect boundaries; production never receives this object."""

    provider_calls: int = 0
    upload_calls: int = 0
    network_calls: int = 0
    credential_access: int = 0
    workspace_mutations: int = 0
    command_executions: int = 0
    runtime_calls: int = 0
    session_creations: int = 0
    permit_issuance: int = 0
    transition_executions: int = 0
    audit_writes: int = 0
    destination_interactions: int = 0
    releases: int = 0
    publications: int = 0
    deployments: int = 0
    ledger_claims: int = 0
    ledger_reads: int = 0

    def snapshot(self) -> tuple[int, ...]:
        return (
            self.provider_calls, self.upload_calls, self.network_calls, self.credential_access,
            self.workspace_mutations, self.command_executions, self.runtime_calls,
            self.session_creations, self.permit_issuance, self.transition_executions,
            self.audit_writes, self.destination_interactions, self.releases, self.publications,
            self.deployments, self.ledger_claims, self.ledger_reads,
        )

    def assert_zero(self) -> None:
        assert self.snapshot() == (0,) * 17


def destination_contract_fixture(*, identity: str = "destination-contract") -> DestinationContractFixture:
    """Build exact public G2.4.15/G2.4.16/G2.4.17 evidence without operational access."""
    authorization_data = authorization_fixture(identity=identity)
    timestamp = authorization_data.timestamp
    authorization_assessment = TransitionAuthorizationAssessment.issue(
        assessment_id=f"g2418-authorization-assessment-{identity}",
        authorization_id=authorization_data.authorization.authorization_id,
        intent=authorization_data.intent,
        disposition=TransitionAuthorizationDisposition.AUTHORIZED,
        findings=(),
        evidence_refs=(f"g2418-authorization-evidence-{identity}",),
        recommendations=(),
        timestamp=timestamp,
    )
    contract = ExternalDestinationContractEvidence.issue(
        destination_contract_id=f"g2418-destination-contract-{identity}",
        destination_identity=authorization_data.intent.destination_identity,
        artifact_id=authorization_data.intent.artifact_id,
        artifact_fingerprint=authorization_data.intent.artifact_fingerprint,
        promotion_assessment_id=authorization_data.promotion_assessment.assessment_id,
        promotion_assessment_digest=authorization_data.promotion_assessment.assessment_digest,
        transition_intent_id=authorization_data.intent.transition_intent_id,
        authorization_id=authorization_data.authorization.authorization_id,
        authorization_binding_digest=authorization_data.authorization.binding_digest,
        authorization_assessment_id=authorization_assessment.assessment_id,
        authorization_assessment_digest=authorization_assessment.assessment_digest,
        promotion_policy_digest=authorization_data.intent.promotion_policy_digest,
        authorization_policy_digest=authorization_data.intent.authorization_policy_digest,
        execution_id=authorization_data.intent.execution_id,
        run_id=authorization_data.intent.run_id,
        transition_profile=DestinationContractProfile.EXTERNAL_ARTIFACT_TRANSITION_V1,
        operation_profile=DestinationOperationProfile.EXTERNAL_ARTIFACT_TRANSFER_V1,
        external_request_schema_id=DestinationRequestSchema.EXTERNAL_ARTIFACT_REQUEST_V1,
        external_receipt_schema_id=DestinationReceiptSchema.EXTERNAL_ARTIFACT_RECEIPT_V1,
        destination_idempotency_profile=DestinationIdempotencyProfile.DESTINATION_IDEMPOTENCY_DECLARATION_V1,
        destination_policy_digest=authorization_data.intent.promotion_policy_digest,
        attestation_issuer_identity="attester-fixture",
        attestation_reference=f"attestation-{identity}",
        issued_at=timestamp,
        expires_at=timestamp + timedelta(minutes=30),
    )
    control_request = ExternalTransitionControlRequest(
        control_request_id=f"g2418-control-request-{identity}",
        authorization_id=authorization_data.authorization.authorization_id,
        authorization_binding_digest=authorization_data.authorization.binding_digest,
        authorization_assessment_id=authorization_assessment.assessment_id,
        authorization_assessment_digest=authorization_assessment.assessment_digest,
        transition_intent_id=authorization_data.intent.transition_intent_id,
        artifact_id=authorization_data.intent.artifact_id,
        artifact_fingerprint=authorization_data.intent.artifact_fingerprint,
        destination_identity=authorization_data.intent.destination_identity,
        promotion_policy_digest=authorization_data.intent.promotion_policy_digest,
        authorization_policy_digest=authorization_data.intent.authorization_policy_digest,
        idempotency_key=authorization_data.intent.idempotency_key,
        transition_profile=TransitionControlProfile.EXTERNAL_ARTIFACT_TRANSITION_CONTROL_V1,
        occurred_at=timestamp,
        execution_id=authorization_data.intent.execution_id,
        run_id=authorization_data.intent.run_id,
    )
    ambiguous = TransitionControlDecision.issue(
        decision_id=f"g2418-ambiguous-control-{identity}", request=control_request,
        control_id=f"g2418-ambiguous-control-id-{identity}",
        disposition=TransitionControlDisposition.AMBIGUOUS,
        findings=(TransitionControlFinding(
            code=TransitionControlFindingCode.AMBIGUOUS_CONTROL,
            evidence_reference=control_request.control_key,
        ),),
        evidence_refs=(authorization_data.authorization.binding_digest,),
        recommendations=("stop; ambiguity has no G2.4.18 reconciliation authority",),
        timestamp=timestamp,
    )
    return DestinationContractFixture(
        promotion_request=authorization_data.promotion_request,
        promotion_assessment=authorization_data.promotion_assessment,
        transition_intent=authorization_data.intent,
        authorization=authorization_data.authorization,
        authorization_assessment=authorization_assessment,
        contract=contract,
        ambiguous_control_evidence=ambiguous,
        timestamp=timestamp,
    )


def assessment_request(
    fixture: DestinationContractFixture,
    *,
    assessment_request_id: str = "g2418-assessment-request",
    promotion_request: PromotionEligibilityRequest | None = None,
    promotion_assessment: PromotionEligibilityAssessment | None = None,
    transition_intent: ExternalTransitionIntentEvidence | None = None,
    authorization: ExternalTransitionAuthorizationReceipt | None = None,
    authorization_assessment: TransitionAuthorizationAssessment | None = None,
    contract: ExternalDestinationContractEvidence | None = None,
    timestamp: datetime | None = None,
    transition_control_evidence: TransitionControlDecision | None = None,
    schema_version: str = "g2.4.18.destination-contract.v1",
    request_digest: str | None = None,
) -> DestinationContractAssessmentRequest:
    """Build only a valid-typed immutable public request; invalid input tests construct directly."""
    return DestinationContractAssessmentRequest(
        assessment_request_id=assessment_request_id,
        promotion_request=fixture.promotion_request if promotion_request is None else promotion_request,
        promotion_assessment=fixture.promotion_assessment if promotion_assessment is None else promotion_assessment,
        transition_intent=fixture.transition_intent if transition_intent is None else transition_intent,
        authorization=fixture.authorization if authorization is None else authorization,
        authorization_assessment=fixture.authorization_assessment if authorization_assessment is None else authorization_assessment,
        contract=fixture.contract if contract is None else contract,
        timestamp=fixture.timestamp if timestamp is None else timestamp,
        transition_control_evidence=transition_control_evidence,
        schema_version=schema_version,
        request_digest=request_digest,
    )


def contract_variant(contract: ExternalDestinationContractEvidence, **changes: object) -> ExternalDestinationContractEvidence:
    """Reissue a contract through the public constructor with exactly selected changes."""
    return ExternalDestinationContractEvidence.issue(
        destination_contract_id=changes.get("destination_contract_id", contract.destination_contract_id),
        destination_identity=changes.get("destination_identity", contract.destination_identity),
        artifact_id=changes.get("artifact_id", contract.artifact_id),
        artifact_fingerprint=changes.get("artifact_fingerprint", contract.artifact_fingerprint),
        promotion_assessment_id=changes.get("promotion_assessment_id", contract.promotion_assessment_id),
        promotion_assessment_digest=changes.get("promotion_assessment_digest", contract.promotion_assessment_digest),
        transition_intent_id=changes.get("transition_intent_id", contract.transition_intent_id),
        authorization_id=changes.get("authorization_id", contract.authorization_id),
        authorization_binding_digest=changes.get("authorization_binding_digest", contract.authorization_binding_digest),
        authorization_assessment_id=changes.get("authorization_assessment_id", contract.authorization_assessment_id),
        authorization_assessment_digest=changes.get("authorization_assessment_digest", contract.authorization_assessment_digest),
        promotion_policy_digest=changes.get("promotion_policy_digest", contract.promotion_policy_digest),
        authorization_policy_digest=changes.get("authorization_policy_digest", contract.authorization_policy_digest),
        execution_id=changes.get("execution_id", contract.execution_id),
        run_id=changes.get("run_id", contract.run_id),
        transition_profile=changes.get("transition_profile", contract.transition_profile),
        operation_profile=changes.get("operation_profile", contract.operation_profile),
        external_request_schema_id=changes.get("external_request_schema_id", contract.external_request_schema_id),
        external_receipt_schema_id=changes.get("external_receipt_schema_id", contract.external_receipt_schema_id),
        destination_idempotency_profile=changes.get("destination_idempotency_profile", contract.destination_idempotency_profile),
        destination_policy_digest=changes.get("destination_policy_digest", contract.destination_policy_digest),
        attestation_issuer_identity=changes.get("attestation_issuer_identity", contract.attestation_issuer_identity),
        attestation_reference=changes.get("attestation_reference", contract.attestation_reference),
        issued_at=changes.get("issued_at", contract.issued_at),
        expires_at=changes.get("expires_at", contract.expires_at),
    )


def assess_without_progression(
    *, assessor: DestinationContractAssessor, request: DestinationContractAssessmentRequest,
    effects: EffectSentinel, temporary_root: Path,
) -> DestinationContractAssessment:
    """Call the real assessor and immediately prove supplied evidence and observed state did not progress."""
    before_effects = effects.snapshot()
    before_files = tuple(sorted(path.name for path in temporary_root.iterdir()))
    before_request = request.to_payload()
    result = assessor.assess(assessment_id=f"{request.assessment_request_id}-assessment", request=request)
    assert effects.snapshot() == before_effects
    assert tuple(sorted(path.name for path in temporary_root.iterdir())) == before_files
    assert request.to_payload() == before_request
    return result


__all__ = [
    "DestinationContractFixture", "EffectSentinel", "assessment_request", "assess_without_progression",
    "contract_variant", "destination_contract_fixture",
]
