"""EBS-037 — direct proof of published-G2.4.10-bound create-only construction."""

from __future__ import annotations

import os
import resource
import signal
import threading
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from threading import Thread

import pytest
from test_support.g2_4_10_workspace_custody_fixture import custody_bindings, custody_store
from test_support.g2_4_22_file_construction_fixture import file_construction_fixture

from eag.governed_file_construction import (
    BoundedWorkspaceFileConstructor,
    ConstructionBatchDisposition,
    ConstructionBatchReceipt,
    ConstructionEvidenceError,
    ConstructionFileAction,
    ConstructionFindingCode,
    ConstructionPlatformCapabilities,
)
from eag.governed_workspace import (
    WorkspaceCustodyGate,
    WorkspaceCustodyRequest,
    WorkspaceCustodyRootHandle,
)

BENCHMARK_ID = "EBS-037"


def _tree_state(root: Path) -> tuple[tuple[str, str, bytes | None], ...]:
    """Direct state proof over test-owned filesystem objects only."""
    state: list[tuple[str, str, bytes | None]] = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item.relative_to(root))):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            state.append((relative, "symlink", None))
        elif path.is_dir():
            state.append((relative, "directory", None))
        else:
            state.append((relative, "file", path.read_bytes()))
    return tuple(state)


def _unsupported_capabilities() -> ConstructionPlatformCapabilities:
    return ConstructionPlatformCapabilities(
        live_root_handle_consumption=True,
        descriptor_relative_open=True,
        no_follow=True,
        exclusive_create=True,
        regular_file_verification=True,
        link_count_verification=False,
    )


def _fresh_handoff_gate(
    tmp_path: Path,
    identity: str,
) -> tuple[WorkspaceCustodyGate, WorkspaceCustodyRequest, Path, Path]:
    custody = custody_bindings(tmp_path, identity=identity)
    return (
        WorkspaceCustodyGate(custody_store=custody_store(custody.control_root)),
        custody.request,
        custody.workspace_root,
        custody.control_root,
    )


def test_ebs_037_descriptor_bound_create_only_construction(tmp_path: Path) -> None:
    """Prove real descriptor effects, direct refusals, and capability absence without instrumentation."""
    positive = file_construction_fixture(tmp_path / "positive", identity="ebs037-positive")
    positive_before = _tree_state(positive.workspace_root)
    positive_receipt = positive.constructor.construct(authorization=positive.authorization, handle=positive.handoff.handle)
    assert positive_before == ()
    assert positive_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_FILES_CREATED
    assert tuple(item.relative_path for item in positive_receipt.action_receipts) == ("src/main.txt", "README.md")
    assert (positive.workspace_root / "src/main.txt").read_bytes() == b"hello\n"
    assert (positive.workspace_root / "README.md").read_bytes() == b"# example\n"
    assert tuple(item.byte_count for item in positive_receipt.action_receipts) == (6, 10)
    assert tuple(item.content_digest for item in positive_receipt.action_receipts) == tuple(
        item.content_digest for item in positive.authorization.plan.actions
    )
    assert positive_receipt.plan_digest == positive.authorization.plan.plan_digest
    assert positive_receipt.authorization_digest == positive.authorization.authorization_digest
    assert positive_receipt.batch_digest == positive_receipt.calculate_digest()
    assert positive.handoff.handle.is_closed is True
    assert not hasattr(positive_receipt, "__dict__")
    with pytest.raises(FrozenInstanceError):
        positive_receipt.disposition = ConstructionBatchDisposition.CONSTRUCTION_REFUSED

    replacement = file_construction_fixture(tmp_path / "replacement", identity="ebs037-replacement")
    old_path = replacement.workspace_root
    retained_root = replacement.workspace_root.parent / "retained-root"
    old_path.rename(retained_root)
    old_path.mkdir()
    replacement_before = _tree_state(old_path)
    replacement_receipt = replacement.constructor.construct(
        authorization=replacement.authorization,
        handle=replacement.handoff.handle,
    )
    assert replacement_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_FILES_CREATED
    assert _tree_state(old_path) == replacement_before
    assert (retained_root / "src/main.txt").read_bytes() == b"hello\n"
    assert (retained_root / "README.md").read_bytes() == b"# example\n"

    provenance_a = file_construction_fixture(tmp_path / "provenance-a", identity="ebs037-provenance-a")
    provenance_b = file_construction_fixture(tmp_path / "provenance-b", identity="ebs037-provenance-b")
    a_before = _tree_state(provenance_a.workspace_root)
    a_request = replace(
        provenance_a.authorization,
        assessment=provenance_b.authorization.assessment,
        authorization_digest=None,
    )
    a_receipt = provenance_a.constructor.construct(authorization=a_request, handle=provenance_a.handoff.handle)
    assert a_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert a_receipt.first_failure is ConstructionFindingCode.REQUEST_PROVENANCE_MISMATCH
    assert _tree_state(provenance_a.workspace_root) == a_before
    b_before = _tree_state(provenance_b.workspace_root)
    b_request = replace(
        provenance_b.authorization,
        assessment=provenance_a.authorization.assessment,
        authorization_digest=None,
    )
    b_receipt = provenance_b.constructor.construct(authorization=b_request, handle=provenance_b.handoff.handle)
    assert b_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert b_receipt.first_failure is ConstructionFindingCode.REQUEST_PROVENANCE_MISMATCH
    assert _tree_state(provenance_b.workspace_root) == b_before

    custody_mismatch = file_construction_fixture(tmp_path / "custody-mismatch", identity="ebs037-custody-mismatch")
    custody_before = _tree_state(custody_mismatch.workspace_root)
    altered_source = tmp_path / "altered-source"
    altered_source.mkdir()
    altered_request = replace(
        custody_mismatch.authorization,
        custody_request=replace(custody_mismatch.authorization.custody_request, source_repository_root=altered_source),
        authorization_digest=None,
    )
    custody_receipt = custody_mismatch.constructor.construct(
        authorization=altered_request,
        handle=custody_mismatch.handoff.handle,
    )
    assert custody_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert custody_receipt.first_failure is ConstructionFindingCode.CUSTODY_HANDOFF_MISMATCH
    assert _tree_state(custody_mismatch.workspace_root) == custody_before

    audit_mismatch = file_construction_fixture(tmp_path / "audit-mismatch", identity="ebs037-audit-mismatch")
    audit_before = _tree_state(audit_mismatch.workspace_root)
    changed_audit = tmp_path / "changed-audit"
    changed_audit.mkdir()
    audit_receipt = audit_mismatch.constructor.construct(
        authorization=replace(
            audit_mismatch.authorization,
            custody_request=replace(audit_mismatch.authorization.custody_request, audit_root=changed_audit),
            authorization_digest=None,
        ),
        handle=audit_mismatch.handoff.handle,
    )
    assert audit_receipt.first_failure is ConstructionFindingCode.CUSTODY_HANDOFF_MISMATCH
    assert _tree_state(audit_mismatch.workspace_root) == audit_before

    control_mismatch = file_construction_fixture(tmp_path / "control-mismatch", identity="ebs037-control-mismatch")
    control_before = _tree_state(control_mismatch.workspace_root)
    changed_control = tmp_path / "changed-control"
    changed_control.mkdir()
    control_receipt = control_mismatch.constructor.construct(
        authorization=replace(
            control_mismatch.authorization,
            custody_request=replace(control_mismatch.authorization.custody_request, control_root=changed_control),
            authorization_digest=None,
        ),
        handle=control_mismatch.handoff.handle,
    )
    assert control_receipt.first_failure is ConstructionFindingCode.CUSTODY_HANDOFF_MISMATCH
    assert _tree_state(control_mismatch.workspace_root) == control_before

    policy_mismatch = file_construction_fixture(tmp_path / "policy-mismatch", identity="ebs037-policy-mismatch")
    policy_before = _tree_state(policy_mismatch.workspace_root)
    policy_receipt = policy_mismatch.constructor.construct(
        authorization=replace(
            policy_mismatch.authorization,
            custody_request=replace(
                policy_mismatch.authorization.custody_request,
                policy=replace(policy_mismatch.authorization.custody_request.policy, require_empty_workspace=False),
            ),
            authorization_digest=None,
        ),
        handle=policy_mismatch.handoff.handle,
    )
    assert policy_receipt.first_failure is ConstructionFindingCode.CUSTODY_HANDOFF_MISMATCH
    assert _tree_state(policy_mismatch.workspace_root) == policy_before

    root_mismatch = file_construction_fixture(tmp_path / "root-mismatch", identity="ebs037-root-mismatch")
    root_before = _tree_state(root_mismatch.workspace_root)
    changed_root = tmp_path / "changed-root"
    changed_root.mkdir()
    root_receipt = root_mismatch.constructor.construct(
        authorization=replace(
            root_mismatch.authorization,
            custody_request=replace(root_mismatch.authorization.custody_request, workspace_root=changed_root),
            authorization_digest=None,
        ),
        handle=root_mismatch.handoff.handle,
    )
    assert root_receipt.first_failure is ConstructionFindingCode.CUSTODY_HANDOFF_MISMATCH
    assert _tree_state(root_mismatch.workspace_root) == root_before
    assert _tree_state(changed_root) == ()

    forged = file_construction_fixture(tmp_path / "forged-handle", identity="ebs037-forged-handle")
    forged_before = _tree_state(forged.workspace_root)
    arbitrary_root = tmp_path / "forged-arbitrary-root"
    arbitrary_root.mkdir()
    arbitrary_before = _tree_state(arbitrary_root)
    arbitrary_descriptor = os.open(arbitrary_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    forged_handle = object.__new__(WorkspaceCustodyRootHandle)
    object.__setattr__(forged_handle, "_descriptor", arbitrary_descriptor)
    object.__setattr__(forged_handle, "_binding_digest", forged.handoff.binding.binding_digest)
    object.__setattr__(forged_handle, "_pid", os.getpid())
    object.__setattr__(forged_handle, "_thread_id", threading.get_ident())
    object.__setattr__(forged_handle, "_state_lock", threading.RLock())
    object.__setattr__(forged_handle, "_transitioning", False)
    object.__setattr__(forged_handle, "_consumed", False)
    object.__setattr__(forged_handle, "_closed", False)
    forged_receipt = forged.constructor.construct(authorization=forged.authorization, handle=forged_handle)
    assert forged_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert forged_receipt.first_failure is ConstructionFindingCode.HANDLE_REJECTED
    assert _tree_state(forged.workspace_root) == forged_before
    assert _tree_state(arbitrary_root) == arbitrary_before
    assert forged.handoff.handle.is_closed is False
    forged.handoff.handle.close()

    closed = file_construction_fixture(tmp_path / "closed", identity="ebs037-closed")
    closed.handoff.handle.close()
    closed_before = _tree_state(closed.workspace_root)
    closed_receipt = closed.constructor.construct(authorization=closed.authorization, handle=closed.handoff.handle)
    assert closed_receipt.first_failure is ConstructionFindingCode.HANDLE_REJECTED
    assert _tree_state(closed.workspace_root) == closed_before

    consumed = file_construction_fixture(tmp_path / "consumed", identity="ebs037-consumed")
    consumed.handoff.handle.consume_for_g2_4_22(binding=consumed.handoff.binding)
    consumed_before = _tree_state(consumed.workspace_root)
    consumed_receipt = consumed.constructor.construct(authorization=consumed.authorization, handle=consumed.handoff.handle)
    assert consumed_receipt.first_failure is ConstructionFindingCode.HANDLE_REJECTED
    assert _tree_state(consumed.workspace_root) == consumed_before

    mismatch_handle = file_construction_fixture(tmp_path / "mismatch-handle", identity="ebs037-mismatch-handle")
    other_handle = file_construction_fixture(tmp_path / "other-handle", identity="ebs037-other-handle")
    mismatch_before = _tree_state(mismatch_handle.workspace_root)
    mismatch_receipt = mismatch_handle.constructor.construct(
        authorization=mismatch_handle.authorization,
        handle=other_handle.handoff.handle,
    )
    assert mismatch_receipt.first_failure is ConstructionFindingCode.HANDLE_REJECTED
    assert _tree_state(mismatch_handle.workspace_root) == mismatch_before
    mismatch_handle.handoff.handle.close()

    attestation_mismatch = file_construction_fixture(tmp_path / "attestation-mismatch", identity="ebs037-attestation-mismatch")
    alternate_attestation = file_construction_fixture(tmp_path / "alternate-attestation", identity="ebs037-alternate-attestation")
    attestation_before = _tree_state(attestation_mismatch.workspace_root)
    attestation_receipt = attestation_mismatch.constructor.construct(
        authorization=replace(
            attestation_mismatch.authorization,
            custody_attestation=alternate_attestation.authorization.custody_attestation,
            authorization_digest=None,
        ),
        handle=attestation_mismatch.handoff.handle,
    )
    assert attestation_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert attestation_receipt.first_failure is ConstructionFindingCode.WORK_ORDER_BINDING_MISMATCH
    assert _tree_state(attestation_mismatch.workspace_root) == attestation_before
    alternate_attestation.handoff.handle.close()

    binding_mismatch = file_construction_fixture(tmp_path / "binding-mismatch", identity="ebs037-binding-mismatch")
    alternate_binding = file_construction_fixture(tmp_path / "alternate-binding", identity="ebs037-alternate-binding")
    binding_before = _tree_state(binding_mismatch.workspace_root)
    binding_receipt = binding_mismatch.constructor.construct(
        authorization=replace(
            binding_mismatch.authorization,
            custody_root_binding=alternate_binding.authorization.custody_root_binding,
            authorization_digest=None,
        ),
        handle=binding_mismatch.handoff.handle,
    )
    assert binding_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert binding_receipt.first_failure is ConstructionFindingCode.CUSTODY_HANDOFF_MISMATCH
    assert _tree_state(binding_mismatch.workspace_root) == binding_before
    alternate_binding.handoff.handle.close()

    context = file_construction_fixture(tmp_path / "context", identity="ebs037-context")
    context_before = _tree_state(context.workspace_root)
    thread_receipts: list[ConstructionBatchReceipt] = []

    def consume_from_other_thread() -> None:
        thread_receipts.append(
            context.constructor.construct(authorization=context.authorization, handle=context.handoff.handle)
        )

    thread = Thread(target=consume_from_other_thread)
    thread.start()
    thread.join()
    assert len(thread_receipts) == 1
    context_receipt = thread_receipts[0]
    assert context_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert context_receipt.first_failure is ConstructionFindingCode.HANDLE_REJECTED
    assert _tree_state(context.workspace_root) == context_before

    unsupported = file_construction_fixture(tmp_path / "unsupported", identity="ebs037-unsupported")
    unsupported_before = _tree_state(unsupported.workspace_root)
    unsupported_receipt = BoundedWorkspaceFileConstructor(platform_capabilities=_unsupported_capabilities()).construct(
        authorization=unsupported.authorization,
        handle=unsupported.handoff.handle,
    )
    assert unsupported_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert unsupported_receipt.first_failure is ConstructionFindingCode.CONSTRUCTION_CAPABILITY_UNSUPPORTED
    assert _tree_state(unsupported.workspace_root) == unsupported_before

    nonempty_gate, nonempty_request, nonempty_root, _ = _fresh_handoff_gate(tmp_path / "nonempty", "ebs037-nonempty")
    (nonempty_root / "existing.txt").write_bytes(b"existing\n")
    nonempty_before = _tree_state(nonempty_root)
    nonempty_handoff = nonempty_gate.attest_and_acquire_root_handoff(request=nonempty_request)
    assert nonempty_handoff.attestation is None
    assert nonempty_handoff.binding is None
    assert nonempty_handoff.handle is None
    assert _tree_state(nonempty_root) == nonempty_before

    symlink_gate, symlink_request, symlink_root, _ = _fresh_handoff_gate(tmp_path / "symlink", "ebs037-symlink")
    target = tmp_path / "symlink-target"
    symlink_root.rename(target)
    symlink_root.symlink_to(target, target_is_directory=True)
    target_before = _tree_state(target)
    symlink_handoff = symlink_gate.attest_and_acquire_root_handoff(request=symlink_request)
    assert symlink_handoff.attestation is None
    assert symlink_handoff.binding is None
    assert symlink_handoff.handle is None
    assert _tree_state(target) == target_before

    _, handoff_request, handoff_root, handoff_control_root = _fresh_handoff_gate(
        tmp_path / "handoff-capability",
        "ebs037-handoff-capability",
    )
    disabled_handoff_gate = WorkspaceCustodyGate(
        custody_store=custody_store(handoff_control_root),
        capability_probe=lambda: False,
    )
    handoff_before = _tree_state(handoff_root)
    unavailable_handoff = disabled_handoff_gate.attest_and_acquire_root_handoff(request=handoff_request)
    assert unavailable_handoff.attestation is None
    assert unavailable_handoff.binding is None
    assert unavailable_handoff.handle is None
    assert _tree_state(handoff_root) == handoff_before

    existing = file_construction_fixture(
        tmp_path / "existing",
        identity="ebs037-existing",
        actions=(ConstructionFileAction(sequence=1, relative_path="README.md", content="# replacement\n"),),
    )
    (existing.workspace_root / "README.md").write_bytes(b"existing\n")
    existing_before = _tree_state(existing.workspace_root)
    existing_receipt = existing.constructor.construct(authorization=existing.authorization, handle=existing.handoff.handle)
    assert existing_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert existing_receipt.first_failure is ConstructionFindingCode.TARGET_EXISTS
    assert _tree_state(existing.workspace_root) == existing_before

    unsafe = file_construction_fixture(
        tmp_path / "unsafe",
        identity="ebs037-unsafe",
        actions=(ConstructionFileAction(sequence=1, relative_path="linked/file.txt", content="unsafe\n"),),
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (unsafe.workspace_root / "linked").symlink_to(outside, target_is_directory=True)
    unsafe_before = _tree_state(unsafe.workspace_root)
    unsafe_receipt = unsafe.constructor.construct(authorization=unsafe.authorization, handle=unsafe.handoff.handle)
    assert unsafe_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert unsafe_receipt.first_failure is ConstructionFindingCode.PATH_UNSAFE
    assert _tree_state(unsafe.workspace_root) == unsafe_before
    assert _tree_state(outside) == ()
    with pytest.raises(ConstructionEvidenceError):
        ConstructionFileAction(sequence=1, relative_path="../escape.txt", content="forbidden")
    with pytest.raises(ConstructionEvidenceError):
        ConstructionFileAction(sequence=1, relative_path="digest.txt", content="content\n", content_digest="0" * 64)
    with pytest.raises(ConstructionEvidenceError):
        ConstructionFileAction(sequence=1, relative_path="bytes.txt", content="content\n", byte_count=1)

    count_limited = file_construction_fixture(
        tmp_path / "count-limited",
        identity="ebs037-count-limited",
        actions=tuple(
            ConstructionFileAction(sequence=index, relative_path=f"file-{index}.txt", content="x\n")
            for index in range(1, 6)
        ),
    )
    count_before = _tree_state(count_limited.workspace_root)
    count_receipt = count_limited.constructor.construct(
        authorization=count_limited.authorization,
        handle=count_limited.handoff.handle,
    )
    assert count_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert count_receipt.first_failure is ConstructionFindingCode.PLAN_BINDING_MISMATCH
    assert _tree_state(count_limited.workspace_root) == count_before

    bytes_limited = file_construction_fixture(
        tmp_path / "bytes-limited",
        identity="ebs037-bytes-limited",
        actions=(ConstructionFileAction(sequence=1, relative_path="large.txt", content="z" * 20_000),),
    )
    bytes_before = _tree_state(bytes_limited.workspace_root)
    bytes_receipt = bytes_limited.constructor.construct(
        authorization=bytes_limited.authorization,
        handle=bytes_limited.handoff.handle,
    )
    assert bytes_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert bytes_receipt.first_failure is ConstructionFindingCode.PLAN_BINDING_MISMATCH
    assert _tree_state(bytes_limited.workspace_root) == bytes_before

    precreate_target = "q" * 300
    precreate = file_construction_fixture(
        tmp_path / "precreate-open-failure",
        identity="ebs037-precreate-open-failure",
        actions=(ConstructionFileAction(sequence=1, relative_path=precreate_target, content="unwritten\n"),),
    )
    precreate_before = _tree_state(precreate.workspace_root)
    precreate_authorization_digest = precreate.authorization.authorization_digest
    precreate_plan_digest = precreate.authorization.plan.plan_digest
    precreate_receipt = precreate.constructor.construct(
        authorization=precreate.authorization,
        handle=precreate.handoff.handle,
    )
    assert precreate_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert precreate_receipt.first_failure is ConstructionFindingCode.FILESYSTEM_FAILURE
    assert precreate_receipt.action_receipts == ()
    assert precreate_receipt.disposition is not ConstructionBatchDisposition.PARTIAL_CONSTRUCTION_STOPPED
    assert precreate_target not in tuple(item[0] for item in _tree_state(precreate.workspace_root))
    assert _tree_state(precreate.workspace_root) == precreate_before
    assert precreate.authorization.authorization_digest == precreate_authorization_digest
    assert precreate.authorization.plan.plan_digest == precreate_plan_digest
    assert precreate.handoff.handle.is_closed is True

    postcreate = file_construction_fixture(
        tmp_path / "postcreate-write-failure",
        identity="ebs037-postcreate-write-failure",
        actions=(ConstructionFileAction(sequence=1, relative_path="created-then-write-fails.txt", content="write\n"),),
    )
    postcreate_before = _tree_state(postcreate.workspace_root)
    postcreate_authorization_digest = postcreate.authorization.authorization_digest
    postcreate_plan_digest = postcreate.authorization.plan.plan_digest
    previous_file_size_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
    previous_sigxfsz_handler = signal.getsignal(signal.SIGXFSZ)
    try:
        # A zero real process file-size limit permits exclusive empty-file creation,
        # then makes the real descriptor write fail with EFBIG after the owned target exists.
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, previous_file_size_limit[1]))
        postcreate_receipt = postcreate.constructor.construct(
            authorization=postcreate.authorization,
            handle=postcreate.handoff.handle,
        )
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, previous_file_size_limit)
        signal.signal(signal.SIGXFSZ, previous_sigxfsz_handler)
    assert postcreate_receipt.disposition is ConstructionBatchDisposition.PARTIAL_CONSTRUCTION_STOPPED
    assert postcreate_receipt.first_failure is ConstructionFindingCode.FILESYSTEM_FAILURE
    assert postcreate_receipt.action_receipts == ()
    assert _tree_state(postcreate.workspace_root) == (("created-then-write-fails.txt", "file", b""),)
    assert _tree_state(postcreate.workspace_root) != postcreate_before
    assert postcreate.authorization.authorization_digest == postcreate_authorization_digest
    assert postcreate.authorization.plan.plan_digest == postcreate_plan_digest
    assert postcreate.handoff.handle.is_closed is True

    partial = file_construction_fixture(
        tmp_path / "partial",
        identity="ebs037-partial",
        actions=(
            ConstructionFileAction(sequence=1, relative_path="first.txt", content="first\n"),
            ConstructionFileAction(sequence=2, relative_path="y" * 300, content="second\n"),
            ConstructionFileAction(sequence=3, relative_path="later.txt", content="later\n"),
        ),
    )
    partial_receipt = partial.constructor.construct(authorization=partial.authorization, handle=partial.handoff.handle)
    assert partial_receipt.disposition is ConstructionBatchDisposition.PARTIAL_CONSTRUCTION_STOPPED
    assert partial_receipt.first_failure is ConstructionFindingCode.FILESYSTEM_FAILURE
    assert tuple(item.relative_path for item in partial_receipt.action_receipts) == ("first.txt",)
    assert (partial.workspace_root / "first.txt").read_bytes() == b"first\n"
    assert not (partial.workspace_root / "later.txt").exists()

    assert not hasattr(positive.constructor, "create_workspace")
    assert not hasattr(positive.constructor, "delete")
    assert not hasattr(positive.constructor, "move")
    assert not hasattr(positive.constructor, "copy")
    assert not hasattr(positive.constructor, "chmod")
    assert not hasattr(positive.constructor, "run")
    assert not hasattr(positive.constructor, "retry")
    assert not hasattr(positive.constructor, "rollback")
    assert not hasattr(positive.constructor, "recover")
    assert not hasattr(positive.constructor, "reconcile")
    assert not hasattr(positive.constructor, "publish")
    assert not hasattr(positive.constructor, "deploy")
