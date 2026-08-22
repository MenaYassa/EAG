"""Read-only, fail-closed G2.4.16 transition authorization evidence assessment."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime

from eag.governed_promotion import (
    PromotionEligibilityAssessment,
    PromotionEligibilityDisposition,
    PromotionEligibilityRequest,
)
from eag.governed_transition_authorization.models import (
    ExternalTransitionAuthorizationReceipt,
    ExternalTransitionIntentEvidence,
    ExternalTransitionProfile,
    HumanAuthorizationDecision,
    TransitionAuthorizationAssessment,
    TransitionAuthorizationDisposition,
    TransitionAuthorizationFinding,
    TransitionAuthorizationFindingCode,
)
from eag.governed_transition_authorization.store import (
    AuthorizationClaimDisposition,
    DurableTransitionAuthorizationStore,
    TransitionAuthorizationStoreCorruptionError,
    TransitionAuthorizationStoreUnavailableError,
)


class TransitionAuthorizationAssessor:
    """Validate supplied human transition-authorization evidence only.

    The assessor cannot create a human decision, permit, session, runtime invocation, destination
    connection, network request, credential access, upload, publication, deployment, command,
    release, retry, rollback, audit record, or external transition receipt.
    """

    def assess(
        self,
        *,
        assessment_id: str,
        intent: ExternalTransitionIntentEvidence,
        authorization: ExternalTransitionAuthorizationReceipt | None,
        promotion_request: PromotionEligibilityRequest | object,
        promotion_assessment: PromotionEligibilityAssessment | object,
        store: DurableTransitionAuthorizationStore,
        timestamp: datetime,
    ) -> TransitionAuthorizationAssessment:
        """Return immutable authorization evidence assessment, claiming only valid evidence once."""
        if not isinstance(intent, ExternalTransitionIntentEvidence):
            raise TypeError("intent must be an ExternalTransitionIntentEvidence")
        if not isinstance(store, DurableTransitionAuthorizationStore):
            raise TypeError("store must satisfy DurableTransitionAuthorizationStore")

        findings: list[TransitionAuthorizationFinding] = []
        references: list[str] = []
        supported = _validate_profile(intent, findings)
        _validate_idempotency_key(intent, findings)
        _validate_eligibility(intent, promotion_request, promotion_assessment, findings, references)
        _validate_authorization(intent, authorization, timestamp, findings, references)

        if not supported:
            return _assessment(
                assessment_id=assessment_id,
                intent=intent,
                authorization=authorization,
                disposition=TransitionAuthorizationDisposition.UNSUPPORTED_TRANSITION,
                findings=findings,
                references=references,
                timestamp=timestamp,
            )
        if findings or authorization is None:
            return _assessment(
                assessment_id=assessment_id,
                intent=intent,
                authorization=authorization,
                disposition=TransitionAuthorizationDisposition.NOT_AUTHORIZED,
                findings=findings,
                references=references,
                timestamp=timestamp,
            )

        try:
            claim = store.claim(authorization)
        except TransitionAuthorizationStoreCorruptionError:
            findings.append(_finding(TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_CORRUPT, "store"))
        except TransitionAuthorizationStoreUnavailableError:
            findings.append(_finding(TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_UNAVAILABLE, "store"))
        else:
            if claim.disposition is AuthorizationClaimDisposition.DUPLICATE:
                findings.append(
                    _finding(TransitionAuthorizationFindingCode.AUTHORIZATION_DUPLICATE, authorization.authorization_id)
                )
            elif claim.disposition is AuthorizationClaimDisposition.CONFLICT:
                findings.append(
                    _finding(TransitionAuthorizationFindingCode.AUTHORIZATION_CONFLICT, authorization.authorization_id)
                )
            else:
                references.append(f"authorization:{authorization.authorization_id}:{authorization.binding_digest}")
                return _assessment(
                    assessment_id=assessment_id,
                    intent=intent,
                    authorization=authorization,
                    disposition=TransitionAuthorizationDisposition.AUTHORIZED,
                    findings=findings,
                    references=references,
                    timestamp=timestamp,
                )

        return _assessment(
            assessment_id=assessment_id,
            intent=intent,
            authorization=authorization,
            disposition=TransitionAuthorizationDisposition.NOT_AUTHORIZED,
            findings=findings,
            references=references,
            timestamp=timestamp,
        )


def _validate_profile(
    intent: ExternalTransitionIntentEvidence,
    findings: list[TransitionAuthorizationFinding],
) -> bool:
    if intent.transition_profile is not ExternalTransitionProfile.EXTERNAL_ARTIFACT_TRANSITION_V1:
        findings.append(
            _finding(
                TransitionAuthorizationFindingCode.UNSUPPORTED_TRANSITION_PROFILE,
                f"profile:{intent.transition_profile}",
            )
        )
        return False
    return True


def _validate_idempotency_key(
    intent: ExternalTransitionIntentEvidence,
    findings: list[TransitionAuthorizationFinding],
) -> None:
    if re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,127}", intent.idempotency_key) is None:
        findings.append(
            _finding(TransitionAuthorizationFindingCode.IDEMPOTENCY_KEY_INVALID, intent.idempotency_key)
        )


def _validate_eligibility(
    intent: ExternalTransitionIntentEvidence,
    promotion_request: PromotionEligibilityRequest | object,
    promotion_assessment: PromotionEligibilityAssessment | object,
    findings: list[TransitionAuthorizationFinding],
    references: list[str],
) -> None:
    if not isinstance(promotion_request, PromotionEligibilityRequest) or not isinstance(
        promotion_assessment, PromotionEligibilityAssessment
    ):
        findings.append(_finding(TransitionAuthorizationFindingCode.ELIGIBILITY_EVIDENCE_INVALID, "eligibility"))
        return
    references.extend(
        (
            f"promotion_assessment:{promotion_assessment.assessment_id}:{promotion_assessment.assessment_digest}",
            f"promotion_intent:{promotion_request.intent_id}:{promotion_request.artifact_fingerprint}",
        )
    )
    if promotion_assessment.disposition is not PromotionEligibilityDisposition.ELIGIBLE:
        findings.append(
            _finding(
                TransitionAuthorizationFindingCode.ELIGIBILITY_EVIDENCE_INVALID,
                promotion_assessment.assessment_id,
            )
        )
    expected_identity = f"{promotion_request.artifact_id}:{promotion_request.artifact_fingerprint}"
    if promotion_assessment.artifact_identity != expected_identity:
        findings.append(
            _finding(TransitionAuthorizationFindingCode.ELIGIBILITY_EVIDENCE_INVALID, "assessment_identity")
        )
    if (
        intent.eligibility_assessment_id != promotion_assessment.assessment_id
        or intent.eligibility_assessment_digest != promotion_assessment.assessment_digest
        or intent.transition_intent_id != promotion_request.intent_id
        or intent.promotion_policy_digest != promotion_request.promotion_policy_digest
    ):
        findings.append(
            _finding(TransitionAuthorizationFindingCode.TRANSITION_INTENT_BINDING_MISMATCH, "eligibility_binding")
        )
    if intent.artifact_id != promotion_request.artifact_id or (
        intent.artifact_fingerprint != promotion_request.artifact_fingerprint
    ):
        findings.append(_finding(TransitionAuthorizationFindingCode.ARTIFACT_IDENTITY_MISMATCH, "artifact"))
    if intent.destination_identity != promotion_request.destination_identity:
        findings.append(
            _finding(TransitionAuthorizationFindingCode.DESTINATION_BINDING_MISMATCH, "destination")
        )


def _validate_authorization(
    intent: ExternalTransitionIntentEvidence,
    authorization: ExternalTransitionAuthorizationReceipt | None,
    timestamp: datetime,
    findings: list[TransitionAuthorizationFinding],
    references: list[str],
) -> None:
    if authorization is None:
        findings.append(_finding(TransitionAuthorizationFindingCode.AUTHORIZATION_MISSING, "authorization"))
        return
    if not isinstance(authorization, ExternalTransitionAuthorizationReceipt):
        findings.append(_finding(TransitionAuthorizationFindingCode.AUTHORIZATION_BINDING_MISMATCH, "authorization"))
        return
    if authorization.decision is not HumanAuthorizationDecision.AUTHORIZED:
        findings.append(
            _finding(TransitionAuthorizationFindingCode.AUTHORIZATION_DENIED, authorization.authorization_id)
        )
    canonical_time = timestamp.astimezone(UTC) if timestamp.tzinfo is not None else timestamp
    if canonical_time >= authorization.expires_at:
        findings.append(
            _finding(TransitionAuthorizationFindingCode.AUTHORIZATION_EXPIRED, authorization.authorization_id)
        )
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
            _finding(TransitionAuthorizationFindingCode.AUTHORIZATION_BINDING_MISMATCH, authorization.authorization_id)
        )
    else:
        references.append(f"authorization:{authorization.authorization_id}:{authorization.binding_digest}")


def _finding(
    code: TransitionAuthorizationFindingCode,
    reference: str,
) -> TransitionAuthorizationFinding:
    return TransitionAuthorizationFinding(code=code, evidence_reference=reference)


def _assessment(
    *,
    assessment_id: str,
    intent: ExternalTransitionIntentEvidence,
    authorization: ExternalTransitionAuthorizationReceipt | None,
    disposition: TransitionAuthorizationDisposition,
    findings: Iterable[TransitionAuthorizationFinding],
    references: Iterable[str],
    timestamp: datetime,
) -> TransitionAuthorizationAssessment:
    ordered_findings = tuple(
        sorted(
            {(finding.code.value, finding.evidence_reference): finding for finding in findings}.values(),
            key=lambda item: (item.code.value, item.evidence_reference),
        )
    )
    ordered_references = tuple(sorted(set(references)))
    recommendations = tuple(sorted({_recommendation(finding.code) for finding in ordered_findings}))
    return TransitionAuthorizationAssessment.issue(
        assessment_id=assessment_id,
        authorization_id=authorization.authorization_id if authorization is not None else None,
        intent=intent,
        disposition=disposition,
        findings=ordered_findings,
        evidence_refs=ordered_references,
        recommendations=recommendations,
        timestamp=timestamp,
    )


def _recommendation(code: TransitionAuthorizationFindingCode) -> str:
    recommendations = {
        TransitionAuthorizationFindingCode.ELIGIBILITY_EVIDENCE_INVALID: "supply the exact published eligible transition evidence",
        TransitionAuthorizationFindingCode.TRANSITION_INTENT_BINDING_MISMATCH: "bind the transition intent to the exact eligibility evidence",
        TransitionAuthorizationFindingCode.ARTIFACT_IDENTITY_MISMATCH: "bind authorization to the exact eligible artifact identity",
        TransitionAuthorizationFindingCode.DESTINATION_BINDING_MISMATCH: "bind authorization to the exact eligible logical destination",
        TransitionAuthorizationFindingCode.AUTHORIZATION_MISSING: "supply explicit immutable human authorization evidence",
        TransitionAuthorizationFindingCode.AUTHORIZATION_DENIED: "obtain an explicit authorized decision before any future executor is considered",
        TransitionAuthorizationFindingCode.AUTHORIZATION_EXPIRED: "supply unexpired authorization evidence bound to the exact transition intent",
        TransitionAuthorizationFindingCode.AUTHORIZATION_BINDING_MISMATCH: "supply authorization evidence bound to the exact transition intent",
        TransitionAuthorizationFindingCode.AUTHORIZATION_DUPLICATE: "use the previously stored immutable authorization evidence rather than replaying its claim",
        TransitionAuthorizationFindingCode.AUTHORIZATION_CONFLICT: "resolve conflicting authorization identity evidence outside this boundary",
        TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_UNAVAILABLE: "restore a safe durable authorization evidence store",
        TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_CORRUPT: "replace the unsafe durable authorization evidence store outside this boundary",
        TransitionAuthorizationFindingCode.IDEMPOTENCY_KEY_INVALID: "supply a canonical idempotency key without claiming it",
        TransitionAuthorizationFindingCode.UNSUPPORTED_TRANSITION_PROFILE: "use the supported evidence-only transition profile",
    }
    return recommendations[code]


__all__ = ["TransitionAuthorizationAssessor"]
