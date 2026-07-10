"""Execution policy for safe command requests."""

from dataclasses import dataclass
from pathlib import Path

from eag.execution.classification import (
    CommandClassifier,
    PolicyDecision,
    PolicyOutcome,
    builtin_rules,
)
from eag.execution.errors import (
    CommandApprovalRequiredError,
    CommandDeniedError,
    InvalidOutputLimitError,
    InvalidTimeoutError,
    WorkingDirectoryOutsideWorkspaceError,
)
from eag.execution.models import CommandRequest


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class ExecutionPolicy:
    """Validate command requests against workspace boundaries."""

    workspace: Path
    default_timeout_seconds: float = 60.0
    max_timeout_seconds: float = 300.0
    default_max_output_bytes: int = 1_000_000
    max_output_bytes: int = 10_000_000
    classifier: CommandClassifier | None = None

    def __post_init__(self) -> None:
        """Initialize the default classifier."""
        if self.classifier is None:
            object.__setattr__(
                self,
                "classifier",
                CommandClassifier(rules=builtin_rules()),
            )

    def evaluate(
        self,
        request: CommandRequest,
    ) -> PolicyDecision:
        """Classify a structurally valid request."""
        self.validate(request)

        assert self.classifier is not None

        return self.classifier.classify(request)

    def authorize(
        self,
        request: CommandRequest,
    ) -> PolicyDecision:
        """Authorize a request or raise a policy error."""
        decision = self.evaluate(request)

        if decision.outcome is PolicyOutcome.DENY:
            raise CommandDeniedError(decision)

        if decision.outcome is PolicyOutcome.REQUIRE_APPROVAL:
            raise CommandApprovalRequiredError(decision)

        return decision

    def validate(
        self,
        request: CommandRequest,
    ) -> None:
        """Validate an execution request."""
        self._validate_timeout(request.timeout_seconds)
        self._validate_output_limit(request.max_output_bytes)
        self.resolve_working_directory(request.working_directory)

    def resolve_working_directory(
        self,
        working_directory: Path | None,
    ) -> Path:
        """Resolve and validate a working directory."""
        workspace = self.workspace.resolve()

        if working_directory is None:
            candidate = workspace
        elif working_directory.is_absolute():
            candidate = working_directory.resolve()
        else:
            candidate = (workspace / working_directory).resolve()

        if not candidate.is_dir():
            raise WorkingDirectoryOutsideWorkspaceError(
                f"Working directory does not exist or is not a directory: '{candidate}'"
            )

        if not candidate.is_relative_to(workspace):
            raise WorkingDirectoryOutsideWorkspaceError(
                f"Working directory escapes workspace: '{candidate}'"
            )

        return candidate

    def _validate_timeout(
        self,
        timeout_seconds: float,
    ) -> None:
        """Validate command timeout."""
        if timeout_seconds <= 0:
            raise InvalidTimeoutError("Command timeout must be greater than zero")

        if timeout_seconds > self.max_timeout_seconds:
            raise InvalidTimeoutError(
                f"Command timeout exceeds maximum of {self.max_timeout_seconds} seconds"
            )

    def _validate_output_limit(
        self,
        max_output_bytes: int,
    ) -> None:
        """Validate command output limit."""
        if max_output_bytes < 1:
            raise InvalidOutputLimitError("Command output limit must be at least 1 byte")

        if max_output_bytes > self.max_output_bytes:
            raise InvalidOutputLimitError(
                f"Command output limit exceeds maximum of {self.max_output_bytes} bytes"
            )
