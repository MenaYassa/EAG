"""Deterministic unit coverage for G2.4.15 promotion eligibility evidence validation."""

from __future__ import annotations

from dataclasses import replace

from test_support.g2_4_15_promotion_fixture import ready_promotion_fixture

from eag.governed_artifact_readiness import (
    ArtifactReadinessAssessment,
    ArtifactReadinessDisposition,
)
from eag.governed_promotion import (
    PromotionEligibilityAssessor,
    PromotionEligibilityDisposition,
    PromotionFindingCode,
)


def _codes(assessment) -> set[PromotionFindingCode]:
    return {finding.code for finding in assessment.findings}


def test_valid_ready_artifact_and_declared_lineage_are_eligible() -> None:
    fixture = ready_promotion_fixture()

    assessment = PromotionEligibilityAssessor().assess(
        assessment_id="unit-eligible",
        request=fixture.promotion_request,
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )

    assert assessment.disposition is PromotionEligibilityDisposition.ELIGIBLE
    assert not assessment.findings
    assert assessment.assessment_digest == assessment.calculate_digest()


def test_missing_or_not_ready_artifact_evidence_is_not_eligible() -> None:
    fixture = ready_promotion_fixture(identity="not-ready")
    assessor = PromotionEligibilityAssessor()
    missing = assessor.assess(
        assessment_id="unit-missing",
        request=fixture.promotion_request,
        lineage=fixture.lineage,
        readiness_request=object(),
        readiness_assessment=object(),
        timestamp=fixture.timestamp,
    )
    not_ready = ArtifactReadinessAssessment.issue(
        assessment_id="unit-not-ready-source",
        artifact_identity=fixture.readiness_assessment.artifact_identity,
        disposition=ArtifactReadinessDisposition.NOT_READY,
        findings=(),
        evidence_references=fixture.readiness_assessment.evidence_references,
        hygiene_observations=fixture.readiness_assessment.hygiene_observations,
        recommendations=(),
    )
    not_ready_assessment = assessor.assess(
        assessment_id="unit-not-ready",
        request=fixture.promotion_request,
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=not_ready,
        timestamp=fixture.timestamp,
    )

    assert PromotionFindingCode.READINESS_EVIDENCE_INVALID in _codes(missing)
    assert PromotionFindingCode.NOT_READY_ARTIFACT in _codes(not_ready_assessment)


def test_changed_artifact_and_lineage_evidence_fail_closed() -> None:
    fixture = ready_promotion_fixture(identity="changed")
    assessor = PromotionEligibilityAssessor()
    changed_request = replace(fixture.promotion_request, artifact_fingerprint="0" * 64)
    changed_lineage = replace(fixture.lineage, custody_reference="custody:altered")

    changed_artifact = assessor.assess(
        assessment_id="unit-changed-artifact",
        request=changed_request,
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )
    changed_lineage_assessment = assessor.assess(
        assessment_id="unit-changed-lineage",
        request=fixture.promotion_request,
        lineage=changed_lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )

    assert PromotionFindingCode.ARTIFACT_IDENTITY_MISMATCH in _codes(changed_artifact)
    assert PromotionFindingCode.LINEAGE_BINDING_MISMATCH in _codes(changed_lineage_assessment)


def test_invalid_destination_and_unsupported_profile_are_refused() -> None:
    fixture = ready_promotion_fixture(identity="destination")
    assessor = PromotionEligibilityAssessor()
    invalid_destination = assessor.assess(
        assessment_id="unit-invalid-destination",
        request=replace(fixture.promotion_request, destination_identity="https://registry.example/token"),
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )
    unsupported_profile = assessor.assess(
        assessment_id="unit-unsupported-profile",
        request=replace(fixture.promotion_request, promotion_profile="unknown_profile"),
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )

    assert invalid_destination.disposition is PromotionEligibilityDisposition.UNSUPPORTED_DESTINATION
    assert PromotionFindingCode.UNSUPPORTED_DESTINATION in _codes(invalid_destination)
    assert unsupported_profile.disposition is PromotionEligibilityDisposition.NOT_ELIGIBLE
    assert PromotionFindingCode.UNSUPPORTED_PROFILE in _codes(unsupported_profile)


def test_assessor_has_no_execution_or_promotion_authority() -> None:
    assessor = PromotionEligibilityAssessor()

    for forbidden_name in (
        "promote",
        "publish",
        "upload",
        "execute",
        "release",
        "create_session",
        "issue_permit",
        "invoke",
        "retry",
        "rollback",
    ):
        assert not hasattr(assessor, forbidden_name)
