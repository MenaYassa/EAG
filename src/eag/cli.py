"""Command-line interface for EAG."""

from pathlib import Path

import typer

from eag import __version__
from eag.bootstrap import bootstrap
from eag.plugins.builtin.command import COMMAND_RUN, COMMAND_WHICH
from eag.plugins.builtin.filesystem import (
    FILESYSTEM_LIST,
    FILESYSTEM_READ,
)
from eag.plugins.builtin.git import GIT_STATUS
from eag.plugins.builtin.workspace import (
    WORKSPACE_INSPECT,
)

app = typer.Typer(
    name="eag",
    help="EAG — Engineering Agent. Eager for Knowledge.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(  # noqa: B008  # noqa: B008
        False,
        "--version",
        "-V",
        help="Show the EAG version and exit.",
    ),
) -> None:
    """Start EAG."""
    if version:
        typer.echo(f"EAG {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    typer.echo()
    typer.echo("EAG — Engineering Agent")
    typer.echo(f"Version {__version__}")
    typer.echo("Eager for Knowledge")
    typer.echo()

    kernel = bootstrap()

    typer.echo(f"Environment: {kernel.settings.kernel.environment}")
    typer.echo(f"Workspace: {kernel.settings.kernel.workspace}")
    typer.echo(f"Kernel state: {kernel.state.value}")
    typer.echo("EAG is ready.")


if __name__ == "__main__":
    app()


@app.command()
def read(path: str) -> None:
    """Read a text file from the current workspace."""
    kernel = bootstrap()

    try:
        registration = kernel.capability_registry.resolve(FILESYSTEM_READ)

        content = registration.handler(path)
        typer.echo(content)
    finally:
        kernel.shutdown()


@app.command(name="list")
def list_directory(
    path: str = ".",
) -> None:
    """List files in a workspace directory."""
    kernel = bootstrap()

    try:
        registration = kernel.capability_registry.resolve(FILESYSTEM_LIST)

        entries = registration.handler(path)

        for entry in entries:
            typer.echo(entry)
    finally:
        kernel.shutdown()


@app.command()
def inspect() -> None:
    """Inspect and profile the current workspace."""
    kernel = bootstrap()

    try:
        registration = kernel.capability_registry.resolve(WORKSPACE_INSPECT)

        inspection = registration.handler()

        typer.echo(f"Workspace: {inspection.profile.root}")
        typer.echo(f"Files: {inspection.profile.total_files}")
        typer.echo(f"Directories: {inspection.profile.total_directories}")

        typer.echo("\nLanguages:")

        for language in inspection.profile.languages:
            typer.echo(f"  {language.language}: {language.files}")

        typer.echo("\nProject markers:")

        for marker in inspection.profile.markers:
            typer.echo(f"  {marker}")

        typer.echo("\nLikely entry points:")

        for path in inspection.likely_entry_points:
            typer.echo(f"  {path}")

        typer.echo("\nImportant files:")

        for path in inspection.important_files:
            typer.echo(f"  {path}")
    finally:
        kernel.shutdown()


@app.command(name="git-status")
def git_status() -> None:
    """Show structured Git workspace status."""
    kernel = bootstrap()

    try:
        registration = kernel.capability_registry.resolve(GIT_STATUS)

        status = registration.handler()

        typer.echo(f"Branch: {status.branch or '(detached HEAD)'}")
        typer.echo(f"Clean: {'yes' if status.clean else 'no'}")

        if status.files:
            typer.echo("\nChanges:")

            for file in status.files:
                typer.echo(f"  {file.index_status}{file.worktree_status} {file.path}")
    finally:
        kernel.shutdown()


@app.command()
def health() -> None:
    """Show EAG runtime health."""
    kernel = bootstrap()

    try:
        report = kernel.health()

        typer.echo(f"Kernel: {report.kernel_state.value}")
        typer.echo(f"Capabilities: {report.capability_count}")

        typer.echo("\nPlugins:")

        for plugin in report.plugins:
            marker = "✓" if plugin.available else "○"

            typer.echo(f"  {marker} {plugin.name}: {plugin.status.value} ({plugin.policy.value})")

            if plugin.error_message:
                typer.echo(f"      {plugin.error_message}")
    finally:
        kernel.shutdown()


@app.command()
def which(
    executable: str,
) -> None:
    """Resolve an executable available to EAG."""
    kernel = bootstrap()

    try:
        registration = kernel.capability_registry.resolve(COMMAND_WHICH)

        resolved = registration.handler(executable)

        if resolved is None:
            typer.echo(f"Executable not found: {executable}")
            raise typer.Exit(code=1)

        typer.echo(str(resolved))
    finally:
        kernel.shutdown()


@app.command(name="run")
def run_command(
    executable: str,
    arguments: list[str] | None = typer.Argument(None),  # noqa: B008
    timeout: float = typer.Option(60.0, "--timeout"),  # noqa: B008
    cwd: Path | None = typer.Option(None, "--cwd"),  # noqa: B008
) -> None:
    """Run a command through EAG's execution engine."""
    kernel = bootstrap()

    try:
        registration = kernel.capability_registry.resolve(COMMAND_RUN)

        result = registration.handler(
            executable=executable,
            arguments=tuple(arguments or ()),
            working_directory=cwd,
            timeout_seconds=timeout,
        )

        typer.echo(f"Executable: {executable}")

        if arguments:
            typer.echo(f"Arguments: {' '.join(arguments)}")

        typer.echo(f"Exit code: {result.exit_code}")
        typer.echo(f"Duration: {result.duration_seconds:.3f}s")
        typer.echo(f"Timed out: {'yes' if result.timed_out else 'no'}")

        if result.stdout:
            typer.echo("\nStdout:")
            typer.echo(result.stdout, nl=False)

            if not result.stdout.endswith("\n"):
                typer.echo()

        if result.stderr:
            typer.echo("\nStderr:")
            typer.echo(result.stderr, nl=False)

            if not result.stderr.endswith("\n"):
                typer.echo()

        if result.stdout_truncated:
            typer.echo("\n[stdout truncated]")

        if result.stderr_truncated:
            typer.echo("\n[stderr truncated]")

        if result.timed_out:
            raise typer.Exit(code=124)

        if result.exit_code not in (
            None,
            0,
        ):
            raise typer.Exit(code=result.exit_code)
    finally:
        kernel.shutdown()
