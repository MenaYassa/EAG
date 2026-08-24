"""Pure fail-closed assessment for G2.4.19 outcome-semantics policy evidence."""

from __future__ import annotations

from datetime import UTC, datetime

from eag.governed_destination_contract import DestinationContractDisposition
from eag.governed_outcome_policy.models import (
    AutomaticRetryDisposition,
    AutomaticRollbackDisposition,
    CompletionVerificationRequirement,
    FutureReceiptClass,
    OutcomePolicyDisposition,
    OutcomePolicyFindingCode,
    OutcomePolicyProfile,
    OutcomeSemanticsAssessment,
    OutcomeSemanticsAssessmentRequest,
    OutcomeSemanticsFinding,
    UnknownOutcomeDisposition,
)
from eag.governed_transition_control import TransitionControlDisposition


class OutcomeSemanticsAssessor:
    """Assess immutable policy evidence without outcome, execution, or recovery authority."""

    def assess(
        self,
        *,
        assessment_id: str,
        request: OutcomeSemanticsAssessmentRequest,
    ) -> OutcomeSemanticsAssessment:
        """Return only deterministic policy evidence; never claim, execute, or reconcile."""
        if not isinstance(request, OutcomeSemanticsAssessmentRequest):
            raise TypeError("request must be an OutcomeSemanticsAssessmentRequest")

        findings: list[OutcomeSemanticsFinding] = []
        references: list[str] = []
        contract_request = request.destination_contract_request
        contract_assessment = request.destination_contract_assessment
        policy = request.policy
        destination_identity = contract_request.contract.destination_identity

        references.extend(
            (
                f"destination_contract_request:{contract_request.assessment_request_id}:{contract_request.request_digest}",
                f"destination_contract_assessment:{contract_assessment.assessment_id}:{contract_assessment.assessment_digest}",
                f"outcome_policy:{policy.outcome_policy_id}:{policy.policy_digest}",
            )
        )
        _validate_contract_evidence(request, findings)
        _validate_policy_binding(request, findings)
        _validate_policy_semantics(request, findings)
        _validate_transition_control_evidence(request, findings, references)

        disposition = _disposition_for(findings)
        return _assessment(
            assessment_id=assessment_id,
            request=request,
            destination_identity=destination_identity,
            policy_id=policy.outcome_policy_id,
            disposition=disposition,
            findings=findings,
            references=references,
            timestamp=request.timestamp,
        )


def _validate_contract_evidence(
    request: OutcomeSemanticsAssessmentRequest,
    findings: list[OutcomeSemanticsFinding],
) -> None:
    contract_request = request.destination_contract_request
    contract_assessment = request.destination_contract_assessment
    contract = contract_request.contract
    if contract_assessment.disposition is not DestinationContractDisposition.CONTRACT_ATTESTED:
        findings.append(_finding(OutcomePolicyFindingCode.CONTRACT_ASSESSMENT_INVALID, contract_assessment.assessment_id))
    if contract_assessment.contract_id != contract.destination_contract_id:
        findings.append(_finding(OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH, "contract_id"))
    if contract_assessment.assessed_request_id != contract_request.assessment_request_id:
        findings.append(_finding(OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH, "assessed_request_id"))
    if contract_assessment.assessed_request_digest != contract_request.request_digest:
        findings.append(_finding(OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH, "assessed_request_digest"))
    current = request.timestamp.astimezone(UTC)
    if current >= contract.expires_at or current >= contract_request.authorization.expires_at:
        findings.append(_finding(OutcomePolicyFindingCode.CONTRACT_ASSESSMENT_INVALID, "expired_upstream_evidence"))


def _validate_policy_binding(
    request: OutcomeSemanticsAssessmentRequest,
    findings: list[OutcomeSemanticsFinding],
) -> None:
    policy = request.policy
    contract_request = request.destination_contract_request
    contract_assessment = request.destination_contract_assessment
    contract = contract_request.contract
    if request.timestamp.astimezone(UTC) >= policy.expires_at:
        findings.append(_finding(OutcomePolicyFindingCode.POLICY_EXPIRED, policy.outcome_policy_id))
    if (
        policy.destination_contract_id != contract.destination_contract_id
        or policy.destination_contract_digest != contract.contract_digest
        or policy.destination_contract_assessment_id != contract_assessment.assessment_id
        or policy.destination_contract_assessment_digest != contract_assessment.assessment_digest
    ):
        findings.append(_finding(OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH, policy.outcome_policy_id))
    if policy.destination_identity != contract.destination_identity:
        findings.append(_finding(OutcomePolicyFindingCode.DESTINATION_BINDING_MISMATCH, policy.destination_identity))
    if (
        policy.destination_operation_profile != contract.operation_profile
        or policy.external_receipt_schema_id != contract.external_receipt_schema_id
        or policy.destination_idempotency_profile != contract.destination_idempotency_profile
    ):
        findings.append(_finding(OutcomePolicyFindingCode.PROFILE_BINDING_MISMATCH, policy.outcome_policy_id))


def _validate_policy_semantics(
    request: OutcomeSemanticsAssessmentRequest,
    findings: list[OutcomeSemanticsFinding],
) -> None:
    policy = request.policy
    expected_classes = tuple(sorted(item.value for item in FutureReceiptClass))
    if policy.operation_profile != OutcomePolicyProfile.EXTERNAL_ARTIFACT_OUTCOME_POLICY_V1.value:
        findings.append(_finding(OutcomePolicyFindingCode.UNSUPPORTED_OUTCOME_PROFILE, policy.operation_profile))
    if policy.future_receipt_classes != expected_classes:
        findings.append(_finding(OutcomePolicyFindingCode.UNSUPPORTED_OUTCOME_PROFILE, "future_receipt_classes"))
    if policy.unknown_outcome_disposition != UnknownOutcomeDisposition.STOP_AND_RECONCILIATION_REQUIRED.value:
        findings.append(_finding(OutcomePolicyFindingCode.UNSAFE_UNKNOWN_OUTCOME_SEMANTICS, policy.outcome_policy_id))
    if policy.automatic_retry_disposition != AutomaticRetryDisposition.FORBIDDEN.value:
        findings.append(_finding(OutcomePolicyFindingCode.AUTOMATIC_RETRY_FORBIDDEN, policy.outcome_policy_id))
    if policy.automatic_rollback_disposition != AutomaticRollbackDisposition.FORBIDDEN.value:
        findings.append(_finding(OutcomePolicyFindingCode.AUTOMATIC_ROLLBACK_FORBIDDEN, policy.outcome_policy_id))
    if (
        policy.completion_verification_requirement
        != CompletionVerificationRequirement.FUTURE_RECEIPT_VERIFICATION_REQUIRED.value
    ):
        findings.append(_finding(OutcomePolicyFindingCode.UNVERIFIED_COMPLETION_FORBIDDEN, policy.outcome_policy_id))


def _validate_transition_control_evidence(
    request: OutcomeSemanticsAssessmentRequest,
    findings: list[OutcomeSemanticsFinding],
    references: list[str],
) -> None:
    evidence = request.transition_control_evidence
    if evidence is None:
        return
    references.append(f"transition_control:{evidence.control_key}:{evidence.decision_digest}")
    if evidence.disposition is TransitionControlDisposition.AMBIGUOUS:
        findings.append(_finding(OutcomePolicyFindingCode.TRANSITION_CONTROL_AMBIGUOUS, evidence.control_key))


def _disposition_for(findings: list[OutcomeSemanticsFinding]) -> OutcomePolicyDisposition:
    if not findings:
        return OutcomePolicyDisposition.OUTCOME_POLICY_ATTESTED
    if any(item.code is OutcomePolicyFindingCode.UNSUPPORTED_OUTCOME_PROFILE for item in findings):
        return OutcomePolicyDisposition.UNSUPPORTED_OUTCOME_POLICY
    return OutcomePolicyDisposition.NOT_ATTESTED


def _finding(code: OutcomePolicyFindingCode, evidence_reference: str) -> OutcomeSemanticsFinding:
    return OutcomeSemanticsFinding(code=code, evidence_reference=evidence_reference)


def _assessment(
    *,
    assessment_id: str,
    request: OutcomeSemanticsAssessmentRequest,
    destination_identity: str,
    policy_id: str,
    disposition: OutcomePolicyDisposition,
    findings: list[OutcomeSemanticsFinding],
    references: list[str],
    timestamp: datetime,
) -> OutcomeSemanticsAssessment:
    ordered_findings = tuple(sorted(findings, key=lambda item: (item.code.value, item.evidence_reference)))
    ordered_references = tuple(sorted(set(references)))
    recommendations = (
        ("policy_evidence_only",)
        if disposition is OutcomePolicyDisposition.OUTCOME_POLICY_ATTESTED
        else ("stop_without_automatic_progress",)
    )
    return OutcomeSemanticsAssessment.issue(
        assessment_id=assessment_id,
        request=request,
        destination_identity=destination_identity,
        policy_id=policy_id,
        disposition=disposition,
        findings=ordered_findings,
        evidence_refs=ordered_references,
        recommendations=recommendations,
        timestamp=timestamp,
    )


__all__ = ["OutcomeSemanticsAssessor"]
