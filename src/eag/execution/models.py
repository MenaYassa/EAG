"""Data models for command execution."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandRequest:
    """Request to execute a command."""

    executable: str
    arguments: tuple[str, ...] = ()
    working_directory: Path | None = None
    timeout_seconds: float = 60.0
    environment: dict[str, str] = field(default_factory=dict)
    max_output_bytes: int = 1_000_000

    def __post_init__(self) -> None:
        """Validate request parameters."""
        if not self.executable:
            raise ValueError("Executable cannot be empty")
        # Timeout and output limit validation is delegated to policy

    @property
    def argv(self) -> tuple[str, ...]:
        """Return full argument vector."""
        return (self.executable,) + self.arguments


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandResult:
    """Result of a command execution."""

    request: CommandRequest
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    stdout_truncated: bool
    stderr_truncated: bool

    @property
    def succeeded(self) -> bool:
        """Return True if the command succeeded (exit code 0 and not timed out)."""
        return self.exit_code == 0 and not self.timed_out

    @property
    def failed(self) -> bool:
        """Return True if the command failed (non-zero exit code or timed out)."""
        return not self.succeeded


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyDecision:
    """Result of evaluating a command request against policy."""

    classification: str
    outcome: str
    rule: str
    reason: str
