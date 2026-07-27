"""Tests for the planning domain enums.

Sprint 5.1A — cross-cutting structural tests that apply to every
planning enum.  Per-enum detail tests are added in subsequent commits.
"""

from enum import StrEnum

import pytest

from eag.planner.enums import (
    ExecutionMode,
    GoalType,
    PlanningStrategy,
    PlanState,
    RiskLevel,
    TaskPriority,
)

ALL_ENUMS: list[type[StrEnum]] = [
    GoalType,
    PlanState,
    TaskPriority,
    RiskLevel,
    PlanningStrategy,
    ExecutionMode,
]


class TestEnums:
    """Cross-cutting tests that apply to all planning enums."""

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS)
    def test_is_str_enum(self, enum_cls: type[StrEnum]) -> None:
        assert issubclass(enum_cls, StrEnum)

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS)
    def test_values_are_unique(self, enum_cls: type[StrEnum]) -> None:
        values = [member.value for member in enum_cls]
        assert len(values) == len(set(values))

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS)
    def test_serialization_roundtrip(self, enum_cls: type[StrEnum]) -> None:
        for member in enum_cls:
            assert enum_cls(member.value) is member

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS)
    def test_string_conversion(self, enum_cls: type[StrEnum]) -> None:
        for member in enum_cls:
            assert str(member) == member.value

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS)
    def test_all_values_non_empty(self, enum_cls: type[StrEnum]) -> None:
        for member in enum_cls:
            assert member.value

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS)
    def test_member_names_uppercase(self, enum_cls: type[StrEnum]) -> None:
        for member in enum_cls:
            assert member.name == member.name.upper()

    @pytest.mark.parametrize("enum_cls", ALL_ENUMS)
    def test_invalid_value_raises_value_error(self, enum_cls: type[StrEnum]) -> None:
        with pytest.raises(ValueError):
            enum_cls("not-a-valid-enum-value")


# ──────────────────────────────────────────────────────────────────────
# Lifecycle enum detail tests
# ──────────────────────────────────────────────────────────────────────


class TestGoalType:
    """Detailed tests for :class:`GoalType`."""

    def test_expected_members(self) -> None:
        expected = {
            "ANALYSIS",
            "BUGFIX",
            "DOCUMENTATION",
            "FEATURE",
            "INFRASTRUCTURE",
            "MAINTENANCE",
            "REFACTOR",
            "TESTING",
        }
        assert {m.name for m in GoalType} == expected

    def test_member_count(self) -> None:
        assert len(list(GoalType)) == 8

    def test_values(self) -> None:
        assert GoalType.ANALYSIS == "analysis"
        assert GoalType.BUGFIX == "bugfix"
        assert GoalType.DOCUMENTATION == "documentation"
        assert GoalType.FEATURE == "feature"
        assert GoalType.INFRASTRUCTURE == "infrastructure"
        assert GoalType.MAINTENANCE == "maintenance"
        assert GoalType.REFACTOR == "refactor"
        assert GoalType.TESTING == "testing"

    def test_all_values_lowercase(self) -> None:
        for member in GoalType:
            assert member.value == member.value.lower()

    def test_from_string(self) -> None:
        assert GoalType("refactor") is GoalType.REFACTOR
        assert GoalType("feature") is GoalType.FEATURE

    def test_string_conversion(self) -> None:
        assert str(GoalType.REFACTOR) == "refactor"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            GoalType("not-a-goal-type")

    def test_refactor_is_engineering_not_ai(self) -> None:
        """GoalType describes engineering work, never AI prompts."""
        assert "prompt" not in GoalType.REFACTOR.value
        assert "agent" not in GoalType.REFACTOR.value


class TestPlanState:
    """Detailed tests for :class:`PlanState`."""

    def test_expected_members(self) -> None:
        expected = {
            "CREATED",
            "PLANNING",
            "VALIDATED",
            "APPROVED",
            "REJECTED",
            "EXECUTING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }
        assert {m.name for m in PlanState} == expected

    def test_member_count(self) -> None:
        assert len(list(PlanState)) == 9

    def test_values(self) -> None:
        assert PlanState.CREATED == "created"
        assert PlanState.PLANNING == "planning"
        assert PlanState.VALIDATED == "validated"
        assert PlanState.APPROVED == "approved"
        assert PlanState.REJECTED == "rejected"
        assert PlanState.EXECUTING == "executing"
        assert PlanState.COMPLETED == "completed"
        assert PlanState.FAILED == "failed"
        assert PlanState.CANCELLED == "cancelled"

    def test_all_values_lowercase(self) -> None:
        for member in PlanState:
            assert member.value == member.value.lower()

    def test_from_string(self) -> None:
        assert PlanState("approved") is PlanState.APPROVED
        assert PlanState("completed") is PlanState.COMPLETED

    def test_string_conversion(self) -> None:
        assert str(PlanState.VALIDATED) == "validated"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            PlanState("not-a-state")

    def test_has_creation_state(self) -> None:
        """Every plan lifecycle starts with CREATED."""
        assert PlanState.CREATED == "created"

    def test_has_terminal_states(self) -> None:
        """COMPLETED, FAILED, and CANCELLED are terminal."""
        terminal = {PlanState.COMPLETED, PlanState.FAILED, PlanState.CANCELLED}
        assert all(t in list(PlanState) for t in terminal)

    def test_has_rejection_state(self) -> None:
        """Plans can be rejected during validation."""
        assert PlanState.REJECTED == "rejected"

    # Append inside class TestPlanState:

    def test_can_transition_to_valid_paths(self) -> None:
        assert PlanState.CREATED.can_transition_to(PlanState.PLANNING)
        assert PlanState.PLANNING.can_transition_to(PlanState.VALIDATED)
        assert PlanState.VALIDATED.can_transition_to(PlanState.APPROVED)
        assert PlanState.APPROVED.can_transition_to(PlanState.EXECUTING)
        assert PlanState.EXECUTING.can_transition_to(PlanState.COMPLETED)

    def test_can_transition_to_cancelled(self) -> None:
        """Most states can transition to CANCELLED."""
        assert PlanState.CREATED.can_transition_to(PlanState.CANCELLED)
        assert PlanState.PLANNING.can_transition_to(PlanState.CANCELLED)
        assert PlanState.VALIDATED.can_transition_to(PlanState.CANCELLED)
        assert PlanState.APPROVED.can_transition_to(PlanState.CANCELLED)

    def test_cannot_transition_from_terminal_states(self) -> None:
        """Terminal states cannot transition to anything."""
        assert not PlanState.COMPLETED.can_transition_to(PlanState.PLANNING)
        assert not PlanState.FAILED.can_transition_to(PlanState.PLANNING)
        assert not PlanState.CANCELLED.can_transition_to(PlanState.PLANNING)

    def test_cannot_transition_invalid_paths(self) -> None:
        """Invalid forward paths are rejected."""
        assert not PlanState.CREATED.can_transition_to(PlanState.APPROVED)
        assert not PlanState.PLANNING.can_transition_to(PlanState.EXECUTING)
        assert not PlanState.REJECTED.can_transition_to(PlanState.APPROVED)

    def test_can_transition_to_self(self) -> None:
        """Idempotent transitions are allowed."""
        assert PlanState.CREATED.can_transition_to(PlanState.CREATED)
        assert PlanState.COMPLETED.can_transition_to(PlanState.COMPLETED)

    def test_is_terminal_property(self) -> None:
        assert not PlanState.CREATED.is_terminal
        assert not PlanState.PLANNING.is_terminal
        assert PlanState.COMPLETED.is_terminal
        assert PlanState.FAILED.is_terminal
        assert PlanState.CANCELLED.is_terminal


class TestExecutionMode:
    """Detailed tests for :class:`ExecutionMode`."""

    def test_expected_members(self) -> None:
        expected = {"DRY_RUN", "EXECUTE", "SIMULATION"}
        assert {m.name for m in ExecutionMode} == expected

    def test_member_count(self) -> None:
        assert len(list(ExecutionMode)) == 3

    def test_values(self) -> None:
        assert ExecutionMode.DRY_RUN == "dry_run"
        assert ExecutionMode.EXECUTE == "execute"
        assert ExecutionMode.SIMULATION == "simulation"

    def test_all_values_lowercase(self) -> None:
        for member in ExecutionMode:
            assert member.value == member.value.lower()

    def test_from_string(self) -> None:
        assert ExecutionMode("execute") is ExecutionMode.EXECUTE
        assert ExecutionMode("dry_run") is ExecutionMode.DRY_RUN

    def test_string_conversion(self) -> None:
        assert str(ExecutionMode.DRY_RUN) == "dry_run"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            ExecutionMode("force")

    def test_has_dry_run_mode(self) -> None:
        """Dry run allows plan validation without side effects."""
        assert ExecutionMode.DRY_RUN == "dry_run"

    def test_has_execute_mode(self) -> None:
        """Execute mode applies changes through the Execution Runtime."""
        assert ExecutionMode.EXECUTE == "execute"

    def test_has_simulation_mode(self) -> None:
        """Simulation mode exercises the plan against a sandbox."""
        assert ExecutionMode.SIMULATION == "simulation"


# ──────────────────────────────────────────────────────────────────────
# Strategy enum detail tests
# ──────────────────────────────────────────────────────────────────────


class TestTaskPriority:
    """Detailed tests for :class:`TaskPriority`."""

    def test_expected_members(self) -> None:
        expected = {"LOW", "NORMAL", "HIGH", "CRITICAL"}
        assert {m.name for m in TaskPriority} == expected

    def test_member_count(self) -> None:
        assert len(list(TaskPriority)) == 4

    def test_values(self) -> None:
        assert TaskPriority.LOW == "low"
        assert TaskPriority.NORMAL == "normal"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.CRITICAL == "critical"

    def test_all_values_lowercase(self) -> None:
        for member in TaskPriority:
            assert member.value == member.value.lower()

    def test_from_string(self) -> None:
        assert TaskPriority("critical") is TaskPriority.CRITICAL
        assert TaskPriority("low") is TaskPriority.LOW

    def test_string_conversion(self) -> None:
        assert str(TaskPriority.HIGH) == "high"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            TaskPriority("urgent")

    def test_has_normal_default(self) -> None:
        """NORMAL is the expected default priority for engineering tasks."""
        assert TaskPriority.NORMAL == "normal"

    def test_has_critical_level(self) -> None:
        """CRITICAL priority is reserved for urgent, blocking work."""
        assert TaskPriority.CRITICAL == "critical"


class TestRiskLevel:
    """Detailed tests for :class:`RiskLevel`."""

    def test_expected_members(self) -> None:
        expected = {"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert {m.name for m in RiskLevel} == expected

    def test_member_count(self) -> None:
        assert len(list(RiskLevel)) == 5

    def test_values(self) -> None:
        assert RiskLevel.NONE == "none"
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"
        assert RiskLevel.CRITICAL == "critical"

    def test_all_values_lowercase(self) -> None:
        for member in RiskLevel:
            assert member.value == member.value.lower()

    def test_from_string(self) -> None:
        assert RiskLevel("high") is RiskLevel.HIGH
        assert RiskLevel("none") is RiskLevel.NONE

    def test_string_conversion(self) -> None:
        assert str(RiskLevel.MEDIUM) == "medium"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            RiskLevel("extreme")

    def test_has_none_level(self) -> None:
        """NONE indicates zero assessed risk — safe to proceed."""
        assert RiskLevel.NONE == "none"

    def test_has_critical_level(self) -> None:
        """CRITICAL risk requires human approval before execution."""
        assert RiskLevel.CRITICAL == "critical"

    def test_covers_full_spectrum(self) -> None:
        """Risk levels span from NONE to CRITICAL in five steps."""
        values = [m.value for m in RiskLevel]
        assert values == ["none", "low", "medium", "high", "critical"]


class TestPlanningStrategy:
    """Detailed tests for :class:`PlanningStrategy`."""

    def test_expected_members(self) -> None:
        expected = {
            "CONSERVATIVE",
            "FAST",
            "MINIMAL_CHANGE",
            "PARALLEL",
            "SAFE",
            "SEQUENTIAL",
        }
        assert {m.name for m in PlanningStrategy} == expected

    def test_member_count(self) -> None:
        assert len(list(PlanningStrategy)) == 6

    def test_values(self) -> None:
        assert PlanningStrategy.CONSERVATIVE == "conservative"
        assert PlanningStrategy.FAST == "fast"
        assert PlanningStrategy.MINIMAL_CHANGE == "minimal_change"
        assert PlanningStrategy.PARALLEL == "parallel"
        assert PlanningStrategy.SAFE == "safe"
        assert PlanningStrategy.SEQUENTIAL == "sequential"

    def test_all_values_lowercase(self) -> None:
        for member in PlanningStrategy:
            assert member.value == member.value.lower()

    def test_from_string(self) -> None:
        assert PlanningStrategy("safe") is PlanningStrategy.SAFE
        assert PlanningStrategy("parallel") is PlanningStrategy.PARALLEL

    def test_string_conversion(self) -> None:
        assert str(PlanningStrategy.SAFE) == "safe"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            PlanningStrategy("aggressive")

    def test_has_safety_oriented_strategies(self) -> None:
        """SAFE and CONSERVATIVE prioritise verification over speed."""
        assert PlanningStrategy.SAFE == "safe"
        assert PlanningStrategy.CONSERVATIVE == "conservative"

    def test_has_speed_oriented_strategies(self) -> None:
        """FAST and PARALLEL prioritise throughput over caution."""
        assert PlanningStrategy.FAST == "fast"
        assert PlanningStrategy.PARALLEL == "parallel"

    def test_has_minimal_change_strategy(self) -> None:
        """MINIMAL_CHANGE produces the smallest possible diff."""
        assert PlanningStrategy.MINIMAL_CHANGE == "minimal_change"

    def test_has_sequential_strategy(self) -> None:
        """SEQUENTIAL executes tasks one at a time in dependency order."""
        assert PlanningStrategy.SEQUENTIAL == "sequential"
