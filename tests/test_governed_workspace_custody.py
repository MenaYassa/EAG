"""Deterministic contracts for G2.4.10 governed workspace custody evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from test_support.g2_4_10_workspace_custody_fixture import (
    UnavailableWorkspaceCustodyStore,
    custody_bindings,
    custody_store,
)

from eag.governed_workspace import (
    WorkspaceCustodyGate,
    WorkspaceCustodyRejectionReason,
)


def _attest(gate: WorkspaceCustodyGate, bindings):
    return gate.attest(
        request=bindings.request,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )


def test_immutable_custody_attestation_is_durable_and_exactly_validates_bindings(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path, identity="success")
    gate = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    admitted = _attest(gate, bindings)
    assert admitted.attestation is not None

    recreated = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    validation = recreated.validate(attestation=admitted.attestation, request=bindings.request)
    altered_workspace = replace(bindings.request, workspace_id="altered-workspace")
    altered_policy = replace(
        bindings.request,
        policy=replace(bindings.request.policy, require_empty_workspace=False),
    )

    assert validation is None
    assert recreated.validate(
        attestation=admitted.attestation,
        request=altered_workspace,
    ) is WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert recreated.validate(
        attestation=admitted.attestation,
        request=altered_policy,
    ) is WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert not hasattr(gate, "create_session")
    assert not hasattr(gate, "execute")
    assert not hasattr(gate, "mutate")


def test_root_aliasing_is_refused_without_workspace_mutation(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "roots", identity="roots")
    gate = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    workspace_before = tuple(bindings.workspace_root.iterdir())

    source_alias = gate.attest(
        request=replace(bindings.request, workspace_root=bindings.source_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )
    audit_alias = gate.attest(
        request=replace(bindings.request, workspace_root=bindings.audit_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )
    control_alias = gate.attest(
        request=replace(bindings.request, workspace_root=bindings.control_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )
    assert source_alias.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert audit_alias.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert control_alias.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert workspace_before == ()
    assert tuple(bindings.source_root.iterdir()) == ()
    assert tuple(bindings.audit_root.iterdir()) == ()


def test_duplicate_conflicting_corrupt_and_unavailable_custody_storage_fail_closed(tmp_path: Path) -> None:
    duplicate_bindings = custody_bindings(tmp_path / "duplicate", identity="duplicate")
    duplicate_gate = WorkspaceCustodyGate(custody_store=custody_store(duplicate_bindings.control_root))
    first = _attest(duplicate_gate, duplicate_bindings)
    duplicate = _attest(duplicate_gate, duplicate_bindings)

    conflict_bindings = custody_bindings(tmp_path / "conflict", identity="conflict")
    conflict_gate = WorkspaceCustodyGate(custody_store=custody_store(conflict_bindings.control_root))
    conflict_first = _attest(conflict_gate, conflict_bindings)
    conflict = conflict_gate.attest(
        request=replace(conflict_bindings.request, workspace_id="conflicting-workspace"),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )

    corrupt_bindings = custody_bindings(tmp_path / "corrupt", identity="corrupt")
    corrupt_gate = WorkspaceCustodyGate(custody_store=custody_store(corrupt_bindings.control_root))
    corrupt_first = _attest(corrupt_gate, corrupt_bindings)
    next(corrupt_bindings.control_root.glob("attestation-*.json")).write_text(
        '{"schema_version":"g2.4.10"}',
        encoding="utf-8",
    )
    corrupt = corrupt_gate.validate(attestation=corrupt_first.attestation, request=corrupt_bindings.request)

    unsafe_bindings = custody_bindings(tmp_path / "unsafe", identity="unsafe")
    unsafe_gate = WorkspaceCustodyGate(custody_store=custody_store(unsafe_bindings.control_root))
    unsafe_first = _attest(unsafe_gate, unsafe_bindings)
    unsafe_record = next(unsafe_bindings.control_root.glob("attestation-*.json"))
    unsafe_target = unsafe_bindings.control_root / "untrusted-record"
    unsafe_target.write_text("untrusted", encoding="utf-8")
    unsafe_record.unlink()
    unsafe_record.symlink_to(unsafe_target)
    unsafe = unsafe_gate.validate(attestation=unsafe_first.attestation, request=unsafe_bindings.request)

    unavailable_bindings = custody_bindings(tmp_path / "unavailable", identity="unavailable")
    unavailable = WorkspaceCustodyGate(
        custody_store=UnavailableWorkspaceCustodyStore(control_root=unavailable_bindings.control_root)
    ).attest(
        request=unavailable_bindings.request,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )

    assert first.attestation is not None
    assert duplicate.reason is WorkspaceCustodyRejectionReason.ATTESTATION_ID_DUPLICATE
    assert conflict_first.attestation is not None
    assert conflict.reason is WorkspaceCustodyRejectionReason.ATTESTATION_ID_CONFLICT
    assert corrupt is WorkspaceCustodyRejectionReason.STORE_CORRUPT
    assert unsafe is WorkspaceCustodyRejectionReason.STORE_CORRUPT
    assert unavailable.reason is WorkspaceCustodyRejectionReason.STORE_UNAVAILABLE
