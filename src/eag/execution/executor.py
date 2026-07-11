"""Command execution engine for EAG."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from eag.events import EventBus
from eag.execution.errors import (
    CommandApprovalRequiredError,
    CommandDeniedError,
    CommandStartError,
    ExecutableNotFoundError,
    ExecutionPolicyError,
)
from eag.execution.events import (
    CommandExecutionCompleted,
    CommandExecutionRejected,
    CommandExecutionStarted,
    CommandExecutionTimedOut,
)
from eag.execution.models import (
    CommandRequest,
    CommandResult,
)
from eag.execution.policy import ExecutionPolicy

if TYPE_CHECKING:
    from eag.approval import ApprovalManager

from eag.execution.classification import PolicyOutcome


class CommandExecutor:
    """Execute structured command requests."""

    def __init__(
        self,
        *,
        workspace: Path,
        policy: ExecutionPolicy | None = None,
        event_bus: EventBus | None = None,
        approval_manager: ApprovalManager | None = None,
    ) -> None:
        self._workspace = workspace.resolve()
        self._policy = policy or ExecutionPolicy(workspace=self._workspace)
        self._event_bus = event_bus
        self._approval_manager = approval_manager

    # ... rest of the methods (keep your existing `execute` and helpers) ...

    def _publish(self, event: object) -> None:
        """Publish an execution event when an event bus is available."""
        if self._event_bus is not None:
            self._event_bus.publish(event)  # type: ignore[arg-type]

    @property
    def workspace(self) -> Path:
        return self._workspace

    @property
    def policy(self) -> ExecutionPolicy:
        return self._policy

    def which(self, executable: str) -> Path | None:
        resolved = shutil.which(executable)
        if resolved is None:
            return None
        return Path(resolved).resolve()

    def execute(
        self,
        request: CommandRequest,
        *,
        approval_id: str | None = None,
    ) -> CommandResult:
        # --- Resolve executable first ---
        executable = self.which(request.executable)
        if executable is None:
            err = ExecutableNotFoundError(f"Executable not found: '{request.executable}'")
            self._publish(
                CommandExecutionRejected(
                    request=request,
                    error_type=type(err).__name__,
                    error_message=str(err),
                )
            )
            raise err

        # --- Evaluate policy ---
        approval_reserved = False  # define before use in exceptions

        try:
            decision = self._policy.evaluate(request)

            if decision.outcome is PolicyOutcome.DENY:
                raise CommandDeniedError(decision)

            # Inside execute(), after evaluating policy:
            if decision.outcome is PolicyOutcome.REQUIRE_APPROVAL:
                if approval_id is None:
                    raise CommandApprovalRequiredError(decision)
                if self._approval_manager is None:
                    raise CommandApprovalRequiredError(decision)

                # Check approval status before reserving
                from eag.approval.models import ApprovalStatus

                approval = self._approval_manager.get(approval_id)
                if approval.status is ApprovalStatus.PENDING:
                    raise CommandApprovalRequiredError(decision)
                if approval.status is ApprovalStatus.REJECTED:
                    raise CommandDeniedError(decision)
                if approval.status is ApprovalStatus.CONSUMED:
                    raise CommandApprovalRequiredError(decision)
                if approval.status is ApprovalStatus.RESERVED:
                    raise CommandApprovalRequiredError(decision)
                # if EXPIRED, reserve will raise, we can let it

                self._approval_manager.reserve(approval_id, command=request)
                approval_reserved = True

        except ExecutionPolicyError as exc:
            self._publish(
                CommandExecutionRejected(
                    request=request,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
            raise

        # --- Prepare execution ---
        working_directory = self._policy.resolve_working_directory(request.working_directory)
        environment = os.environ.copy()
        environment.update(request.environment)

        started_at = time.monotonic()
        self._publish(CommandExecutionStarted(request=request))

        try:
            completed = subprocess.run(
                (str(executable), *request.arguments),
                cwd=working_directory,
                env=environment,
                capture_output=True,
                check=False,
                timeout=request.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started_at
            stdout = self._decode_output(exc.stdout)
            stderr = self._decode_output(exc.stderr)
            stdout, stdout_truncated = self._truncate_output(stdout, request.max_output_bytes)
            stderr, stderr_truncated = self._truncate_output(stderr, request.max_output_bytes)

            # --- Consume approval on timeout ---
            if approval_reserved and approval_id is not None and self._approval_manager is not None:
                self._approval_manager.consume(
                    approval_id,
                    command=request,
                )

            result = CommandResult(
                request=request,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                timed_out=True,
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
            )
            self._publish(CommandExecutionTimedOut(result=result))
            return result

        except OSError as exc:
            # --- Release approval on launch failure ---
            if approval_reserved and approval_id is not None and self._approval_manager is not None:
                self._approval_manager.release(approval_id)

            start_error = CommandStartError(
                f"Failed to start executable '{request.executable}': {exc}"
            )
            self._publish(
                CommandExecutionRejected(
                    request=request,
                    error_type=type(start_error).__name__,
                    error_message=str(start_error),
                )
            )
            raise start_error from exc

        # --- Normal completion: consume approval ---
        if approval_reserved and approval_id is not None and self._approval_manager is not None:
            self._approval_manager.consume(
                approval_id,
                command=request,
            )

        duration = time.monotonic() - started_at
        stdout = self._decode_output(completed.stdout)
        stderr = self._decode_output(completed.stderr)
        stdout, stdout_truncated = self._truncate_output(stdout, request.max_output_bytes)
        stderr, stderr_truncated = self._truncate_output(stderr, request.max_output_bytes)

        result = CommandResult(
            request=request,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            timed_out=False,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )
        self._publish(CommandExecutionCompleted(result=result))
        return result

    @staticmethod
    def _decode_output(output: bytes | str | None) -> str:
        if output is None:
            return ""
        if isinstance(output, str):
            return output
        return output.decode("utf-8", errors="replace")

    @staticmethod
    def _truncate_output(output: str, max_bytes: int) -> tuple[str, bool]:
        encoded = output.encode("utf-8")
        if len(encoded) <= max_bytes:
            return output, False
        truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
        return truncated, True
