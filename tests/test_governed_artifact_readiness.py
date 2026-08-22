"""Deterministic unit coverage for G2.4.14 artifact readiness evidence validation."""

from __future__ import annotations

from dataclasses import replace

import pytest
from test_support.g2_4_14_artifact_readiness_fixture import (
    calculator_snapshot,
    corrected_bindings,
    matching_receipts,
    readiness_request,
)

from eag.governed_artifact_readiness import (
    ArtifactHygieneClassification,
    ArtifactReadinessDisposition,
    ArtifactReadinessFindingCode,
    ArtifactReadinessValidator,
    ArtifactValidationResult,
)


def _codes(assessment) -> set[ArtifactReadinessFindingCode]:
    return {finding.code for finding in assessment.findings}


def test_corrected_calculator_evidence_is_ready_and_immutable() -> None:
    bindings = corrected_bindings()
    validator = ArtifactReadinessValidator()

    assessment = validator.assess(
        assessment_id="unit-ready",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=bindings.receipts,
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )

    assert assessment.disposition is ArtifactReadinessDisposition.READY
    assert not assessment.findings
    assert assessment.digest == assessment.calculate_digest()
    assert all(observation.classification is not ArtifactHygieneClassification.POLICY_VIOLATION for observation in assessment.hygiene_observations)
    with pytest.raises(Exception):  # noqa: B017
        assessment.disposition = ArtifactReadinessDisposition.NOT_READY  # type: ignore[misc]


def test_broken_flat_calculator_metadata_is_not_ready() -> None:
    snapshot = calculator_snapshot(identity="broken", corrected=False)
    request = readiness_request(identity="broken", snapshot=snapshot)

    assessment = ArtifactReadinessValidator().assess(
        assessment_id="unit-broken",
        request=request,
        snapshot=snapshot,
        receipts=matching_receipts(fingerprint=request.artifact_fingerprint),
        observed_hygiene_paths=(),
    )

    assert assessment.disposition is ArtifactReadinessDisposition.NOT_READY
    assert ArtifactReadinessFindingCode.PACKAGE_LAYOUT_AMBIGUOUS in _codes(assessment)


def test_receipts_fail_closed_on_changed_artifact_or_altered_content() -> None:
    bindings = corrected_bindings(identity="receipt")
    validator = ArtifactReadinessValidator()
    wrong_fingerprint = replace(
        bindings.receipts[0],
        artifact_fingerprint="0" * 64,
    )
    altered_receipt = replace(
        bindings.receipts[1],
        result=ArtifactValidationResult.FAILED,
    )

    wrong_assessment = validator.assess(
        assessment_id="unit-wrong-fingerprint",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=(wrong_fingerprint, *bindings.receipts[1:]),
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    altered_assessment = validator.assess(
        assessment_id="unit-altered-receipt",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=(bindings.receipts[0], altered_receipt, *bindings.receipts[2:]),
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )

    assert ArtifactReadinessFindingCode.ARTIFACT_FINGERPRINT_MISMATCH in _codes(wrong_assessment)
    assert ArtifactReadinessFindingCode.RECEIPT_INVALID in _codes(altered_assessment)


def test_changed_source_metadata_or_entrypoint_evidence_cannot_reuse_prior_receipts() -> None:
    bindings = corrected_bindings(identity="changed-artifact")
    validator = ArtifactReadinessValidator()
    changed_snapshots = (
        calculator_snapshot(
            identity="changed-artifact",
            corrected=True,
            calculator_source="def main():\n    return 1\n",
        ),
        calculator_snapshot(
            identity="changed-artifact",
            corrected=True,
            pyproject_suffix="dependencies=[\"example\"]\n",
        ),
        calculator_snapshot(
            identity="changed-artifact",
            corrected=True,
            entrypoint="different=calculator:main",
        ),
    )

    for index, changed_snapshot in enumerate(changed_snapshots):
        assessment = validator.assess(
            assessment_id=f"unit-changed-{index}",
            request=bindings.request,
            snapshot=changed_snapshot,
            receipts=bindings.receipts,
            observed_hygiene_paths=bindings.observed_hygiene_paths,
        )
        assert assessment.disposition is ArtifactReadinessDisposition.NOT_READY
        assert ArtifactReadinessFindingCode.ARTIFACT_FINGERPRINT_MISMATCH in _codes(assessment)


def test_hygiene_policy_is_classified_but_never_cleaned() -> None:
    bindings = corrected_bindings(identity="hygiene")
    request = readiness_request(
        identity="hygiene",
        snapshot=bindings.snapshot,
        hygiene_policy={".venv": ArtifactHygieneClassification.ABSENT},
    )

    assessment = ArtifactReadinessValidator().assess(
        assessment_id="unit-hygiene",
        request=request,
        snapshot=bindings.snapshot,
        receipts=matching_receipts(fingerprint=request.artifact_fingerprint),
        observed_hygiene_paths=(".venv",),
    )

    assert assessment.disposition is ArtifactReadinessDisposition.NOT_READY
    assert ArtifactReadinessFindingCode.HYGIENE_POLICY_VIOLATION in _codes(assessment)
    assert assessment.hygiene_observations[0].classification is ArtifactHygieneClassification.ABSENT


def test_validator_has_no_execution_or_control_authority() -> None:
    validator = ArtifactReadinessValidator()

    for forbidden_name in (
        "execute",
        "repair",
        "retry",
        "approve",
        "publish",
        "create_session",
        "issue_permit",
        "invoke",
        "cleanup",
    ):
        assert not hasattr(validator, forbidden_name)
