"""Deterministic fixture support for G2.4.19 outcome-semantics policy evidence tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from eag.governed_destination_contract import (
    DestinationContractAssessment,
    DestinationContractAssessmentRequest,
    DestinationContractAssessor,
)
from eag.governed_outcome_policy import (
    AutomaticRetryDisposition,
    AutomaticRollbackDisposition,
    CompletionVerificationRequirement,
    ExternalOutcomeSemanticsPolicyEvidence,
    FutureReceiptClass,
    OutcomePolicyProfile,
    OutcomeSemanticsAssessmentRequest,
    UnknownOutcomeDisposition,
)
from eag.governed_transition_control import TransitionControlDecision
from test_support.g2_4_18_destination_contract_fixture import (
    DestinationContractFixture,
    destination_contract_fixture,
)
from test_support.g2_4_18_destination_contract_fixture import (
    assessment_request as destination_assessment_request,
)


@dataclass(frozen=True, slots=True)
class OutcomePolicyFixture:
    """Exact public G2.4.18 evidence plus one safe immutable policy declaration."""

    destination_fixture: DestinationContractFixture
    destination_request: DestinationContractAssessmentRequest
    destination_assessment: DestinationContractAssessment
    policy: ExternalOutcomeSemanticsPolicyEvidence
    timestamp: datetime


def outcome_policy_fixture(*, identity: str = "outcome-policy") -> OutcomePolicyFixture:
    """Build valid public evidence without operational access or durable state."""
    destination_fixture_data = destination_contract_fixture(identity=identity)
    timestamp = destination_fixture_data.timestamp
    destination_request = destination_assessment_request(
        destination_fixture_data, assessment_request_id=f"g2419-destination-request-{identity}"
    )
    destination_assessment = DestinationContractAssessor().assess(
        assessment_id=f"g2419-destination-assessment-{identity}", request=destination_request
    )
    contract = destination_fixture_data.contract
    policy = ExternalOutcomeSemanticsPolicyEvidence.issue(
        outcome_policy_id=f"g2419-outcome-policy-{identity}",
        destination_contract_id=contract.destination_contract_id,
        destination_contract_digest=contract.contract_digest,
        destination_contract_assessment_id=destination_assessment.assessment_id,
        destination_contract_assessment_digest=destination_assessment.assessment_digest,
        destination_identity=contract.destination_identity,
        operation_profile=OutcomePolicyProfile.EXTERNAL_ARTIFACT_OUTCOME_POLICY_V1,
        destination_operation_profile=contract.operation_profile,
        external_receipt_schema_id=contract.external_receipt_schema_id,
        destination_idempotency_profile=contract.destination_idempotency_profile,
        future_receipt_classes=tuple(sorted(item.value for item in FutureReceiptClass)),
        unknown_outcome_disposition=UnknownOutcomeDisposition.STOP_AND_RECONCILIATION_REQUIRED,
        automatic_retry_disposition=AutomaticRetryDisposition.FORBIDDEN,
        automatic_rollback_disposition=AutomaticRollbackDisposition.FORBIDDEN,
        completion_verification_requirement=(
            CompletionVerificationRequirement.FUTURE_RECEIPT_VERIFICATION_REQUIRED
        ),
        issued_at=timestamp,
        expires_at=timestamp + timedelta(minutes=20),
    )
    return OutcomePolicyFixture(
        destination_fixture=destination_fixture_data,
        destination_request=destination_request,
        destination_assessment=destination_assessment,
        policy=policy,
        timestamp=timestamp,
    )


def outcome_assessment_request(
    fixture: OutcomePolicyFixture,
    *,
    assessment_request_id: str = "g2419-assessment-request",
    destination_request: DestinationContractAssessmentRequest | None = None,
    destination_assessment: DestinationContractAssessment | None = None,
    policy: ExternalOutcomeSemanticsPolicyEvidence | None = None,
    timestamp: datetime | None = None,
    transition_control_evidence: TransitionControlDecision | None = None,
    schema_version: str = "g2.4.19.outcome-semantics-policy.v1",
    request_digest: str | None = None,
) -> OutcomeSemanticsAssessmentRequest:
    """Build only valid-typed immutable requests; invalid type tests construct directly."""
    return OutcomeSemanticsAssessmentRequest(
        assessment_request_id=assessment_request_id,
        destination_contract_request=(
            fixture.destination_request if destination_request is None else destination_request
        ),
        destination_contract_assessment=(
            fixture.destination_assessment if destination_assessment is None else destination_assessment
        ),
        policy=fixture.policy if policy is None else policy,
        timestamp=fixture.timestamp if timestamp is None else timestamp,
        transition_control_evidence=transition_control_evidence,
        schema_version=schema_version,
        request_digest=request_digest,
    )


def policy_variant(
    policy: ExternalOutcomeSemanticsPolicyEvidence,
    **changes: object,
) -> ExternalOutcomeSemanticsPolicyEvidence:
    """Reissue policy evidence through the public constructor with selected changes only."""
    return ExternalOutcomeSemanticsPolicyEvidence.issue(
        outcome_policy_id=changes.get("outcome_policy_id", policy.outcome_policy_id),
        destination_contract_id=changes.get("destination_contract_id", policy.destination_contract_id),
        destination_contract_digest=changes.get(
            "destination_contract_digest", policy.destination_contract_digest
        ),
        destination_contract_assessment_id=changes.get(
            "destination_contract_assessment_id", policy.destination_contract_assessment_id
        ),
        destination_contract_assessment_digest=changes.get(
            "destination_contract_assessment_digest", policy.destination_contract_assessment_digest
        ),
        destination_identity=changes.get("destination_identity", policy.destination_identity),
        operation_profile=changes.get("operation_profile", policy.operation_profile),
        destination_operation_profile=changes.get(
            "destination_operation_profile", policy.destination_operation_profile
        ),
        external_receipt_schema_id=changes.get(
            "external_receipt_schema_id", policy.external_receipt_schema_id
        ),
        destination_idempotency_profile=changes.get(
            "destination_idempotency_profile", policy.destination_idempotency_profile
        ),
        future_receipt_classes=changes.get("future_receipt_classes", policy.future_receipt_classes),
        unknown_outcome_disposition=changes.get(
            "unknown_outcome_disposition", policy.unknown_outcome_disposition
        ),
        automatic_retry_disposition=changes.get(
            "automatic_retry_disposition", policy.automatic_retry_disposition
        ),
        automatic_rollback_disposition=changes.get(
            "automatic_rollback_disposition", policy.automatic_rollback_disposition
        ),
        completion_verification_requirement=changes.get(
            "completion_verification_requirement", policy.completion_verification_requirement
        ),
        issued_at=changes.get("issued_at", policy.issued_at),
        expires_at=changes.get("expires_at", policy.expires_at),
    )


__all__ = [
    "OutcomePolicyFixture",
    "outcome_assessment_request",
    "outcome_policy_fixture",
    "policy_variant",
]
