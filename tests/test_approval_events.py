"""Tests for approval lifecycle events."""

from datetime import UTC, datetime, timedelta

import pytest

from eag.approval import (
    ApprovalApproved,
    ApprovalConsumed,
    ApprovalExpired,
    ApprovalExpiredError,
    ApprovalManager,
    ApprovalRejected,
    ApprovalRequested,
    InMemoryApprovalStore,
)
from eag.events import Event, EventBus
from eag.execution.classification import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.models import CommandRequest


def make_command() -> CommandRequest:
    """Create a command request for approval tests."""
    return CommandRequest(
        executable="git",
        arguments=(
            "commit",
            "-m",
            "approval event test",
        ),
    )


def make_manager(
    event_bus: EventBus,
) -> ApprovalManager:
    """Create an event-enabled approval manager."""
    return ApprovalManager(
        store=InMemoryApprovalStore(),
        event_bus=event_bus,
    )


def create_pending(
    manager: ApprovalManager,
    *,
    command: CommandRequest | None = None,
    now: datetime | None = None,
    expires_at: datetime | None = None,
):
    """Create a pending approval request."""
    return manager.create(
        command=command or make_command(),
        classification=CommandClassification.MUTATING,
        policy_outcome=PolicyOutcome.REQUIRE_APPROVAL,
        policy_reason=("Creating commits requires explicit approval."),
        matched_rule="git.commit",
        now=now,
        expires_at=expires_at,
    )


def test_create_publishes_requested_event() -> None:
    """Test request creation publishes ApprovalRequested."""
    event_bus = EventBus()
    manager = make_manager(event_bus)
    received = []

    event_bus.subscribe(
        ApprovalRequested,
        received.append,
    )

    request = create_pending(manager)

    assert len(received) == 1
    assert isinstance(received[0], ApprovalRequested)
    assert received[0].request is request


def test_approve_publishes_approved_event() -> None:
    """Test approval publishes ApprovalApproved."""
    event_bus = EventBus()
    manager = make_manager(event_bus)
    received = []

    request = create_pending(manager)

    event_bus.subscribe(
        ApprovalApproved,
        received.append,
    )

    approved = manager.approve(request.id)

    assert len(received) == 1
    assert isinstance(received[0], ApprovalApproved)
    assert received[0].request is approved


def test_reject_publishes_rejected_event() -> None:
    """Test rejection publishes ApprovalRejected."""
    event_bus = EventBus()
    manager = make_manager(event_bus)
    received = []

    request = create_pending(manager)

    event_bus.subscribe(
        ApprovalRejected,
        received.append,
    )

    rejected = manager.reject(request.id)

    assert len(received) == 1
    assert isinstance(received[0], ApprovalRejected)
    assert received[0].request is rejected


def test_consume_publishes_consumed_event() -> None:
    """Test consumption publishes ApprovalConsumed."""
    event_bus = EventBus()
    manager = make_manager(event_bus)
    received = []

    command = make_command()
    request = create_pending(
        manager,
        command=command,
    )

    manager.approve(request.id)
    manager.reserve(request.id, command=command)
    event_bus.subscribe(
        ApprovalConsumed,
        received.append,
    )

    consumed = manager.consume(
        request.id,
        command=command,
    )

    assert len(received) == 1
    assert isinstance(received[0], ApprovalConsumed)
    assert received[0].request is consumed


def test_explicit_expiry_publishes_expired_event() -> None:
    """Test explicit expiry publishes ApprovalExpired."""
    event_bus = EventBus()
    manager = make_manager(event_bus)
    received = []

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

    event_bus.subscribe(
        ApprovalExpired,
        received.append,
    )

    expired = manager.expire(
        request.id,
        now=now + timedelta(minutes=5),
    )

    assert len(received) == 1
    assert isinstance(received[0], ApprovalExpired)
    assert received[0].request is expired


def test_lazy_expiry_publishes_expired_event() -> None:
    """Test lazy expiry publishes ApprovalExpired."""
    event_bus = EventBus()
    manager = make_manager(event_bus)
    received = []

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

    event_bus.subscribe(
        ApprovalExpired,
        received.append,
    )

    with pytest.raises(ApprovalExpiredError):
        manager.approve(
            request.id,
            now=now + timedelta(minutes=6),
        )

    assert len(received) == 1
    assert isinstance(received[0], ApprovalExpired)
    assert received[0].request.status.value == "expired"


def test_manager_without_event_bus_still_works() -> None:
    """Test event publication remains optional."""
    manager = ApprovalManager(store=InMemoryApprovalStore())

    request = create_pending(manager)
    approved = manager.approve(request.id)

    assert approved.id == request.id


def test_full_lifecycle_event_order() -> None:
    """Test lifecycle events are published in order."""
    event_bus = EventBus()
    manager = make_manager(event_bus)
    received = []

    event_bus.subscribe(
        ApprovalRequested,
        received.append,
    )
    event_bus.subscribe(
        ApprovalApproved,
        received.append,
    )
    event_bus.subscribe(
        ApprovalConsumed,
        received.append,
    )

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

    assert [type(event) for event in received] == [
        ApprovalRequested,
        ApprovalApproved,
        ApprovalConsumed,
    ]


@pytest.mark.parametrize(
    "event_type",
    (
        ApprovalRequested,
        ApprovalApproved,
        ApprovalRejected,
        ApprovalExpired,
        ApprovalConsumed,
    ),
)
def test_approval_events_follow_event_contract(
    event_type: type[Event],
) -> None:
    """Test approval events inherit the EAG event contract."""
    assert issubclass(event_type, Event)
