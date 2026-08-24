"""Pure, fail-closed G2.4.18 destination-contract evidence assessment."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from eag.governed_destination_contract.models import (
    DestinationContractAssessment,
    DestinationContractAssessmentRequest,
    DestinationContractDisposition,
    DestinationContractFinding,
    DestinationContractFindingCode,
    DestinationIdempotencyProfile,
    DestinationOperationProfile,
    DestinationReceiptSchema,
    DestinationRequestSchema,
    ExternalDestinationContractEvidence,
)
from eag.governed_promotion import (
    PromotionEligibilityAssessment,
    PromotionEligibilityDisposition,
    PromotionEligibilityRequest,
)
from eag.governed_transition_authorization import (
    ExternalTransitionAuthorizationReceipt,
    ExternalTransitionIntentEvidence,
    HumanAuthorizationDecision,
    TransitionAuthorizationAssessment,
    TransitionAuthorizationDisposition,
)
from eag.governed_transition_control import TransitionControlDecision, TransitionControlDisposition


class DestinationContractAssessor:
    """Assess supplied immutable destination evidence without operational authority."""

    def assess(
        self,
        *,
        assessment_id: str,
        request: DestinationContractAssessmentRequest,
    ) -> DestinationContractAssessment:
        """Return deterministic evidence only; never claim, execute, or contact a destination."""
        if not isinstance(request, DestinationContractAssessmentRequest):
            raise TypeError("request must be a DestinationContractAssessmentRequest")

        findings: list[DestinationContractFinding] = []
        references: list[str] = []
        destination_identity = _destination_identity(request)
        contract = _contract_or_finding(request.contract, findings)
        contract_id = contract.destination_contract_id if contract is not None else None

        promotion_request, promotion_assessment = _validate_eligibility(
            request, findings, references
        )
        intent = _validate_intent(request, promotion_request, promotion_assessment, findings, references)
        authorization = _validate_authorization(request, intent, findings, references)
        _validate_authorization_assessment(request, intent, authorization, findings, references)
        _validate_contract(
            request,
            contract,
            promotion_request,
            promotion_assessment,
            intent,
            authorization,
            request.authorization_assessment,
            findings,
            references,
        )
        _validate_transition_control_evidence(request, findings, references)

        disposition = _disposition_for(findings)
        return _assessment(
            assessment_id=assessment_id,
            request=request,
            destination_identity=destination_identity,
            contract_id=contract_id,
            disposition=disposition,
            findings=findings,
            references=references,
            timestamp=request.timestamp,
        )


def _destination_identity(request: DestinationContractAssessmentRequest) -> str:
    if isinstance(request.promotion_request, PromotionEligibilityRequest):
        return request.promotion_request.destination_identity
    if isinstance(request.transition_intent, ExternalTransitionIntentEvidence):
        return request.transition_intent.destination_identity
    if isinstance(request.contract, ExternalDestinationContractEvidence):
        return request.contract.destination_identity
    return "unavailable-destination"


def _contract_or_finding(
    value: ExternalDestinationContractEvidence,
    findings: list[DestinationContractFinding],
) -> ExternalDestinationContractEvidence | None:
    if isinstance(value, ExternalDestinationContractEvidence):
        return value
    findings.append(_finding(DestinationContractFindingCode.CONTRACT_EVIDENCE_INVALID, "contract"))
    return None


def _validate_eligibility(
    request: DestinationContractAssessmentRequest,
    findings: list[DestinationContractFinding],
    references: list[str],
) -> tuple[PromotionEligibilityRequest | None, PromotionEligibilityAssessment | None]:
    promotion_request = request.promotion_request
    promotion_assessment = request.promotion_assessment
    if not isinstance(promotion_request, PromotionEligibilityRequest) or not isinstance(
        promotion_assessment, PromotionEligibilityAssessment
    ):
        findings.append(_finding(DestinationContractFindingCode.ELIGIBILITY_EVIDENCE_INVALID, "eligibility"))
        return None, None
    references.extend(
        (
            f"promotion_intent:{promotion_request.intent_id}:{promotion_request.artifact_fingerprint}",
            f"promotion_assessment:{promotion_assessment.assessment_id}:{promotion_assessment.assessment_digest}",
        )
    )
    if promotion_assessment.disposition is not PromotionEligibilityDisposition.ELIGIBLE:
        findings.append(
            _finding(DestinationContractFindingCode.ELIGIBILITY_EVIDENCE_INVALID, promotion_assessment.assessment_id)
        )
    if promotion_assessment.artifact_identity != (
        f"{promotion_request.artifact_id}:{promotion_request.artifact_fingerprint}"
    ):
        findings.append(_finding(DestinationContractFindingCode.ELIGIBILITY_BINDING_MISMATCH, "artifact_identity"))
    if promotion_assessment.destination_identity != promotion_request.destination_identity:
        findings.append(_finding(DestinationContractFindingCode.ELIGIBILITY_BINDING_MISMATCH, "destination"))
    return promotion_request, promotion_assessment


def _validate_intent(
    request: DestinationContractAssessmentRequest,
    promotion_request: PromotionEligibilityRequest | None,
    promotion_assessment: PromotionEligibilityAssessment | None,
    findings: list[DestinationContractFinding],
    references: list[str],
) -> ExternalTransitionIntentEvidence | None:
    intent = request.transition_intent
    if not isinstance(intent, ExternalTransitionIntentEvidence):
        findings.append(_finding(DestinationContractFindingCode.TRANSITION_BINDING_MISMATCH, "transition_intent"))
        return None
    references.append(f"transition_intent:{intent.transition_intent_id}:{intent.artifact_fingerprint}")
    if promotion_request is None or promotion_assessment is None:
        return intent
    if (
        intent.transition_intent_id != promotion_request.intent_id
        or intent.eligibility_assessment_id != promotion_assessment.assessment_id
        or intent.eligibility_assessment_digest != promotion_assessment.assessment_digest
    ):
        findings.append(_finding(DestinationContractFindingCode.ASSESSMENT_BINDING_MISMATCH, "eligibility"))
    if (
        intent.artifact_id != promotion_request.artifact_id
        or intent.artifact_fingerprint != promotion_request.artifact_fingerprint
    ):
        findings.append(_finding(DestinationContractFindingCode.ARTIFACT_IDENTITY_MISMATCH, "artifact"))
    if intent.destination_identity != promotion_request.destination_identity:
        findings.append(_finding(DestinationContractFindingCode.CONTRACT_DESTINATION_MISMATCH, "destination"))
    if intent.promotion_policy_digest != promotion_request.promotion_policy_digest:
        findings.append(_finding(DestinationContractFindingCode.CONTRACT_POLICY_MISMATCH, "promotion_policy"))
    return intent


def _validate_authorization(
    request: DestinationContractAssessmentRequest,
    intent: ExternalTransitionIntentEvidence | None,
    findings: list[DestinationContractFinding],
    references: list[str],
) -> ExternalTransitionAuthorizationReceipt | None:
    authorization = request.authorization
    if authorization is None:
        findings.append(_finding(DestinationContractFindingCode.AUTHORIZATION_MISSING, "authorization"))
        return None
    if not isinstance(authorization, ExternalTransitionAuthorizationReceipt):
        findings.append(_finding(DestinationContractFindingCode.AUTHORIZATION_EVIDENCE_INVALID, "authorization"))
        return None
    references.append(f"authorization:{authorization.authorization_id}:{authorization.binding_digest}")
    if authorization.decision is not HumanAuthorizationDecision.AUTHORIZED:
        findings.append(_finding(DestinationContractFindingCode.AUTHORIZATION_DENIED, authorization.authorization_id))
    if request.timestamp.astimezone(UTC) >= authorization.expires_at:
        findings.append(_finding(DestinationContractFindingCode.AUTHORIZATION_EXPIRED, authorization.authorization_id))
    if intent is not None:
        expected = {
            "transition_intent_id": intent.transition_intent_id,
            "artifact_id": intent.artifact_id,
            "artifact_fingerprint": intent.artifact_fingerprint,
            "destination_identity": intent.destination_identity,
            "eligibility_assessment_id": intent.eligibility_assessment_id,
            "eligibility_assessment_digest": intent.eligibility_assessment_digest,
            "promotion_policy_digest": intent.promotion_policy_digest,
            "authorization_policy_digest": intent.authorization_policy_digest,
            "execution_id": intent.execution_id,
            "run_id": intent.run_id,
        }
        if any(getattr(authorization, field_name) != value for field_name, value in expected.items()):
            findings.append(
                _finding(DestinationContractFindingCode.AUTHORIZATION_BINDING_MISMATCH, authorization.authorization_id)
            )
    return authorization


def _validate_authorization_assessment(
    request: DestinationContractAssessmentRequest,
    intent: ExternalTransitionIntentEvidence | None,
    authorization: ExternalTransitionAuthorizationReceipt | None,
    findings: list[DestinationContractFinding],
    references: list[str],
) -> None:
    assessment = request.authorization_assessment
    if not isinstance(assessment, TransitionAuthorizationAssessment):
        findings.append(_finding(DestinationContractFindingCode.AUTHORIZATION_EVIDENCE_INVALID, "authorization_assessment"))
        return
    references.append(f"authorization_assessment:{assessment.assessment_id}:{assessment.assessment_digest}")
    if assessment.disposition is not TransitionAuthorizationDisposition.AUTHORIZED:
        findings.append(_finding(DestinationContractFindingCode.AUTHORIZATION_EVIDENCE_INVALID, assessment.assessment_id))
    if authorization is not None and assessment.authorization_id != authorization.authorization_id:
        findings.append(_finding(DestinationContractFindingCode.ASSESSMENT_BINDING_MISMATCH, "authorization_id"))
    if intent is not None and (
        assessment.artifact_id != intent.artifact_id
        or assessment.artifact_fingerprint != intent.artifact_fingerprint
        or assessment.destination_identity != intent.destination_identity
    ):
        findings.append(_finding(DestinationContractFindingCode.ASSESSMENT_BINDING_MISMATCH, "authorization_assessment"))


def _validate_contract(
    request: DestinationContractAssessmentRequest,
    contract: ExternalDestinationContractEvidence | None,
    promotion_request: PromotionEligibilityRequest | None,
    promotion_assessment: PromotionEligibilityAssessment | None,
    intent: ExternalTransitionIntentEvidence | None,
    authorization: ExternalTransitionAuthorizationReceipt | None,
    authorization_assessment: TransitionAuthorizationAssessment | object | None,
    findings: list[DestinationContractFinding],
    references: list[str],
) -> None:
    if contract is None:
        return
    references.append(f"destination_contract:{contract.destination_contract_id}:{contract.contract_digest}")
    if request.timestamp.astimezone(UTC) >= contract.expires_at:
        findings.append(_finding(DestinationContractFindingCode.CONTRACT_EXPIRED, contract.destination_contract_id))
    if not contract.attestation_issuer_identity.startswith("attester-") or not contract.attestation_reference.startswith(
        "attestation-"
    ):
        findings.append(_finding(DestinationContractFindingCode.ISSUER_REFERENCE_INVALID, contract.destination_contract_id))
    if intent is not None:
        if contract.destination_identity != intent.destination_identity:
            findings.append(_finding(DestinationContractFindingCode.CONTRACT_DESTINATION_MISMATCH, contract.destination_identity))
        if contract.artifact_id != intent.artifact_id or contract.artifact_fingerprint != intent.artifact_fingerprint:
            findings.append(_finding(DestinationContractFindingCode.ARTIFACT_IDENTITY_MISMATCH, "artifact"))
        if (
            contract.transition_intent_id != intent.transition_intent_id
            or contract.promotion_assessment_id != intent.eligibility_assessment_id
            or contract.promotion_assessment_digest != intent.eligibility_assessment_digest
        ):
            findings.append(_finding(DestinationContractFindingCode.TRANSITION_BINDING_MISMATCH, "transition_intent"))
        if (
            contract.promotion_policy_digest != intent.promotion_policy_digest
            or contract.authorization_policy_digest != intent.authorization_policy_digest
            or contract.destination_policy_digest != intent.promotion_policy_digest
        ):
            findings.append(_finding(DestinationContractFindingCode.CONTRACT_POLICY_MISMATCH, "policy"))
        if contract.execution_id != intent.execution_id or contract.run_id != intent.run_id:
            findings.append(_finding(DestinationContractFindingCode.EXECUTION_RUN_BINDING_MISMATCH, "execution_run"))
        if contract.transition_profile != str(intent.transition_profile):
            findings.append(_finding(DestinationContractFindingCode.UNSUPPORTED_PROFILE, contract.transition_profile))
    if promotion_request is not None and contract.destination_identity != promotion_request.destination_identity:
        findings.append(_finding(DestinationContractFindingCode.CONTRACT_DESTINATION_MISMATCH, contract.destination_identity))
    if promotion_assessment is not None and contract.destination_identity != promotion_assessment.destination_identity:
        findings.append(_finding(DestinationContractFindingCode.CONTRACT_DESTINATION_MISMATCH, contract.destination_identity))
    if authorization is not None:
        if contract.destination_identity != authorization.destination_identity:
            findings.append(_finding(DestinationContractFindingCode.CONTRACT_DESTINATION_MISMATCH, contract.destination_identity))
        if (
            contract.authorization_id != authorization.authorization_id
            or contract.authorization_binding_digest != authorization.binding_digest
        ):
            findings.append(_finding(DestinationContractFindingCode.AUTHORIZATION_BINDING_MISMATCH, "authorization"))
    if isinstance(authorization_assessment, TransitionAuthorizationAssessment) and (
        contract.authorization_assessment_id != authorization_assessment.assessment_id
        or contract.authorization_assessment_digest != authorization_assessment.assessment_digest
    ):
        findings.append(_finding(DestinationContractFindingCode.ASSESSMENT_BINDING_MISMATCH, "authorization_assessment"))
    supported = (
        contract.operation_profile == DestinationOperationProfile.EXTERNAL_ARTIFACT_TRANSFER_V1.value
        and contract.external_request_schema_id == DestinationRequestSchema.EXTERNAL_ARTIFACT_REQUEST_V1.value
        and contract.external_receipt_schema_id == DestinationReceiptSchema.EXTERNAL_ARTIFACT_RECEIPT_V1.value
        and contract.destination_idempotency_profile
        == DestinationIdempotencyProfile.DESTINATION_IDEMPOTENCY_DECLARATION_V1.value
    )
    if not supported:
        findings.append(_finding(DestinationContractFindingCode.UNSUPPORTED_PROFILE, contract.destination_contract_id))


def _validate_transition_control_evidence(
    request: DestinationContractAssessmentRequest,
    findings: list[DestinationContractFinding],
    references: list[str],
) -> None:
    evidence = request.transition_control_evidence
    if evidence is None:
        return
    if not isinstance(evidence, TransitionControlDecision):
        findings.append(_finding(DestinationContractFindingCode.CONTRACT_EVIDENCE_INVALID, "transition_control"))
        return
    references.append(f"transition_control:{evidence.control_key}:{evidence.decision_digest}")
    if evidence.disposition is TransitionControlDisposition.AMBIGUOUS:
        findings.append(_finding(DestinationContractFindingCode.TRANSITION_CONTROL_AMBIGUOUS, evidence.control_key))


def _disposition_for(
    findings: list[DestinationContractFinding],
) -> DestinationContractDisposition:
    if not findings:
        return DestinationContractDisposition.CONTRACT_ATTESTED
    if any(finding.code is DestinationContractFindingCode.UNSUPPORTED_PROFILE for finding in findings):
        return DestinationContractDisposition.UNSUPPORTED_DESTINATION_CONTRACT
    return DestinationContractDisposition.NOT_ATTESTED


def _finding(code: DestinationContractFindingCode, reference: str) -> DestinationContractFinding:
    return DestinationContractFinding(code=code, evidence_reference=reference)


def _assessment(
    *,
    assessment_id: str,
    request: DestinationContractAssessmentRequest,
    destination_identity: str,
    contract_id: str | None,
    disposition: DestinationContractDisposition,
    findings: Iterable[DestinationContractFinding],
    references: Iterable[str],
    timestamp: datetime,
) -> DestinationContractAssessment:
    ordered_findings = tuple(
        sorted(
            {(finding.code.value, finding.evidence_reference): finding for finding in findings}.values(),
            key=lambda finding: (finding.code.value, finding.evidence_reference),
        )
    )
    ordered_references = tuple(sorted(set(references)))
    recommendations = tuple(sorted({_recommendation(finding.code) for finding in ordered_findings}))
    return DestinationContractAssessment.issue(
        assessment_id=assessment_id,
        request=request,
        destination_identity=destination_identity,
        contract_id=contract_id,
        disposition=disposition,
        findings=ordered_findings,
        evidence_refs=ordered_references,
        recommendations=recommendations,
        timestamp=timestamp,
    )


def _recommendation(code: DestinationContractFindingCode) -> str:
    recommendations = {
        DestinationContractFindingCode.CONTRACT_MISSING: "supply one immutable destination contract declaration",
        DestinationContractFindingCode.CONTRACT_EVIDENCE_INVALID: "supply exact canonical destination contract evidence",
        DestinationContractFindingCode.CONTRACT_EXPIRED: "supply unexpired destination contract evidence",
        DestinationContractFindingCode.CONTRACT_DESTINATION_MISMATCH: "bind the contract to the exact logical destination",
        DestinationContractFindingCode.CONTRACT_POLICY_MISMATCH: "bind the contract to the exact promotion policy",
        DestinationContractFindingCode.ELIGIBILITY_EVIDENCE_INVALID: "supply exact eligible promotion evidence",
        DestinationContractFindingCode.ELIGIBILITY_BINDING_MISMATCH: "align eligibility evidence with the exact artifact and destination",
        DestinationContractFindingCode.AUTHORIZATION_MISSING: "supply exact authorized transition evidence",
        DestinationContractFindingCode.AUTHORIZATION_EVIDENCE_INVALID: "supply exact authorized transition assessment evidence",
        DestinationContractFindingCode.AUTHORIZATION_DENIED: "supply an explicitly authorized decision",
        DestinationContractFindingCode.AUTHORIZATION_EXPIRED: "supply unexpired authorization evidence",
        DestinationContractFindingCode.AUTHORIZATION_BINDING_MISMATCH: "align authorization with the exact transition intent",
        DestinationContractFindingCode.TRANSITION_BINDING_MISMATCH: "supply exact transition intent evidence",
        DestinationContractFindingCode.ARTIFACT_IDENTITY_MISMATCH: "align the exact artifact identity and fingerprint",
        DestinationContractFindingCode.EXECUTION_RUN_BINDING_MISMATCH: "align execution and run evidence",
        DestinationContractFindingCode.ASSESSMENT_BINDING_MISMATCH: "align exact assessment identity and digest evidence",
        DestinationContractFindingCode.ISSUER_REFERENCE_INVALID: "supply a structurally valid non-secret attestation reference",
        DestinationContractFindingCode.TRANSITION_CONTROL_AMBIGUOUS: "stop; transition control remains ambiguous",
        DestinationContractFindingCode.UNSUPPORTED_PROFILE: "use the supported non-executable destination contract profile",
    }
    return recommendations[code]


__all__ = ["DestinationContractAssessor"]
