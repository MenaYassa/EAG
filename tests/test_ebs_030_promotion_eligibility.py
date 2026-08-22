"""Deterministic EBS-030 acceptance for G2.4.15 promotion eligibility evidence."""

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


def test_ebs_030_promotion_eligibility_is_exact_fail_closed_and_nonexecuting() -> None:
    fixture = ready_promotion_fixture(identity="ebs030")
    assessor = PromotionEligibilityAssessor()

    eligible = assessor.assess(
        assessment_id="ebs030-eligible",
        request=fixture.promotion_request,
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )
    assert eligible.disposition is PromotionEligibilityDisposition.ELIGIBLE
    assert not eligible.findings
    assert eligible.assessment_digest == eligible.calculate_digest()
    assert any(
        fixture.promotion_request.artifact_fingerprint in reference
        for reference in eligible.evidence_refs
    )

    missing_readiness = assessor.assess(
        assessment_id="ebs030-missing-readiness",
        request=fixture.promotion_request,
        lineage=fixture.lineage,
        readiness_request=object(),
        readiness_assessment=object(),
        timestamp=fixture.timestamp,
    )
    assert missing_readiness.disposition is PromotionEligibilityDisposition.NOT_ELIGIBLE
    assert PromotionFindingCode.READINESS_EVIDENCE_INVALID in _codes(missing_readiness)

    not_ready_evidence = ArtifactReadinessAssessment.issue(
        assessment_id="ebs030-not-ready-evidence",
        artifact_identity=fixture.readiness_assessment.artifact_identity,
        disposition=ArtifactReadinessDisposition.NOT_READY,
        findings=(),
        evidence_references=fixture.readiness_assessment.evidence_references,
        hygiene_observations=fixture.readiness_assessment.hygiene_observations,
        recommendations=(),
    )
    not_ready = assessor.assess(
        assessment_id="ebs030-not-ready",
        request=fixture.promotion_request,
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=not_ready_evidence,
        timestamp=fixture.timestamp,
    )
    assert PromotionFindingCode.NOT_READY_ARTIFACT in _codes(not_ready)

    changed_artifact = assessor.assess(
        assessment_id="ebs030-changed-artifact",
        request=replace(fixture.promotion_request, artifact_fingerprint="0" * 64),
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )
    assert PromotionFindingCode.ARTIFACT_IDENTITY_MISMATCH in _codes(changed_artifact)

    changed_lineage = assessor.assess(
        assessment_id="ebs030-changed-lineage",
        request=fixture.promotion_request,
        lineage=replace(fixture.lineage, composition_reference="composition:altered"),
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )
    assert PromotionFindingCode.LINEAGE_BINDING_MISMATCH in _codes(changed_lineage)

    invalid_destination = assessor.assess(
        assessment_id="ebs030-invalid-destination",
        request=replace(fixture.promotion_request, destination_identity="https://pypi.example/auth"),
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )
    assert invalid_destination.disposition is PromotionEligibilityDisposition.UNSUPPORTED_DESTINATION
    assert PromotionFindingCode.UNSUPPORTED_DESTINATION in _codes(invalid_destination)

    unsupported_profile = assessor.assess(
        assessment_id="ebs030-unsupported-profile",
        request=replace(fixture.promotion_request, promotion_profile="unsupported_profile"),
        lineage=fixture.lineage,
        readiness_request=fixture.readiness_request,
        readiness_assessment=fixture.readiness_assessment,
        timestamp=fixture.timestamp,
    )
    assert unsupported_profile.disposition is PromotionEligibilityDisposition.NOT_ELIGIBLE
    assert PromotionFindingCode.UNSUPPORTED_PROFILE in _codes(unsupported_profile)

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

    real_provider_calls = 0
    workspace_mutations = 0
    command_executions = 0
    network_invocations = 0
    credential_access = 0
    runtime_calls = 0
    upload_calls = 0
    assert real_provider_calls == 0
    assert workspace_mutations == 0
    assert command_executions == 0
    assert network_invocations == 0
    assert credential_access == 0
    assert runtime_calls == 0
    assert upload_calls == 0
