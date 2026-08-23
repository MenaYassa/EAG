"""Deterministic fixtures for G2.4.17 transition-control evidence tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eag.governed_transition_authorization import TransitionAuthorizationAssessor
from eag.governed_transition_control import (
    ExternalTransitionControlRequest,
    FileDurableTransitionControlLedger,
    TransitionControlProfile,
)
from test_support.g2_4_16_transition_authorization_fixture import (
    authorization_fixture,
)
from test_support.g2_4_16_transition_authorization_fixture import (
    durable_store as authorization_store,
)


@dataclass(frozen=True, slots=True)
class TransitionControlFixture:
    request: ExternalTransitionControlRequest
    authorization: object
    authorization_assessment: object
    timestamp: object


def control_fixture(*, control_root: Path, identity: str = "control") -> TransitionControlFixture:
    """Return exact published G2.4.16 AUTHORIZED evidence and a G2.4.17 control request only."""
    authorization_data = authorization_fixture(identity=identity)
    authorization_root = control_root / "authorization-evidence"
    authorization_root.mkdir()
    assessment = TransitionAuthorizationAssessor().assess(
        assessment_id=f"g2417-authorization-assessment-{identity}",
        intent=authorization_data.intent,
        authorization=authorization_data.authorization,
        promotion_request=authorization_data.promotion_request,
        promotion_assessment=authorization_data.promotion_assessment,
        store=authorization_store(authorization_root),
        timestamp=authorization_data.timestamp,
    )
    request = ExternalTransitionControlRequest(
        control_request_id=f"g2417-control-request-{identity}",
        authorization_id=authorization_data.authorization.authorization_id,
        authorization_binding_digest=authorization_data.authorization.binding_digest,
        authorization_assessment_id=assessment.assessment_id,
        authorization_assessment_digest=assessment.assessment_digest,
        transition_intent_id=authorization_data.intent.transition_intent_id,
        artifact_id=authorization_data.intent.artifact_id,
        artifact_fingerprint=authorization_data.intent.artifact_fingerprint,
        destination_identity=authorization_data.intent.destination_identity,
        promotion_policy_digest=authorization_data.intent.promotion_policy_digest,
        authorization_policy_digest=authorization_data.intent.authorization_policy_digest,
        idempotency_key=authorization_data.intent.idempotency_key,
        transition_profile=TransitionControlProfile.EXTERNAL_ARTIFACT_TRANSITION_CONTROL_V1,
        occurred_at=authorization_data.timestamp,
        execution_id=authorization_data.intent.execution_id,
        run_id=authorization_data.intent.run_id,
    )
    return TransitionControlFixture(
        request=request,
        authorization=authorization_data.authorization,
        authorization_assessment=assessment,
        timestamp=authorization_data.timestamp,
    )


def durable_ledger(control_root: Path) -> FileDurableTransitionControlLedger:
    """Return a file-backed ledger for a caller-created disposable control root."""
    return FileDurableTransitionControlLedger(control_root=control_root)


__all__ = ["TransitionControlFixture", "control_fixture", "durable_ledger"]
