"""Pure fail-closed assessment for G2.4.20 attestation-policy evidence."""

from __future__ import annotations

from datetime import UTC, datetime

from eag.governed_attestation_policy.models import (
    AttestationPolicyAssessment,
    AttestationPolicyAssessmentRequest,
    AttestationPolicyDisposition,
    AttestationPolicyFinding,
    AttestationPolicyFindingCode,
    AttestationPolicyProfile,
)
from eag.governed_destination_contract import DestinationContractDisposition
from eag.governed_outcome_policy import OutcomePolicyDisposition


class AttestationPolicyAssessor:
    """Assess declared attestation metadata policy without authentication or execution authority."""

    def assess(
        self,
        *,
        assessment_id: str,
        request: AttestationPolicyAssessmentRequest,
    ) -> AttestationPolicyAssessment:
        """Return immutable policy evidence only; never authenticate, resolve, execute, or recover."""
        if not isinstance(request, AttestationPolicyAssessmentRequest):
            raise TypeError("request must be an AttestationPolicyAssessmentRequest")

        findings: list[AttestationPolicyFinding] = []
        references: list[str] = []
        contract_request = request.destination_contract_request
        contract_assessment = request.destination_contract_assessment
        outcome_request = request.outcome_policy_request
        outcome_assessment = request.outcome_policy_assessment
        policy = request.policy
        contract = contract_request.contract
        outcome_policy = outcome_request.policy

        references.extend(
            (
                f"destination_contract_request:{contract_request.assessment_request_id}:{contract_request.request_digest}",
                f"destination_contract_assessment:{contract_assessment.assessment_id}:{contract_assessment.assessment_digest}",
                f"outcome_policy_request:{outcome_request.assessment_request_id}:{outcome_request.request_digest}",
                f"outcome_policy_assessment:{outcome_assessment.assessment_id}:{outcome_assessment.assessment_digest}",
                f"attestation_policy:{policy.attestation_policy_id}:{policy.policy_digest}",
            )
        )
        _validate_contract_evidence(request, findings)
        _validate_outcome_policy_evidence(request, findings)
        _validate_policy_binding(request, findings)
        _validate_policy_profile(request, findings)

        disposition = _disposition_for(findings)
        return _assessment(
            assessment_id=assessment_id,
            destination_identity=contract.destination_identity,
            policy_id=policy.attestation_policy_id,
            disposition=disposition,
            findings=findings,
            references=references,
            timestamp=request.timestamp,
        )


def _validate_contract_evidence(
    request: AttestationPolicyAssessmentRequest,
    findings: list[AttestationPolicyFinding],
) -> None:
    contract_request = request.destination_contract_request
    contract_assessment = request.destination_contract_assessment
    contract = contract_request.contract
    if contract_assessment.disposition is not DestinationContractDisposition.CONTRACT_ATTESTED:
        findings.append(_finding(AttestationPolicyFindingCode.CONTRACT_ASSESSMENT_INVALID, contract_assessment.assessment_id))
    if contract_assessment.contract_id != contract.destination_contract_id:
        findings.append(_finding(AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH, "contract_id"))
    if contract_assessment.assessed_request_id != contract_request.assessment_request_id:
        findings.append(
            _finding(AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH, "contract_assessed_request_id")
        )
    if contract_assessment.assessed_request_digest != contract_request.request_digest:
        findings.append(
            _finding(AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH, "contract_assessed_request_digest")
        )
    if contract_assessment.destination_identity != contract.destination_identity:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.DESTINATION_BINDING_MISMATCH,
                contract_assessment.destination_identity,
            )
        )
    if request.timestamp.astimezone(UTC) >= contract.expires_at:
        findings.append(_finding(AttestationPolicyFindingCode.CONTRACT_ASSESSMENT_INVALID, "expired_contract"))


def _validate_outcome_policy_evidence(
    request: AttestationPolicyAssessmentRequest,
    findings: list[AttestationPolicyFinding],
) -> None:
    contract_request = request.destination_contract_request
    contract_assessment = request.destination_contract_assessment
    outcome_request = request.outcome_policy_request
    outcome_assessment = request.outcome_policy_assessment
    outcome_policy = outcome_request.policy
    if outcome_assessment.disposition is not OutcomePolicyDisposition.OUTCOME_POLICY_ATTESTED:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_ASSESSMENT_INVALID,
                outcome_assessment.assessment_id,
            )
        )
    if outcome_assessment.policy_id != outcome_policy.outcome_policy_id:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "outcome_policy_assessment_id",
            )
        )
    if outcome_assessment.assessed_request_id != outcome_request.assessment_request_id:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "outcome_policy_assessed_request_id",
            )
        )
    if outcome_assessment.assessed_request_digest != outcome_request.request_digest:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "outcome_policy_assessed_request_digest",
            )
        )
    if outcome_request.destination_contract_request.request_digest != contract_request.request_digest:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "destination_contract_request",
            )
        )
    if outcome_request.destination_contract_assessment.assessment_digest != contract_assessment.assessment_digest:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "destination_contract_assessment",
            )
        )
    if outcome_policy.destination_contract_id != contract_request.contract.destination_contract_id:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "destination_contract_id",
            )
        )
    if outcome_policy.destination_contract_digest != contract_request.contract.contract_digest:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "destination_contract_digest",
            )
        )
    if outcome_policy.destination_contract_assessment_id != contract_assessment.assessment_id:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "destination_contract_assessment_id",
            )
        )
    if outcome_policy.destination_contract_assessment_digest != contract_assessment.assessment_digest:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "destination_contract_assessment_digest",
            )
        )
    if outcome_policy.destination_identity != contract_request.contract.destination_identity:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.DESTINATION_BINDING_MISMATCH,
                outcome_policy.destination_identity,
            )
        )
    if outcome_assessment.destination_identity != contract_request.contract.destination_identity:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.DESTINATION_BINDING_MISMATCH,
                outcome_assessment.destination_identity,
            )
        )


def _validate_policy_binding(
    request: AttestationPolicyAssessmentRequest,
    findings: list[AttestationPolicyFinding],
) -> None:
    contract_request = request.destination_contract_request
    contract_assessment = request.destination_contract_assessment
    outcome_request = request.outcome_policy_request
    outcome_assessment = request.outcome_policy_assessment
    policy = request.policy
    contract = contract_request.contract
    outcome_policy = outcome_request.policy
    if request.timestamp.astimezone(UTC) >= policy.expires_at:
        findings.append(_finding(AttestationPolicyFindingCode.POLICY_EXPIRED, policy.attestation_policy_id))
    if (
        policy.destination_contract_id != contract.destination_contract_id
        or policy.destination_contract_digest != contract.contract_digest
        or policy.destination_contract_assessment_id != contract_assessment.assessment_id
        or policy.destination_contract_assessment_digest != contract_assessment.assessment_digest
    ):
        findings.append(_finding(AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH, policy.attestation_policy_id))
    if (
        policy.outcome_policy_id != outcome_policy.outcome_policy_id
        or policy.outcome_policy_digest != outcome_policy.policy_digest
        or policy.outcome_policy_assessment_id != outcome_assessment.assessment_id
        or policy.outcome_policy_assessment_digest != outcome_assessment.assessment_digest
    ):
        findings.append(
            _finding(AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH, policy.attestation_policy_id)
        )
    if policy.destination_identity != contract.destination_identity:
        findings.append(
            _finding(AttestationPolicyFindingCode.DESTINATION_BINDING_MISMATCH, policy.destination_identity)
        )
    if policy.declared_attestation_issuer_identity != contract.attestation_issuer_identity:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.ATTESTATION_ISSUER_BINDING_MISMATCH,
                policy.declared_attestation_issuer_identity,
            )
        )
    if policy.declared_attestation_reference != contract.attestation_reference:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.ATTESTATION_REFERENCE_BINDING_MISMATCH,
                policy.declared_attestation_reference,
            )
        )


def _validate_policy_profile(
    request: AttestationPolicyAssessmentRequest,
    findings: list[AttestationPolicyFinding],
) -> None:
    policy = request.policy
    if policy.attestation_policy_profile != AttestationPolicyProfile.DECLARED_ATTESTATION_POLICY_V1.value:
        findings.append(
            _finding(
                AttestationPolicyFindingCode.UNSUPPORTED_ATTESTATION_PROFILE,
                policy.attestation_policy_profile,
            )
        )


def _disposition_for(findings: list[AttestationPolicyFinding]) -> AttestationPolicyDisposition:
    if not findings:
        return AttestationPolicyDisposition.ATTESTATION_POLICY_ATTESTED
    if any(item.code is AttestationPolicyFindingCode.UNSUPPORTED_ATTESTATION_PROFILE for item in findings):
        return AttestationPolicyDisposition.UNSUPPORTED_ATTESTATION_POLICY
    return AttestationPolicyDisposition.NOT_ATTESTED


def _finding(code: AttestationPolicyFindingCode, evidence_reference: str) -> AttestationPolicyFinding:
    return AttestationPolicyFinding(code=code, evidence_reference=evidence_reference)


def _assessment(
    *,
    assessment_id: str,
    destination_identity: str,
    policy_id: str,
    disposition: AttestationPolicyDisposition,
    findings: list[AttestationPolicyFinding],
    references: list[str],
    timestamp: datetime,
) -> AttestationPolicyAssessment:
    ordered_findings = tuple(sorted(findings, key=lambda item: (item.code.value, item.evidence_reference)))
    ordered_references = tuple(sorted(set(references)))
    recommendations = (
        ("attestation_policy_evidence_only",)
        if disposition is AttestationPolicyDisposition.ATTESTATION_POLICY_ATTESTED
        else ("stop_without_automatic_progress",)
    )
    return AttestationPolicyAssessment.issue(
        assessment_id=assessment_id,
        destination_identity=destination_identity,
        policy_id=policy_id,
        disposition=disposition,
        findings=ordered_findings,
        evidence_refs=ordered_references,
        recommendations=recommendations,
        timestamp=timestamp,
    )


__all__ = ["AttestationPolicyAssessor"]
