"""Plan simulation engine for EAG."""

from typing import Any

from eag.planner.enums import RiskLevel
from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.simulation.analyzers import (
    CheckpointAnalyzer,
    ImpactAnalyzer,
    TimelineAnalyzer,
)
from eag.planner.simulation.models import (
    EngineeringSimulationReport,
    SimulationStatus,
)


class PlanSimulator:
    """Orchestrates simulation analyzers to predict plan outcomes."""

    def __init__(self) -> None:
        self._impact_analyzer = ImpactAnalyzer()
        self._timeline_analyzer = TimelineAnalyzer()
        self._checkpoint_analyzer = CheckpointAnalyzer()

    def simulate(self, artifact: EngineeringPlanningArtifact) -> EngineeringSimulationReport:
        """Run all simulation analyzers and aggregate the results."""
        impact = self._impact_analyzer.analyze(artifact)
        timeline = self._timeline_analyzer.analyze(artifact)
        checkpoints = self._checkpoint_analyzer.analyze(artifact)

        warnings: list[str] = []

        if artifact.risk.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            warnings.append(f"High risk operation ({artifact.risk.overall_risk.value}) detected.")

        if impact.affected_files > 10:
            warnings.append(f"Impact affects {impact.affected_files} files.")

        status = SimulationStatus.READY
        if warnings:
            status = SimulationStatus.WARNING

        summary = self._build_summary(status, impact, timeline, warnings)

        return EngineeringSimulationReport(
            status=status,
            impact=impact,
            timeline=timeline,
            checkpoints=checkpoints,
            warnings=tuple(warnings),
            summary=summary,
        )

    def _build_summary(
        self,
        status: SimulationStatus,
        impact: Any,  # Could be ImpactAnalysis, but not imported; using Any
        timeline: Any,  # Could be TimelineAnalysis
        warnings: list[str],
    ) -> str:
        if status == SimulationStatus.READY:
            return (
                "Plan is ready for execution. "
                f"Estimated time: {timeline.estimated_minutes:.1f} minutes."
            )
        if status == SimulationStatus.WARNING:
            return (
                f"Plan can proceed with {len(warnings)} warnings. "
                f"Estimated time: {timeline.estimated_minutes:.1f} minutes."
            )
        return "Plan is blocked and cannot proceed."
