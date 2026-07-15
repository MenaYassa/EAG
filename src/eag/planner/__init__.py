"""Engineering Planning Platform — domain vocabulary, models, errors, and events."""

from eag.planner.enums import (
    ExecutionMode,
    GoalType,
    PlannerRuntimeState,
    PlanningStrategy,
    PlanState,
    RiskLevel,
    TaskPriority,
)
from eag.planner.errors import (
    ApprovalRequiredError,
    DuplicatePlanningStrategyError,
    InvalidGoalError,
    PlanGenerationError,
    PlannerError,
    PlanningExecutionError,
    PlanningStrategyError,
    PlanningStrategyNotFoundError,
    PlanningStrategyUnavailableError,
    PlanningValidationError,
    UnsafePlanError,
)
from eag.planner.events import (
    GoalValidated,
    PlanGenerated,
    PlanningCompleted,
    PlanningFailed,
    PlanningStarted,
    PlanValidated,
    StrategySelected,
)
from eag.planner.models import (
    EngineeringTask,
    ExecutionAction,
    ExecutionPlan,
    ExecutionStep,
    PlanningContext,
    PlanningGoal,
    PlanningResult,
    PlanningRuntimeHealth,
    PlanningRuntimeMetrics,
    PlanningStatistics,
    PlanningStrategyInfo,
)
from eag.planner.registry import PlanningStrategyRegistry
from eag.planner.runtime import PlannerRuntime
from eag.planner.strategies import SequentialStrategy
from eag.planner.strategy import PlanningStrategy as IPlanningStrategy

__all__ = [
    # Enums
    "ExecutionMode",
    "GoalType",
    "PlanState",
    "PlanningStrategy",
    "RiskLevel",
    "TaskPriority",
    # Errors
    "ApprovalRequiredError",
    "DuplicatePlanningStrategyError",
    "InvalidGoalError",
    "PlanGenerationError",
    "PlannerError",
    "PlanningExecutionError",
    "PlanningStrategyError",
    "PlanningStrategyNotFoundError",
    "PlanningStrategyUnavailableError",
    "PlanningValidationError",
    "UnsafePlanError",
    # Events
    "GoalValidated",
    "PlanGenerated",
    "PlanValidated",
    "PlanningCompleted",
    "PlanningFailed",
    "PlanningStarted",
    "StrategySelected",
    # Models
    "EngineeringTask",
    "ExecutionAction",
    "ExecutionPlan",
    "ExecutionStep",
    "PlanningContext",
    "PlanningGoal",
    "PlanningResult",
    "PlanningStatistics",
    "PlanningStrategyInfo",
    "PlanningRuntimeHealth",
    "PlanningRuntimeMetrics",
    "PlannerRuntimeState",
    # Registry & Strategy
    "PlanningStrategyRegistry",
    "IPlanningStrategy",
    "SequentialStrategy",
    # Runtime
    "PlannerRuntime",
]
