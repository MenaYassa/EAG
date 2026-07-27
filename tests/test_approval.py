"""Tests for the approval domain and store."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from eag.approval import (
    ApprovalAlreadyExistsError,
    ApprovalNotFoundError,
    ApprovalRequest,
    ApprovalStatus,
    InMemoryApprovalStore,
    new_approval_request,
)
from eag.execution.classification import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.models import CommandRequest


def make_approval(
    *,
    executable: str = "git",
    arguments: tuple[str, ...] = (
        "commit",
        "-m",
        "test",
    ),
    now: datetime | None = None,
    expires_at: datetime | None = None,
) -> ApprovalRequest:
    """Create an approval request for tests."""
    return new_approval_request(
        command=CommandRequest(
            executable=executable,
            arguments=arguments,
            working_directory=Path("."),
        ),
        classification=(CommandClassification.MUTATING),
        policy_outcome=(PolicyOutcome.REQUIRE_APPROVAL),
        policy_reason=("Creating commits requires explicit approval."),
        matched_rule="git.commit",
        now=now,
        expires_at=expires_at,
    )


def test_new_approval_is_pending() -> None:
    """Test new approvals start pending."""
    request = make_approval()

    assert request.status is ApprovalStatus.PENDING
    assert request.is_pending
    assert not request.is_terminal
    assert request.decided_at is None
    assert request.consumed_at is None


def test_new_approval_has_unique_id() -> None:
    """Test approval requests receive unique IDs."""
    first = make_approval()
    second = make_approval()

    assert first.id != second.id


def test_approval_preserves_command_snapshot() -> None:
    """Test approval stores the exact command request."""
    request = make_approval(
        arguments=(
            "commit",
            "-m",
            "feat: add approval system",
        )
    )

    assert request.command.executable == "git"
    assert request.command.arguments == (
        "commit",
        "-m",
        "feat: add approval system",
    )


def test_approval_requires_approval_outcome() -> None:
    """Test safe commands cannot create approval requests."""
    with pytest.raises(
        ValueError,
        match="require_approval",
    ):
        new_approval_request(
            command=CommandRequest(
                executable="git",
                arguments=("status",),
            ),
            classification=(CommandClassification.READ_ONLY),
            policy_outcome=PolicyOutcome.ALLOW,
            policy_reason="Git status is read-only.",
            matched_rule="git.status",
        )


def test_approval_rejects_past_expiry() -> None:
    """Test approval expiry must follow creation."""
    now = datetime(
        2026,
        7,
        10,
        12,
        0,
        tzinfo=UTC,
    )

    with pytest.raises(
        ValueError,
        match="later than creation",
    ):
        make_approval(
            now=now,
            expires_at=now - timedelta(seconds=1),
        )


def test_approval_expiry_detection() -> None:
    """Test expiry is evaluated against a supplied time."""
    now = datetime(
        2026,
        7,
        10,
        12,
        0,
        tzinfo=UTC,
    )

    request = make_approval(
        now=now,
        expires_at=now + timedelta(minutes=10),
    )

    assert not request.is_expired(now=now + timedelta(minutes=5))
    assert request.is_expired(now=now + timedelta(minutes=10))


def test_approval_without_expiry_never_expires() -> None:
    """Test approvals without expiry remain unexpired."""
    request = make_approval()

    assert not request.is_expired(now=datetime.now(UTC) + timedelta(days=365))


def test_store_add_and_get() -> None:
    """Test storing and retrieving an approval."""
    store = InMemoryApprovalStore()
    request = make_approval()

    store.add(request)

    assert store.get(request.id) == request


def test_store_rejects_duplicate_id() -> None:
    """Test duplicate approval IDs are rejected."""
    store = InMemoryApprovalStore()
    request = make_approval()

    store.add(request)

    with pytest.raises(ApprovalAlreadyExistsError):
        store.add(request)


def test_store_get_missing_request() -> None:
    """Test missing approval lookup fails clearly."""
    store = InMemoryApprovalStore()

    with pytest.raises(ApprovalNotFoundError):
        store.get("missing")


def test_store_save_existing_request() -> None:
    """Test replacing an existing approval state."""
    store = InMemoryApprovalStore()
    request = make_approval()
    store.add(request)

    approved = replace(
        request,
        status=ApprovalStatus.APPROVED,
        decided_at=datetime.now(UTC),
    )

    store.save(approved)

    assert store.get(request.id).status is ApprovalStatus.APPROVED


def test_store_save_missing_request() -> None:
    """Test saving an unknown approval fails."""
    store = InMemoryApprovalStore()
    request = make_approval()

    with pytest.raises(ApprovalNotFoundError):
        store.save(request)


def test_store_lists_all_requests() -> None:
    """Test listing all approval requests."""
    store = InMemoryApprovalStore()
    first = make_approval()
    second = make_approval(
        executable="docker",
        arguments=("compose", "down"),
    )

    store.add(first)
    store.add(second)

    assert store.list() == (
        first,
        second,
    )


def test_store_filters_by_status() -> None:
    """Test approval listing by lifecycle status."""
    store = InMemoryApprovalStore()

    pending = make_approval()
    approved = replace(
        make_approval(),
        status=ApprovalStatus.APPROVED,
        decided_at=datetime.now(UTC),
    )

    store.add(pending)
    store.add(approved)

    assert store.list(status=ApprovalStatus.PENDING) == (pending,)

    assert store.list(status=ApprovalStatus.APPROVED) == (approved,)


def test_approval_request_is_immutable() -> None:
    """Test approval requests cannot mutate in place."""
    request = make_approval()

    with pytest.raises(AttributeError):
        request.status = ApprovalStatus.APPROVED
