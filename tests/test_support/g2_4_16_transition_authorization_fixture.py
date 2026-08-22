"""Deterministic evidence-only fixtures for G2.4.16 authorization tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from eag.governed_promotion import (
    PromotionEligibilityAssessment,
    PromotionEligibilityAssessor,
    PromotionEligibilityRequest,
)
from eag.governed_transition_authorization import (
    ExternalTransitionAuthorizationReceipt,
    ExternalTransitionIntentEvidence,
    ExternalTransitionProfile,
    FileDurableTransitionAuthorizationStore,
    HumanAuthorizationDecision,
)
from test_support.g2_4_15_promotion_fixture import ready_promotion_fixture


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TransitionAuthorizationFixture:
    intent: ExternalTransitionIntentEvidence
    authorization: ExternalTransitionAuthorizationReceipt
    promotion_request: PromotionEligibilityRequest
    promotion_assessment: PromotionEligibilityAssessment
    timestamp: datetime


def authorization_fixture(*, identity: str = "transition") -> TransitionAuthorizationFixture:
    """Return exact immutable G2.4.15 evidence plus authorized G2.4.16 receipt only."""
    promotion = ready_promotion_fixture(identity=identity)
    timestamp = datetime(2026, 8, 22, tzinfo=UTC)
    promotion_assessment = PromotionEligibilityAssessor().assess(
        assessment_id=f"g2416-promotion-{identity}",
        request=promotion.promotion_request,
        lineage=promotion.lineage,
        readiness_request=promotion.readiness_request,
        readiness_assessment=promotion.readiness_assessment,
        timestamp=timestamp,
    )
    intent = ExternalTransitionIntentEvidence(
        transition_intent_id=promotion.promotion_request.intent_id,
        artifact_id=promotion.promotion_request.artifact_id,
        artifact_fingerprint=promotion.promotion_request.artifact_fingerprint,
        destination_identity=promotion.promotion_request.destination_identity,
        eligibility_assessment_id=promotion_assessment.assessment_id,
        eligibility_assessment_digest=promotion_assessment.assessment_digest,
        promotion_policy_digest=promotion.promotion_request.promotion_policy_digest,
        authorization_policy_digest=_digest("g2416-authorization-policy-v1"),
        idempotency_key=f"transition-{identity}-v1",
        transition_profile=ExternalTransitionProfile.EXTERNAL_ARTIFACT_TRANSITION_V1,
        execution_id="declared-execution-only",
        run_id="declared-run-only",
    )
    authorization = ExternalTransitionAuthorizationReceipt.issue(
        authorization_id=f"g2416-authorization-{identity}",
        approver_identity="operator@example.invalid",
        decision=HumanAuthorizationDecision.AUTHORIZED,
        occurred_at=timestamp,
        expires_at=timestamp + timedelta(hours=1),
        transition_intent=intent,
    )
    return TransitionAuthorizationFixture(
        intent=intent,
        authorization=authorization,
        promotion_request=promotion.promotion_request,
        promotion_assessment=promotion_assessment,
        timestamp=timestamp,
    )


def durable_store(control_root: Path) -> FileDurableTransitionAuthorizationStore:
    """Return a file-backed store for a caller-created non-workspace test control root."""
    return FileDurableTransitionAuthorizationStore(control_root=control_root)


__all__ = [
    "TransitionAuthorizationFixture",
    "authorization_fixture",
    "durable_store",
]
