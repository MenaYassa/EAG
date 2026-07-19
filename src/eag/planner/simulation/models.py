"""Simulation domain models for EAG."""

from dataclasses import dataclass
from enum import StrEnum


class SimulationStatus(StrEnum):
    """Status of a simulated plan."""

    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationImpact:
    """Predicted impact of executing a plan."""

    task_count: int
    operation_count: int
    affected_files: int
    affected_symbols: int
    affected_modules: int

    def __post_init__(self) -> None:
        for field_name in [
            "task_count",
            "operation_count",
            "affected_files",
            "affected_symbols",
            "affected_modules",
        ]:
            val = getattr(self, field_name)
            if not isinstance(val, int) or isinstance(val, bool) or val < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationTimeline:
    """Predicted timeline for a plan."""

    estimated_minutes: float
    critical_path_minutes: float
    parallel_savings_minutes: float
    phases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in [
            "estimated_minutes",
            "critical_path_minutes",
            "parallel_savings_minutes",
        ]:
            val = getattr(self, field_name)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or val < 0:
                raise ValueError(f"{field_name} must be a non-negative number")
        if not isinstance(self.phases, tuple):
            raise TypeError("phases must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationCheckpoint:
    """A predicted checkpoint for rollback during execution."""

    name: str
    task_ids: tuple[str, ...]
    rollback_available: bool

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")
        if not isinstance(self.task_ids, tuple):
            raise TypeError("task_ids must be a tuple")
        if not isinstance(self.rollback_available, bool):
            raise TypeError("rollback_available must be a bool")


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringSimulationReport:
    """The final artifact produced by the PlanSimulator."""

    status: SimulationStatus
    impact: SimulationImpact
    timeline: SimulationTimeline
    checkpoints: tuple[SimulationCheckpoint, ...] = ()
    warnings: tuple[str, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, SimulationStatus):
            raise TypeError("status must be a SimulationStatus")
        if not isinstance(self.impact, SimulationImpact):
            raise TypeError("impact must be a SimulationImpact")
        if not isinstance(self.timeline, SimulationTimeline):
            raise TypeError("timeline must be a SimulationTimeline")
        if not isinstance(self.checkpoints, tuple):
            raise TypeError("checkpoints must be a tuple")
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple")
        if not isinstance(self.summary, str):
            raise TypeError("summary must be a str")
