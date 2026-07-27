"""Planning domain errors for EAG.

Provides a rich hierarchy of exceptions with structured context,
allowing the Planner to surface detailed failure reasons to the
UI, logs, or Chief AI without parsing string messages.
"""

from collections.abc import Mapping
from typing import Any


class PlannerError(Exception):
    """Base error for all planning failures."""

    def __init__(
        self,
        message: str,
        *,
        goal: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.goal = goal
        self.metadata = dict(metadata) if metadata else {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize error context to a dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "goal": self.goal,
            "metadata": self.metadata,
        }


class PlanningValidationError(PlannerError):
    """Raised when a planning goal, task, or plan fails validation."""


class InvalidGoalError(PlanningValidationError):
    """Raised when a goal is invalid, unknown, or impossible."""


class PlanningStrategyError(PlannerError):
    """Raised when a planning strategy is unavailable or incompatible."""


class PlanGenerationError(PlannerError):
    """Raised when the planner fails to generate an execution plan."""


class UnsafePlanError(PlannerError):
    """Raised when a plan is detected as unsafe before reaching runtime."""


class ApprovalRequiredError(PlannerError):
    """Raised when a plan requires approval but none is provided."""


class PlanningExecutionError(PlannerError):
    """Raised when the planner attempts to hand over an invalid plan."""


class DuplicatePlanningStrategyError(PlannerError):
    """Raised when registering a strategy with a name that already exists."""


class PlanningStrategyNotFoundError(PlannerError):
    """Raised when a specific strategy by name is not found."""


class PlanningStrategyUnavailableError(PlannerError):
    """Raised when no registered strategy supports the given goal and context."""


class DuplicateTaskError(PlannerError):
    """Raised when duplicate task IDs are detected."""


class UnknownDependencyError(PlannerError):
    """Raised when a task depends on an unknown task."""


class DependencyCycleError(PlannerError):
    """Raised when a cycle is detected in the task dependency graph."""
