"""Sequential planning strategy for EAG."""

from datetime import timedelta

from eag.planner.enums import GoalType, PlanState, RiskLevel
from eag.planner.errors import InvalidGoalError
from eag.planner.models import (
    EngineeringTask,
    ExecutionAction,
    ExecutionPlan,
    ExecutionStep,
    PlanningContext,
    PlanningGoal,
    PlanningStatistics,
    PlanningStrategyInfo,
)


class SequentialStrategy:
    """A deterministic, sequential planning strategy.

    This strategy serves as the reference implementation for engineering
    planning. It converts any supported goal into a standard 5-phase
    engineering workflow: Locate, Analyze, Modify, Update, Validate.
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

    def supports(self, goal: PlanningGoal, context: PlanningContext) -> bool:
        return goal.goal_type in self._SUPPORTED_GOALS

    def estimate_risk(self, goal: PlanningGoal, context: PlanningContext) -> RiskLevel:
        if goal.goal_type == GoalType.ANALYSIS:
            return RiskLevel.NONE
        if goal.goal_type == GoalType.BUGFIX:
            return RiskLevel.LOW
        if goal.goal_type in (GoalType.FEATURE, GoalType.REFACTOR):
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    def estimate_duration(self, goal: PlanningGoal, context: PlanningContext) -> timedelta:
        # Estimate based on the standard 5-task workflow (2.5 minutes)
        return timedelta(minutes=2.5)

    def create_plan(self, goal: PlanningGoal, context: PlanningContext) -> ExecutionPlan:
        """Generate a deterministic execution plan.

        The pipeline is strictly ordered:
        1. Analyze Goal
        2. Build Tasks
        3. Order Tasks
        4. Build Execution Steps
        5. Build Statistics
        6. Assemble Plan
        """
        # Phase 1: Analyze Goal
        self._analyze_goal(goal)

        # Phase 2: Build Tasks
        tasks = self._create_tasks(goal)

        # Phase 3: Order Tasks
        ordered_tasks = self._order_tasks(tasks)

        # Phase 4: Build Execution Steps
        steps = self._create_execution_steps(ordered_tasks)

        # Phase 5: Build Statistics
        stats = self._build_statistics(goal, ordered_tasks, steps)

        # Phase 6: Assemble Plan
        return self._assemble_plan(goal, ordered_tasks, steps, stats)

    def _analyze_goal(self, goal: PlanningGoal) -> None:
        """Validate that the strategy can handle the goal."""
        if not self.supports(goal, PlanningContext()):
            raise InvalidGoalError(
                f"SequentialStrategy does not support goal type: {goal.goal_type}",
                goal=goal.title,
            )

    def _create_tasks(self, goal: PlanningGoal) -> list[EngineeringTask]:
        """Create the canonical 5-phase engineering workflow."""
        return [
            EngineeringTask(
                id="task-1",
                title="Locate Target",
                description=f"Locate the target for goal: {goal.title}",
                estimated_duration=0.5,
            ),
            EngineeringTask(
                id="task-2",
                title="Analyze Impact",
                description="Estimate the engineering impact of the changes.",
                dependencies=("task-1",),
                estimated_duration=0.5,
            ),
            EngineeringTask(
                id="task-3",
                title="Apply Changes",
                description="Apply the core modifications.",
                dependencies=("task-2",),
                estimated_duration=1.0,
            ),
            EngineeringTask(
                id="task-4",
                title="Update References",
                description="Update all dependent references.",
                dependencies=("task-3",),
                estimated_duration=0.5,
            ),
            EngineeringTask(
                id="task-5",
                title="Validate Repository",
                description="Run tests and linters to validate changes.",
                dependencies=("task-4",),
                estimated_duration=0.5,
            ),
        ]

    def _order_tasks(self, tasks: list[EngineeringTask]) -> tuple[EngineeringTask, ...]:
        """Order tasks based on dependencies.

        For this simple sequential strategy, creation order is dependency order.
        A real topological sort would go here for complex dependency graphs.
        """
        return tuple(tasks)

    def _create_execution_steps(
        self, tasks: tuple[EngineeringTask, ...]
    ) -> tuple[ExecutionStep, ...]:
        """Expand tasks into concrete execution steps."""
        steps: list[ExecutionStep] = []
        step_counter = 1
        action_counter = 1

        def make_step(task_id: str, desc: str, kind: str, target: str) -> ExecutionStep:
            nonlocal step_counter, action_counter
            action = ExecutionAction(
                id=f"action-{action_counter}",
                kind=kind,
                target=target,
            )
            step = ExecutionStep(
                id=f"step-{step_counter}",
                task_id=task_id,
                action=action,
                description=desc,
            )
            step_counter += 1
            action_counter += 1
            return step

        for task in tasks:
            if task.id == "task-1":
                steps.append(make_step(task.id, "Search for symbol", "SearchSymbol", "repository"))
            elif task.id == "task-2":
                steps.append(
                    make_step(
                        task.id, "Analyze dependency graph", "AnalyzeGraph", "engineering_graph"
                    )
                )
            elif task.id == "task-3":
                steps.append(
                    make_step(task.id, "Modify file contents", "ModifyFile", "target_file")
                )
            elif task.id == "task-4":
                steps.append(
                    make_step(task.id, "Search references", "SearchReferences", "repository")
                )
                steps.append(
                    make_step(task.id, "Update references", "ModifyFile", "dependent_files")
                )
            elif task.id == "task-5":
                steps.append(make_step(task.id, "Run pytest", "RunCommand", "pytest"))
                steps.append(make_step(task.id, "Run ruff", "RunCommand", "ruff check ."))

        return tuple(steps)

    def _build_statistics(
        self,
        goal: PlanningGoal,
        tasks: tuple[EngineeringTask, ...],
        steps: tuple[ExecutionStep, ...],
    ) -> PlanningStatistics:
        """Generate deterministic planning statistics."""
        risk = self.estimate_risk(goal, PlanningContext())
        risk_map = {
            RiskLevel.NONE: 0.0,
            RiskLevel.LOW: 0.25,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.75,
            RiskLevel.CRITICAL: 1.0,
        }

        estimated_minutes = sum(t.estimated_duration for t in tasks)

        return PlanningStatistics(
            task_count=len(tasks),
            step_count=len(steps),
            estimated_minutes=estimated_minutes,
            risk_score=risk_map.get(risk, 0.0),
        )

    def _assemble_plan(
        self,
        goal: PlanningGoal,
        tasks: tuple[EngineeringTask, ...],
        steps: tuple[ExecutionStep, ...],
        stats: PlanningStatistics,
    ) -> ExecutionPlan:
        """Assemble the final execution plan."""
        return ExecutionPlan(
            id=f"plan-{goal.id}",
            goal=goal,
            tasks=tasks,
            steps=steps,
            risk=self.estimate_risk(goal, PlanningContext()),
            state=PlanState.VALIDATED,
            statistics=stats,
            strategy=self.info.name,  # Add this line
        )
