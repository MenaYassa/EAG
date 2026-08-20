"""Deterministic G2.3.1 tests for the governed workspace mutation boundary."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from eag.events import EventBus
from eag.mutation import (
    ChangeProposal,
    GovernedMutationRuntime,
    MutationAuthorization,
    MutationAuthorizationState,
    MutationAuthorizer,
    MutationCompleted,
    MutationFailed,
    MutationOperation,
    MutationPolicySettings,
    MutationPolicyValidator,
    MutationPostcondition,
    MutationPrecondition,
    MutationProposed,
    MutationRejected,
    MutationResult,
    MutationStarted,
    MutationViolationCode,
)


def _runtime(root: Path, bus: EventBus | None = None) -> GovernedMutationRuntime:
    policy = MutationPolicyValidator(
        settings=MutationPolicySettings(max_content_bytes=128, max_target_bytes=128)
    )
    return GovernedMutationRuntime(
        workspace_root=root,
        policy=policy,
        authorizer=MutationAuthorizer(policy_version=policy.policy_version),
        event_bus=bus or EventBus(),
    )


def _proposal(
    *,
    path: str,
    operation: MutationOperation,
    content: str,
    precondition: MutationPrecondition,
    expected_fingerprint: str | None = None,
) -> ChangeProposal:
    return ChangeProposal(
        run_id="run-1",
        decision_id="decision-1",
        target_path=path,
        operation=operation,
        content=content,
        precondition=precondition,
        reason="deterministic fixture change",
        provenance_ids=("file:fixture.txt",),
        expected_postcondition=MutationPostcondition(expected_fingerprint=expected_fingerprint),
        context_fingerprint="context-safe",
        repository_snapshot_fingerprint="snapshot-safe",
    )


def _fingerprint(content: str) -> str:
    return _proposal(
        path="unused.txt",
        operation=MutationOperation.CREATE_FILE,
        content=content,
        precondition=MutationPrecondition(expect_exists=False),
    ).content_fingerprint


def test_valid_file_creation_produces_verified_redacted_receipt(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="created.txt",
        operation=MutationOperation.CREATE_FILE,
        content="created content\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.COMPLETED
    assert receipt.verification_passed is True
    assert receipt.pre_fingerprint is None
    assert receipt.post_fingerprint == proposal.content_fingerprint
    assert receipt.bytes_after == len(b"created content\n")
    assert (tmp_path / "created.txt").read_text() == "created content\n"
    assert "created content" not in repr(receipt)


def test_valid_file_modification_requires_matching_fingerprint(tmp_path: Path) -> None:
    target = tmp_path / "existing.txt"
    target.write_text("before\n")
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="existing.txt",
        operation=MutationOperation.MODIFY_FILE,
        content="after\n",
        precondition=MutationPrecondition(expect_exists=True, expected_fingerprint=_fingerprint("before\n")),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.COMPLETED
    assert receipt.pre_fingerprint == _fingerprint("before\n")
    assert receipt.post_fingerprint == _fingerprint("after\n")
    assert target.read_text() == "after\n"


@pytest.mark.parametrize("path", ["../outside.py", "../../etc/passwd", "/absolute/path", "dir/../target.py"])
def test_policy_rejects_absolute_and_traversal_paths_without_mutation(tmp_path: Path, path: str) -> None:
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path=path,
        operation=MutationOperation.CREATE_FILE,
        content="safe\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.REJECTED
    assert receipt.failure_code in {
        MutationViolationCode.ABSOLUTE_PATH.value,
        MutationViolationCode.PATH_TRAVERSAL.value,
    }
    assert list(tmp_path.iterdir()) == []


def test_policy_rejects_symlink_parent_escape_without_mutation(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    link.symlink_to(outside, target_is_directory=True)
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="link/escape.py",
        operation=MutationOperation.CREATE_FILE,
        content="safe\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.REJECTED
    assert receipt.failure_code == MutationViolationCode.SYMLINK_PATH.value
    assert not (outside / "escape.py").exists()


def test_policy_rejects_nested_symlink_target_without_mutation(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    outside = tmp_path.parent / "outside-target.txt"
    outside.write_text("outside")
    (nested / "target.txt").symlink_to(outside)
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="nested/target.txt",
        operation=MutationOperation.MODIFY_FILE,
        content="attempt\n",
        precondition=MutationPrecondition(expect_exists=True, expected_fingerprint=_fingerprint("outside")),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.REJECTED
    assert receipt.failure_code == MutationViolationCode.SYMLINK_PATH.value
    assert outside.read_text() == "outside"


@pytest.mark.parametrize("path", [".env", "secrets/token.txt", "keys/private.key", ".git/config"])
def test_policy_rejects_sensitive_targets(tmp_path: Path, path: str) -> None:
    if "/" in path:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path=path,
        operation=MutationOperation.CREATE_FILE,
        content="safe\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.REJECTED
    assert receipt.failure_code == MutationViolationCode.SENSITIVE_PATH.value


def test_policy_rejects_sensitive_content_without_retaining_it(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="safe.txt",
        operation=MutationOperation.CREATE_FILE,
        content="api_key=super-secret-value\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.REJECTED
    assert receipt.failure_code == MutationViolationCode.SENSITIVE_CONTENT.value
    assert "super-secret-value" not in repr(receipt)
    assert not (tmp_path / "safe.txt").exists()


def test_policy_rejects_unsupported_operation_and_oversized_content(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    unsupported = _proposal(
        path="safe.txt",
        operation="delete",  # type: ignore[arg-type]
        content="safe\n",
        precondition=MutationPrecondition(expect_exists=False),
    )
    oversized = _proposal(
        path="large.txt",
        operation=MutationOperation.CREATE_FILE,
        content="x" * 129,
        precondition=MutationPrecondition(expect_exists=False),
    )

    unsupported_receipt = runtime.execute(unsupported)
    oversized_receipt = runtime.execute(oversized)

    assert unsupported_receipt.failure_code == MutationViolationCode.UNSUPPORTED_OPERATION.value
    assert oversized_receipt.failure_code == MutationViolationCode.CONTENT_TOO_LARGE.value
    assert list(tmp_path.iterdir()) == []


def test_policy_rejects_stale_modify_precondition_without_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "stale.txt"
    target.write_text("current\n")
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="stale.txt",
        operation=MutationOperation.MODIFY_FILE,
        content="replacement\n",
        precondition=MutationPrecondition(expect_exists=True, expected_fingerprint=_fingerprint("older\n")),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.REJECTED
    assert receipt.failure_code == MutationViolationCode.PRECONDITION_STALE.value
    assert target.read_text() == "current\n"


def test_policy_rejects_create_existing_target_without_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "already.txt"
    target.write_text("original\n")
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="already.txt",
        operation=MutationOperation.CREATE_FILE,
        content="replacement\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    receipt = runtime.execute(proposal)

    assert receipt.failure_code == MutationViolationCode.CREATE_TARGET_EXISTS.value
    assert target.read_text() == "original\n"


def test_authorization_mismatch_prevents_mutation_and_produces_receipt(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="authorized.txt",
        operation=MutationOperation.CREATE_FILE,
        content="content\n",
        precondition=MutationPrecondition(expect_exists=False),
    )
    validated = runtime.validate(proposal)
    authorization = runtime.authorize(validated)
    mismatched = MutationAuthorization(
        proposal_id=authorization.proposal_id,
        proposal_digest="mismatched",
        target_path=authorization.target_path,
        operation=authorization.operation,
        workspace_fingerprint=authorization.workspace_fingerprint,
        repository_snapshot_fingerprint=authorization.repository_snapshot_fingerprint,
        policy_version=authorization.policy_version,
    )

    receipt = runtime.mutate(validated, mismatched)

    assert receipt.result is MutationResult.REJECTED
    assert receipt.failure_code == MutationViolationCode.AUTHORIZATION_MISMATCH.value
    assert not (tmp_path / "authorized.txt").exists()


def test_authorization_is_one_time_and_cannot_be_reused(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="one-time.txt",
        operation=MutationOperation.CREATE_FILE,
        content="content\n",
        precondition=MutationPrecondition(expect_exists=False),
    )
    validated = runtime.validate(proposal)
    authorization = runtime.authorize(validated)

    first = runtime.mutate(validated, authorization)
    second = runtime.mutate(validated, authorization)

    assert first.result is MutationResult.COMPLETED
    assert second.result is MutationResult.REJECTED
    assert second.failure_code in {
        MutationViolationCode.CREATE_TARGET_EXISTS.value,
        MutationViolationCode.AUTHORIZATION_REUSED.value,
    }


def test_postcondition_failure_performs_conditional_rollback_for_create(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="rollback.txt",
        operation=MutationOperation.CREATE_FILE,
        content="content\n",
        precondition=MutationPrecondition(expect_exists=False),
        expected_fingerprint="not-the-content-fingerprint",
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.FAILED
    assert receipt.failure_code == MutationViolationCode.POSTCONDITION_MISMATCH.value
    assert receipt.rollback_performed is True
    assert not (tmp_path / "rollback.txt").exists()


def test_write_failure_produces_failed_receipt_without_shell_or_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="failed.txt",
        operation=MutationOperation.CREATE_FILE,
        content="content\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    def fail_write(_: Path, __: str) -> None:
        raise OSError("simulated")

    monkeypatch.setattr(runtime, "_atomic_write", fail_write)
    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.FAILED
    assert receipt.failure_code == MutationViolationCode.WRITE_FAILED.value
    assert not (tmp_path / "failed.txt").exists()
    assert receipt.authorization_state is MutationAuthorizationState.CONSUMED


def test_event_ordering_and_event_payloads_are_content_free(tmp_path: Path) -> None:
    bus = EventBus()
    events: list[object] = []
    for event_type in (MutationProposed, MutationStarted, MutationCompleted, MutationRejected, MutationFailed):
        bus.subscribe(event_type, events.append)
    runtime = _runtime(tmp_path, bus)
    proposal = _proposal(
        path="events.txt",
        operation=MutationOperation.CREATE_FILE,
        content="unrestricted-provider-body-must-not-appear\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.COMPLETED
    assert [type(event) for event in events] == [MutationProposed, MutationStarted, MutationCompleted]
    assert all("unrestricted-provider-body-must-not-appear" not in repr(event) for event in events)


def test_repeated_safe_operations_are_deterministic_and_workspace_outside_target_unchanged(tmp_path: Path) -> None:
    untouched = tmp_path / "untouched.txt"
    untouched.write_text("unchanged\n")
    runtime = _runtime(tmp_path)
    create = _proposal(
        path="target.txt",
        operation=MutationOperation.CREATE_FILE,
        content="first\n",
        precondition=MutationPrecondition(expect_exists=False),
    )
    first = runtime.execute(create)
    modify = _proposal(
        path="target.txt",
        operation=MutationOperation.MODIFY_FILE,
        content="second\n",
        precondition=MutationPrecondition(expect_exists=True, expected_fingerprint=first.post_fingerprint),
    )

    second = runtime.execute(modify)

    assert first.result is MutationResult.COMPLETED
    assert second.result is MutationResult.COMPLETED
    assert (tmp_path / "target.txt").read_text() == "second\n"
    assert untouched.read_text() == "unchanged\n"
    assert os.listdir(tmp_path) == ["target.txt", "untouched.txt"] or os.listdir(tmp_path) == ["untouched.txt", "target.txt"]


def test_authorized_mutation_invokes_no_shell_git_or_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deterministic first slice must remain local and capability-bounded."""
    import socket
    import subprocess

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("external operation is forbidden in G2.3.1 mutation")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    runtime = _runtime(tmp_path)
    proposal = _proposal(
        path="local-only.txt",
        operation=MutationOperation.CREATE_FILE,
        content="local\n",
        precondition=MutationPrecondition(expect_exists=False),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.COMPLETED
    assert (tmp_path / "local-only.txt").read_text() == "local\n"
