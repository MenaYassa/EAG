"""Tests for the planning domain errors."""

import pytest

from eag.planner.errors import (
    ApprovalRequiredError,
    InvalidGoalError,
    PlanGenerationError,
    PlannerError,
    PlanningExecutionError,
    PlanningStrategyError,
    PlanningValidationError,
    UnsafePlanError,
)


class TestPlannerErrorsHierarchy:
    def test_all_inherit_from_planner_error(self) -> None:
        assert issubclass(PlanningValidationError, PlannerError)
        assert issubclass(InvalidGoalError, PlannerError)
        assert issubclass(PlanningStrategyError, PlannerError)
        assert issubclass(PlanGenerationError, PlannerError)
        assert issubclass(UnsafePlanError, PlannerError)
        assert issubclass(ApprovalRequiredError, PlannerError)
        assert issubclass(PlanningExecutionError, PlannerError)

    def test_invalid_goal_is_validation_error(self) -> None:
        assert issubclass(InvalidGoalError, PlanningValidationError)


class TestPlannerErrorsContext:
    def test_planner_error_carries_context(self) -> None:
        err = InvalidGoalError(
            "Target symbol not found",
            goal="Rename EventBus",
            metadata={"symbol": "EventBus"},
        )
        assert err.message == "Target symbol not found"
        assert err.goal == "Rename EventBus"
        assert err.metadata["symbol"] == "EventBus"

    def test_to_dict_serialization(self) -> None:
        err = UnsafePlanError(
            "Cannot delete src/",
            goal="Delete src/",
            metadata={"path": "src/"},
        )
        d = err.to_dict()
        assert d["error"] == "UnsafePlanError"
        assert d["message"] == "Cannot delete src/"
        assert d["goal"] == "Delete src/"
        assert d["metadata"]["path"] == "src/"

    def test_default_metadata_is_empty_dict(self) -> None:
        err = PlanGenerationError("Missing graph")
        assert err.metadata == {}
        assert err.goal is None


class TestPlannerErrorsRaising:
    def test_raise_and_catch_base(self) -> None:
        with pytest.raises(PlannerError) as exc_info:
            raise InvalidGoalError("bad goal")
        assert isinstance(exc_info.value, PlanningValidationError)

    def test_raise_and_catch_unsafe(self) -> None:
        with pytest.raises(UnsafePlanError) as exc_info:
            raise UnsafePlanError("too risky")
        assert "too risky" in str(exc_info.value)
