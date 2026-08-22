"""Deterministic evidence-only fixtures for G2.4.15 promotion eligibility tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from eag.governed_artifact_readiness import ArtifactReadinessAssessment, ArtifactReadinessRequest
from eag.governed_artifact_readiness.validator import ArtifactReadinessValidator
from eag.governed_promotion import (
    ArtifactLineageReference,
    PromotionEligibilityRequest,
    PromotionProfile,
)
from test_support.g2_4_14_artifact_readiness_fixture import corrected_bindings


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PromotionEvidenceFixture:
    promotion_request: PromotionEligibilityRequest
    lineage: ArtifactLineageReference
    readiness_request: ArtifactReadinessRequest
    readiness_assessment: ArtifactReadinessAssessment
    timestamp: datetime


def ready_promotion_fixture(*, identity: str = "promotion") -> PromotionEvidenceFixture:
    """Return a fully valid, immutable G2.4.14-to-G2.4.15 evidence set only."""
    artifact_bindings = corrected_bindings(identity=identity)
    readiness_assessment = ArtifactReadinessValidator().assess(
        assessment_id=f"g2415-readiness-{identity}",
        request=artifact_bindings.request,
        snapshot=artifact_bindings.snapshot,
        receipts=artifact_bindings.receipts,
        observed_hygiene_paths=artifact_bindings.observed_hygiene_paths,
    )
    readiness_reference = (
        f"readiness:{readiness_assessment.assessment_id}:{readiness_assessment.digest}"
    )
    lineage = ArtifactLineageReference.declare(
        artifact_identity=readiness_assessment.artifact_identity,
        source_evidence_refs=tuple(sorted(("activation:declared-only", readiness_reference))),
        composition_reference="composition:declared-only",
        readiness_reference=readiness_reference,
        custody_reference="custody:declared-only",
    )
    promotion_request = PromotionEligibilityRequest(
        intent_id=f"g2415-intent-{identity}",
        artifact_id=artifact_bindings.request.artifact_id,
        artifact_fingerprint=artifact_bindings.request.artifact_fingerprint,
        readiness_evidence_reference=readiness_reference,
        lineage_reference=f"lineage:{lineage.lineage_digest}",
        destination_identity="pypi-production",
        promotion_policy_digest=_digest("g2415-promotion-policy-v1"),
        promotion_profile=PromotionProfile.ARTIFACT_TRANSITION_ELIGIBILITY_V1,
    )
    return PromotionEvidenceFixture(
        promotion_request=promotion_request,
        lineage=lineage,
        readiness_request=artifact_bindings.request,
        readiness_assessment=readiness_assessment,
        timestamp=datetime(2026, 8, 22, tzinfo=UTC),
    )


__all__ = ["PromotionEvidenceFixture", "ready_promotion_fixture"]
