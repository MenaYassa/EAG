"""Tests for the safe command execution subsystem."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

# --- Add imports for event testing ---
from eag.events import EventBus
from eag.execution import (
    CommandExecutor,
    CommandRequest,
    ExecutableNotFoundError,
    ExecutionPolicy,
    InvalidOutputLimitError,
    InvalidTimeoutError,
    WorkingDirectoryOutsideWorkspaceError,
)
from eag.execution.events import (
    CommandExecutionCompleted,
    CommandExecutionRejected,
    CommandExecutionStarted,
    CommandExecutionTimedOut,
)

# -------------------------------------

# [Existing tests remain unchanged...]


def test_command_request_is_immutable() -> None:
    request = CommandRequest(
        executable="python",
    )

    with pytest.raises(FrozenInstanceError):
        request.executable = "other"  # type: ignore[misc]


def test_command_request_argv() -> None:
    request = CommandRequest(
        executable="python",
        arguments=("-c", "print('hello')"),
    )

    assert request.argv == (
        "python",
        "-c",
        "print('hello')",
    )


def test_policy_accepts_workspace(
    tmp_path: Path,
) -> None:
    policy = ExecutionPolicy(workspace=tmp_path)

    request = CommandRequest(
        executable="python",
    )

    policy.validate(request)


def test_policy_accepts_relative_directory(
    tmp_path: Path,
) -> None:
    child = tmp_path / "child"
    child.mkdir()

    policy = ExecutionPolicy(workspace=tmp_path)

    resolved = policy.resolve_working_directory(Path("child"))

    assert resolved == child.resolve()


def test_policy_rejects_workspace_escape(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    policy = ExecutionPolicy(workspace=workspace)

    with pytest.raises(WorkingDirectoryOutsideWorkspaceError):
        policy.resolve_working_directory(outside)


def test_policy_rejects_symlink_escape(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    link = workspace / "escape"
    link.symlink_to(
        outside,
        target_is_directory=True,
    )

    policy = ExecutionPolicy(workspace=workspace)

    with pytest.raises(WorkingDirectoryOutsideWorkspaceError):
        policy.resolve_working_directory(link)


@pytest.mark.parametrize(
    "timeout",
    [0.0, -1.0],
)
def test_policy_rejects_non_positive_timeout(
    tmp_path: Path,
    timeout: float,
) -> None:
    policy = ExecutionPolicy(workspace=tmp_path)

    request = CommandRequest(
        executable="python",
        timeout_seconds=timeout,
    )

    with pytest.raises(InvalidTimeoutError):
        policy.validate(request)


def test_policy_rejects_excessive_timeout(
    tmp_path: Path,
) -> None:
    policy = ExecutionPolicy(
        workspace=tmp_path,
        max_timeout_seconds=10.0,
    )

    request = CommandRequest(
        executable="python",
        timeout_seconds=11.0,
    )

    with pytest.raises(InvalidTimeoutError):
        policy.validate(request)


@pytest.mark.parametrize(
    "limit",
    [0, -1],
)
def test_policy_rejects_invalid_output_limit(
    tmp_path: Path,
    limit: int,
) -> None:
    policy = ExecutionPolicy(workspace=tmp_path)

    request = CommandRequest(
        executable="python",
        max_output_bytes=limit,
    )

    with pytest.raises(InvalidOutputLimitError):
        policy.validate(request)


def test_executor_resolves_executable(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    resolved = executor.which("python")

    assert resolved is not None
    assert resolved.is_absolute()


def test_executor_returns_none_for_missing_executable(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    assert executor.which("eag-definitely-not-a-real-command") is None


def test_executor_runs_successful_command(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    result = executor.execute(
        CommandRequest(
            executable="python",
            arguments=(
                "-c",
                "print('hello from EAG')",
            ),
        )
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == ("hello from EAG")
    assert result.stderr == ""
    assert result.timed_out is False
    assert result.succeeded is True
    assert result.failed is False


def test_executor_captures_nonzero_exit(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    result = executor.execute(
        CommandRequest(
            executable="python",
            arguments=(
                "-c",
                "import sys; sys.exit(3)",
            ),
        )
    )

    assert result.exit_code == 3
    assert result.succeeded is False
    assert result.failed is True
    assert result.timed_out is False


def test_executor_captures_stderr(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    result = executor.execute(
        CommandRequest(
            executable="python",
            arguments=(
                "-c",
                ("import sys; print('problem', file=sys.stderr)"),
            ),
        )
    )

    assert result.exit_code == 0
    assert result.stderr.strip() == "problem"


def test_executor_reports_timeout(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    result = executor.execute(
        CommandRequest(
            executable="python",
            arguments=(
                "-c",
                "import time; time.sleep(2)",
            ),
            timeout_seconds=0.05,
        )
    )

    assert result.timed_out is True
    assert result.exit_code is None
    assert result.succeeded is False


def test_executor_rejects_missing_executable(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    request = CommandRequest(executable=("eag-definitely-not-a-real-command"))

    with pytest.raises(ExecutableNotFoundError):
        executor.execute(request)


def test_executor_uses_working_directory(
    tmp_path: Path,
) -> None:
    child = tmp_path / "child"
    child.mkdir()

    executor = CommandExecutor(workspace=tmp_path)

    result = executor.execute(
        CommandRequest(
            executable="python",
            arguments=(
                "-c",
                ("from pathlib import Path; print(Path.cwd())"),
            ),
            working_directory=Path("child"),
        )
    )

    assert Path(result.stdout.strip()).resolve() == child.resolve()


def test_executor_passes_environment_values(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    result = executor.execute(
        CommandRequest(
            executable="python",
            arguments=(
                "-c",
                ("import os; print(os.environ['EAG_TEST_VALUE'])"),
            ),
            environment={"EAG_TEST_VALUE": "working"},
        )
    )

    assert result.stdout.strip() == "working"


def test_executor_truncates_stdout(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    result = executor.execute(
        CommandRequest(
            executable="python",
            arguments=(
                "-c",
                "print('x' * 1000)",
            ),
            max_output_bytes=100,
        )
    )

    assert result.stdout_truncated is True
    assert len(result.stdout.encode("utf-8")) <= 100


def test_executor_preserves_arguments_without_shell(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    result = executor.execute(
        CommandRequest(
            executable="python",
            arguments=(
                "-c",
                ("import sys; print(sys.argv[1])"),
                "hello && echo dangerous",
            ),
        )
    )

    assert result.stdout.strip() == ("hello && echo dangerous")


# ====================================================================
# New event‑publication tests
# ====================================================================


@pytest.fixture
def event_bus() -> EventBus:
    """Create an isolated event bus for testing."""
    return EventBus()


@pytest.fixture
def executor_with_events(tmp_path: Path, event_bus: EventBus) -> CommandExecutor:
    """Return a CommandExecutor configured with an event bus."""
    return CommandExecutor(workspace=tmp_path, event_bus=event_bus)


def test_successful_execution_publishes_started_and_completed(
    executor_with_events: CommandExecutor,
    event_bus: EventBus,
) -> None:
    received = []

    def handler(event):
        received.append(event)

    event_bus.subscribe(CommandExecutionStarted, handler)
    event_bus.subscribe(CommandExecutionCompleted, handler)

    request = CommandRequest(
        executable="python",
        arguments=("-c", "print('event test')"),
    )
    result = executor_with_events.execute(request)

    assert len(received) == 2
    assert isinstance(received[0], CommandExecutionStarted)
    assert received[0].request is request
    assert isinstance(received[1], CommandExecutionCompleted)
    assert received[1].result is result


def test_timeout_publishes_started_and_timed_out(
    executor_with_events: CommandExecutor,
    event_bus: EventBus,
) -> None:
    received = []

    def handler(event):
        received.append(event)

    event_bus.subscribe(CommandExecutionStarted, handler)
    event_bus.subscribe(CommandExecutionTimedOut, handler)

    request = CommandRequest(
        executable="python",
        arguments=("-c", "import time; time.sleep(2)"),
        timeout_seconds=0.05,
    )
    result = executor_with_events.execute(request)

    assert len(received) == 2
    assert isinstance(received[0], CommandExecutionStarted)
    assert isinstance(received[1], CommandExecutionTimedOut)
    assert received[1].result is result
    assert result.timed_out is True


def test_policy_rejection_publishes_rejected(
    tmp_path: Path,
    event_bus: EventBus,
) -> None:
    # Create a workspace and an executor with a strict policy (default)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executor = CommandExecutor(workspace=workspace, event_bus=event_bus)

    received = []

    def handler(event):
        received.append(event)

    event_bus.subscribe(CommandExecutionRejected, handler)

    # Request with working directory outside workspace
    outside = tmp_path / "outside"
    outside.mkdir()
    request = CommandRequest(
        executable="python",
        arguments=("-c", "print('should reject')"),
        working_directory=outside,
    )

    with pytest.raises(WorkingDirectoryOutsideWorkspaceError):
        executor.execute(request)

    assert len(received) == 1
    assert isinstance(received[0], CommandExecutionRejected)
    assert received[0].request is request
    # Optionally check error fields
    assert "outside" in received[0].error_message


def test_missing_executable_publishes_rejected(
    tmp_path: Path,
    event_bus: EventBus,
) -> None:
    executor = CommandExecutor(workspace=tmp_path, event_bus=event_bus)

    received = []

    def handler(event):
        received.append(event)

    event_bus.subscribe(CommandExecutionRejected, handler)

    request = CommandRequest(
        executable="this-command-does-not-exist-xyz",
        arguments=(),
    )

    with pytest.raises(ExecutableNotFoundError):
        executor.execute(request)

    assert len(received) == 1
    assert isinstance(received[0], CommandExecutionRejected)
    assert received[0].request is request
    assert "not found" in received[0].error_message.lower()
