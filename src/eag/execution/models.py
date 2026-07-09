"""Data models for command execution."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType


def _empty_environment() -> Mapping[str, str]:
    """Return an immutable empty environment mapping."""
    return MappingProxyType({})


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class CommandRequest:
    """Describe a command execution request."""

    executable: str
    arguments: tuple[str, ...] = ()
    working_directory: Path | None = None
    timeout_seconds: float = 60.0
    environment: Mapping[str, str] = field(default_factory=_empty_environment)
    max_output_bytes: int = 1_000_000

    @property
    def argv(self) -> tuple[str, ...]:
        """Return the complete argument vector."""
        return (
            self.executable,
            *self.arguments,
        )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class CommandResult:
    """Describe the result of command execution."""

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
        """Return whether the command completed successfully."""
        return not self.timed_out and self.exit_code == 0

    @property
    def failed(self) -> bool:
        """Return whether the command did not succeed."""
        return not self.succeeded
