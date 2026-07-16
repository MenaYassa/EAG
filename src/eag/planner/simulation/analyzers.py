"""Simulation analyzers for EAG."""

from typing import Protocol, runtime_checkable

from eag.planner.intelligence.models import (
    EngineeringPlanningArtifact,
    EngineeringOperation as EngOpEnum,
)
from eag.planner.models import EngineeringTask
from eag.planner.simulation.models import (
    SimulationCheckpoint,
    SimulationImpact,
    SimulationTimeline,
)


@runtime_checkable
class SimulationAnalyzer(Protocol):
    """Protocol for simulation analyzers."""
    def analyze(self, artifact: EngineeringPlanningArtifact) -> object: ...


class ImpactAnalyzer:
    """Predicts the impact of a plan on the repository."""

    def analyze(self, artifact: EngineeringPlanningArtifact) -> SimulationImpact:
        op = artifact.engineering_goal.operation
        affected_files = 0
        affected_symbols = 0
        affected_modules = 0

        if op == EngOpEnum.RENAME:
            affected_symbols = 5
            affected_files = 2
        elif op == EngOpEnum.MOVE:
            affected_modules = 1
            affected_files = 2
        elif op == EngOpEnum.DELETE:
            affected_symbols = 1
            affected_files = 1
        elif op == EngOpEnum.CREATE:
            affected_files = 1
        elif op == EngOpEnum.EXTRACT:
            affected_modules = 1
            affected_files = 2
            affected_symbols = 3

        return SimulationImpact(
            task_count=len(artifact.tasks),
            operation_count=1,
            affected_files=affected_files,
            affected_symbols=affected_symbols,
            affected_modules=affected_modules,
        )


class TimelineAnalyzer:
    """Predicts the execution timeline using the effort estimate."""

    def analyze(self, artifact: EngineeringPlanningArtifact) -> SimulationTimeline:
        profile = artifact.execution_profile
        phases = tuple(t.title for t in artifact.tasks)
        
        return SimulationTimeline(
            estimated_minutes=profile.total_engineering_time,
            critical_path_minutes=profile.critical_path_duration,
            parallel_savings_minutes=profile.parallel_savings,
            phases=phases,
        )


class CheckpointAnalyzer:
    """Identifies rollback checkpoints based on risk and operations."""

    def analyze(self, artifact: EngineeringPlanningArtifact) -> tuple[SimulationCheckpoint, ...]:
        checkpoints: list[SimulationCheckpoint] = []
        
        # Always add a pre-execution checkpoint for dangerous ops
        dangerous_ops = [EngOpEnum.DELETE, EngOpEnum.UPGRADE, EngOpEnum.MOVE]
        if artifact.engineering_goal.operation in dangerous_ops:
            checkpoints.append(SimulationCheckpoint(
                name=f"Pre-{artifact.engineering_goal.operation.value}",
                task_ids=(),
                rollback_available=True
            ))

        # Add a checkpoint after validation tasks
        for task in artifact.tasks:
            if "validate" in task.title.lower() or "test" in task.title.lower():
                checkpoints.append(SimulationCheckpoint(
                    name=f"After {task.title}",
                    task_ids=(task.id,),
                    rollback_available=True
                ))

        return tuple(checkpoints)