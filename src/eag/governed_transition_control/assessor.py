"""Read-only, fail-closed G2.4.17 transition-control evidence assessment."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime

from eag.governed_transition_authorization import (
    ExternalTransitionAuthorizationReceipt,
    HumanAuthorizationDecision,
    TransitionAuthorizationAssessment,
    TransitionAuthorizationDisposition,
)
from eag.governed_transition_control.ledger import (
    DurableTransitionControlLedger,
    TransitionControlClaimDisposition,
    TransitionControlLedgerCorruptionError,
    TransitionControlLedgerUnavailableError,
)
from eag.governed_transition_control.models import (
    ExternalTransitionControlRequest,
    TransitionControlDecision,
    TransitionControlDisposition,
    TransitionControlFinding,
    TransitionControlFindingCode,
    TransitionControlProfile,
)


class TransitionControlAssessor:
    """Assess pre-execution control evidence without a permit, session, or external action."""

    def assess(
        self,
        *,
        decision_id: str,
        request: ExternalTransitionControlRequest,
        authorization: ExternalTransitionAuthorizationReceipt | object,
        authorization_assessment: TransitionAuthorizationAssessment | object,
        ledger: DurableTransitionControlLedger,
        timestamp: datetime,
    ) -> TransitionControlDecision:
        """Return immutable control evidence after at most one durable claim attempt."""
        if not isinstance(request, ExternalTransitionControlRequest):
            raise TypeError("request must be an ExternalTransitionControlRequest")
        if not isinstance(ledger, DurableTransitionControlLedger):
            raise TypeError("ledger must satisfy DurableTransitionControlLedger")
        canonical_time = timestamp.astimezone(UTC) if isinstance(timestamp, datetime) and timestamp.tzinfo else timestamp
        if not isinstance(canonical_time, datetime) or canonical_time.tzinfo is None:
            raise TypeError("timestamp must be timezone-aware")

        findings: list[TransitionControlFinding] = []
        references: list[str] = []
        supported = _validate_profile(request, findings)
        _validate_idempotency(request, findings)
        _validate_authorization_assessment(request, authorization_assessment, findings, references)
        _validate_authorization_receipt(request, authorization, canonical_time, findings, references)

        if not supported:
            return _decision(
                decision_id=decision_id,
                request=request,
                control_id=None,
                disposition=TransitionControlDisposition.UNSUPPORTED_PROFILE,
                findings=findings,
                references=references,
                timestamp=canonical_time,
            )
        if findings:
            return _decision(
                decision_id=decision_id,
                request=request,
                control_id=None,
                disposition=TransitionControlDisposition.NOT_CONTROLLABLE,
                findings=findings,
                references=references,
                timestamp=canonical_time,
            )

        try:
            claim = ledger.claim(request)
        except TransitionControlLedgerUnavailableError:
            findings.append(_finding(TransitionControlFindingCode.CONTROL_STORE_UNAVAILABLE, request.control_key))
            return _decision(
                decision_id=decision_id,
                request=request,
                control_id=None,
                disposition=TransitionControlDisposition.NOT_CONTROLLABLE,
                findings=findings,
                references=references,
                timestamp=canonical_time,
            )
        except TransitionControlLedgerCorruptionError:
            findings.append(_finding(TransitionControlFindingCode.CONTROL_STORE_CORRUPT, request.control_key))
            return _decision(
                decision_id=decision_id,
                request=request,
                control_id=None,
                disposition=TransitionControlDisposition.NOT_CONTROLLABLE,
                findings=findings,
                references=references,
                timestamp=canonical_time,
            )

        references.append(claim.record.record_digest)
        if claim.disposition is TransitionControlClaimDisposition.CLAIMED:
            disposition = TransitionControlDisposition.CLAIMED
        elif claim.disposition is TransitionControlClaimDisposition.DUPLICATE:
            findings.append(_finding(TransitionControlFindingCode.DUPLICATE_CONTROL, request.control_key))
            disposition = TransitionControlDisposition.DUPLICATE
        elif claim.disposition is TransitionControlClaimDisposition.CONFLICT:
            findings.append(_finding(TransitionControlFindingCode.CONFLICTING_CONTROL, request.control_key))
            disposition = TransitionControlDisposition.CONFLICT
        else:
            findings.append(_finding(TransitionControlFindingCode.AMBIGUOUS_CONTROL, request.control_key))
            disposition = TransitionControlDisposition.AMBIGUOUS
        return _decision(
            decision_id=decision_id,
            request=request,
            control_id=claim.record.control_id,
            disposition=disposition,
            findings=findings,
            references=references,
            timestamp=canonical_time,
        )


def _validate_profile(
    request: ExternalTransitionControlRequest,
    findings: list[TransitionControlFinding],
) -> bool:
    if request.transition_profile is not TransitionControlProfile.EXTERNAL_ARTIFACT_TRANSITION_CONTROL_V1:
        findings.append(_finding(TransitionControlFindingCode.UNSUPPORTED_PROFILE, str(request.transition_profile)))
        return False
    return True


def _validate_idempotency(
    request: ExternalTransitionControlRequest,
    findings: list[TransitionControlFinding],
) -> None:
    if re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,127}", request.idempotency_key) is None:
        findings.append(_finding(TransitionControlFindingCode.IDEMPOTENCY_KEY_INVALID, request.idempotency_key))


def _validate_authorization_assessment(
    request: ExternalTransitionControlRequest,
    assessment: TransitionAuthorizationAssessment | object,
    findings: list[TransitionControlFinding],
    references: list[str],
) -> None:
    if not isinstance(assessment, TransitionAuthorizationAssessment):
        findings.append(_finding(TransitionControlFindingCode.AUTHORIZATION_EVIDENCE_INVALID, request.authorization_assessment_id))
        return
    if assessment.disposition is not TransitionAuthorizationDisposition.AUTHORIZED:
        findings.append(_finding(TransitionControlFindingCode.AUTHORIZATION_EVIDENCE_INVALID, assessment.assessment_id))
    if assessment.assessment_id != request.authorization_assessment_id or assessment.assessment_digest != request.authorization_assessment_digest:
        findings.append(_finding(TransitionControlFindingCode.AUTHORIZATION_BINDING_MISMATCH, request.authorization_assessment_id))
    if assessment.authorization_id != request.authorization_id:
        findings.append(_finding(TransitionControlFindingCode.AUTHORIZATION_BINDING_MISMATCH, request.authorization_id))
    if assessment.artifact_id != request.artifact_id or assessment.artifact_fingerprint != request.artifact_fingerprint:
        findings.append(_finding(TransitionControlFindingCode.ARTIFACT_IDENTITY_MISMATCH, request.artifact_id))
    if assessment.destination_identity != request.destination_identity:
        findings.append(_finding(TransitionControlFindingCode.DESTINATION_BINDING_MISMATCH, request.destination_identity))
    references.append(assessment.assessment_digest)


def _validate_authorization_receipt(
    request: ExternalTransitionControlRequest,
    authorization: ExternalTransitionAuthorizationReceipt | object,
    timestamp: datetime,
    findings: list[TransitionControlFinding],
    references: list[str],
) -> None:
    if not isinstance(authorization, ExternalTransitionAuthorizationReceipt):
        findings.append(_finding(TransitionControlFindingCode.AUTHORIZATION_EVIDENCE_INVALID, request.authorization_id))
        return
    if authorization.decision is not HumanAuthorizationDecision.AUTHORIZED or authorization.expires_at < timestamp:
        findings.append(_finding(TransitionControlFindingCode.AUTHORIZATION_EVIDENCE_INVALID, authorization.authorization_id))
    if authorization.authorization_id != request.authorization_id or authorization.binding_digest != request.authorization_binding_digest:
        findings.append(_finding(TransitionControlFindingCode.AUTHORIZATION_BINDING_MISMATCH, request.authorization_id))
    if authorization.transition_intent_id != request.transition_intent_id:
        findings.append(_finding(TransitionControlFindingCode.TRANSITION_BINDING_MISMATCH, request.transition_intent_id))
    if authorization.artifact_id != request.artifact_id or authorization.artifact_fingerprint != request.artifact_fingerprint:
        findings.append(_finding(TransitionControlFindingCode.ARTIFACT_IDENTITY_MISMATCH, request.artifact_id))
    if authorization.destination_identity != request.destination_identity:
        findings.append(_finding(TransitionControlFindingCode.DESTINATION_BINDING_MISMATCH, request.destination_identity))
    if (
        authorization.promotion_policy_digest != request.promotion_policy_digest
        or authorization.authorization_policy_digest != request.authorization_policy_digest
    ):
        findings.append(_finding(TransitionControlFindingCode.POLICY_BINDING_MISMATCH, request.transition_intent_id))
    if authorization.execution_id != request.execution_id or authorization.run_id != request.run_id:
        findings.append(_finding(TransitionControlFindingCode.TRANSITION_BINDING_MISMATCH, request.transition_intent_id))
    references.append(authorization.binding_digest)


def _finding(code: TransitionControlFindingCode, reference: str) -> TransitionControlFinding:
    return TransitionControlFinding(code=code, evidence_reference=reference)


def _decision(
    *,
    decision_id: str,
    request: ExternalTransitionControlRequest,
    control_id: str | None,
    disposition: TransitionControlDisposition,
    findings: Iterable[TransitionControlFinding],
    references: Iterable[str],
    timestamp: datetime,
) -> TransitionControlDecision:
    normalized_findings = tuple(sorted(set(findings), key=lambda finding: (finding.code.value, finding.evidence_reference)))
    normalized_refs = tuple(sorted(set(references)))
    recommendation_values: set[str] = set()
    for finding in normalized_findings:
        recommendation = _recommendation(finding.code)
        if recommendation is not None:
            recommendation_values.add(recommendation)
    recommendations = tuple(sorted(recommendation_values))
    return TransitionControlDecision.issue(
        decision_id=decision_id,
        request=request,
        control_id=control_id,
        disposition=disposition,
        findings=normalized_findings,
        evidence_refs=normalized_refs,
        recommendations=recommendations,
        timestamp=timestamp,
    )


def _recommendation(code: TransitionControlFindingCode) -> str | None:
    recommendations = {
        TransitionControlFindingCode.AUTHORIZATION_EVIDENCE_INVALID: "supply exact current G2.4.16 AUTHORIZED evidence",
        TransitionControlFindingCode.AUTHORIZATION_BINDING_MISMATCH: "align request with exact authorization evidence",
        TransitionControlFindingCode.TRANSITION_BINDING_MISMATCH: "align request with exact authorized transition intent",
        TransitionControlFindingCode.ARTIFACT_IDENTITY_MISMATCH: "align request with the authorized artifact identity",
        TransitionControlFindingCode.DESTINATION_BINDING_MISMATCH: "align request with the authorized logical destination",
        TransitionControlFindingCode.POLICY_BINDING_MISMATCH: "align request with exact authorized policy digests",
        TransitionControlFindingCode.IDEMPOTENCY_KEY_INVALID: "supply a canonical idempotency key",
        TransitionControlFindingCode.DUPLICATE_CONTROL: "treat the existing control record as already claimed",
        TransitionControlFindingCode.CONFLICTING_CONTROL: "do not reuse an idempotency key across incompatible transition evidence",
        TransitionControlFindingCode.AMBIGUOUS_CONTROL: "stop; ambiguous control state requires a future reconciliation authority",
        TransitionControlFindingCode.CONTROL_STORE_UNAVAILABLE: "restore a safe durable control store before proceeding",
        TransitionControlFindingCode.CONTROL_STORE_CORRUPT: "treat control state as unsafe; do not repair or retry automatically",
        TransitionControlFindingCode.UNSUPPORTED_PROFILE: "use an explicitly supported transition-control profile",
    }
    return recommendations.get(code)


__all__ = ["TransitionControlAssessor"]
