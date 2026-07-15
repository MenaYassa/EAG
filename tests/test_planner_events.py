"""Tests for the planning domain events."""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from eag.planner.enums import GoalType, RiskLevel
from eag.planner.events import (
    PlanGenerated,
    PlanningFailed,
    PlanningStarted,
    PlanValidated,
    StrategySelected,
)


class TestPlanningEvents:
    def test_planning_started(self) -> None:
        event = PlanningStarted(goal_id="g1", goal_type=GoalType.REFACTOR)
        assert event.goal_id == "g1"
        assert event.goal_type == GoalType.REFACTOR
        assert event.plan_id is None
        assert event.strategy is None
        assert isinstance(event.timestamp, datetime)

    def test_strategy_selected(self) -> None:
        event = StrategySelected(goal_id="g1", strategy="SAFE")
        assert event.strategy == "SAFE"
        assert event.goal_id == "g1"

    def test_plan_generated(self) -> None:
        event = PlanGenerated(
            goal_id="g1",
            plan_id="p1",
            strategy="FAST",
            task_count=5,
            step_count=10,
            risk=RiskLevel.LOW,
        )
        assert event.plan_id == "p1"
        assert event.task_count == 5
        assert event.strategy == "FAST"

    def test_planning_failed(self) -> None:
        event = PlanningFailed(goal_id="g1", error="Graph missing")
        assert event.error == "Graph missing"
        assert event.goal_id == "g1"

    def test_events_are_immutable(self) -> None:
        event = PlanValidated(goal_id="g1", plan_id="p1")
        # Fix B011 & B017: Use pytest.raises to intercept the proper FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            event.plan_id = "p2"  # type: ignore[misc]
