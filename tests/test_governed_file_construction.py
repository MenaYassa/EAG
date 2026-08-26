"""Focused G2.4.22 tests for descriptor-bound create-only construction."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from test_support.g2_4_22_file_construction_fixture import file_construction_fixture

from eag.governed_file_construction import (
    BoundedWorkspaceFileConstructor,
    ConstructionActionPlan,
    ConstructionBatchDisposition,
    ConstructionFileAction,
    ConstructionFindingCode,
    ConstructionPlatformCapabilities,
)


def _tree_state(root: Path) -> tuple[tuple[str, str, bytes | None], ...]:
    records: list[tuple[str, str, bytes | None]] = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item.relative_to(root))):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            records.append((relative, "symlink", None))
        elif path.is_dir():
            records.append((relative, "directory", None))
        else:
            records.append((relative, "file", path.read_bytes()))
    return tuple(records)


def test_constructs_exact_declared_files_through_one_live_handle(tmp_path: Path) -> None:
    fixture = file_construction_fixture(tmp_path, identity="positive")

    receipt = fixture.constructor.construct(authorization=fixture.authorization, handle=fixture.handoff.handle)

    assert receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_FILES_CREATED
    assert tuple(item.relative_path for item in receipt.action_receipts) == ("src/main.txt", "README.md")
    assert (fixture.workspace_root / "src/main.txt").read_text() == "hello\n"
    assert (fixture.workspace_root / "README.md").read_text() == "# example\n"
    assert fixture.handoff.handle.is_closed is True


def test_pathname_replacement_after_handoff_changes_only_descriptor_retained_root(tmp_path: Path) -> None:
    fixture = file_construction_fixture(tmp_path, identity="replacement")
    original_path = fixture.workspace_root
    retained_root = tmp_path / "retained-original"
    original_path.rename(retained_root)
    original_path.mkdir()
    replacement_before = _tree_state(original_path)

    receipt = fixture.constructor.construct(authorization=fixture.authorization, handle=fixture.handoff.handle)

    assert receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_FILES_CREATED
    assert _tree_state(original_path) == replacement_before
    assert (retained_root / "src/main.txt").read_text() == "hello\n"
    assert (retained_root / "README.md").read_text() == "# example\n"


def test_closed_consumed_and_mismatched_handles_refuse_before_effect(tmp_path: Path) -> None:
    closed = file_construction_fixture(tmp_path / "closed", identity="closed")
    closed.handoff.handle.close()
    closed_before = _tree_state(closed.workspace_root)
    closed_receipt = closed.constructor.construct(authorization=closed.authorization, handle=closed.handoff.handle)
    assert closed_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert closed_receipt.first_failure is ConstructionFindingCode.HANDLE_REJECTED
    assert _tree_state(closed.workspace_root) == closed_before

    consumed = file_construction_fixture(tmp_path / "consumed", identity="consumed")
    consumed.handoff.handle.consume_for_g2_4_22(binding=consumed.handoff.binding)
    consumed_before = _tree_state(consumed.workspace_root)
    consumed_receipt = consumed.constructor.construct(authorization=consumed.authorization, handle=consumed.handoff.handle)
    assert consumed_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert consumed_receipt.first_failure is ConstructionFindingCode.HANDLE_REJECTED
    assert _tree_state(consumed.workspace_root) == consumed_before

    expected = file_construction_fixture(tmp_path / "expected", identity="expected")
    other = file_construction_fixture(tmp_path / "other", identity="other")
    expected_before = _tree_state(expected.workspace_root)
    mismatch_receipt = expected.constructor.construct(authorization=expected.authorization, handle=other.handoff.handle)
    assert mismatch_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert mismatch_receipt.first_failure is ConstructionFindingCode.HANDLE_REJECTED
    assert _tree_state(expected.workspace_root) == expected_before
    expected.handoff.handle.close()


def test_plan_and_capability_refusals_preserve_test_owned_state(tmp_path: Path) -> None:
    fixture = file_construction_fixture(tmp_path / "plan", identity="plan")
    before = _tree_state(fixture.workspace_root)
    other_plan = ConstructionActionPlan(
        actions=(ConstructionFileAction(sequence=1, relative_path="other.txt", content="other\n"),)
    )
    plan_receipt = fixture.constructor.construct(
        authorization=replace(fixture.authorization, plan=other_plan, authorization_digest=None),
        handle=fixture.handoff.handle,
    )
    assert plan_receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert plan_receipt.first_failure is ConstructionFindingCode.PLAN_BINDING_MISMATCH
    assert _tree_state(fixture.workspace_root) == before

    capability = file_construction_fixture(tmp_path / "capability", identity="capability")
    unsupported = ConstructionPlatformCapabilities(
        live_root_handle_consumption=True,
        descriptor_relative_open=False,
        no_follow=True,
        exclusive_create=True,
        regular_file_verification=True,
        link_count_verification=True,
    )
    capability_before = _tree_state(capability.workspace_root)
    receipt = BoundedWorkspaceFileConstructor(platform_capabilities=unsupported).construct(
        authorization=capability.authorization,
        handle=capability.handoff.handle,
    )
    assert receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert receipt.first_failure is ConstructionFindingCode.CONSTRUCTION_CAPABILITY_UNSUPPORTED
    assert _tree_state(capability.workspace_root) == capability_before


def test_stops_after_first_real_effect_without_retry_or_rollback(tmp_path: Path) -> None:
    fixture = file_construction_fixture(
        tmp_path,
        identity="partial",
        actions=(
            ConstructionFileAction(sequence=1, relative_path="first.txt", content="first\n"),
            ConstructionFileAction(sequence=2, relative_path="x" * 300, content="second\n"),
            ConstructionFileAction(sequence=3, relative_path="later.txt", content="later\n"),
        ),
    )

    receipt = fixture.constructor.construct(authorization=fixture.authorization, handle=fixture.handoff.handle)

    assert receipt.disposition is ConstructionBatchDisposition.PARTIAL_CONSTRUCTION_STOPPED
    assert receipt.first_failure is ConstructionFindingCode.FILESYSTEM_FAILURE
    assert tuple(item.relative_path for item in receipt.action_receipts) == ("first.txt",)
    assert (fixture.workspace_root / "first.txt").read_text() == "first\n"
    assert not (fixture.workspace_root / "later.txt").exists()


def test_definitive_precreate_open_failure_is_refused_without_partial_claim(tmp_path: Path) -> None:
    target_name = "z" * 300
    fixture = file_construction_fixture(
        tmp_path,
        identity="precreate-open-failure",
        actions=(ConstructionFileAction(sequence=1, relative_path=target_name, content="unwritten\n"),),
    )
    before = _tree_state(fixture.workspace_root)
    authorization_digest = fixture.authorization.authorization_digest
    plan_digest = fixture.authorization.plan.plan_digest

    receipt = fixture.constructor.construct(authorization=fixture.authorization, handle=fixture.handoff.handle)

    assert receipt.disposition is ConstructionBatchDisposition.CONSTRUCTION_REFUSED
    assert receipt.first_failure is ConstructionFindingCode.FILESYSTEM_FAILURE
    assert receipt.action_receipts == ()
    assert receipt.disposition is not ConstructionBatchDisposition.PARTIAL_CONSTRUCTION_STOPPED
    assert target_name not in tuple(item[0] for item in _tree_state(fixture.workspace_root))
    assert _tree_state(fixture.workspace_root) == before
    assert fixture.authorization.authorization_digest == authorization_digest
    assert fixture.authorization.plan.plan_digest == plan_digest
    assert fixture.handoff.handle.is_closed is True
