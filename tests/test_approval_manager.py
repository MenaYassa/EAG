"""Tests for approval lifecycle management."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from eag.approval import (
    ApprovalCommandMismatchError,
    ApprovalExpiredError,
    ApprovalInvalidTransitionError,
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
    InMemoryApprovalStore,
)
from eag.execution.classification import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.models import CommandRequest


def make_manager() -> ApprovalManager:
    """Create an approval manager for tests."""
    return ApprovalManager(store=InMemoryApprovalStore())


def make_command(
    *,
    arguments: tuple[str, ...] = (
        "commit",
        "-m",
        "test",
    ),
) -> CommandRequest:
    """Create a command request for tests."""
    return CommandRequest(
        executable="git",
        arguments=arguments,
    )


def create_pending(
    manager: ApprovalManager,
    *,
    command: CommandRequest | None = None,
    now: datetime | None = None,
    expires_at: datetime | None = None,
) -> ApprovalRequest:
    """Create a pending approval request."""
    return manager.create(
        command=command or make_command(),
        classification=CommandClassification.MUTATING,
        policy_outcome=PolicyOutcome.REQUIRE_APPROVAL,
        policy_reason="Creating commits requires explicit approval.",
        matched_rule="git.commit",
        now=now,
        expires_at=expires_at,
    )


def test_manager_creates_and_persists_request() -> None:
    """Test manager creates a stored pending request."""
    manager = make_manager()

    request = create_pending(manager)

    assert manager.get(request.id) == request
    assert request.status is ApprovalStatus.PENDING


def test_manager_lists_requests() -> None:
    """Test manager exposes stored requests."""
    manager = make_manager()

    first = create_pending(manager)
    second = create_pending(
        manager,
        command=make_command(arguments=("commit", "-m", "second")),
    )

    assert manager.list() == (
        first,
        second,
    )


def test_manager_approves_pending_request() -> None:
    """Test pending request can be approved."""
    manager = make_manager()
    request = create_pending(manager)

    approved = manager.approve(
        request.id,
        reason="Reviewed by operator.",
    )

    assert approved.status is ApprovalStatus.APPROVED
    assert approved.decided_at is not None
    assert approved.decision_reason == "Reviewed by operator."


def test_manager_rejects_pending_request() -> None:
    """Test pending request can be rejected."""
    manager = make_manager()
    request = create_pending(manager)

    rejected = manager.reject(
        request.id,
        reason="Change not authorized.",
    )

    assert rejected.status is ApprovalStatus.REJECTED
    assert rejected.decided_at is not None
    assert rejected.decision_reason == "Change not authorized."


def test_approved_request_can_be_consumed() -> None:
    """Test approved request can authorize exact command."""
    manager = make_manager()
    command = make_command()
    request = create_pending(
        manager,
        command=command,
    )

    manager.approve(request.id)

    # --- NEW: reserve before consume ---
    manager.reserve(
        request.id,
        command=command,
    )

    consumed = manager.consume(
        request.id,
        command=command,
    )

    assert consumed.status is ApprovalStatus.CONSUMED
    assert consumed.consumed_at is not None


def test_pending_request_cannot_be_consumed() -> None:
    """Test pending request cannot authorize execution."""
    manager = make_manager()
    command = make_command()
    request = create_pending(
        manager,
        command=command,
    )

    with pytest.raises(ApprovalInvalidTransitionError):
        manager.consume(
            request.id,
            command=command,
        )


def test_rejected_request_cannot_be_approved() -> None:
    """Test rejected requests cannot change decision."""
    manager = make_manager()
    request = create_pending(manager)

    manager.reject(request.id)

    with pytest.raises(ApprovalInvalidTransitionError):
        manager.approve(request.id)


def test_approved_request_cannot_be_approved_twice() -> None:
    """Test approval decisions cannot be repeated."""
    manager = make_manager()
    request = create_pending(manager)

    manager.approve(request.id)

    with pytest.raises(ApprovalInvalidTransitionError):
        manager.approve(request.id)


def test_consumed_request_cannot_be_replayed() -> None:
    """Test consumed approval is single-use."""
    manager = make_manager()
    command = make_command()
    request = create_pending(
        manager,
        command=command,
    )

    manager.approve(request.id)
    manager.reserve(
        request.id,
        command=command,
    )
    manager.consume(
        request.id,
        command=command,
    )

    # Attempt to consume again should fail
    with pytest.raises(ApprovalInvalidTransitionError):
        manager.consume(
            request.id,
            command=command,
        )


def test_consume_rejects_command_mismatch() -> None:
    """Test approval cannot authorize another command."""
    manager = make_manager()
    original = make_command()
    different = make_command(
        arguments=(
            "commit",
            "-m",
            "different",
        )
    )

    request = create_pending(
        manager,
        command=original,
    )
    manager.approve(request.id)

    # Reserve with original command (should succeed)
    manager.reserve(
        request.id,
        command=original,
    )

    # Consume with different command should fail
    with pytest.raises(ApprovalCommandMismatchError):
        manager.consume(
            request.id,
            command=different,
        )

    # After mismatch, the reservation is released, so status is back to APPROVED
    assert manager.get(request.id).status is ApprovalStatus.APPROVED


def test_expired_pending_request_cannot_be_approved() -> None:
    """Test expired pending request cannot be approved."""
    manager = make_manager()

    now = datetime(
        2026,
        7,
        10,
        12,
        0,
        tzinfo=UTC,
    )

    request = create_pending(
        manager,
        now=now,
        expires_at=now + timedelta(minutes=5),
    )

    with pytest.raises(ApprovalExpiredError):
        manager.approve(
            request.id,
            now=now + timedelta(minutes=6),
        )

    assert manager.get(request.id).status is ApprovalStatus.EXPIRED


def test_expired_approved_request_cannot_be_reserved() -> None:
    """Test approved request cannot be reserved after expiry."""
    manager = make_manager()

    now = datetime(
        2026,
        7,
        10,
        12,
        0,
        tzinfo=UTC,
    )

    command = make_command()

    request = create_pending(
        manager,
        command=command,
        now=now,
        expires_at=now + timedelta(minutes=5),
    )

    manager.approve(
        request.id,
        now=now + timedelta(minutes=1),
    )

    # Reserve after expiry should raise ApprovalExpiredError
    with pytest.raises(ApprovalExpiredError):
        manager.reserve(
            request.id,
            command=command,
            now=now + timedelta(minutes=6),
        )

    assert manager.get(request.id).status is ApprovalStatus.EXPIRED


def test_manager_can_expire_due_request() -> None:
    """Test explicit expiry transition."""
    manager = make_manager()

    now = datetime(
        2026,
        7,
        10,
        12,
        0,
        tzinfo=UTC,
    )

    request = create_pending(
        manager,
        now=now,
        expires_at=now + timedelta(minutes=5),
    )

    expired = manager.expire(
        request.id,
        now=now + timedelta(minutes=5),
    )

    assert expired.status is ApprovalStatus.EXPIRED


def test_manager_cannot_expire_request_early() -> None:
    """Test active request cannot expire before deadline."""
    manager = make_manager()

    now = datetime(
        2026,
        7,
        10,
        12,
        0,
        tzinfo=UTC,
    )

    request = create_pending(
        manager,
        now=now,
        expires_at=now + timedelta(minutes=5),
    )

    with pytest.raises(ApprovalInvalidTransitionError):
        manager.expire(
            request.id,
            now=now + timedelta(minutes=4),
        )


def test_rejected_request_cannot_expire() -> None:
    """Test terminal rejected state cannot transition."""
    manager = make_manager()
    request = create_pending(manager)

    manager.reject(request.id)

    with pytest.raises(ApprovalInvalidTransitionError):
        manager.expire(request.id)


def test_approved_request_can_be_reserved() -> None:
    """Test approved authorization can be reserved."""
    manager = make_manager()
    command = make_command()

    request = create_pending(
        manager,
        command=command,
    )

    manager.approve(request.id)

    reserved = manager.reserve(
        request.id,
        command=command,
    )

    assert reserved.status is ApprovalStatus.RESERVED


def test_reserved_request_can_be_released() -> None:
    """Test reserved authorization can return to approved."""
    manager = make_manager()
    command = make_command()

    request = create_pending(
        manager,
        command=command,
    )

    manager.approve(request.id)

    manager.reserve(
        request.id,
        command=command,
    )

    released = manager.release(request.id)

    assert released.status is ApprovalStatus.APPROVED


def test_reserved_request_can_be_consumed() -> None:
    """Test reserved authorization can be consumed."""
    manager = make_manager()
    command = make_command()

    request = create_pending(
        manager,
        command=command,
    )

    manager.approve(request.id)

    manager.reserve(
        request.id,
        command=command,
    )

    consumed = manager.consume(
        request.id,
        command=command,
    )

    assert consumed.status is ApprovalStatus.CONSUMED


def test_approved_request_cannot_be_consumed_without_reservation() -> None:
    """Test approval must be reserved before consumption."""
    manager = make_manager()
    command = make_command()

    request = create_pending(
        manager,
        command=command,
    )

    manager.approve(request.id)

    with pytest.raises(ApprovalInvalidTransitionError):
        manager.consume(
            request.id,
            command=command,
        )


def test_only_one_concurrent_reservation_succeeds() -> None:
    """Test approved authorization can be reserved only once."""
    manager = make_manager()
    command = make_command()

    request = create_pending(
        manager,
        command=command,
    )

    manager.approve(request.id)

    def attempt_reservation() -> bool:
        try:
            manager.reserve(
                request.id,
                command=command,
            )
        except ApprovalInvalidTransitionError:
            return False

        return True

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(
            executor.map(
                lambda _: attempt_reservation(),
                range(8),
            )
        )

    assert results.count(True) == 1
    assert results.count(False) == 7
    assert manager.get(request.id).status is ApprovalStatus.RESERVED
