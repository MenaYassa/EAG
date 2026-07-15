"""Tests for the planning domain models."""

from dataclasses import FrozenInstanceError

import pytest

from eag.planner.enums import (
    ExecutionMode,
    GoalType,
    PlanningStrategy,
    PlanState,
    RiskLevel,
    TaskPriority,
)
from eag.planner.errors import (
    PlanGenerationError,
    PlannerError,
    PlanningExecutionError,
    PlanningValidationError,
)
from eag.planner.models import (
    EngineeringTask,
    ExecutionAction,
    ExecutionPlan,
    ExecutionStep,
    PlanningContext,
    PlanningGoal,
    PlanningResult,
    PlanningStatistics,
)


class TestPlanningGoal:
    def test_valid_construction(self) -> None:
        goal = PlanningGoal(
            goal_type=GoalType.REFACTOR,
            title="Rename EventBus",
            description="Rename the class everywhere",
        )
        assert goal.goal_type == GoalType.REFACTOR
        assert goal.title == "Rename EventBus"
        assert goal.priority == TaskPriority.NORMAL
        assert isinstance(goal.id, str)

    def test_generated_id_is_unique(self) -> None:
        g1 = PlanningGoal(goal_type=GoalType.FEATURE, title="Goal 1")
        g2 = PlanningGoal(goal_type=GoalType.FEATURE, title="Goal 2")
        assert g1.id != g2.id

    def test_empty_title_raises(self) -> None:
        with pytest.raises(ValueError, match="title cannot be empty"):
            PlanningGoal(goal_type=GoalType.FEATURE, title="")

    def test_invalid_goal_type_raises(self) -> None:
        with pytest.raises(TypeError, match="goal_type must be a GoalType"):
            PlanningGoal(goal_type="refactor", title="Goal")  # type: ignore[arg-type]

    def test_invalid_description_raises(self) -> None:
        with pytest.raises(TypeError, match="description must be a str"):
            PlanningGoal(goal_type=GoalType.FEATURE, title="Goal", description=123)  # type: ignore[arg-type]

    def test_immutability(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.FEATURE, title="Goal")
        # Fix B017: Intercept the specific dataclass FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            goal.title = "New Title"  # type: ignore[misc]

    def test_hashable(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.FEATURE, title="Goal")
        assert hash(goal) is not None


class TestEngineeringTask:
    def test_valid_construction(self) -> None:
        task = EngineeringTask(
            title="Locate Symbol",
            priority=TaskPriority.HIGH,
            estimated_duration=1.5,
            dependencies=("t1", "t2"),
        )
        assert task.title == "Locate Symbol"
        assert task.priority == TaskPriority.HIGH
        assert task.estimated_duration == 1.5
        assert task.dependencies == ("t1", "t2")

    def test_empty_title_raises(self) -> None:
        with pytest.raises(ValueError, match="title cannot be empty"):
            EngineeringTask(title="   ")

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="estimated_duration must be a non-negative number"):
            EngineeringTask(title="Task", estimated_duration=-1.0)

    def test_invalid_dependencies_raises(self) -> None:
        with pytest.raises(TypeError, match="dependencies must be a tuple"):
            EngineeringTask(title="Task", dependencies="t1")  # type: ignore[arg-type]


class TestExecutionAction:
    def test_valid_construction(self) -> None:
        action = ExecutionAction(
            kind="RunCommand",
            target="pytest",
            parameters={"verbose": "true"},
        )
        assert action.kind == "RunCommand"
        assert action.target == "pytest"
        assert action.parameters["verbose"] == "true"

    def test_empty_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="kind cannot be empty"):
            ExecutionAction(kind="", target="pytest")


class TestExecutionStep:
    def test_valid_construction(self) -> None:
        action = ExecutionAction(kind="RunCommand", target="pytest")
        step = ExecutionStep(
            task_id="task-1",
            action=action,
            description="Run tests",
            expected_result="All pass",
        )
        assert step.task_id == "task-1"
        assert step.action == action

    def test_empty_task_id_raises(self) -> None:
        action = ExecutionAction(kind="RunCommand", target="pytest")
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            ExecutionStep(task_id="", action=action)

    def test_invalid_action_raises(self) -> None:
        with pytest.raises(TypeError, match="action must be an ExecutionAction"):
            ExecutionStep(task_id="t1", action="not-an-action")  # type: ignore[arg-type]


class TestPlanningStatistics:
    def test_defaults(self) -> None:
        stats = PlanningStatistics()
        assert stats.task_count == 0
        assert stats.step_count == 0
        assert stats.estimated_minutes == 0.0
        assert stats.risk_score == 0.0

    def test_negative_task_count_raises(self) -> None:
        with pytest.raises(ValueError, match="task_count must be a non-negative integer"):
            PlanningStatistics(task_count=-1)

    def test_negative_risk_score_raises(self) -> None:
        with pytest.raises(ValueError, match="risk_score must be a non-negative number"):
            PlanningStatistics(risk_score=-0.5)


class TestExecutionPlan:
    def test_valid_construction(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        plan = ExecutionPlan(goal=goal)
        assert plan.goal == goal
        assert plan.tasks == ()
        assert plan.steps == ()
        assert plan.risk == RiskLevel.NONE
        assert plan.state == PlanState.CREATED

    def test_invalid_goal_raises(self) -> None:
        with pytest.raises(TypeError, match="goal must be a PlanningGoal"):
            ExecutionPlan(goal="not-a-goal")  # type: ignore[arg-type]

    def test_invalid_tasks_type_raises(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        with pytest.raises(TypeError, match="tasks must be a tuple"):
            ExecutionPlan(goal=goal, tasks=[])  # type: ignore[arg-type]

    def test_invalid_tasks_item_raises(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        with pytest.raises(TypeError, match="tasks items must be of type EngineeringTask"):
            ExecutionPlan(goal=goal, tasks=("not-a-task",))  # type: ignore[arg-type]

    # Append inside class TestExecutionPlan:

    def test_is_executable_true_for_approved(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        plan = ExecutionPlan(goal=goal, state=PlanState.APPROVED)
        assert plan.is_executable is True

    def test_is_executable_true_for_validated(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        plan = ExecutionPlan(goal=goal, state=PlanState.VALIDATED)
        assert plan.is_executable is True

    def test_is_executable_false_for_rejected(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        plan = ExecutionPlan(goal=goal, state=PlanState.REJECTED)
        assert plan.is_executable is False

    def test_is_executable_false_for_cancelled(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        plan = ExecutionPlan(goal=goal, state=PlanState.CANCELLED)
        assert plan.is_executable is False

    def test_is_executable_false_for_failed(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        plan = ExecutionPlan(goal=goal, state=PlanState.FAILED)
        assert plan.is_executable is False

    def test_is_executable_false_for_created(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        plan = ExecutionPlan(goal=goal, state=PlanState.CREATED)
        assert plan.is_executable is False


class TestPlanningResult:
    def test_valid_construction(self) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename")
        plan = ExecutionPlan(goal=goal)
        result = PlanningResult(plan=plan, warnings=("dep1",), risk=RiskLevel.LOW)
        assert result.plan == plan
        assert result.warnings == ("dep1",)
        assert result.risk == RiskLevel.LOW

    def test_invalid_plan_raises(self) -> None:
        with pytest.raises(TypeError, match="plan must be an ExecutionPlan"):
            PlanningResult(plan="not-a-plan")  # type: ignore[arg-type]


class TestErrors:
    def test_hierarchy(self) -> None:
        assert issubclass(PlanningValidationError, PlannerError)
        assert issubclass(PlanGenerationError, PlannerError)
        assert issubclass(PlanningExecutionError, PlannerError)


class TestPlanningContext:
    def test_defaults(self) -> None:
        ctx = PlanningContext()
        assert ctx.execution_mode == ExecutionMode.DRY_RUN
        assert ctx.strategy == PlanningStrategy.SAFE
        assert ctx.repository is None

    def test_immutability(self) -> None:
        ctx = PlanningContext()
        # Fix B017: Intercept the specific dataclass FrozenInstanceError instead of broad Exception
        with pytest.raises(FrozenInstanceError):
            ctx.strategy = PlanningStrategy.FAST  # type: ignore[misc]

    def test_invalid_execution_mode_raises(self) -> None:
        with pytest.raises(TypeError, match="execution_mode must be an ExecutionMode"):
            PlanningContext(execution_mode="dry_run")  # type: ignore[arg-type]
