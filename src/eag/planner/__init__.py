"""Engineering Planning Platform — domain vocabulary, models, errors, and events."""

# ------------------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------------------
from eag.planner.enums import (
    ExecutionMode,
    GoalType,
    PlannerRuntimeState,
    PlanState,
    RiskLevel,
    TaskPriority,
)
from eag.planner.enums import (
    PlanningStrategy as PlanningStrategyType,  # enum (renamed to avoid clash)
)

# ------------------------------------------------------------------------------
# Errors
# ------------------------------------------------------------------------------
from eag.planner.errors import (
    ApprovalRequiredError,
    DependencyCycleError,
    DuplicatePlanningStrategyError,
    DuplicateTaskError,
    InvalidGoalError,
    PlanGenerationError,
    PlannerError,
    PlanningExecutionError,
    PlanningStrategyError,
    PlanningStrategyNotFoundError,
    PlanningStrategyUnavailableError,
    PlanningValidationError,
    UnknownDependencyError,
    UnsafePlanError,
)

# ------------------------------------------------------------------------------
# Events
# ------------------------------------------------------------------------------
from eag.planner.events import (
    PlanGenerated,
    PlanningCompleted,
    PlanningFailed,
    PlanningStarted,
    StrategySelected,
)

# ------------------------------------------------------------------------------
# Intelligence
# ------------------------------------------------------------------------------
from eag.planner.intelligence import (
    EffortEstimator,
    EngineeringComplexity,
    EngineeringExecutionProfile,
    EngineeringGoal,
    EngineeringIntelligencePipeline,
    EngineeringOperation,
    EngineeringPlanningArtifact,
    EngineeringRiskAssessment,
    EngineeringRiskFactor,
    EngineeringScope,
    GoalAnalyzer,
    RiskAnalyzer,
    TaskDecomposer,
    TaskDependencyGraph,
    TaskDependencyNode,
    TaskDependencyResolver,
    TaskDependencyStatistics,
)

# ------------------------------------------------------------------------------
# Core models
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Registry, Runtime, and Strategies
# ------------------------------------------------------------------------------
from eag.planner.registry import PlanningStrategyRegistry
from eag.planner.runtime import PlannerRuntime
from eag.planner.strategies import SequentialStrategy
from eag.planner.strategy import PlanningStrategy  # base class (not the enum)

# ------------------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------------------
__all__ = [
    # Enums
    "ExecutionMode",
    "GoalType",
    "PlanState",
    "PlannerRuntimeState",
    "PlanningStrategyType",  # the enum (renamed)
    "RiskLevel",
    "TaskPriority",
    # Errors
    "ApprovalRequiredError",
    "DependencyCycleError",
    "DuplicatePlanningStrategyError",
    "DuplicateTaskError",
    "InvalidGoalError",
    "PlanGenerationError",
    "PlannerError",
    "PlanningExecutionError",
    "PlanningStrategyError",
    "PlanningStrategyNotFoundError",
    "PlanningStrategyUnavailableError",
    "PlanningValidationError",
    "UnknownDependencyError",
    "UnsafePlanError",
    # Events
    "PlanGenerated",
    "PlanningCompleted",
    "PlanningFailed",
    "PlanningStarted",
    "StrategySelected",
    # Intelligence
    "EffortEstimator",
    "EngineeringComplexity",
    "EngineeringExecutionProfile",
    "EngineeringGoal",
    "EngineeringIntelligencePipeline",
    "EngineeringOperation",
    "EngineeringPlanningArtifact",
    "EngineeringRiskAssessment",
    "EngineeringRiskFactor",
    "EngineeringScope",
    "GoalAnalyzer",
    "RiskAnalyzer",
    "TaskDecomposer",
    "TaskDependencyGraph",
    "TaskDependencyNode",
    "TaskDependencyResolver",
    "TaskDependencyStatistics",
    # Core models
    "EngineeringTask",
    "ExecutionAction",
    "ExecutionPlan",
    "ExecutionStep",
    "PlanningContext",
    "PlanningGoal",
    "PlanningResult",
    "PlanningRuntimeHealth",
    "PlanningRuntimeMetrics",
    "PlanningStatistics",
    "PlanningStrategyInfo",
    # Registry / Runtime / Strategies
    "PlanningStrategyRegistry",
    "PlannerRuntime",
    "SequentialStrategy",
    "PlanningStrategy",  # base class
]
