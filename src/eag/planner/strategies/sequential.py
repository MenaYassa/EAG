"""Sequential planning strategy for EAG."""

from datetime import timedelta

from eag.planner.enums import GoalType, PlanState, RiskLevel
from eag.planner.errors import InvalidGoalError
from eag.planner.intelligence.models import (
    EngineeringGoal,
    EngineeringOperation,
    EngineeringPlanningArtifact,
)
from eag.planner.intelligence.pipeline import EngineeringIntelligencePipeline
from eag.planner.models import (
    EngineeringTask,
    ExecutionAction,
    ExecutionPlan,
    ExecutionStep,
    PlanningContext,
    PlanningStatistics,
    PlanningStrategyInfo,
)


class SequentialStrategy:
    """A deterministic, sequential planning strategy.

    This strategy delegates all engineering reasoning (decomposition,
    dependency resolution, risk analysis, effort estimation) to the
    EngineeringIntelligencePipeline and consumes the resulting artifact.
    """

    def __init__(self) -> None:
        self.name = "Sequential"
        self.priority = 100

    _SUPPORTED_GOALS = (
        GoalType.REFACTOR,
        GoalType.BUGFIX,
        GoalType.FEATURE,
        GoalType.ANALYSIS,
    )

    _SUPPORTED_OPS = (
        EngineeringOperation.REFACTOR,
        EngineeringOperation.FIX,
        EngineeringOperation.CREATE,
        EngineeringOperation.ANALYZE,
    )

    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(
            name=self.name,
            description="A deterministic, step-by-step engineering strategy.",
            priority=self.priority,
            supported_goal_types=self._SUPPORTED_GOALS,
            supports_parallelism=False,
            experimental=False,
        )

    def supports(self, eng_goal: EngineeringGoal, context: PlanningContext) -> bool:
        # Validate both the underlying goal type and the engineering operation
        planning_goal = getattr(eng_goal, "planning_goal", None)
        if not planning_goal:
            return False

        goal_type_supported = planning_goal.goal_type in self._SUPPORTED_GOALS
        operation_supported = getattr(eng_goal, "operation", None) in self._SUPPORTED_OPS

        return goal_type_supported and operation_supported

    def estimate_risk(self, eng_goal: EngineeringGoal, context: PlanningContext) -> RiskLevel:
        """Determine overall risk using the intelligence pipeline."""
        artifact = EngineeringIntelligencePipeline().analyze(eng_goal)
        return artifact.risk.overall_risk

    def estimate_duration(self, eng_goal: EngineeringGoal, context: PlanningContext) -> timedelta:
        """Estimate total duration using the intelligence pipeline."""
        artifact = EngineeringIntelligencePipeline().analyze(eng_goal)
        return timedelta(minutes=artifact.execution_profile.total_engineering_time)

    def create_plan(self, eng_goal: EngineeringGoal, context: PlanningContext) -> ExecutionPlan:
        """Generate a deterministic execution plan using the intelligence pipeline."""
        self._validate_goal(eng_goal)

        # Delegate all engineering reasoning to the pipeline
        artifact = EngineeringIntelligencePipeline().analyze(eng_goal)

        steps = self._create_execution_steps(artifact.tasks)
        stats = self._build_statistics(artifact)

        return self._assemble_plan(eng_goal, artifact, steps, stats)

    def _validate_goal(self, eng_goal: EngineeringGoal) -> None:
        if not self.supports(eng_goal, PlanningContext()):
            operation = getattr(eng_goal, "operation", "UNKNOWN")
            title = "Unknown Goal"
            planning_goal = getattr(eng_goal, "planning_goal", None)
            if planning_goal:
                title = getattr(planning_goal, "title", title)

            raise InvalidGoalError(
                f"SequentialStrategy does not support operation: {operation}",
                goal=title,
            )

    def _create_execution_steps(
        self, tasks: tuple[EngineeringTask, ...]
    ) -> tuple[ExecutionStep, ...]:
        """Create a generic execution step for each task."""
        steps = []
        for i, task in enumerate(tasks, start=1):
            action = ExecutionAction(
                id=f"action-{i}",
                kind="ExecuteTask",
                target=task.title,
            )
            step = ExecutionStep(
                id=f"step-{i}",
                task_id=task.id,
                action=action,
                description=f"Execute: {task.title}",
            )
            steps.append(step)
        return tuple(steps)

    def _build_statistics(self, artifact: EngineeringPlanningArtifact) -> PlanningStatistics:
        """Build planning statistics from the artifact."""
        risk = artifact.risk.overall_risk
        risk_map = {
            RiskLevel.NONE: 0.0,
            RiskLevel.LOW: 0.25,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.75,
            RiskLevel.CRITICAL: 1.0,
        }
        return PlanningStatistics(
            task_count=len(artifact.tasks),
            step_count=len(artifact.tasks),  # 1:1 mapping in this strategy
            estimated_minutes=artifact.execution_profile.total_engineering_time,
            risk_score=risk_map.get(risk, 0.0),
        )

    def _assemble_plan(
        self,
        eng_goal: EngineeringGoal,
        artifact: EngineeringPlanningArtifact,
        steps: tuple[ExecutionStep, ...],
        stats: PlanningStatistics,
    ) -> ExecutionPlan:
        """Assemble the final ExecutionPlan from the artifact and computed data."""
        return ExecutionPlan(
            id=f"plan-{eng_goal.planning_goal.id}",
            goal=artifact.goal,
            tasks=artifact.tasks,
            steps=steps,
            risk=artifact.risk.overall_risk,
            state=PlanState.VALIDATED,
            statistics=stats,
            strategy=self.info.name,
            risk_assessment=artifact.risk,
            execution_profile=artifact.execution_profile,
        )
