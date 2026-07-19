"""Command-line interface for EAG."""

from pathlib import Path

import click
import typer

from eag import __version__
from eag.bootstrap import bootstrap
from eag.execution.errors import (
    CommandApprovalRequiredError,
    CommandDeniedError,
)

# Add these imports to the top of src/eag/cli.py
from eag.explorer.formatter import JsonFormatter, TerminalFormatter
from eag.explorer.models import (
    DependencyRequest,
    FindSymbolRequest,
    ModuleRequest,
    OverviewRequest,
    SearchRequest,
    StatisticsRequest,
)
from eag.explorer.runtime import ExplorerRuntime
from eag.index.runtime import IndexRuntime
from eag.planner.cli import register_planner_commands
from eag.plugins.builtin.command import (
    COMMAND_EVALUATE,
    COMMAND_RUN,
    COMMAND_WHICH,
)
from eag.plugins.builtin.filesystem import (
    FILESYSTEM_LIST,
    FILESYSTEM_READ,
)
from eag.plugins.builtin.git import GIT_STATUS
from eag.plugins.builtin.workspace import (
    WORKSPACE_INSPECT,
)
from eag.safety import SafetyBackend
from eag.source.python.analyzer import PythonAnalyzer
from eag.source.registry import SourceAnalyzerRegistry
from eag.source.runtime import SourceRuntime

app = typer.Typer(
    name="eag",
    help="EAG — Engineering Agent. Eager for Knowledge.",
    no_args_is_help=False,
)

# Register Planner CLI commands
register_planner_commands(app)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(  # noqa: B008
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
def safety() -> None:
    """Show engineering safety status."""
    kernel = bootstrap()

    try:
        report = kernel.context.safety_runtime.inspect()

        print("\nEngineering Safety")
        print("─────────────────────────\n")

        repo_marker = "✓" if report.status.backend == SafetyBackend.GIT else "○"
        print(f"Workspace:\n  {repo_marker} Git repository")

        print(f"\nBranch:\n  {report.status.branch or '(detached HEAD)'}")
        print(f"\nHEAD:\n  {report.status.head or 'None'}")

        tree_marker = "✓ Clean" if not report.status.dirty else "✗ Dirty"
        print(f"\nWorking Tree:\n  {tree_marker}")

        print(f"\nConflicts:\n  {'None' if not report.status.has_conflicts else 'Present'}")

        print(f"\nRollback:\n  {'✓ Available' if report.checkpoint else '○ Not available'}")
        print(f"\nStatus:\n  {report.state.value.upper()}\n")

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


@app.command()
def policy(
    executable: str,
    arguments: list[str] = typer.Argument([]),  # noqa: B008
    cwd: Path | None = typer.Option(None, "--cwd"),  # noqa: B008
    timeout: float = typer.Option(60.0, "--timeout"),  # noqa: B008
) -> None:
    """Evaluate command policy without execution."""
    kernel = bootstrap()

    try:
        registration = kernel.capability_registry.resolve(COMMAND_EVALUATE)

        decision = registration.handler(
            executable=executable,
            arguments=tuple(arguments),
            working_directory=cwd,
            timeout_seconds=timeout,
        )

        typer.echo(f"Command: {executable} {' '.join(arguments)}")
        typer.echo(f"Classification: {decision.classification.value}")
        typer.echo(f"Outcome: {decision.outcome.value}")
        typer.echo(f"Rule: {decision.matched_rule}")
        typer.echo(f"Reason: {decision.reason}")
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

        # --- Execute the command, handling policy rejections ---
        try:
            result = registration.handler(
                executable=executable,
                arguments=tuple(arguments or ()),
                working_directory=cwd,
                timeout_seconds=timeout,
            )
        except CommandApprovalRequiredError as exc:
            typer.echo("Execution blocked: approval required")
            typer.echo(f"Reason: {exc}")
            raise typer.Exit(code=3) from None
        except CommandDeniedError as exc:
            typer.echo("Execution denied")
            typer.echo(f"Reason: {exc}")
            raise typer.Exit(code=4) from None

        # --- Render the result (unchanged) ---
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

        if result.exit_code not in (None, 0):
            raise typer.Exit(code=result.exit_code)

    finally:
        kernel.shutdown()


@app.command()
def scan(
    path: Path | None = typer.Argument(  # noqa: B008
        None,
        help="Path to repository to scan (defaults to workspace)",
    ),
) -> None:
    """Scan a repository and display its profile."""
    kernel = bootstrap()

    from eag.repository.ignore import IgnoreEngine
    from eag.repository.runtime import RepositoryRuntime, RepositoryServices
    from eag.repository.scanner import RepositoryScanner

    ignore_engine = IgnoreEngine()
    scanner = RepositoryScanner(ignore_engine=ignore_engine)
    services = RepositoryServices(
        scanner=scanner,
        event_bus=kernel.context.event_bus,
        settings=kernel.context.settings,
    )
    runtime = RepositoryRuntime(services=services)

    target = path or kernel.context.settings.kernel.workspace
    snapshot = runtime.scan(target)
    profile = snapshot.profile

    click.echo("Repository")
    click.echo("─" * 40)
    click.echo(f"Name:    {profile.identity.name}")
    click.echo(f"Root:    {profile.identity.root}")
    click.echo(f"Health:  {profile.health.value.upper()}")
    click.echo(f"Kind:    {profile.kind.value.upper()}")
    click.echo(f"Layout:  {profile.layout.value.upper()}")
    click.echo("")
    click.echo("Statistics")
    click.echo("─" * 40)
    click.echo(f"Directories:   {profile.statistics.directories}")
    click.echo(f"Files:         {profile.statistics.files}")
    click.echo(f"Packages:      {profile.statistics.packages}")
    click.echo(f"Tests:         {profile.statistics.tests}")
    click.echo(f"Documentation: {profile.statistics.documentation}")
    click.echo(f"Total Size:    {profile.statistics.total_bytes} bytes")
    click.echo("")
    click.echo("Capabilities")
    click.echo("─" * 40)
    caps = profile.capabilities
    click.echo(f"{'✓' if caps.git else '✗'} Git")
    click.echo(f"{'✓' if caps.tests else '✗'} Tests")
    pkg_str = f" ({profile.metadata.package_manager})" if profile.metadata.package_manager else ""
    click.echo(f"{'✓' if caps.package_manager else '✗'} Package Manager{pkg_str}")
    click.echo(f"{'✓' if caps.docker else '✗'} Docker")
    click.echo(f"{'✓' if caps.type_checking else '✗'} Type Checking")
    click.echo(f"{'✓' if caps.formatting else '✗'} Formatting")
    click.echo("")
    click.echo("Metadata")
    click.echo("─" * 40)
    if profile.metadata.git_repository:
        click.echo("Git Repository: Yes")
    else:
        click.echo("Git Repository: No")

    if profile.metadata.pyproject:
        click.echo("pyproject.toml: Present")
    if profile.metadata.readme:
        click.echo("README: Present")
    if profile.metadata.license:
        click.echo("License: Present")

    click.echo("")
    click.echo("Repository Facts")
    click.echo("─" * 40)
    for fact in profile.facts:
        click.echo(f"- {fact.kind}: {fact.value} (confidence: {fact.confidence:.0%})")

    click.echo("")
    click.echo(f"Generated: {profile.generated_at.isoformat()}")


# ==================== MODIFIED symbols COMMAND ====================
@app.command()
def symbols(
    path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        dir_okay=False,
        help="Path to the source file to analyze.",
    ),
) -> None:
    """Analyze a source file and display its engineering symbols."""
    from eag.source.analyzer import AnalysisContext
    from eag.source.python.analyzer import PythonAnalyzer

    kernel = bootstrap()
    analyzer = PythonAnalyzer()

    if not analyzer.supports(path):
        click.echo(f"Unsupported file type: {path.suffix}")
        return

    context = AnalysisContext(
        path=path,
        repository_root=kernel.context.settings.kernel.workspace,
        settings=kernel.context.settings,
        cache=None,
    )

    result = analyzer.analyze(context)

    click.echo("Module")
    click.echo("─" * 40)
    click.echo(result.module.name)
    click.echo("")

    click.echo("Public API")
    click.echo("─" * 40)

    classes = [s for s in result.symbols if s.identity.kind.value == "class"]
    functions = [s for s in result.symbols if s.identity.kind.value == "function"]
    methods = [s for s in result.symbols if s.identity.kind.value == "method"]

    if classes:
        click.echo("Classes:")
        for c in classes:
            name = c.identity.qualified_name.split(".")[-1]
            click.echo(f"  - {name}")
    if functions:
        click.echo("Functions:")
        for f in functions:
            name = f.identity.qualified_name.split(".")[-1]
            click.echo(f"  - {name}()")
    if methods:
        click.echo("Methods:")
        for m in methods:
            parts = m.identity.qualified_name.split(".")
            click.echo(f"  - {parts[-2]}.{parts[-1]}()")

    click.echo("")
    click.echo("Dependencies")
    click.echo("─" * 40)
    for dep in result.dependencies:
        click.echo(f"  - {dep.target}")

    click.echo("")
    click.echo("Metrics")
    click.echo("─" * 40)
    click.echo(f"Lines:    {result.metrics.lines}")
    click.echo(f"Symbols:  {result.metrics.symbols}")
    click.echo(f"Imports:  {result.metrics.dependencies}")


# ==================== MODIFIED index COMMAND ====================
@app.command()
def index() -> None:
    """Build and display the repository engineering index."""
    import time

    from eag.index.runtime import IndexRuntime
    from eag.source.python.analyzer import PythonAnalyzer
    from eag.source.registry import SourceAnalyzerRegistry
    from eag.source.runtime import SourceRuntime

    kernel = bootstrap()

    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)

    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)

    repo_root = kernel.context.settings.kernel.workspace
    repo_name = repo_root.name

    click.echo(f"Building engineering index for {repo_name}...")
    start_time = time.time()
    idx = index_runtime.build(repo_root, repo_name)
    duration_ms = (time.time() - start_time) * 1000

    click.echo("")
    click.echo("Repository Index")
    click.echo("─" * 40)
    click.echo(f"Repository:   {repo_name}")
    click.echo(f"Files:        {idx.statistics.files}")
    click.echo(f"Modules:      {idx.statistics.modules}")
    click.echo("")
    click.echo("Symbols")
    click.echo("─" * 40)
    click.echo(f"Classes:      {idx.statistics.classes}")
    click.echo(f"Interfaces:   {idx.statistics.interfaces}")
    click.echo(f"Protocols:    {idx.statistics.protocols}")
    click.echo(f"Enums:        {idx.statistics.enums}")
    click.echo(f"Dataclasses:  {idx.statistics.dataclasses}")
    click.echo(f"Functions:    {idx.statistics.functions}")
    click.echo(f"Methods:      {idx.statistics.methods}")
    click.echo(f"Constants:    {idx.statistics.constants}")
    click.echo(f"Total:        {idx.statistics.symbols}")
    click.echo("")
    click.echo(f"Dependencies: {idx.statistics.dependencies}")
    click.echo("")
    click.echo(f"Generated in: {duration_ms:.0f} ms")


# Helper function to get the explorer runtime
def _get_explorer_runtime() -> tuple[ExplorerRuntime, str]:
    kernel = bootstrap()

    # 1. Setup Source Runtime
    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)

    # 2. Setup Index Runtime and build index
    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)
    repo_root = kernel.context.settings.kernel.workspace
    repo_name = repo_root.name

    # In a real app, this would be cached. For now, we build it on demand.
    index = index_runtime.build(repo_root, repo_name)

    # 3. Setup Explorer Runtime
    return ExplorerRuntime(index, repo_name), repo_name


# ==================== EXPLORER COMMANDS (TYPER NATIVE) ====================


@app.command()
def overview(
    json: bool = typer.Option(  # noqa: B008
        False, "--json", help="Output as JSON"
    ),
) -> None:
    """Display the engineering overview of the repository."""
    runtime, repo_name = _get_explorer_runtime()
    view = runtime.overview(OverviewRequest())

    formatter = JsonFormatter() if json else TerminalFormatter()
    click.echo(formatter.format(view))


@app.command()
def stats(
    json: bool = typer.Option(  # noqa: B008
        False, "--json", help="Output as JSON"
    ),
) -> None:
    """Display engineering statistics."""
    runtime, _ = _get_explorer_runtime()
    view = runtime.statistics(StatisticsRequest())

    formatter = JsonFormatter() if json else TerminalFormatter()
    click.echo(formatter.format(view))


@app.command()
def find(
    name: str = typer.Argument(..., help="The symbol name to locate"),
    json: bool = typer.Option(  # noqa: B008
        False, "--json", help="Output as JSON"
    ),
) -> None:
    """Find a specific symbol in the engineering index."""
    runtime, _ = _get_explorer_runtime()

    try:
        view = runtime.find_symbol(FindSymbolRequest(name=name))
        formatter = JsonFormatter() if json else TerminalFormatter()
        click.echo(formatter.format(view))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command()
def module(
    name: str = typer.Argument(..., help="The module name to locate"),
    json: bool = typer.Option(  # noqa: B008
        False, "--json", help="Output as JSON"
    ),
) -> None:
    """View details of a specific module."""
    runtime, _ = _get_explorer_runtime()

    try:
        view = runtime.module(ModuleRequest(name=name))
        formatter = JsonFormatter() if json else TerminalFormatter()
        click.echo(formatter.format(view))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command()
def deps(
    source: str = typer.Argument(..., help="The source target module or symbol"),
    json: bool = typer.Option(  # noqa: B008
        False, "--json", help="Output as JSON"
    ),
) -> None:
    """View dependencies of a module or symbol."""
    runtime, _ = _get_explorer_runtime()

    view = runtime.dependencies(DependencyRequest(source=source))
    formatter = JsonFormatter() if json else TerminalFormatter()
    click.echo(formatter.format(view))


@app.command()
def search(
    query: str = typer.Argument(..., help="The index search search query"),
    json: bool = typer.Option(  # noqa: B008
        False, "--json", help="Output as JSON"
    ),
) -> None:
    """Search the engineering index."""
    runtime, _ = _get_explorer_runtime()

    view = runtime.search(SearchRequest(query=query))
    formatter = JsonFormatter() if json else TerminalFormatter()
    click.echo(formatter.format(view))


@app.command()
def graph() -> None:
    """Display engineering graph metrics and statistics."""
    from eag.graph.builder import GraphBuilder
    from eag.graph.runtime import GraphRuntime
    from eag.index.runtime import IndexRuntime
    from eag.source.python.analyzer import PythonAnalyzer
    from eag.source.registry import SourceAnalyzerRegistry
    from eag.source.runtime import SourceRuntime

    kernel = bootstrap()

    # Setup Runtimes
    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)
    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)
    graph_runtime = GraphRuntime(GraphBuilder(kernel.context.event_bus), kernel.context.event_bus)

    repo_root = kernel.context.settings.kernel.workspace
    repo_name = repo_root.name

    click.echo(f"Building engineering graph for {repo_name}...")
    index = index_runtime.build(repo_root, repo_name)

    # Prepend an underscore to mark it explicitly as unused
    _snapshot = graph_runtime.build(index)
    metrics = graph_runtime.metrics()

    if metrics.most_referenced:
        # Wrap line 707 cleanly across multiple lines
        click.echo(
            f"Most Referenced: {metrics.most_referenced.name} "
            f"({metrics.most_referenced.kind.value})"
        )

    click.echo("")
    click.echo("Engineering Graph")
    click.echo("─" * 40)
    click.echo(f"Nodes:           {metrics.nodes}")
    click.echo(f"Edges:           {metrics.edges}")
    click.echo("")
    click.echo("Key Nodes")
    click.echo("─" * 40)
    if metrics.most_referenced:
        click.echo(
            f"Most Referenced: {metrics.most_referenced.name} "
            f"({metrics.most_referenced.kind.value})"
        )
    if metrics.most_connected:
        click.echo(
            f"Most Connected:  {metrics.most_connected.name} ({metrics.most_connected.kind.value})"
        )


@app.command(name="dependents")
def dependents(name: str) -> None:
    """View direct dependents of a node."""
    from eag.graph.builder import GraphBuilder
    from eag.graph.runtime import GraphRuntime
    from eag.index.runtime import IndexRuntime
    from eag.source.python.analyzer import PythonAnalyzer
    from eag.source.registry import SourceAnalyzerRegistry
    from eag.source.runtime import SourceRuntime

    kernel = bootstrap()
    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)
    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)
    graph_runtime = GraphRuntime(GraphBuilder(kernel.context.event_bus), kernel.context.event_bus)

    repo_root = kernel.context.settings.kernel.workspace
    index = index_runtime.build(repo_root, repo_root.name)
    graph_runtime.build(index)

    try:
        node = graph_runtime.find_node(name)
        deps = graph_runtime.dependents(node.id)

        click.echo(f"Dependents for {node.name}")
        click.echo("─" * 40)
        if not deps:
            click.echo("  None")
        else:
            for d in deps:
                click.echo(f"  • {d.name} ({d.kind.value})")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command(name="graph")
@click.argument("subcommand", required=False)
@click.argument("target", required=False)
def graph_cmd(subcommand: str | None, target: str | None) -> None:
    """Engineering graph operations."""
    from eag.graph.builder import GraphBuilder
    from eag.graph.runtime import GraphRuntime
    from eag.graph.services import GraphExporter, GraphFormatter, GraphValidator
    from eag.index.runtime import IndexRuntime
    from eag.source.python.analyzer import PythonAnalyzer
    from eag.source.registry import SourceAnalyzerRegistry
    from eag.source.runtime import SourceRuntime

    kernel = bootstrap()
    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)
    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)
    graph_builder = GraphBuilder(kernel.context.event_bus)
    graph_runtime = GraphRuntime(graph_builder, kernel.context.event_bus)

    repo_root = kernel.context.settings.kernel.workspace
    index = index_runtime.build(repo_root, repo_root.name)
    graph_runtime.build(index)

    formatter = GraphFormatter()
    graph = graph_runtime.graph()

    if subcommand == "stats" or subcommand is None:
        click.echo(formatter.format_graph_stats(graph))
    elif subcommand == "validate":
        validator = GraphValidator()
        report = validator.validate(graph)
        click.echo("Engineering Graph Validation")
        click.echo("─" * 40)
        if report.healthy:
            click.echo("✓ Graph is healthy.")
        else:
            for err in report.errors:
                click.echo(f"✗ {err}", err=True)
    elif subcommand == "export":
        exporter = GraphExporter()
        click.echo(exporter.to_json(graph))
    else:
        click.echo(f"Unknown subcommand: {subcommand}")


@app.command(name="graph-deps")
@click.argument("name")
def graph_deps(name: str) -> None:
    """View direct dependencies of a node."""
    from eag.graph.builder import GraphBuilder
    from eag.graph.runtime import GraphRuntime
    from eag.graph.services import GraphFormatter
    from eag.index.runtime import IndexRuntime
    from eag.source.python.analyzer import PythonAnalyzer
    from eag.source.registry import SourceAnalyzerRegistry
    from eag.source.runtime import SourceRuntime

    kernel = bootstrap()
    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)
    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)
    graph_builder = GraphBuilder(kernel.context.event_bus)
    graph_runtime = GraphRuntime(graph_builder, kernel.context.event_bus)

    repo_root = kernel.context.settings.kernel.workspace
    index = index_runtime.build(repo_root, repo_root.name)
    graph_runtime.build(index)

    try:
        node = graph_runtime.find_node(name)
        resolved_deps = graph_runtime.dependencies(node.id)
        formatter = GraphFormatter()
        click.echo(formatter.format_dependencies(node, list(resolved_deps)))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command(name="why")
@click.argument("name")
def why(name: str) -> None:
    """Explain why a node is connected to the rest of the system."""
    from eag.graph.builder import GraphBuilder
    from eag.graph.runtime import GraphRuntime
    from eag.graph.services import GraphFormatter
    from eag.index.runtime import IndexRuntime
    from eag.source.python.analyzer import PythonAnalyzer
    from eag.source.registry import SourceAnalyzerRegistry
    from eag.source.runtime import SourceRuntime

    kernel = bootstrap()
    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)
    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)
    graph_builder = GraphBuilder(kernel.context.event_bus)
    graph_runtime = GraphRuntime(graph_builder, kernel.context.event_bus)

    repo_root = kernel.context.settings.kernel.workspace
    index = index_runtime.build(repo_root, repo_root.name)
    graph_runtime.build(index)

    try:
        node = graph_runtime.find_node(name)
        graph = graph_runtime.graph()

        incoming = [
            (graph_runtime.node(e.source), e.relationship)
            for e in graph.edges
            if e.target == node.id
        ]
        outgoing = [
            (graph_runtime.node(e.target), e.relationship)
            for e in graph.edges
            if e.source == node.id
        ]

        formatter = GraphFormatter()
        click.echo(formatter.format_why(node, incoming, outgoing))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command(name="impact")
@click.argument("name")
def impact(name: str) -> None:
    """Analyze the engineering impact of changing a node."""
    from eag.graph.builder import GraphBuilder
    from eag.graph.runtime import GraphRuntime
    from eag.graph.services import GraphFormatter
    from eag.index.runtime import IndexRuntime
    from eag.source.python.analyzer import PythonAnalyzer
    from eag.source.registry import SourceAnalyzerRegistry
    from eag.source.runtime import SourceRuntime

    kernel = bootstrap()
    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)
    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)
    graph_builder = GraphBuilder(kernel.context.event_bus)
    graph_runtime = GraphRuntime(graph_builder, kernel.context.event_bus)

    repo_root = kernel.context.settings.kernel.workspace
    index = index_runtime.build(repo_root, repo_root.name)
    graph_runtime.build(index)

    try:
        node = graph_runtime.find_node(name)
        report = graph_runtime.impact(node.id)
        formatter = GraphFormatter()
        click.echo(formatter.format_impact(report))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command(name="path")
@click.argument("start")
@click.argument("end")
def path(start: str, end: str) -> None:
    """Find the shortest engineering path between two nodes."""
    from eag.graph.builder import GraphBuilder
    from eag.graph.runtime import GraphRuntime
    from eag.graph.services import GraphFormatter
    from eag.index.runtime import IndexRuntime
    from eag.source.python.analyzer import PythonAnalyzer
    from eag.source.registry import SourceAnalyzerRegistry
    from eag.source.runtime import SourceRuntime

    kernel = bootstrap()
    registry = SourceAnalyzerRegistry()
    registry.register(PythonAnalyzer())
    source_runtime = SourceRuntime(registry, kernel.context.event_bus)
    index_runtime = IndexRuntime(source_runtime, kernel.context.event_bus)
    graph_builder = GraphBuilder(kernel.context.event_bus)
    graph_runtime = GraphRuntime(graph_builder, kernel.context.event_bus)

    repo_root = kernel.context.settings.kernel.workspace
    index = index_runtime.build(repo_root, repo_root.name)
    graph_runtime.build(index)

    try:
        start_node = graph_runtime.find_node(start)
        end_node = graph_runtime.find_node(end)
        report = graph_runtime.path(start_node.id, end_node.id)
        formatter = GraphFormatter()
        click.echo(formatter.format_path(report))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
