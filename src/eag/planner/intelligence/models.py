"""Engineering Intelligence domain models for EAG."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from eag.planner.enums import RiskLevel
from eag.planner.errors import DependencyCycleError
from eag.planner.models import EngineeringTask, PlanningGoal, _validate_str_tuple


class EngineeringOperation(StrEnum):
    """Deterministic engineering operations."""

    ANALYZE = "analyze"
    CREATE = "create"
    DELETE = "delete"
    DOCUMENT = "document"
    EXTRACT = "extract"
    FIX = "fix"
    MOVE = "move"
    RENAME = "rename"
    REFACTOR = "refactor"
    TEST = "test"
    UPGRADE = "upgrade"


class EngineeringComplexity(StrEnum):
    """Complexity levels for engineering work."""

    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class EngineeringScope(StrEnum):
    """The blast radius or scope of an engineering operation."""

    SYMBOL = "symbol"
    FILE = "file"
    MODULE = "module"
    PACKAGE = "package"
    REPOSITORY = "repository"
    SYSTEM = "system"


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringGoal:
    """The deterministic, machine-readable representation of a user's goal.

    This enriches the original PlanningGoal with strict engineering semantics,
    allowing strategies to reason over operations rather than natural language.
    """

    planning_goal: PlanningGoal
    operation: EngineeringOperation
    target: str
    complexity: EngineeringComplexity
    scope: EngineeringScope
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.planning_goal, PlanningGoal):
            raise TypeError("planning_goal must be a PlanningGoal")
        if not isinstance(self.operation, EngineeringOperation):
            raise TypeError("operation must be an EngineeringOperation")
        if not isinstance(self.target, str) or not self.target.strip():
            raise ValueError("target cannot be empty or whitespace")
        if not isinstance(self.complexity, EngineeringComplexity):
            raise TypeError("complexity must be an EngineeringComplexity")
        if not isinstance(self.scope, EngineeringScope):
            raise TypeError("scope must be an EngineeringScope")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be a float")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDependencyStatistics:
    """Statistics about the task dependency graph."""

    task_count: int = 0
    edge_count: int = 0
    root_count: int = 0
    leaf_count: int = 0
    maximum_depth: int = 0
    independent_tasks: int = 0
    cyclic: bool = False

    def __post_init__(self) -> None:
        fields = (
            "task_count",
            "edge_count",
            "root_count",
            "leaf_count",
            "maximum_depth",
            "independent_tasks",
        )
        for field_name in fields:
            val = getattr(self, field_name)
            if not isinstance(val, int) or isinstance(val, bool) or val < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if not isinstance(self.cyclic, bool):
            raise TypeError("cyclic must be a bool")


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDependencyNode:
    """A node in the task dependency graph."""

    task: EngineeringTask
    incoming: tuple[str, ...] = ()  # Tasks that depend on this task (successors)
    outgoing: tuple[str, ...] = ()  # Tasks this task depends on (predecessors)

    def __post_init__(self) -> None:
        if not isinstance(self.task, EngineeringTask):
            raise TypeError("task must be an EngineeringTask")
        object.__setattr__(self, "incoming", _validate_str_tuple(self.incoming, "incoming"))
        object.__setattr__(self, "outgoing", _validate_str_tuple(self.outgoing, "outgoing"))


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDependencyGraph:
    """An immutable, validated directed acyclic graph of engineering tasks."""

    nodes: Mapping[str, TaskDependencyNode]
    statistics: TaskDependencyStatistics

    def __post_init__(self) -> None:
        if not isinstance(self.nodes, Mapping):
            raise TypeError("nodes must be a Mapping")
        if not isinstance(self.statistics, TaskDependencyStatistics):
            raise TypeError("statistics must be a TaskDependencyStatistics")
        object.__setattr__(self, "nodes", MappingProxyType(dict(self.nodes)))

    def ordered_tasks(self) -> tuple[EngineeringTask, ...]:
        """Return tasks in topologically sorted order (Kahn's algorithm)."""
        import heapq

        in_degree = {task_id: len(node.outgoing) for task_id, node in self.nodes.items()}
        queue = [task_id for task_id, deg in in_degree.items() if deg == 0]
        heapq.heapify(queue)

        sorted_order = []
        while queue:
            current_id = heapq.heappop(queue)
            sorted_order.append(current_id)

            node = self.nodes[current_id]
            for succ_id in node.incoming:
                in_degree[succ_id] -= 1
                if in_degree[succ_id] == 0:
                    heapq.heappush(queue, succ_id)

        if len(sorted_order) != len(self.nodes):
            raise DependencyCycleError("Cycle detected during topological sort")

        return tuple(self.nodes[tid].task for tid in sorted_order)

    def roots(self) -> tuple[EngineeringTask, ...]:
        """Return tasks with no dependencies (starting points)."""
        return tuple(node.task for node in self.nodes.values() if not node.outgoing)

    def leaves(self) -> tuple[EngineeringTask, ...]:
        """Return tasks with no dependents (final steps)."""
        return tuple(node.task for node in self.nodes.values() if not node.incoming)


class EngineeringRiskFactor(StrEnum):
    """Deterministic reasons contributing to engineering risk."""

    LARGE_SCOPE = "large_scope"
    MANY_DEPENDENCIES = "many_dependencies"
    DELETE_OPERATION = "delete_operation"
    REFACTOR = "refactor"
    INFRASTRUCTURE = "infrastructure"
    TESTING_ONLY = "testing_only"
    DOCUMENTATION_ONLY = "documentation_only"
    ANALYSIS_ONLY = "analysis_only"


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringRiskAssessment:
    """A rich, explainable assessment of engineering risk."""

    overall_risk: RiskLevel
    confidence: float = 1.0
    scope_risk: RiskLevel = RiskLevel.NONE
    change_risk: RiskLevel = RiskLevel.NONE
    graph_risk: RiskLevel = RiskLevel.NONE
    dependency_risk: RiskLevel = RiskLevel.NONE
    factors: tuple[EngineeringRiskFactor, ...] = ()
    requires_approval: bool = False
    rollback_complexity: EngineeringComplexity = EngineeringComplexity.LOW
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.overall_risk, RiskLevel):
            raise TypeError("overall_risk must be a RiskLevel")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be a float")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not isinstance(self.factors, tuple):
            raise TypeError("factors must be a tuple")
        for f in self.factors:
            if not isinstance(f, EngineeringRiskFactor):
                raise TypeError("factors must contain EngineeringRiskFactor instances")
        if not isinstance(self.requires_approval, bool):
            raise TypeError("requires_approval must be a bool")
        if not isinstance(self.rollback_complexity, EngineeringComplexity):
            raise TypeError("rollback_complexity must be an EngineeringComplexity")
        if not isinstance(self.summary, str):
            raise TypeError("summary must be a str")


# ---------- Validation helpers (copied from models.py to avoid circular import) ----------
def _validate_non_negative_float(value: float, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")
    return float(value)


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


# ---------- The moved EngineeringExecutionProfile ----------
@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringExecutionProfile:
    """A rich, deterministic profile of engineering effort and execution metrics."""

    total_engineering_time: float
    critical_path_duration: float
    parallel_savings: float
    estimated_active_work: float
    estimated_validation: float
    estimated_review: float
    confidence: float
    summary: str

    def __post_init__(self) -> None:
        for field_name in [
            "total_engineering_time",
            "critical_path_duration",
            "parallel_savings",
            "estimated_active_work",
            "estimated_validation",
            "estimated_review",
        ]:
            val = getattr(self, field_name)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or val < 0:
                raise ValueError(f"{field_name} must be a non-negative number")

        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be a float")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not isinstance(self.summary, str):
            raise TypeError("summary must be a str")


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringPlanningArtifact:
    """The canonical handoff object between the Intelligence Layer and the Planning Layer.

    Encapsulates all intermediate engineering artifacts produced by the intelligence
    pipeline, allowing strategies, dashboards, and future AI to consume them
    without knowing how they were produced.
    """

    goal: PlanningGoal
    engineering_goal: EngineeringGoal
    tasks: tuple[EngineeringTask, ...]
    graph: TaskDependencyGraph
    risk: EngineeringRiskAssessment
    execution_profile: EngineeringExecutionProfile

    def __post_init__(self) -> None:
        if not isinstance(self.goal, PlanningGoal):
            raise TypeError("goal must be a PlanningGoal")
        if not isinstance(self.engineering_goal, EngineeringGoal):
            raise TypeError("engineering_goal must be an EngineeringGoal")
        if not isinstance(self.tasks, tuple):
            raise TypeError("tasks must be a tuple")
        if not isinstance(self.graph, TaskDependencyGraph):
            raise TypeError("graph must be a TaskDependencyGraph")
        if not isinstance(self.risk, EngineeringRiskAssessment):
            raise TypeError("risk must be an EngineeringRiskAssessment")
        if not isinstance(self.execution_profile, EngineeringExecutionProfile):
            raise TypeError("execution_profile must be an EngineeringExecutionProfile")
