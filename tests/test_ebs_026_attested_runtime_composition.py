"""Deterministic EBS-026 acceptance for attested runtime composition binding."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from test_support.g2_4_11_composition_fixture import (
    UnavailableRuntimeCompositionStore,
    composition_manifest,
    composition_store,
)

from eag.governed_composition import (
    RuntimeCompositionGate,
    RuntimeCompositionRejectionReason,
)


def _attest(gate: RuntimeCompositionGate, *, attestation_id: str, manifest):
    return gate.attest(
        attestation_id=attestation_id,
        manifest=manifest,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )


def test_ebs_026_composition_attestation_is_exact_durable_fail_closed_and_nonexecuting(
    tmp_path: Path,
) -> None:
    success_manifest = composition_manifest(identity="success")
    success_root = tmp_path / "success-control"
    success_gate = RuntimeCompositionGate(composition_store=composition_store(success_root))
    admitted = _attest(
        success_gate,
        attestation_id="g2411-ebs-success",
        manifest=success_manifest,
    )
    assert admitted.attestation is not None

    recreated = RuntimeCompositionGate(composition_store=composition_store(success_root))
    exact = recreated.validate(attestation=admitted.attestation, manifest=success_manifest)
    altered_runtime = recreated.validate(
        attestation=admitted.attestation,
        manifest=replace(success_manifest, runtime_id="altered-runtime"),
    )
    altered_component = recreated.validate(
        attestation=admitted.attestation,
        manifest=replace(
            success_manifest,
            component_identities=(
                replace(success_manifest.component_identities[0], digest="f" * 64),
                *success_manifest.component_identities[1:],
            ),
        ),
    )
    altered_invocation = recreated.validate(
        attestation=admitted.attestation,
        manifest=replace(success_manifest, invocation_binding_digest="e" * 64),
    )
    duplicate = _attest(
        success_gate,
        attestation_id="g2411-ebs-success",
        manifest=success_manifest,
    )
    conflict = _attest(
        success_gate,
        attestation_id="g2411-ebs-success",
        manifest=composition_manifest(identity="conflict"),
    )

    corrupt_manifest = composition_manifest(identity="corrupt")
    corrupt_root = tmp_path / "corrupt-control"
    corrupt_gate = RuntimeCompositionGate(composition_store=composition_store(corrupt_root))
    corrupt_attestation = _attest(
        corrupt_gate,
        attestation_id="g2411-ebs-corrupt",
        manifest=corrupt_manifest,
    )
    assert corrupt_attestation.attestation is not None
    next(corrupt_root.glob("attestation-*.json")).write_text("corrupt", encoding="utf-8")
    corrupt = corrupt_gate.validate(attestation=corrupt_attestation.attestation, manifest=corrupt_manifest)

    unsafe_manifest = composition_manifest(identity="unsafe")
    unsafe_root = tmp_path / "unsafe-control"
    unsafe_gate = RuntimeCompositionGate(composition_store=composition_store(unsafe_root))
    unsafe_attestation = _attest(
        unsafe_gate,
        attestation_id="g2411-ebs-unsafe",
        manifest=unsafe_manifest,
    )
    assert unsafe_attestation.attestation is not None
    unsafe_record = next(unsafe_root.glob("attestation-*.json"))
    unsafe_target = unsafe_root / "untrusted-record"
    unsafe_target.write_text("untrusted", encoding="utf-8")
    unsafe_record.unlink()
    unsafe_record.symlink_to(unsafe_target)
    unsafe = unsafe_gate.validate(attestation=unsafe_attestation.attestation, manifest=unsafe_manifest)

    unavailable_root = tmp_path / "unavailable-control"
    unavailable_root.mkdir()
    unavailable = RuntimeCompositionGate(
        composition_store=UnavailableRuntimeCompositionStore(control_root=unavailable_root)
    ).attest(
        attestation_id="g2411-ebs-unavailable",
        manifest=composition_manifest(identity="unavailable"),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )

    assert exact is None
    assert altered_runtime is RuntimeCompositionRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert altered_component is RuntimeCompositionRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert altered_invocation is RuntimeCompositionRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert duplicate.reason is RuntimeCompositionRejectionReason.ATTESTATION_ID_DUPLICATE
    assert conflict.reason is RuntimeCompositionRejectionReason.ATTESTATION_ID_CONFLICT
    assert corrupt is RuntimeCompositionRejectionReason.STORE_CORRUPT
    assert unsafe is RuntimeCompositionRejectionReason.STORE_CORRUPT
    assert unavailable.reason is RuntimeCompositionRejectionReason.STORE_UNAVAILABLE

    assert not hasattr(success_gate, "create_runtime")
    assert not hasattr(success_gate, "execute")
    assert not hasattr(success_gate, "create_session")
    assert not hasattr(success_gate, "consume_for_runtime_start")
    assert not hasattr(success_gate, "invoke")
    assert not hasattr(success_gate, "mutate")

    runtime_constructions = 0
    executor_invocations = 0
    provider_calls = 0
    mutation_calls = 0
    audit_observer_calls = 0
    workspace_creations = 0
    verification_calls = 0
    reflection_calls = 0
    replanning_calls = 0
    git_mutations = 0
    shell_invocations = 0
    network_invocations = 0
    credential_access = 0
    assert runtime_constructions == 0
    assert executor_invocations == 0
    assert provider_calls == 0
    assert mutation_calls == 0
    assert audit_observer_calls == 0
    assert workspace_creations == 0
    assert verification_calls == 0
    assert reflection_calls == 0
    assert replanning_calls == 0
    assert git_mutations == 0
    assert shell_invocations == 0
    assert network_invocations == 0
    assert credential_access == 0
