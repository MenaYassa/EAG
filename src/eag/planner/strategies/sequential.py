"""Sequential planning strategy for EAG."""

from datetime import timedelta

from eag.planner.enums import GoalType, PlanState, RiskLevel
from eag.planner.errors import InvalidGoalError
from eag.planner.intelligence.models import (
    EngineeringGoal,
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
    """A deterministic, step-by-step sequential planning strategy."""

    def __init__(self) -> None:
        self.name = "Sequential"
        self.priority = 100

    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(
            name="Sequential",
            description="A deterministic, step-by-step engineering strategy.",
            priority=100,
            supported_goal_types=tuple(GoalType),
            supports_parallelism=False,
            experimental=False,
        )

    def supports(self, eng_goal: EngineeringGoal, context: PlanningContext) -> bool:
        planning_goal = getattr(eng_goal, "planning_goal", None)
        if not planning_goal:
            return True

        # Explicitly deny MAINTENANCE goal types
        return bool(planning_goal.goal_type != GoalType.MAINTENANCE)

    def estimate_risk(self, eng_goal: EngineeringGoal, context: PlanningContext) -> RiskLevel:
        planning_goal = getattr(eng_goal, "planning_goal", None)
        if planning_goal:
            if planning_goal.goal_type == GoalType.REFACTOR:
                return RiskLevel.MEDIUM
            if planning_goal.goal_type == GoalType.BUGFIX:
                return RiskLevel.LOW
            if planning_goal.goal_type == GoalType.ANALYSIS:
                return RiskLevel.NONE
        try:
            artifact = EngineeringIntelligencePipeline().analyze(eng_goal)
            return artifact.risk.overall_risk
        except Exception:
            return RiskLevel.MEDIUM

    def estimate_duration(self, eng_goal: EngineeringGoal, context: PlanningContext) -> timedelta:
        if not self.supports(eng_goal, context):
            return timedelta(0)
        try:
            artifact = EngineeringIntelligencePipeline().analyze(eng_goal)
            return timedelta(minutes=artifact.execution_profile.total_engineering_time)
        except Exception:
            return timedelta(minutes=60)

    def create_plan(self, eng_goal: EngineeringGoal, context: PlanningContext) -> ExecutionPlan:
        """Generate a deterministic execution plan."""
        self._validate_goal(eng_goal)

        # Delegate engineering reasoning to the intelligence pipeline
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
        steps = []
        for i, task in enumerate(tasks, start=1):
            action = ExecutionAction(id=f"action-{i}", kind="ExecuteTask", target=task.title)
            step = ExecutionStep(
                id=f"step-{i}", task_id=task.id, action=action, description=f"Execute: {task.title}"
            )
            steps.append(step)
        return tuple(steps)

    def _build_statistics(self, artifact: EngineeringPlanningArtifact) -> PlanningStatistics:
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
            step_count=len(artifact.tasks),
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
        return ExecutionPlan(
            id=f"plan-{eng_goal.planning_goal.id}",
            goal=artifact.goal,
            tasks=artifact.tasks,
            steps=steps,
            risk=self.estimate_risk(eng_goal, PlanningContext()),
            state=PlanState.VALIDATED,
            statistics=stats,
            strategy=self.info.name,
            risk_assessment=artifact.risk,
            execution_profile=artifact.execution_profile,
        )
