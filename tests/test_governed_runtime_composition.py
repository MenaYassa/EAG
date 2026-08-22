"""Deterministic contracts for G2.4.11 runtime composition provenance evidence."""

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
    RuntimeComponentIdentity,
    RuntimeCompositionGate,
    RuntimeCompositionRejectionReason,
)


def _attest(gate: RuntimeCompositionGate, *, attestation_id: str, manifest):
    return gate.attest(
        attestation_id=attestation_id,
        manifest=manifest,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )


def test_composition_attestation_is_durable_self_validating_and_exactly_bound(tmp_path: Path) -> None:
    manifest = composition_manifest(identity="success")
    control_root = tmp_path / "control"
    gate = RuntimeCompositionGate(composition_store=composition_store(control_root))
    admitted = _attest(gate, attestation_id="g2411-attestation-success", manifest=manifest)
    assert admitted.attestation is not None

    recreated = RuntimeCompositionGate(composition_store=composition_store(control_root))
    altered_runtime = replace(manifest, runtime_id="altered-runtime")
    altered_component = replace(
        manifest,
        component_identities=(
            replace(
                manifest.component_identities[0],
                digest="f" * 64,
            ),
            *manifest.component_identities[1:],
        ),
    )
    altered_invocation = replace(manifest, invocation_binding_digest="e" * 64)

    assert recreated.validate(attestation=admitted.attestation, manifest=manifest) is None
    assert recreated.validate(
        attestation=admitted.attestation,
        manifest=altered_runtime,
    ) is RuntimeCompositionRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert recreated.validate(
        attestation=admitted.attestation,
        manifest=altered_component,
    ) is RuntimeCompositionRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert recreated.validate(
        attestation=admitted.attestation,
        manifest=altered_invocation,
    ) is RuntimeCompositionRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert not hasattr(gate, "create_runtime")
    assert not hasattr(gate, "execute")
    assert not hasattr(gate, "create_session")
    assert not hasattr(gate, "consume_for_runtime_start")


def test_duplicate_conflicting_corrupt_unsafe_and_unavailable_composition_store_fail_closed(tmp_path: Path) -> None:
    duplicate_manifest = composition_manifest(identity="duplicate")
    duplicate_root = tmp_path / "duplicate"
    duplicate_gate = RuntimeCompositionGate(composition_store=composition_store(duplicate_root))
    first = _attest(
        duplicate_gate,
        attestation_id="g2411-attestation-duplicate",
        manifest=duplicate_manifest,
    )
    duplicate = _attest(
        duplicate_gate,
        attestation_id="g2411-attestation-duplicate",
        manifest=duplicate_manifest,
    )
    conflict = _attest(
        duplicate_gate,
        attestation_id="g2411-attestation-duplicate",
        manifest=composition_manifest(identity="conflict"),
    )

    corrupt_manifest = composition_manifest(identity="corrupt")
    corrupt_root = tmp_path / "corrupt"
    corrupt_gate = RuntimeCompositionGate(composition_store=composition_store(corrupt_root))
    corrupt_first = _attest(
        corrupt_gate,
        attestation_id="g2411-attestation-corrupt",
        manifest=corrupt_manifest,
    )
    next(corrupt_root.glob("attestation-*.json")).write_text(
        '{"schema_version":"g2.4.11"}',
        encoding="utf-8",
    )
    corrupt = corrupt_gate.validate(attestation=corrupt_first.attestation, manifest=corrupt_manifest)

    unsafe_manifest = composition_manifest(identity="unsafe")
    unsafe_root = tmp_path / "unsafe"
    unsafe_gate = RuntimeCompositionGate(composition_store=composition_store(unsafe_root))
    unsafe_first = _attest(
        unsafe_gate,
        attestation_id="g2411-attestation-unsafe",
        manifest=unsafe_manifest,
    )
    unsafe_record = next(unsafe_root.glob("attestation-*.json"))
    unsafe_target = unsafe_root / "untrusted-record"
    unsafe_target.write_text("untrusted", encoding="utf-8")
    unsafe_record.unlink()
    unsafe_record.symlink_to(unsafe_target)
    unsafe = unsafe_gate.validate(attestation=unsafe_first.attestation, manifest=unsafe_manifest)

    unavailable_manifest = composition_manifest(identity="unavailable")
    unavailable_root = tmp_path / "unavailable"
    unavailable_root.mkdir()
    unavailable = RuntimeCompositionGate(
        composition_store=UnavailableRuntimeCompositionStore(control_root=unavailable_root)
    ).attest(
        attestation_id="g2411-attestation-unavailable",
        manifest=unavailable_manifest,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )

    assert first.attestation is not None
    assert duplicate.reason is RuntimeCompositionRejectionReason.ATTESTATION_ID_DUPLICATE
    assert conflict.reason is RuntimeCompositionRejectionReason.ATTESTATION_ID_CONFLICT
    assert corrupt is RuntimeCompositionRejectionReason.STORE_CORRUPT
    assert unsafe is RuntimeCompositionRejectionReason.STORE_CORRUPT
    assert unavailable.reason is RuntimeCompositionRejectionReason.STORE_UNAVAILABLE


def test_component_identities_remain_immutable_contract_values() -> None:
    component = RuntimeComponentIdentity(
        role="verifier",
        component_id="g2411-verifier",
        version="v1",
        digest="a" * 64,
    )
    assert component.to_payload() == {
        "component_id": "g2411-verifier",
        "digest": "a" * 64,
        "role": "verifier",
        "version": "v1",
    }
