"""Integration tests for approval‑guarded command execution."""

from pathlib import Path

import pytest
from helpers import approval_required_python_policy

from eag.approval import (
    ApprovalCoordinator,
    ApprovalManager,
    ApprovalStatus,
    InMemoryApprovalStore,
)
from eag.approval.errors import ApprovalCommandMismatchError
from eag.execution import CommandExecutor, CommandRequest, ExecutionPolicy
from eag.execution.classification import (
    CommandClassification,
    CommandClassifier,
    ExecutableRule,
    PolicyOutcome,
)
from eag.execution.errors import (
    CommandApprovalRequiredError,
    CommandDeniedError,
    CommandStartError,
)


@pytest.fixture
def approval_manager() -> ApprovalManager:
    """Create an isolated approval manager."""
    return ApprovalManager(store=InMemoryApprovalStore())


@pytest.fixture
def approval_coordinator(
    approval_manager: ApprovalManager,
) -> ApprovalCoordinator:
    """Create an isolated approval coordinator."""
    return ApprovalCoordinator(manager=approval_manager)


@pytest.fixture
def executor(tmp_path: Path, approval_manager: ApprovalManager) -> CommandExecutor:
    """Create an executor with approval‑required policy."""
    policy = approval_required_python_policy(tmp_path)
    return CommandExecutor(
        workspace=tmp_path,
        policy=policy,
        approval_manager=approval_manager,
    )


def make_command(script: str = "print('hello')") -> CommandRequest:
    """Create a Python command request."""
    return CommandRequest(
        executable="python",
        arguments=("-c", script),
    )


def test_require_approval_without_id_raises(
    executor: CommandExecutor,
) -> None:
    """Test that a command requiring approval fails without approval_id."""
    request = make_command()
    with pytest.raises(CommandApprovalRequiredError):
        executor.execute(request)


def test_pending_approval_cannot_execute(
    executor: CommandExecutor,
    approval_manager: ApprovalManager,
    approval_coordinator: ApprovalCoordinator,
) -> None:
    """Test that a pending (not approved) command cannot execute."""
    request = make_command()
    decision = executor.policy.evaluate(request)  # should be REQUIRE_APPROVAL
    assert decision.outcome is PolicyOutcome.REQUIRE_APPROVAL

    # Create a pending request via coordinator
    coordination = approval_coordinator.coordinate(decision)
    approval_id = coordination.approval.id

    # Try to execute without approving
    with pytest.raises(CommandApprovalRequiredError):
        executor.execute(request, approval_id=approval_id)


def test_rejected_approval_cannot_execute(
    executor: CommandExecutor,
    approval_manager: ApprovalManager,
    approval_coordinator: ApprovalCoordinator,
) -> None:
    """Test that a rejected command cannot execute."""
    request = make_command()
    decision = executor.policy.evaluate(request)
    coordination = approval_coordinator.coordinate(decision)
    approval_id = coordination.approval.id

    # Reject the approval
    approval_manager.reject(approval_id)

    with pytest.raises(CommandDeniedError):
        executor.execute(request, approval_id=approval_id)


def test_approved_exact_command_executes_and_consumes(
    executor: CommandExecutor,
    approval_manager: ApprovalManager,
    approval_coordinator: ApprovalCoordinator,
) -> None:
    """Test that an approved exact command executes and consumes the approval."""
    request = make_command()
    decision = executor.policy.evaluate(request)
    coordination = approval_coordinator.coordinate(decision)
    approval_id = coordination.approval.id

    # Approve the request
    approval_manager.approve(approval_id)

    # Execute with approval_id
    result = executor.execute(request, approval_id=approval_id)

    assert result.succeeded is True
    # The approval should now be consumed
    approved_obj = approval_manager.get(approval_id)
    assert approved_obj.status is ApprovalStatus.CONSUMED


def test_approved_different_command_rejected(
    executor: CommandExecutor,
    approval_manager: ApprovalManager,
    approval_coordinator: ApprovalCoordinator,
) -> None:
    """Test that an approval for one command cannot be used for a different one."""
    request1 = make_command("print('original')")
    request2 = make_command("print('different')")

    decision = executor.policy.evaluate(request1)
    coordination = approval_coordinator.coordinate(decision)
    approval_id = coordination.approval.id

    approval_manager.approve(approval_id)

    # Try to execute a different command with the same approval_id
    with pytest.raises(ApprovalCommandMismatchError):
        executor.execute(request2, approval_id=approval_id)


def test_consumed_approval_cannot_replay(
    executor: CommandExecutor,
    approval_manager: ApprovalManager,
    approval_coordinator: ApprovalCoordinator,
) -> None:
    """Test that a consumed approval cannot be reused."""
    request = make_command()
    decision = executor.policy.evaluate(request)
    coordination = approval_coordinator.coordinate(decision)
    approval_id = coordination.approval.id

    approval_manager.approve(approval_id)

    # First execution consumes
    result1 = executor.execute(request, approval_id=approval_id)
    assert result1.succeeded

    # Second execution should fail (approval already consumed)
    with pytest.raises(CommandApprovalRequiredError):
        executor.execute(request, approval_id=approval_id)


def test_timeout_consumes_approval(
    executor: CommandExecutor,
    approval_manager: ApprovalManager,
    approval_coordinator: ApprovalCoordinator,
) -> None:
    """Test that a timeout consumes the approval."""
    request = CommandRequest(
        executable="python",
        arguments=("-c", "import time; time.sleep(2)"),
        timeout_seconds=0.05,
    )
    decision = executor.policy.evaluate(request)
    coordination = approval_coordinator.coordinate(decision)
    approval_id = coordination.approval.id

    approval_manager.approve(approval_id)

    # Execute with approval; it will timeout
    result = executor.execute(request, approval_id=approval_id)

    assert result.timed_out is True
    # Approval should be consumed
    assert approval_manager.get(approval_id).status is ApprovalStatus.CONSUMED


def test_oserror_releases_approval_back_to_approved(
    executor: CommandExecutor,
    approval_manager: ApprovalManager,
    approval_coordinator: ApprovalCoordinator,
    tmp_path: Path,
) -> None:
    """Test that an OSError (launch failure) releases the approval back to APPROVED."""
    # Create a dummy executable that fails to run (invalid binary)
    dummy = tmp_path / "dummy_binary"
    dummy.write_bytes(b"invalid binary content")
    dummy.chmod(0o755)

    # Create a policy that requires approval for this executable
    classifier = CommandClassifier(
        rules=(
            ExecutableRule(
                rule_name="test.dummy",
                executables=frozenset({str(dummy)}),
                classification=CommandClassification.MUTATING,
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                reason="Dummy requires approval.",
            ),
        )
    )
    policy = ExecutionPolicy(workspace=tmp_path, classifier=classifier)
    executor_oserror = CommandExecutor(
        workspace=tmp_path,
        policy=policy,
        approval_manager=approval_manager,
    )

    request = CommandRequest(executable=str(dummy))
    decision = executor_oserror.policy.evaluate(request)
    coordination = approval_coordinator.coordinate(decision)
    approval_id = coordination.approval.id

    approval_manager.approve(approval_id)

    # Execute will raise CommandStartError because dummy is not a valid executable
    with pytest.raises(CommandStartError):
        executor_oserror.execute(request, approval_id=approval_id)

    # After failure, approval should be released back to APPROVED
    assert approval_manager.get(approval_id).status is ApprovalStatus.APPROVED


def test_allowed_command_executes_without_approval(
    tmp_path: Path,
    approval_manager: ApprovalManager,
) -> None:
    """Test that commands classified as ALLOW run without approval."""
    # Use a permissive policy for a different command, e.g., "ls" if available
    # We'll use a simple allow policy for "echo"
    from helpers import allowing_policy

    policy = allowing_policy(tmp_path, "echo")
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=policy,
        approval_manager=approval_manager,
    )
    request = CommandRequest(
        executable="echo",
        arguments=("hello",),
    )
    result = executor.execute(request)
    assert result.succeeded
    assert result.stdout.strip() == "hello"
