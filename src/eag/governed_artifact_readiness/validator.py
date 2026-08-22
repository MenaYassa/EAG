"""Read-only, fail-closed artifact readiness assessment over supplied immutable evidence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from eag.governed_artifact_readiness.models import (
    ArtifactHygieneClassification,
    ArtifactHygieneObservation,
    ArtifactPackagingProfile,
    ArtifactReadinessAssessment,
    ArtifactReadinessDisposition,
    ArtifactReadinessFinding,
    ArtifactReadinessFindingCode,
    ArtifactReadinessRequest,
    ArtifactSnapshotEvidence,
    ArtifactValidationClass,
    ArtifactValidationReceipt,
    ArtifactValidationResult,
    calculate_artifact_fingerprint,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class _AssessmentInput:
    """Private immutable input bundle; it contains evidence only and no operational handle."""

    request: ArtifactReadinessRequest
    snapshot: ArtifactSnapshotEvidence | object
    receipts: tuple[ArtifactValidationReceipt | object, ...]
    observed_hygiene_paths: tuple[str, ...]


class ArtifactReadinessValidator:
    """Assess supplied artifact evidence without reading, executing, changing, or publishing anything.

    This validator has no workspace, runtime, provider, session, permit, audit, mutation, command,
    subprocess, package-tool, or cleanup dependency. It evaluates only caller-supplied contracts.
    """

    def assess(
        self,
        *,
        assessment_id: str,
        request: ArtifactReadinessRequest,
        snapshot: ArtifactSnapshotEvidence | object,
        receipts: tuple[ArtifactValidationReceipt | object],
        observed_hygiene_paths: tuple[str, ...],
    ) -> ArtifactReadinessAssessment:
        """Return one immutable readiness conclusion over exact supplied evidence only."""
        evidence = _AssessmentInput(
            request=request,
            snapshot=snapshot,
            receipts=receipts,
            observed_hygiene_paths=observed_hygiene_paths,
        )
        findings: list[ArtifactReadinessFinding] = []
        references: list[str] = []
        hygiene = _classify_hygiene(evidence, findings)

        if not isinstance(request, ArtifactReadinessRequest):
            raise TypeError("request must be an ArtifactReadinessRequest")
        if not isinstance(snapshot, ArtifactSnapshotEvidence):
            findings.append(_finding(ArtifactReadinessFindingCode.SNAPSHOT_MANIFEST_MISMATCH, "snapshot"))
            return _assessment(
                assessment_id=assessment_id,
                request=request,
                disposition=ArtifactReadinessDisposition.NOT_READY,
                findings=findings,
                references=references,
                hygiene=hygiene,
            )

        references.append(f"snapshot:{snapshot.snapshot_id}:{snapshot.manifest_digest}")
        _validate_snapshot_binding(request, snapshot, findings)
        profile_supported = _validate_packaging_profile(request, snapshot, findings)
        _validate_entrypoints(request, snapshot, findings)
        _validate_receipts(request, snapshot, receipts, findings, references)

        disposition = (
            ArtifactReadinessDisposition.UNSUPPORTED_PROFILE
            if not profile_supported
            else ArtifactReadinessDisposition.NOT_READY
            if findings
            else ArtifactReadinessDisposition.READY
        )
        return _assessment(
            assessment_id=assessment_id,
            request=request,
            disposition=disposition,
            findings=findings,
            references=references,
            hygiene=hygiene,
        )


def _validate_snapshot_binding(
    request: ArtifactReadinessRequest,
    snapshot: ArtifactSnapshotEvidence,
    findings: list[ArtifactReadinessFinding],
) -> None:
    if request.snapshot_id != snapshot.snapshot_id:
        findings.append(_finding(ArtifactReadinessFindingCode.SNAPSHOT_MANIFEST_MISMATCH, "snapshot_id"))
    expected_fingerprint = calculate_artifact_fingerprint(
        artifact_id=request.artifact_id,
        snapshot_id=snapshot.snapshot_id,
        root_identity=request.root_identity,
        manifest_digest=snapshot.manifest_digest,
        pyproject_digest=snapshot.pyproject_digest,
    )
    if request.artifact_fingerprint != expected_fingerprint:
        findings.append(
            _finding(
                ArtifactReadinessFindingCode.ARTIFACT_FINGERPRINT_MISMATCH,
                f"artifact:{request.artifact_id}",
            )
        )


def _validate_packaging_profile(
    request: ArtifactReadinessRequest,
    snapshot: ArtifactSnapshotEvidence,
    findings: list[ArtifactReadinessFinding],
) -> bool:
    if request.packaging_profile is not ArtifactPackagingProfile.SETUPTOOLS_FLAT_MODULE:
        findings.append(
            _finding(
                ArtifactReadinessFindingCode.UNSUPPORTED_PACKAGING_PROFILE,
                f"profile:{request.packaging_profile}",
            )
        )
        return False
    if snapshot.packaging_backend != "setuptools.build_meta":
        findings.append(
            _finding(
                ArtifactReadinessFindingCode.UNSUPPORTED_PACKAGING_PROFILE,
                f"backend:{snapshot.packaging_backend}",
            )
        )
        return False

    root_modules = tuple(
        path.removesuffix(".py")
        for path in snapshot.file_paths
        if path.endswith(".py") and "/" not in path
    )
    declared_modules = snapshot.setuptools_py_modules
    if not declared_modules:
        code = (
            ArtifactReadinessFindingCode.PACKAGE_LAYOUT_AMBIGUOUS
            if len(root_modules) > 1
            else ArtifactReadinessFindingCode.PACKAGE_CONFIGURATION_MISSING
        )
        findings.append(_finding(code, "pyproject.toml"))
        return True
    if any(f"{module}.py" not in snapshot.file_paths for module in declared_modules):
        findings.append(
            _finding(ArtifactReadinessFindingCode.PACKAGE_CONFIGURATION_MISSING, "pyproject.toml")
        )
    return True


def _validate_entrypoints(
    request: ArtifactReadinessRequest,
    snapshot: ArtifactSnapshotEvidence,
    findings: list[ArtifactReadinessFinding],
) -> None:
    for entrypoint in request.expected_entrypoints:
        if entrypoint not in snapshot.declared_entrypoints:
            findings.append(_finding(ArtifactReadinessFindingCode.ENTRYPOINT_MISSING, entrypoint))


def _validate_receipts(
    request: ArtifactReadinessRequest,
    snapshot: ArtifactSnapshotEvidence,
    receipts: tuple[ArtifactValidationReceipt | object, ...],
    findings: list[ArtifactReadinessFinding],
    references: list[str],
) -> None:
    receipt_by_type: dict[ArtifactValidationClass, ArtifactValidationReceipt] = {}
    for index, candidate in enumerate(receipts):
        reference = f"receipt:{index}"
        if not isinstance(candidate, ArtifactValidationReceipt):
            findings.append(_finding(ArtifactReadinessFindingCode.RECEIPT_INVALID, reference))
            continue
        references.append(f"receipt:{candidate.receipt_id}:{candidate.receipt_digest}")
        if not isinstance(candidate.receipt_type, ArtifactValidationClass):
            findings.append(
                _finding(ArtifactReadinessFindingCode.RECEIPT_UNKNOWN_CLASS, candidate.receipt_id)
            )
            continue
        if candidate.artifact_fingerprint != request.artifact_fingerprint:
            findings.append(
                _finding(ArtifactReadinessFindingCode.ARTIFACT_FINGERPRINT_MISMATCH, candidate.receipt_id)
            )
            continue
        if not isinstance(candidate.result, ArtifactValidationResult) or candidate.receipt_digest != candidate.digest:
            findings.append(_finding(ArtifactReadinessFindingCode.RECEIPT_INVALID, candidate.receipt_id))
            continue
        if candidate.receipt_type in receipt_by_type:
            findings.append(_finding(ArtifactReadinessFindingCode.RECEIPT_DUPLICATE, candidate.receipt_id))
            continue
        receipt_by_type[candidate.receipt_type] = candidate
        if candidate.result is not ArtifactValidationResult.PASSED:
            findings.append(_finding(ArtifactReadinessFindingCode.RECEIPT_FAILED, candidate.receipt_id))

    for validation_class in request.required_validation_classes:
        if validation_class not in receipt_by_type:
            findings.append(
                _finding(ArtifactReadinessFindingCode.RECEIPT_MISSING, validation_class.value)
            )


def _classify_hygiene(
    evidence: _AssessmentInput,
    findings: list[ArtifactReadinessFinding],
) -> tuple[ArtifactHygieneObservation, ...]:
    if not isinstance(evidence.request, ArtifactReadinessRequest):
        return ()
    observed = _safe_observed_paths(evidence.observed_hygiene_paths, findings)
    observations: list[ArtifactHygieneObservation] = []
    for policy_path, expected in evidence.request.hygiene_policy.items():
        present_paths = tuple(path for path in observed if _policy_matches(policy_path, path))
        classification = (
            ArtifactHygieneClassification.ABSENT
            if not present_paths
            else expected
        )
        observations.append(
            ArtifactHygieneObservation(path=policy_path, classification=classification)
        )
        if expected is ArtifactHygieneClassification.POLICY_VIOLATION and present_paths or expected is ArtifactHygieneClassification.ABSENT and present_paths:
            findings.append(
                _finding(ArtifactReadinessFindingCode.HYGIENE_POLICY_VIOLATION, policy_path)
            )
    return tuple(sorted(observations, key=lambda observation: observation.path))


def _safe_observed_paths(
    values: tuple[str, ...],
    findings: list[ArtifactReadinessFinding],
) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(not isinstance(value, str) or not value for value in values):
        findings.append(_finding(ArtifactReadinessFindingCode.HYGIENE_POLICY_VIOLATION, "hygiene_input"))
        return ()
    return tuple(sorted(set(values)))


def _policy_matches(policy_path: str, observed_path: str) -> bool:
    if policy_path == "*.egg-info":
        return observed_path.endswith(".egg-info") or ".egg-info/" in observed_path
    return observed_path == policy_path or observed_path.startswith(f"{policy_path}/")


def _finding(
    code: ArtifactReadinessFindingCode,
    evidence_reference: str,
) -> ArtifactReadinessFinding:
    return ArtifactReadinessFinding(code=code, evidence_reference=evidence_reference)


def _assessment(
    *,
    assessment_id: str,
    request: ArtifactReadinessRequest,
    disposition: ArtifactReadinessDisposition,
    findings: Iterable[ArtifactReadinessFinding],
    references: Iterable[str],
    hygiene: tuple[ArtifactHygieneObservation, ...],
) -> ArtifactReadinessAssessment:
    ordered_findings = tuple(
        sorted({(finding.code.value, finding.evidence_reference): finding for finding in findings}.values(), key=lambda item: (item.code.value, item.evidence_reference))
    )
    ordered_references = tuple(sorted(set(references)))
    recommendations = tuple(
        sorted({_recommendation(finding.code) for finding in ordered_findings})
    )
    return ArtifactReadinessAssessment.issue(
        assessment_id=assessment_id,
        artifact_identity=f"{request.artifact_id}:{request.snapshot_id}",
        disposition=disposition,
        findings=ordered_findings,
        evidence_references=ordered_references,
        hygiene_observations=hygiene,
        recommendations=recommendations,
    )


def _recommendation(code: ArtifactReadinessFindingCode) -> str:
    recommendations = {
        ArtifactReadinessFindingCode.ARTIFACT_FINGERPRINT_MISMATCH: "supply evidence bound to the exact artifact fingerprint",
        ArtifactReadinessFindingCode.ENTRYPOINT_MISSING: "declare each required entrypoint in supplied metadata evidence",
        ArtifactReadinessFindingCode.HYGIENE_POLICY_VIOLATION: "supply artifact outputs that satisfy the declared hygiene policy",
        ArtifactReadinessFindingCode.PACKAGE_CONFIGURATION_MISSING: "declare explicit setuptools py-modules for the flat module layout",
        ArtifactReadinessFindingCode.PACKAGE_LAYOUT_AMBIGUOUS: "declare explicit setuptools py-modules for the flat module layout",
        ArtifactReadinessFindingCode.RECEIPT_DUPLICATE: "supply one canonical receipt per required validation class",
        ArtifactReadinessFindingCode.RECEIPT_FAILED: "supply a passed immutable receipt from the declared external validator",
        ArtifactReadinessFindingCode.RECEIPT_INVALID: "supply a complete canonical immutable validation receipt",
        ArtifactReadinessFindingCode.RECEIPT_MISSING: "supply every required external validation receipt",
        ArtifactReadinessFindingCode.RECEIPT_UNKNOWN_CLASS: "supply only declared validation receipt classes",
        ArtifactReadinessFindingCode.SNAPSHOT_MANIFEST_MISMATCH: "supply snapshot evidence matching the declared snapshot identity",
        ArtifactReadinessFindingCode.UNSUPPORTED_PACKAGING_PROFILE: "use an explicitly supported packaging profile and backend",
        ArtifactReadinessFindingCode.PYPROJECT_DIGEST_MISMATCH: "supply canonical pyproject metadata evidence",
    }
    return recommendations[code]


__all__ = ["ArtifactReadinessValidator"]
