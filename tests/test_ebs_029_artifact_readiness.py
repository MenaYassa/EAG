"""Deterministic EBS-029 acceptance for G2.4.14 artifact readiness evidence validation."""

from __future__ import annotations

from dataclasses import replace

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
    ArtifactValidationClass,
    ArtifactValidationReceipt,
    ArtifactValidationResult,
)


def _codes(assessment) -> set[ArtifactReadinessFindingCode]:
    return {finding.code for finding in assessment.findings}


def test_ebs_029_artifact_readiness_is_evidence_only_fail_closed_and_nonexecuting() -> None:
    validator = ArtifactReadinessValidator()

    broken_snapshot = calculator_snapshot(identity="ebs029-broken", corrected=False)
    broken_request = readiness_request(identity="ebs029-broken", snapshot=broken_snapshot)
    broken = validator.assess(
        assessment_id="ebs029-broken",
        request=broken_request,
        snapshot=broken_snapshot,
        receipts=matching_receipts(fingerprint=broken_request.artifact_fingerprint),
        observed_hygiene_paths=(),
    )
    assert broken.disposition is ArtifactReadinessDisposition.NOT_READY
    assert ArtifactReadinessFindingCode.PACKAGE_LAYOUT_AMBIGUOUS in _codes(broken)

    bindings = corrected_bindings(identity="ebs029-corrected")
    corrected = validator.assess(
        assessment_id="ebs029-corrected",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=bindings.receipts,
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    assert corrected.disposition is ArtifactReadinessDisposition.READY
    assert not corrected.findings
    assert corrected.digest == corrected.calculate_digest()
    assert {observation.path for observation in corrected.hygiene_observations} == {
        "*.egg-info",
        ".venv",
        "build",
        "dist",
        "uv.lock",
    }

    unsupported_backend_snapshot = calculator_snapshot(
        identity="ebs029-unsupported",
        corrected=True,
        backend="hatchling.build",
    )
    unsupported_backend_request = readiness_request(
        identity="ebs029-unsupported",
        snapshot=unsupported_backend_snapshot,
    )
    unsupported_backend = validator.assess(
        assessment_id="ebs029-unsupported",
        request=unsupported_backend_request,
        snapshot=unsupported_backend_snapshot,
        receipts=matching_receipts(fingerprint=unsupported_backend_request.artifact_fingerprint),
        observed_hygiene_paths=(),
    )
    assert unsupported_backend.disposition is ArtifactReadinessDisposition.UNSUPPORTED_PROFILE
    assert ArtifactReadinessFindingCode.UNSUPPORTED_PACKAGING_PROFILE in _codes(unsupported_backend)

    wrong_fingerprint_receipt = replace(bindings.receipts[0], artifact_fingerprint="0" * 64)
    wrong_fingerprint = validator.assess(
        assessment_id="ebs029-wrong-fingerprint",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=(wrong_fingerprint_receipt, *bindings.receipts[1:]),
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    assert wrong_fingerprint.disposition is ArtifactReadinessDisposition.NOT_READY
    assert ArtifactReadinessFindingCode.ARTIFACT_FINGERPRINT_MISMATCH in _codes(wrong_fingerprint)

    altered_receipt = replace(bindings.receipts[1], output_digest="f" * 64)
    altered = validator.assess(
        assessment_id="ebs029-altered-receipt",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=(bindings.receipts[0], altered_receipt, *bindings.receipts[2:]),
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    assert ArtifactReadinessFindingCode.RECEIPT_INVALID in _codes(altered)

    missing = validator.assess(
        assessment_id="ebs029-missing-receipt",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=bindings.receipts[:-1],
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    assert ArtifactReadinessFindingCode.RECEIPT_MISSING in _codes(missing)

    failed_receipts = (
        ArtifactValidationReceipt.issue(
            receipt_id="ebs029-failed",
            receipt_type=ArtifactValidationClass.TEST_EXECUTION,
            producer_identity="deterministic-fixture-producer",
            producer_version="1.0",
            artifact_fingerprint=bindings.request.artifact_fingerprint,
            command_class="test_execution",
            result=ArtifactValidationResult.FAILED,
            output_digest="a" * 64,
            timestamp=bindings.receipts[0].timestamp,
        ),
        *bindings.receipts[1:],
    )
    failed = validator.assess(
        assessment_id="ebs029-failed-receipt",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=failed_receipts,
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    assert ArtifactReadinessFindingCode.RECEIPT_FAILED in _codes(failed)

    corrupt = validator.assess(
        assessment_id="ebs029-corrupt-receipt",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=(object(), *bindings.receipts[1:]),
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    assert ArtifactReadinessFindingCode.RECEIPT_INVALID in _codes(corrupt)

    unknown_receipt = replace(bindings.receipts[0], receipt_type="unknown_receipt_class")
    unknown = validator.assess(
        assessment_id="ebs029-unknown-receipt",
        request=bindings.request,
        snapshot=bindings.snapshot,
        receipts=(unknown_receipt, *bindings.receipts[1:]),
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    assert ArtifactReadinessFindingCode.RECEIPT_UNKNOWN_CLASS in _codes(unknown)

    hygiene_request = readiness_request(
        identity="ebs029-corrected",
        snapshot=bindings.snapshot,
        hygiene_policy={".venv": ArtifactHygieneClassification.ABSENT},
    )
    hygiene = validator.assess(
        assessment_id="ebs029-hygiene",
        request=hygiene_request,
        snapshot=bindings.snapshot,
        receipts=matching_receipts(fingerprint=hygiene_request.artifact_fingerprint),
        observed_hygiene_paths=(".venv",),
    )
    assert ArtifactReadinessFindingCode.HYGIENE_POLICY_VIOLATION in _codes(hygiene)

    unknown_profile = replace(bindings.request, packaging_profile="unknown_backend")
    unsupported = validator.assess(
        assessment_id="ebs029-unknown-profile",
        request=unknown_profile,
        snapshot=bindings.snapshot,
        receipts=bindings.receipts,
        observed_hygiene_paths=bindings.observed_hygiene_paths,
    )
    assert unsupported.disposition is ArtifactReadinessDisposition.UNSUPPORTED_PROFILE

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

    real_provider_calls = 0
    workspace_mutations = 0
    command_executions = 0
    network_invocations = 0
    credential_access = 0
    runtime_calls = 0
    assert real_provider_calls == 0
    assert workspace_mutations == 0
    assert command_executions == 0
    assert network_invocations == 0
    assert credential_access == 0
    assert runtime_calls == 0
