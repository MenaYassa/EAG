"""Read-only, fail-closed G2.4.15 promotion eligibility assessment."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from eag.governed_artifact_readiness import (
    ArtifactReadinessAssessment,
    ArtifactReadinessDisposition,
    ArtifactReadinessRequest,
)
from eag.governed_promotion.models import (
    ArtifactLineageReference,
    PromotionEligibilityAssessment,
    PromotionEligibilityDisposition,
    PromotionEligibilityFinding,
    PromotionEligibilityRequest,
    PromotionFindingCode,
    PromotionProfile,
    is_supported_destination,
)


class PromotionEligibilityAssessor:
    """Assess promotion eligibility from supplied evidence only.

    The assessor has no workspace, artifact, runtime, session, permit, provider, credential,
    network, upload, registry, release, deployment, mutation, audit-write, or retry dependency.
    It cannot cause or record a transition.
    """

    def assess(
        self,
        *,
        assessment_id: str,
        request: PromotionEligibilityRequest,
        lineage: ArtifactLineageReference | object,
        readiness_request: ArtifactReadinessRequest | object,
        readiness_assessment: ArtifactReadinessAssessment | object,
        timestamp: datetime,
    ) -> PromotionEligibilityAssessment:
        """Return an immutable eligibility conclusion over exact supplied evidence."""
        if not isinstance(request, PromotionEligibilityRequest):
            raise TypeError("request must be a PromotionEligibilityRequest")

        findings: list[PromotionEligibilityFinding] = []
        references: list[str] = []
        destination_supported = _validate_destination(request, findings)
        profile_supported = _validate_profile(request, findings)
        _validate_readiness(request, readiness_request, readiness_assessment, findings, references)
        _validate_lineage(request, lineage, readiness_request, readiness_assessment, findings, references)

        disposition = (
            PromotionEligibilityDisposition.UNSUPPORTED_DESTINATION
            if not destination_supported
            else PromotionEligibilityDisposition.NOT_ELIGIBLE
            if findings or not profile_supported
            else PromotionEligibilityDisposition.ELIGIBLE
        )
        return _assessment(
            assessment_id=assessment_id,
            request=request,
            disposition=disposition,
            findings=findings,
            references=references,
            timestamp=timestamp,
        )


def _validate_destination(
    request: PromotionEligibilityRequest,
    findings: list[PromotionEligibilityFinding],
) -> bool:
    if not is_supported_destination(request.destination_identity):
        findings.append(
            _finding(PromotionFindingCode.UNSUPPORTED_DESTINATION, request.destination_identity)
        )
        return False
    return True


def _validate_profile(
    request: PromotionEligibilityRequest,
    findings: list[PromotionEligibilityFinding],
) -> bool:
    if request.promotion_profile is not PromotionProfile.ARTIFACT_TRANSITION_ELIGIBILITY_V1:
        findings.append(
            _finding(PromotionFindingCode.UNSUPPORTED_PROFILE, f"profile:{request.promotion_profile}")
        )
        return False
    return True


def _validate_readiness(
    request: PromotionEligibilityRequest,
    readiness_request: ArtifactReadinessRequest | object,
    readiness_assessment: ArtifactReadinessAssessment | object,
    findings: list[PromotionEligibilityFinding],
    references: list[str],
) -> None:
    if not isinstance(readiness_request, ArtifactReadinessRequest) or not isinstance(
        readiness_assessment, ArtifactReadinessAssessment
    ):
        findings.append(_finding(PromotionFindingCode.READINESS_EVIDENCE_INVALID, "readiness"))
        return

    references.extend(
        (
            f"readiness_assessment:{readiness_assessment.assessment_id}:{readiness_assessment.digest}",
            f"readiness_request:{readiness_request.artifact_id}:{readiness_request.artifact_fingerprint}",
        )
    )
    expected_readiness_reference = (
        f"readiness:{readiness_assessment.assessment_id}:{readiness_assessment.digest}"
    )
    if request.readiness_evidence_reference != expected_readiness_reference:
        findings.append(
            _finding(
                PromotionFindingCode.READINESS_EVIDENCE_INVALID,
                request.readiness_evidence_reference,
            )
        )
    expected_artifact_identity = f"{readiness_request.artifact_id}:{readiness_request.snapshot_id}"
    if readiness_assessment.artifact_identity != expected_artifact_identity:
        findings.append(
            _finding(PromotionFindingCode.READINESS_EVIDENCE_INVALID, "readiness_artifact_identity")
        )
    if readiness_assessment.disposition is not ArtifactReadinessDisposition.READY:
        findings.append(
            _finding(PromotionFindingCode.NOT_READY_ARTIFACT, readiness_assessment.assessment_id)
        )
    if request.artifact_id != readiness_request.artifact_id or (
        request.artifact_fingerprint != readiness_request.artifact_fingerprint
    ):
        findings.append(
            _finding(PromotionFindingCode.ARTIFACT_IDENTITY_MISMATCH, request.artifact_id)
        )


def _validate_lineage(
    request: PromotionEligibilityRequest,
    lineage: ArtifactLineageReference | object,
    readiness_request: ArtifactReadinessRequest | object,
    readiness_assessment: ArtifactReadinessAssessment | object,
    findings: list[PromotionEligibilityFinding],
    references: list[str],
) -> None:
    if not isinstance(lineage, ArtifactLineageReference):
        findings.append(_finding(PromotionFindingCode.LINEAGE_BINDING_MISMATCH, "lineage"))
        return
    references.append(f"lineage:{lineage.lineage_digest}")
    if lineage.lineage_digest != lineage.calculate_digest():
        findings.append(
            _finding(PromotionFindingCode.LINEAGE_BINDING_MISMATCH, "lineage_digest")
        )
        return
    if request.lineage_reference != f"lineage:{lineage.lineage_digest}":
        findings.append(
            _finding(PromotionFindingCode.LINEAGE_BINDING_MISMATCH, request.lineage_reference)
        )
    if not isinstance(readiness_request, ArtifactReadinessRequest) or not isinstance(
        readiness_assessment, ArtifactReadinessAssessment
    ):
        return
    readiness_reference = f"readiness:{readiness_assessment.assessment_id}:{readiness_assessment.digest}"
    expected_artifact_identity = f"{readiness_request.artifact_id}:{readiness_request.snapshot_id}"
    if (
        lineage.artifact_identity != expected_artifact_identity
        or lineage.readiness_reference != readiness_reference
        or readiness_reference not in lineage.source_evidence_refs
    ):
        findings.append(
            _finding(PromotionFindingCode.LINEAGE_BINDING_MISMATCH, "lineage_bindings")
        )


def _finding(code: PromotionFindingCode, reference: str) -> PromotionEligibilityFinding:
    return PromotionEligibilityFinding(code=code, evidence_reference=reference)


def _assessment(
    *,
    assessment_id: str,
    request: PromotionEligibilityRequest,
    disposition: PromotionEligibilityDisposition,
    findings: Iterable[PromotionEligibilityFinding],
    references: Iterable[str],
    timestamp: datetime,
) -> PromotionEligibilityAssessment:
    ordered_findings = tuple(
        sorted(
            {(finding.code.value, finding.evidence_reference): finding for finding in findings}.values(),
            key=lambda item: (item.code.value, item.evidence_reference),
        )
    )
    ordered_references = tuple(sorted(set(references)))
    recommendations = tuple(sorted({_recommendation(finding.code) for finding in ordered_findings}))
    return PromotionEligibilityAssessment.issue(
        assessment_id=assessment_id,
        artifact_identity=f"{request.artifact_id}:{request.artifact_fingerprint}",
        destination_identity=request.destination_identity,
        disposition=disposition,
        findings=ordered_findings,
        evidence_refs=ordered_references,
        recommendations=recommendations,
        timestamp=timestamp.astimezone(UTC) if timestamp.tzinfo is not None else timestamp,
    )


def _recommendation(code: PromotionFindingCode) -> str:
    recommendations = {
        PromotionFindingCode.ARTIFACT_IDENTITY_MISMATCH: "supply promotion intent bound to the exact ready artifact fingerprint",
        PromotionFindingCode.DESTINATION_IDENTITY_INVALID: "supply a canonical non-secret logical destination identity",
        PromotionFindingCode.LINEAGE_BINDING_MISMATCH: "supply canonical declared lineage bound to the exact readiness evidence",
        PromotionFindingCode.NOT_READY_ARTIFACT: "supply a published READY artifact readiness assessment",
        PromotionFindingCode.READINESS_EVIDENCE_INVALID: "supply valid published artifact readiness evidence",
        PromotionFindingCode.UNSUPPORTED_DESTINATION: "use one supported non-secret logical destination identity",
        PromotionFindingCode.UNSUPPORTED_PROFILE: "use the supported artifact transition eligibility profile",
    }
    return recommendations[code]


__all__ = ["PromotionEligibilityAssessor"]
