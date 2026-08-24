"""Deterministic fixture support for G2.4.20 attestation-policy evidence tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from eag.governed_attestation_policy import (
    AttestationPolicyAssessmentRequest,
    AttestationPolicyProfile,
    DestinationContractAttestationPolicyEvidence,
)
from eag.governed_outcome_policy import (
    OutcomeSemanticsAssessment,
    OutcomeSemanticsAssessmentRequest,
    OutcomeSemanticsAssessor,
)
from test_support.g2_4_19_outcome_policy_fixture import (
    OutcomePolicyFixture,
    outcome_assessment_request,
    outcome_policy_fixture,
)


@dataclass(frozen=True, slots=True)
class AttestationPolicyFixture:
    """Exact public G2.4.18/G2.4.19 evidence plus one static policy declaration."""

    outcome_fixture: OutcomePolicyFixture
    outcome_request: OutcomeSemanticsAssessmentRequest
    outcome_assessment: OutcomeSemanticsAssessment
    policy: DestinationContractAttestationPolicyEvidence
    timestamp: datetime


def attestation_policy_fixture(*, identity: str = "attestation-policy") -> AttestationPolicyFixture:
    """Build valid public evidence without issuer authentication or external access."""
    outcome_fixture_data = outcome_policy_fixture(identity=identity)
    timestamp = outcome_fixture_data.timestamp
    outcome_request = outcome_assessment_request(
        outcome_fixture_data,
        assessment_request_id=f"g2420-outcome-request-{identity}",
    )
    outcome_assessment = OutcomeSemanticsAssessor().assess(
        assessment_id=f"g2420-outcome-assessment-{identity}",
        request=outcome_request,
    )
    contract = outcome_fixture_data.destination_fixture.contract
    policy = DestinationContractAttestationPolicyEvidence.issue(
        attestation_policy_id=f"g2420-attestation-policy-{identity}",
        destination_contract_id=contract.destination_contract_id,
        destination_contract_digest=contract.contract_digest,
        destination_contract_assessment_id=outcome_fixture_data.destination_assessment.assessment_id,
        destination_contract_assessment_digest=outcome_fixture_data.destination_assessment.assessment_digest,
        outcome_policy_id=outcome_fixture_data.policy.outcome_policy_id,
        outcome_policy_digest=outcome_fixture_data.policy.policy_digest,
        outcome_policy_assessment_id=outcome_assessment.assessment_id,
        outcome_policy_assessment_digest=outcome_assessment.assessment_digest,
        destination_identity=contract.destination_identity,
        declared_attestation_issuer_identity=contract.attestation_issuer_identity,
        declared_attestation_reference=contract.attestation_reference,
        attestation_policy_profile=AttestationPolicyProfile.DECLARED_ATTESTATION_POLICY_V1,
        issued_at=timestamp,
        expires_at=timestamp + timedelta(minutes=10),
    )
    return AttestationPolicyFixture(
        outcome_fixture=outcome_fixture_data,
        outcome_request=outcome_request,
        outcome_assessment=outcome_assessment,
        policy=policy,
        timestamp=timestamp,
    )


def assessment_request(
    fixture: AttestationPolicyFixture,
    *,
    assessment_request_id: str = "g2420-assessment-request",
    outcome_request: OutcomeSemanticsAssessmentRequest | None = None,
    outcome_assessment: OutcomeSemanticsAssessment | None = None,
    policy: DestinationContractAttestationPolicyEvidence | None = None,
    timestamp: datetime | None = None,
    schema_version: str = "g2.4.20.destination-contract-attestation-policy.v1",
    request_digest: str | None = None,
) -> AttestationPolicyAssessmentRequest:
    """Build valid exact-typed requests; invalid type tests construct directly."""
    selected_outcome_request = fixture.outcome_request if outcome_request is None else outcome_request
    selected_outcome_assessment = fixture.outcome_assessment if outcome_assessment is None else outcome_assessment
    return AttestationPolicyAssessmentRequest(
        assessment_request_id=assessment_request_id,
        destination_contract_request=fixture.outcome_fixture.destination_request,
        destination_contract_assessment=fixture.outcome_fixture.destination_assessment,
        outcome_policy_request=selected_outcome_request,
        outcome_policy_assessment=selected_outcome_assessment,
        policy=fixture.policy if policy is None else policy,
        timestamp=fixture.timestamp if timestamp is None else timestamp,
        schema_version=schema_version,
        request_digest=request_digest,
    )


def policy_variant(
    policy: DestinationContractAttestationPolicyEvidence,
    **changes: object,
) -> DestinationContractAttestationPolicyEvidence:
    """Reissue attestation-policy evidence through the public constructor."""
    return DestinationContractAttestationPolicyEvidence.issue(
        attestation_policy_id=changes.get("attestation_policy_id", policy.attestation_policy_id),
        destination_contract_id=changes.get("destination_contract_id", policy.destination_contract_id),
        destination_contract_digest=changes.get(
            "destination_contract_digest",
            policy.destination_contract_digest,
        ),
        destination_contract_assessment_id=changes.get(
            "destination_contract_assessment_id",
            policy.destination_contract_assessment_id,
        ),
        destination_contract_assessment_digest=changes.get(
            "destination_contract_assessment_digest",
            policy.destination_contract_assessment_digest,
        ),
        outcome_policy_id=changes.get("outcome_policy_id", policy.outcome_policy_id),
        outcome_policy_digest=changes.get("outcome_policy_digest", policy.outcome_policy_digest),
        outcome_policy_assessment_id=changes.get(
            "outcome_policy_assessment_id",
            policy.outcome_policy_assessment_id,
        ),
        outcome_policy_assessment_digest=changes.get(
            "outcome_policy_assessment_digest",
            policy.outcome_policy_assessment_digest,
        ),
        destination_identity=changes.get("destination_identity", policy.destination_identity),
        declared_attestation_issuer_identity=changes.get(
            "declared_attestation_issuer_identity",
            policy.declared_attestation_issuer_identity,
        ),
        declared_attestation_reference=changes.get(
            "declared_attestation_reference",
            policy.declared_attestation_reference,
        ),
        attestation_policy_profile=changes.get(
            "attestation_policy_profile",
            policy.attestation_policy_profile,
        ),
        issued_at=changes.get("issued_at", policy.issued_at),
        expires_at=changes.get("expires_at", policy.expires_at),
    )


__all__ = [
    "AttestationPolicyFixture",
    "assessment_request",
    "attestation_policy_fixture",
    "policy_variant",
]
