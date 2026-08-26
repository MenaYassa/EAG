"""Deterministic contracts for G2.4.10 governed workspace custody evidence."""

from __future__ import annotations

import inspect
import os
import threading
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from test_support.g2_4_10_workspace_custody_fixture import (
    UnavailableWorkspaceCustodyStore,
    custody_bindings,
    custody_store,
)

from eag.governed_workspace import (
    WorkspaceCustodyGate,
    WorkspaceCustodyHandleError,
    WorkspaceCustodyRejectionReason,
    WorkspaceCustodyRootBinding,
    WorkspaceCustodyRootHandle,
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


def test_model_a_handoff_issues_v2_evidence_and_retains_exact_live_descriptor(tmp_path: Path) -> None:
    assert tuple(inspect.signature(WorkspaceCustodyGate.attest_and_acquire_root_handoff).parameters) == (
        "self",
        "request",
    )
    bindings = custody_bindings(tmp_path / "handoff", identity="handoff")
    gate = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    handoff = gate.attest_and_acquire_root_handoff(
        request=bindings.request,
    )

    assert handoff.reason is None
    assert handoff.attestation is not None
    assert handoff.binding is not None
    assert handoff.handle is not None
    assert handoff.attestation.custody_request_id == bindings.request.custody_request_id
    assert handoff.attestation.custody_request_digest == bindings.request.request_digest
    assert handoff.binding.custody_attestation_binding_digest == handoff.attestation.binding_digest
    assert tuple(inspect.signature(type(handoff.handle).consume_for_g2_4_22).parameters) == (
        "self",
        "binding",
    )

    descriptor = handoff.handle.consume_for_g2_4_22(
        binding=handoff.binding,
    )
    descriptor_identity = os.fstat(descriptor)
    workspace_identity = handoff.binding.workspace_object_identity
    assert str(descriptor_identity.st_dev) == workspace_identity.device_id
    assert str(descriptor_identity.st_ino) == workspace_identity.inode
    assert tuple(bindings.workspace_root.iterdir()) == ()
    handoff.handle.close()
    assert handoff.handle.is_closed


def test_model_a_handoff_refuses_consumption_mismatch_and_reuse_without_effect(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "refusal", identity="refusal")
    gate = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    handoff = gate.attest_and_acquire_root_handoff(
        request=bindings.request,
    )
    assert handoff.binding is not None
    assert handoff.handle is not None
    before = tuple(bindings.workspace_root.iterdir())

    mismatch_bindings = custody_bindings(tmp_path / "mismatch", identity="mismatch")
    mismatch_gate = WorkspaceCustodyGate(custody_store=custody_store(mismatch_bindings.control_root))
    mismatch = mismatch_gate.attest_and_acquire_root_handoff(
        request=mismatch_bindings.request,
    )
    assert mismatch.binding is not None
    assert mismatch.handle is not None
    with pytest.raises(WorkspaceCustodyHandleError, match="handle_binding_mismatch"):
        handoff.handle.consume_for_g2_4_22(binding=mismatch.binding)
    mismatch.handle.close()
    descriptor = handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
    assert descriptor >= 0
    with pytest.raises(WorkspaceCustodyHandleError, match="handle_already_consumed"):
        handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
    handoff.handle.close()
    with pytest.raises(WorkspaceCustodyHandleError, match="handle_closed"):
        handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
    assert tuple(bindings.workspace_root.iterdir()) == before == ()


def test_model_a_handoff_replacement_after_acquisition_keeps_original_descriptor(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "replacement", identity="replacement")
    gate = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    handoff = gate.attest_and_acquire_root_handoff(
        request=bindings.request,
    )
    assert handoff.binding is not None
    assert handoff.handle is not None
    original_root = bindings.workspace_root
    renamed_root = original_root.with_name("workspace-original")
    original_root.rename(renamed_root)
    original_root.mkdir()

    descriptor = handoff.handle.consume_for_g2_4_22(
        binding=handoff.binding,
    )
    observed = os.fstat(descriptor)
    assert str(observed.st_dev) == handoff.binding.workspace_object_identity.device_id
    assert str(observed.st_ino) == handoff.binding.workspace_object_identity.inode
    assert tuple(original_root.iterdir()) == ()
    assert tuple(renamed_root.iterdir()) == ()
    handoff.handle.close()


def test_model_a_handoff_refuses_nonempty_and_symlink_roots_before_handle(tmp_path: Path) -> None:
    nonempty = custody_bindings(tmp_path / "nonempty", identity="nonempty")
    (nonempty.workspace_root / "existing.txt").write_text("existing", encoding="utf-8")
    nonempty_gate = WorkspaceCustodyGate(custody_store=custody_store(nonempty.control_root))
    nonempty_result = nonempty_gate.attest_and_acquire_root_handoff(
        request=nonempty.request,
    )

    symlinked = custody_bindings(tmp_path / "symlink", identity="symlink")
    target = symlinked.workspace_root.with_name("workspace-target")
    symlinked.workspace_root.rename(target)
    symlinked.workspace_root.symlink_to(target, target_is_directory=True)
    symlink_gate = WorkspaceCustodyGate(custody_store=custody_store(symlinked.control_root))
    symlink_result = symlink_gate.attest_and_acquire_root_handoff(
        request=symlinked.request,
    )

    assert nonempty_result.reason is WorkspaceCustodyRejectionReason.NONEMPTY_WORKSPACE
    assert nonempty_result.handle is None
    assert symlink_result.reason is WorkspaceCustodyRejectionReason.UNSAFE_ROOT
    assert symlink_result.handle is None
    assert (nonempty.workspace_root / "existing.txt").read_text(encoding="utf-8") == "existing"
    assert tuple(target.iterdir()) == ()


def test_model_a_handoff_capability_refusal_and_handle_nonserialization_preserve_state(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "capability", identity="capability")
    before = tuple(bindings.workspace_root.iterdir())
    unavailable_gate = WorkspaceCustodyGate(
        custody_store=custody_store(bindings.control_root),
        capability_probe=lambda: False,
    )
    unavailable = unavailable_gate.attest_and_acquire_root_handoff(
        request=bindings.request,
    )
    assert unavailable.reason is WorkspaceCustodyRejectionReason.HANDOFF_CAPABILITY_UNSUPPORTED
    assert unavailable.handle is None
    assert tuple(bindings.workspace_root.iterdir()) == before == ()

    supported_gate = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    supported = supported_gate.attest_and_acquire_root_handoff(
        request=bindings.request,
    )
    assert supported.handle is not None
    with pytest.raises(WorkspaceCustodyHandleError, match="cannot be serialized"):
        __import__("pickle").dumps(supported.handle)
    supported.handle.close()


def test_model_a_handoff_is_thread_local_noncopyable_and_closed_on_abandonment(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "thread-local", identity="thread-local")
    gate = WorkspaceCustodyGate(custody_store=custody_store(bindings.control_root))
    handoff = gate.attest_and_acquire_root_handoff(
        request=bindings.request,
    )
    assert handoff.binding is not None
    assert handoff.handle is not None
    thread_failure: list[WorkspaceCustodyHandleError] = []

    def _cross_thread_consume() -> None:
        try:
            handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
        except WorkspaceCustodyHandleError as error:
            thread_failure.append(error)

    worker = threading.Thread(target=_cross_thread_consume)
    worker.start()
    worker.join()
    assert [str(error) for error in thread_failure] == ["handle_context_mismatch"]
    with pytest.raises(WorkspaceCustodyHandleError, match="cannot be copied"):
        __import__("copy").copy(handoff.handle)
    with pytest.raises(WorkspaceCustodyHandleError, match="cannot be copied"):
        __import__("copy").deepcopy(handoff.handle)
    with pytest.raises(RuntimeError, match="abandoned"), handoff.handle:
        raise RuntimeError("abandoned")
    assert handoff.handle.is_closed
    with pytest.raises(WorkspaceCustodyHandleError, match="handle_closed"):
        handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
    assert tuple(bindings.workspace_root.iterdir()) == ()


def test_model_a_handoff_refuses_same_thread_reentrant_descriptor_consumption(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "reentrant", identity="reentrant")
    handoff = WorkspaceCustodyGate(
        custody_store=custody_store(bindings.control_root)
    ).attest_and_acquire_root_handoff(request=bindings.request)
    assert handoff.binding is not None
    assert handoff.handle is not None
    original_binding = handoff.binding
    reentrant_error: list[WorkspaceCustodyHandleError] = []

    class _ReentrantBinding:
        @property
        def binding_digest(self) -> str:
            try:
                handoff.handle.consume_for_g2_4_22(binding=original_binding)
            except WorkspaceCustodyHandleError as error:
                reentrant_error.append(error)
            return original_binding.binding_digest

    descriptor = handoff.handle.consume_for_g2_4_22(
        binding=cast(WorkspaceCustodyRootBinding, _ReentrantBinding()),
    )
    assert os.fstat(descriptor).st_ino == int(original_binding.workspace_object_identity.inode)
    assert [str(error) for error in reentrant_error] == ["handle_already_consumed"]
    with pytest.raises(WorkspaceCustodyHandleError, match="handle_already_consumed"):
        handoff.handle.consume_for_g2_4_22(binding=original_binding)
    assert handoff.binding == original_binding
    handoff.handle.close()
    assert handoff.handle.is_closed
    assert tuple(bindings.workspace_root.iterdir()) == ()


def test_model_a_public_handle_construction_cannot_forge_matching_binding_provenance(tmp_path: Path) -> None:
    bindings = custody_bindings(tmp_path / "forged", identity="forged")
    handoff = WorkspaceCustodyGate(
        custody_store=custody_store(bindings.control_root)
    ).attest_and_acquire_root_handoff(request=bindings.request)
    assert handoff.binding is not None
    assert handoff.handle is not None
    before_workspace = tuple(bindings.workspace_root.iterdir())
    before_source = tuple(bindings.source_root.iterdir())
    arbitrary_descriptor = os.open(bindings.source_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with pytest.raises(WorkspaceCustodyHandleError, match="custody_continuity_broken"):
            WorkspaceCustodyRootHandle(descriptor=arbitrary_descriptor, binding=handoff.binding)
        assert os.fstat(arbitrary_descriptor).st_ino == os.stat(bindings.source_root).st_ino
        assert tuple(bindings.workspace_root.iterdir()) == before_workspace == ()
        assert tuple(bindings.source_root.iterdir()) == before_source == ()
        descriptor = handoff.handle.consume_for_g2_4_22(binding=handoff.binding)
        assert os.fstat(descriptor).st_ino == int(handoff.binding.workspace_object_identity.inode)
    finally:
        os.close(arbitrary_descriptor)
        handoff.handle.close()
