"""Tests for policy-to-approval coordination."""

from pathlib import Path

import pytest

from eag.approval import (
    ApprovalCoordinator,
    ApprovalManager,
    ApprovalRequested,
    ApprovalStatus,
    InMemoryApprovalStore,
)
from eag.events import EventBus
from eag.execution import ExecutionPolicy
from eag.execution.classification import (
    CommandClassification,
    PolicyDecision,
    PolicyOutcome,
)
from eag.execution.models import CommandRequest


def make_decision(
    *,
    outcome: PolicyOutcome,
    classification: CommandClassification,
    reason: str,
    matched_rule: str,
) -> PolicyDecision:
    """Create a policy decision for coordinator tests."""
    return PolicyDecision(
        request=CommandRequest(
            executable="git",
            arguments=(
                "commit",
                "-m",
                "coordinator test",
            ),
        ),
        classification=classification,
        outcome=outcome,
        reason=reason,
        matched_rule=matched_rule,
    )


def make_coordinator(
    *,
    event_bus: EventBus | None = None,
) -> tuple[
    ApprovalCoordinator,
    ApprovalManager,
]:
    """Create coordinator and manager for tests."""
    manager = ApprovalManager(
        store=InMemoryApprovalStore(),
        event_bus=event_bus,
    )

    coordinator = ApprovalCoordinator(
        manager=manager,
    )

    return coordinator, manager


def test_allow_creates_no_approval() -> None:
    """Test allowed decisions create no approval workflow."""
    coordinator, manager = make_coordinator()

    decision = make_decision(
        outcome=PolicyOutcome.ALLOW,
        classification=CommandClassification.READ_ONLY,
        reason="Read-only command is allowed.",
        matched_rule="git.status",
    )

    result = coordinator.coordinate(decision)

    assert result.decision is decision
    assert result.approval is None
    assert not result.approval_created
    assert manager.list() == ()


def test_deny_creates_no_approval() -> None:
    """Test denied decisions create no approval workflow."""
    coordinator, manager = make_coordinator()

    decision = make_decision(
        outcome=PolicyOutcome.DENY,
        classification=CommandClassification.DESTRUCTIVE,
        reason="Destructive command is denied.",
        matched_rule="system.destructive",
    )

    result = coordinator.coordinate(decision)

    assert result.decision is decision
    assert result.approval is None
    assert not result.approval_created
    assert manager.list() == ()


def test_require_approval_creates_pending_request() -> None:
    """Test approval-required decision creates workflow."""
    coordinator, manager = make_coordinator()

    decision = make_decision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        classification=CommandClassification.MUTATING,
        reason="Creating commits requires explicit approval.",
        matched_rule="git.commit",
    )

    result = coordinator.coordinate(decision)

    assert result.approval is not None
    assert result.approval_created

    approval = result.approval

    assert approval.status is ApprovalStatus.PENDING
    assert manager.get(approval.id) == approval


def test_approval_preserves_policy_decision() -> None:
    """Test approval preserves exact policy decision details."""
    coordinator, _ = make_coordinator()

    decision = make_decision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        classification=CommandClassification.MUTATING,
        reason="Creating commits requires explicit approval.",
        matched_rule="git.commit",
    )

    result = coordinator.coordinate(decision)

    assert result.approval is not None

    approval = result.approval

    assert approval.command == decision.request
    assert approval.command is decision.request
    assert approval.classification is decision.classification
    assert approval.policy_outcome is decision.outcome
    assert approval.policy_reason == decision.reason
    assert approval.matched_rule == decision.matched_rule


def test_require_approval_publishes_requested_event() -> None:
    """Test coordination publishes one approval request event."""
    event_bus = EventBus()
    coordinator, _ = make_coordinator(
        event_bus=event_bus,
    )

    received: list[ApprovalRequested] = []

    event_bus.subscribe(
        ApprovalRequested,
        received.append,
    )

    decision = make_decision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        classification=CommandClassification.MUTATING,
        reason="Creating commits requires explicit approval.",
        matched_rule="git.commit",
    )

    result = coordinator.coordinate(decision)

    assert result.approval is not None
    assert len(received) == 1
    assert received[0].request is result.approval


def test_allow_publishes_no_approval_event() -> None:
    """Test allowed decisions emit no approval event."""
    event_bus = EventBus()
    coordinator, _ = make_coordinator(
        event_bus=event_bus,
    )

    received: list[ApprovalRequested] = []

    event_bus.subscribe(
        ApprovalRequested,
        received.append,
    )

    decision = make_decision(
        outcome=PolicyOutcome.ALLOW,
        classification=CommandClassification.VALIDATION,
        reason="Validation command is allowed.",
        matched_rule="python.pytest",
    )

    coordinator.coordinate(decision)

    assert received == []


def test_deny_publishes_no_approval_event() -> None:
    """Test denied decisions emit no approval event."""
    event_bus = EventBus()
    coordinator, _ = make_coordinator(
        event_bus=event_bus,
    )

    received: list[ApprovalRequested] = []

    event_bus.subscribe(
        ApprovalRequested,
        received.append,
    )

    decision = make_decision(
        outcome=PolicyOutcome.DENY,
        classification=CommandClassification.DESTRUCTIVE,
        reason="Destructive command is denied.",
        matched_rule="system.destructive",
    )

    coordinator.coordinate(decision)

    assert received == []


def test_each_coordination_creates_distinct_approval() -> None:
    """Test separate coordination calls create separate workflows."""
    coordinator, manager = make_coordinator()

    decision = make_decision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        classification=CommandClassification.MUTATING,
        reason="Creating commits requires explicit approval.",
        matched_rule="git.commit",
    )

    first = coordinator.coordinate(decision)
    second = coordinator.coordinate(decision)

    assert first.approval is not None
    assert second.approval is not None

    assert first.approval.id != second.approval.id
    assert len(manager.list()) == 2


def test_real_policy_decision_creates_approval(
    tmp_path: Path,
) -> None:
    """Test real policy evaluation bridges into approval."""
    policy = ExecutionPolicy(
        workspace=tmp_path,
    )

    command = CommandRequest(
        executable="git",
        arguments=(
            "commit",
            "-m",
            "real policy bridge",
        ),
    )

    decision = policy.evaluate(command)

    coordinator, manager = make_coordinator()

    result = coordinator.coordinate(decision)

    assert decision.requires_approval
    assert result.approval is not None
    assert result.approval.command == command
    assert result.approval.policy_reason == decision.reason
    assert result.approval.matched_rule == decision.matched_rule
    assert manager.get(result.approval.id) == result.approval


def test_result_is_immutable() -> None:
    """Test coordination results cannot mutate."""
    coordinator, _ = make_coordinator()

    decision = make_decision(
        outcome=PolicyOutcome.ALLOW,
        classification=CommandClassification.READ_ONLY,
        reason="Read-only command is allowed.",
        matched_rule="git.status",
    )

    result = coordinator.coordinate(decision)

    with pytest.raises(AttributeError):
        result.approval = None
