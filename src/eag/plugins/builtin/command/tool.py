"""Command execution tool for EAG."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from eag.core import ComponentMetadata, Tool
from eag.execution import (
    CommandExecutor,
    CommandRequest,
    CommandResult,
)
from eag.registry import Capability

COMMAND_RUN = Capability.parse("command.run")
COMMAND_WHICH = Capability.parse("command.which")


class CommandTool(Tool):
    """Expose safe command execution capabilities."""

    def __init__(
        self,
        executor: CommandExecutor,
    ) -> None:
        self._executor = executor

    @property
    def metadata(self) -> ComponentMetadata:
        """Return command tool metadata."""
        return ComponentMetadata(
            name="command-tool",
            version="0.1.0",
            description="Safe structured command execution",
        )

    @property
    def capabilities(self) -> tuple[Capability, ...]:
        """Return supported command capabilities."""
        return (
            COMMAND_RUN,
            COMMAND_WHICH,
        )

    def execute(
        self,
        capability: Capability,
        arguments: Mapping[str, Any],
    ) -> Any:
        """Execute a command capability."""
        if capability == COMMAND_WHICH:
            executable = str(arguments["executable"])
            return self.which(executable)

        if capability == COMMAND_RUN:
            return self.run(
                executable=str(arguments["executable"]),
                arguments=tuple(
                    str(argument)
                    for argument in arguments.get(
                        "arguments",
                        (),
                    )
                ),
                working_directory=self._optional_path(arguments.get("working_directory")),
                timeout_seconds=float(
                    arguments.get(
                        "timeout_seconds",
                        60.0,
                    )
                ),
                environment={
                    str(key): str(value)
                    for key, value in dict(
                        arguments.get(
                            "environment",
                            {},
                        )
                    ).items()
                },
                max_output_bytes=int(
                    arguments.get(
                        "max_output_bytes",
                        1_000_000,
                    )
                ),
            )

        raise ValueError(f"Unsupported capability: '{capability.identifier}'")

    def which(
        self,
        executable: str,
    ) -> Path | None:
        """Resolve an executable."""
        return self._executor.which(executable)

    def run(
        self,
        *,
        executable: str,
        arguments: tuple[str, ...] = (),
        working_directory: Path | None = None,
        timeout_seconds: float = 60.0,
        environment: Mapping[str, str] | None = None,
        max_output_bytes: int = 1_000_000,
    ) -> CommandResult:
        """Run a structured command request."""
        request = CommandRequest(
            executable=executable,
            arguments=arguments,
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
            environment=environment or {},
            max_output_bytes=max_output_bytes,
        )

        return self._executor.execute(request)

    @staticmethod
    def _optional_path(
        value: object,
    ) -> Path | None:
        """Convert an optional value into a path."""
        if value is None:
            return None

        return Path(str(value))
