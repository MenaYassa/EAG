"""Command-line interface for EAG."""

import typer

from eag import __version__
from eag.bootstrap import bootstrap
from eag.plugins.builtin.filesystem import (
    FILESYSTEM_LIST,
    FILESYSTEM_READ,
)

app = typer.Typer(
    name="eag",
    help="EAG — Engineering Agent. Eager for Knowledge.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
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
