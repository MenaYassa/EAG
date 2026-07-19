"""Tests for the planner CLI commands."""

from typer.testing import CliRunner

from eag.cli import app

runner = CliRunner()


class TestPlannerCLI:
    def test_plan_command(self) -> None:
        result = runner.invoke(app, ["plan", "Rename EventBus"])
        assert result.exit_code == 0
        assert "Engineering Plan" in result.stdout
        assert "Strategy: Sequential" in result.stdout

    def test_validate_command(self) -> None:
        result = runner.invoke(app, ["validate", "Rename EventBus"])
        assert result.exit_code == 0
        assert "Validation Report" in result.stdout
        assert "Status: PASS" in result.stdout

    def test_simulate_command(self) -> None:
        result = runner.invoke(app, ["simulate", "Rename EventBus"])
        assert result.exit_code == 0
        assert "Simulation Report" in result.stdout

    def test_approve_command(self) -> None:
        result = runner.invoke(app, ["approve", "Rename EventBus"])
        assert result.exit_code == 0
        assert "Approval Report" in result.stdout

    def test_explain_command(self) -> None:
        result = runner.invoke(app, ["explain", "Rename EventBus"])
        assert result.exit_code == 0
        assert "Engineering Decision Report" in result.stdout

    def test_strategies_command(self) -> None:
        result = runner.invoke(app, ["strategies"])
        assert result.exit_code == 0
        assert "Available Strategies" in result.stdout
        assert "Sequential" in result.stdout

    def test_operations_command(self) -> None:
        result = runner.invoke(app, ["operations"])
        assert result.exit_code == 0
        assert "Available Operations" in result.stdout
        assert "Rename Symbol" in result.stdout

    def test_policies_command(self) -> None:
        result = runner.invoke(app, ["policies"])
        assert result.exit_code == 0
        assert "Available Policies" in result.stdout
        assert "RiskApprovalPolicy" in result.stdout

    def test_status_command(self) -> None:
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Engineering Planning Platform" in result.stdout

    def test_doctor_command(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Engineering Agent Diagnostics" in result.stdout

    def test_about_command(self) -> None:
        result = runner.invoke(app, ["about"])
        assert result.exit_code == 0
        assert "Engineering Agent" in result.stdout

    def test_export_command(self) -> None:
        result = runner.invoke(app, ["export", "Rename EventBus"])
        assert result.exit_code == 0
        assert "# Engineering Plan" in result.stdout
