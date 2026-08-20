"""G2.0 canonical autonomous composition contracts."""

from pathlib import Path

from typer.testing import CliRunner

from eag.autonomous import LoopContext, create_autonomous_engineering_composition
from eag.autonomous.enums import LoopOutcome
from eag.cli import app

runner = CliRunner()


def test_canonical_composition_runs_through_chief_and_coordinator(tmp_path: Path) -> None:
    """The canonical factory owns the public Chief → Coordinator → Loop path."""
    composition = create_autonomous_engineering_composition(tmp_path)

    assert composition.chief.coordinator is composition.coordinator

    result = composition.loop.execute(
        LoopContext(
            goal="Build a calculator",
            max_iterations=1,
            metadata={"workspace_path": tmp_path},
        )
    )

    assert result.outcome == LoopOutcome.FINISHED
    assert result.metrics.total_iterations == 1
    assert composition.memory_runtime.statistics().total_runs == 1


def test_build_command_uses_canonical_composition(tmp_path: Path, monkeypatch) -> None:
    """The user-facing build command must enter the one canonical factory path."""
    import eag.autonomous as autonomous

    workspace = tmp_path / "build-workspace"
    observed_roots: list[Path] = []
    original_factory = autonomous.create_autonomous_engineering_composition

    def recording_factory(workspace_root: Path):
        observed_roots.append(workspace_root.resolve())
        return original_factory(workspace_root)

    monkeypatch.setattr(autonomous, "create_autonomous_engineering_composition", recording_factory)

    result = runner.invoke(app, ["build", "Build a calculator", "--workspace", str(workspace)])

    assert result.exit_code == 0, result.stdout
    assert observed_roots == [workspace.resolve()]
    assert "Autonomous Engineering Complete" in result.stdout
