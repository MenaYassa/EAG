"""Deterministic EBS-025 acceptance for governed workspace custody evidence."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_support.g2_4_10_workspace_custody_fixture import (
    UnavailableWorkspaceCustodyStore,
    custody_bindings,
    custody_store,
)

from eag.governed_workspace import (
    WorkspaceCustodyError,
    WorkspaceCustodyGate,
    WorkspaceCustodyHandleError,
    WorkspaceCustodyRejectionReason,
    WorkspaceCustodyRootHandle,
)


def _attest(gate: WorkspaceCustodyGate, bindings):
    return gate.attest(
        request=bindings.request,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )


def test_ebs_025_workspace_custody_is_exact_durable_fail_closed_and_nonexecuting(tmp_path: Path) -> None:
    success = custody_bindings(tmp_path / "success", identity="success")
    workspace_before = tuple(success.workspace_root.iterdir())
    source_before = tuple(success.source_root.iterdir())
    audit_before = tuple(success.audit_root.iterdir())
    success_gate = WorkspaceCustodyGate(custody_store=custody_store(success.control_root))
    attested = _attest(success_gate, success)
    assert attested.attestation is not None
    recreated = WorkspaceCustodyGate(custody_store=custody_store(success.control_root))
    exact_validation = recreated.validate(attestation=attested.attestation, request=success.request)
    altered_workspace = recreated.validate(
        attestation=attested.attestation,
        request=replace(success.request, workspace_id="altered-workspace"),
    )
    altered_policy = recreated.validate(
        attestation=attested.attestation,
        request=replace(
            success.request,
            policy=replace(success.request.policy, require_empty_workspace=False),
        ),
    )
    duplicate = _attest(success_gate, success)

    aliases = custody_bindings(tmp_path / "aliases", identity="aliases")
    alias_gate = WorkspaceCustodyGate(custody_store=custody_store(aliases.control_root))
    workspace_equals_source = alias_gate.attest(
        request=replace(aliases.request, workspace_root=aliases.source_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )
    workspace_equals_audit = alias_gate.attest(
        request=replace(aliases.request, workspace_root=aliases.audit_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )
    workspace_equals_control = alias_gate.attest(
        request=replace(aliases.request, workspace_root=aliases.control_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )

    corrupt = custody_bindings(tmp_path / "corrupt", identity="corrupt")
    corrupt_gate = WorkspaceCustodyGate(custody_store=custody_store(corrupt.control_root))
    corrupt_attestation = _attest(corrupt_gate, corrupt)
    assert corrupt_attestation.attestation is not None
    next(corrupt.control_root.glob("attestation-*.json")).write_text("corrupt", encoding="utf-8")
    corrupt_result = corrupt_gate.validate(
        attestation=corrupt_attestation.attestation,
        request=corrupt.request,
    )

    unavailable = custody_bindings(tmp_path / "unavailable", identity="unavailable")
    unavailable_result = WorkspaceCustodyGate(
        custody_store=UnavailableWorkspaceCustodyStore(control_root=unavailable.control_root)
    ).attest(
        request=unavailable.request,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )

    assert exact_validation is None
    assert altered_workspace is WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert altered_policy is WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert duplicate.reason is WorkspaceCustodyRejectionReason.ATTESTATION_ID_DUPLICATE
    assert workspace_equals_source.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert workspace_equals_audit.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert workspace_equals_control.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert corrupt_result is WorkspaceCustodyRejectionReason.STORE_CORRUPT
    assert unavailable_result.reason is WorkspaceCustodyRejectionReason.STORE_UNAVAILABLE

    assert tuple(success.workspace_root.iterdir()) == workspace_before == ()
    assert tuple(success.source_root.iterdir()) == source_before == ()
    assert tuple(success.audit_root.iterdir()) == audit_before == ()
    assert not hasattr(success_gate, "create_session")
    assert not hasattr(success_gate, "consume_for_runtime_start")
    assert not hasattr(success_gate, "execute")
    assert not hasattr(success_gate, "invoke")
    assert not hasattr(success_gate, "mutate")



def test_ebs_025_model_a_handoff_issues_v2_evidence_from_one_live_descriptor_event(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "model-a", identity="model-a")
    gate = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    handoff = gate.attest_and_acquire_root_handoff(
        request=bindings.request,
    )
    assert handoff.reason is None
    assert handoff.attestation is not None
    assert handoff.binding is not None
    assert handoff.handle is not None
    assert handoff.attestation.schema_version == "g2.4.10-custody-attestation.v2"
    assert handoff.attestation.custody_request_id == bindings.request.custody_request_id
    assert handoff.attestation.custody_request_digest == bindings.request.request_digest
    assert handoff.binding.custody_attestation_id == handoff.attestation.attestation_id
    assert handoff.binding.custody_attestation_binding_digest == handoff.attestation.binding_digest
    attestation_payload = handoff.attestation.to_payload()
    tampered_attestation_payload = dict(attestation_payload)
    tampered_attestation_payload["binding_digest"] = "0" * 64
    with pytest.raises(WorkspaceCustodyError, match="invalid workspace custody payload"):
        type(handoff.attestation).from_payload(tampered_attestation_payload)
    with pytest.raises(WorkspaceCustodyError, match="binding_digest does not match canonical custody root binding"):
        replace(handoff.binding, custody_request_digest="0" * 64)
    assert handoff.attestation.to_payload() == attestation_payload
    assert tuple(bindings.workspace_root.iterdir()) == ()

    original_root = bindings.workspace_root
    retained_root = original_root.with_name("workspace-retained")
    original_root.rename(retained_root)
    original_root.mkdir()
    descriptor = handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
    descriptor_identity = os.fstat(descriptor)
    assert str(descriptor_identity.st_dev) == handoff.binding.workspace_object_identity.device_id
    assert str(descriptor_identity.st_ino) == handoff.binding.workspace_object_identity.inode
    assert tuple(original_root.iterdir()) == ()
    assert tuple(retained_root.iterdir()) == ()
    handoff.handle.close()
    assert handoff.handle.is_closed


def test_ebs_025_model_a_refusal_and_handle_lifecycle_are_pre_effect(tmp_path: Path) -> None:
    primary = custody_bindings(tmp_path / "primary", identity="primary")
    gate = WorkspaceCustodyGate(custody_store=custody_store(primary.control_root))
    handoff = gate.attest_and_acquire_root_handoff(
        request=primary.request,
    )
    assert handoff.binding is not None
    assert handoff.handle is not None
    before = tuple(primary.workspace_root.iterdir())

    different = custody_bindings(tmp_path / "different", identity="different")
    different_handoff = WorkspaceCustodyGate(
        custody_store=custody_store(different.control_root)
    ).attest_and_acquire_root_handoff(
        request=different.request,
    )
    assert different_handoff.binding is not None
    assert different_handoff.handle is not None
    with pytest.raises(WorkspaceCustodyHandleError, match="handle_binding_mismatch"):
        handoff.handle.consume_for_g2_4_22(binding=different_handoff.binding)
    different_handoff.handle.close()
    handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
    with pytest.raises(WorkspaceCustodyHandleError, match="handle_already_consumed"):
        handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
    handoff.handle.close()
    with pytest.raises(WorkspaceCustodyHandleError, match="handle_closed"):
        handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
    assert tuple(primary.workspace_root.iterdir()) == before == ()


def test_ebs_025_model_a_unsupported_capability_refuses_before_custody_effect(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "unsupported", identity="unsupported")
    gate = WorkspaceCustodyGate(
        custody_store=custody_store(bindings.control_root),
        capability_probe=lambda: False,
    )
    result = gate.attest_and_acquire_root_handoff(
        request=bindings.request,
    )
    assert result.reason is WorkspaceCustodyRejectionReason.HANDOFF_CAPABILITY_UNSUPPORTED
    assert result.attestation is None
    assert result.binding is None
    assert result.handle is None
    assert tuple(bindings.workspace_root.iterdir()) == ()
    assert tuple(bindings.control_root.glob("attestation-*.json")) == ()


def test_ebs_025_model_a_symlinked_root_refuses_before_handoff_or_effect(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "symlinked-root", identity="symlinked-root")
    workspace_target = bindings.workspace_root.with_name("workspace-target")
    bindings.workspace_root.rename(workspace_target)
    bindings.workspace_root.symlink_to(workspace_target, target_is_directory=True)
    before = (
        bindings.workspace_root.is_symlink(),
        os.readlink(bindings.workspace_root),
        tuple(workspace_target.iterdir()),
        tuple(bindings.source_root.iterdir()),
        tuple(bindings.audit_root.iterdir()),
        tuple(bindings.control_root.iterdir()),
    )
    result = WorkspaceCustodyGate(
        custody_store=custody_store(bindings.control_root)
    ).attest_and_acquire_root_handoff(request=bindings.request)

    assert result.reason is WorkspaceCustodyRejectionReason.UNSAFE_ROOT
    assert result.attestation is None
    assert result.binding is None
    assert result.handle is None
    assert (
        bindings.workspace_root.is_symlink(),
        os.readlink(bindings.workspace_root),
        tuple(workspace_target.iterdir()),
        tuple(bindings.source_root.iterdir()),
        tuple(bindings.audit_root.iterdir()),
        tuple(bindings.control_root.iterdir()),
    ) == before


def test_ebs_025_model_a_nonempty_root_refuses_before_handoff_or_effect(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "nonempty-root", identity="nonempty-root")
    existing_file = bindings.workspace_root / "existing.txt"
    existing_file.write_text("pre-existing", encoding="utf-8")
    before = (
        tuple((entry.name, entry.read_bytes()) for entry in bindings.workspace_root.iterdir()),
        tuple(bindings.source_root.iterdir()),
        tuple(bindings.audit_root.iterdir()),
        tuple(bindings.control_root.iterdir()),
    )
    result = WorkspaceCustodyGate(
        custody_store=custody_store(bindings.control_root)
    ).attest_and_acquire_root_handoff(request=bindings.request)

    assert result.reason is WorkspaceCustodyRejectionReason.NONEMPTY_WORKSPACE
    assert result.attestation is None
    assert result.binding is None
    assert result.handle is None
    assert (
        tuple((entry.name, entry.read_bytes()) for entry in bindings.workspace_root.iterdir()),
        tuple(bindings.source_root.iterdir()),
        tuple(bindings.audit_root.iterdir()),
        tuple(bindings.control_root.iterdir()),
    ) == before


def test_ebs_025_model_a_public_matching_binding_handle_cannot_forge_descriptor_provenance(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "forged-provenance", identity="forged-provenance")
    handoff = WorkspaceCustodyGate(
        custody_store=custody_store(bindings.control_root)
    ).attest_and_acquire_root_handoff(request=bindings.request)
    assert handoff.binding is not None
    assert handoff.handle is not None
    before = (
        tuple(bindings.workspace_root.iterdir()),
        tuple(bindings.source_root.iterdir()),
        tuple(bindings.audit_root.iterdir()),
        tuple(bindings.control_root.iterdir()),
    )
    arbitrary_descriptor = os.open(bindings.source_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with pytest.raises(WorkspaceCustodyHandleError, match="custody_continuity_broken"):
            WorkspaceCustodyRootHandle(descriptor=arbitrary_descriptor, binding=handoff.binding)
        assert os.fstat(arbitrary_descriptor).st_ino == os.stat(bindings.source_root).st_ino
        assert handoff.handle.consume_for_g2_4_22(binding=handoff.binding) >= 0
        assert (
            tuple(bindings.workspace_root.iterdir()),
            tuple(bindings.source_root.iterdir()),
            tuple(bindings.audit_root.iterdir()),
            tuple(bindings.control_root.iterdir()),
        ) == before
    finally:
        os.close(arbitrary_descriptor)
        handoff.handle.close()
