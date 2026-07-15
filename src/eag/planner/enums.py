"""Planning domain vocabulary for EAG.

This module defines the enumerations that form the vocabulary of the
Engineering Planning Platform.  These enums describe *why* we plan,
*how* we plan, and *what state* a plan can be in.

All enums are :class:`enum.StrEnum` instances, meaning they are directly
serialisable as strings and can be used in JSON payloads, CLI output,
and log records without conversion.
"""

from enum import StrEnum


class GoalType(StrEnum):
    """The engineering purpose behind a planning goal.

    These are engineering goals, not AI prompts.  Each value describes a
    distinct category of engineering work that EAG can plan for.

    Examples
    --------
    - ``REFACTOR`` — Rename EventBus to EventHub
    - ``FEATURE`` — Add Graph Export
    - ``BUGFIX`` — Fix Session rollback
    - ``ANALYSIS`` — Understand Planner dependencies
    """

    ANALYSIS = "analysis"
    BUGFIX = "bugfix"
    DOCUMENTATION = "documentation"
    FEATURE = "feature"
    INFRASTRUCTURE = "infrastructure"
    MAINTENANCE = "maintenance"
    REFACTOR = "refactor"
    TESTING = "testing"


class PlanState(StrEnum):
    """Lifecycle state of an execution plan.

    The plan lifecycle mirrors the session and execution lifecycles
    established in earlier sprints.  Execution states appear here because
    a plan has a lifecycle even though execution itself belongs to the
    Execution Runtime.
    """

    CREATED = "created"
    PLANNING = "planning"
    VALIDATED = "validated"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Return True if this state is terminal (no outgoing transitions)."""
        return self in {
            PlanState.COMPLETED,
            PlanState.FAILED,
            PlanState.CANCELLED,
        }

    def can_transition_to(self, target: "PlanState") -> bool:
        """Check if a transition to the target state is valid.

        Args:
            target: The desired next state.

        Returns:
            True if the transition is allowed, False otherwise.
        """
        if self is target:
            return True

        if self.is_terminal:
            return False

        allowed_transitions: dict[PlanState, set[PlanState]] = {
            PlanState.CREATED: {PlanState.PLANNING, PlanState.CANCELLED},
            PlanState.PLANNING: {
                PlanState.VALIDATED,
                PlanState.FAILED,
                PlanState.CANCELLED,
            },
            PlanState.VALIDATED: {
                PlanState.APPROVED,
                PlanState.REJECTED,
                PlanState.CANCELLED,
            },
            PlanState.APPROVED: {PlanState.EXECUTING, PlanState.CANCELLED},
            PlanState.REJECTED: {PlanState.CANCELLED},
            PlanState.EXECUTING: {
                PlanState.COMPLETED,
                PlanState.FAILED,
                PlanState.CANCELLED,
            },
        }

        return target in allowed_transitions.get(self, set())


class TaskPriority(StrEnum):
    """Priority level for an engineering task."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(StrEnum):
    """Risk assessment for a plan or task.

    Risk is later computed from graph impact, repository safety,
    protected files, and approval policy.
    """

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PlanningStrategy(StrEnum):
    """Strategy that guides how the Planner decomposes and orders tasks.

    The strategy is chosen by the caller (human or future Chief AI) and
    influences task ordering, parallelism, and safety margins without
    changing Planner code.

    Examples
    --------
    - ``SAFE`` — maximise verification steps, prefer sequential execution
    - ``FAST`` — minimise non-essential steps, allow parallelism
    - ``MINIMAL_CHANGE`` — produce the smallest possible changeset
    """

    CONSERVATIVE = "conservative"
    FAST = "fast"
    MINIMAL_CHANGE = "minimal_change"
    PARALLEL = "parallel"
    SAFE = "safe"
    SEQUENTIAL = "sequential"


class ExecutionMode(StrEnum):
    """How a plan should be executed.

    The Planner itself never executes — it simply records the intended
    mode so that the Execution Runtime knows how to proceed.
    """

    DRY_RUN = "dry_run"
    EXECUTE = "execute"
    SIMULATION = "simulation"


class PlannerRuntimeState(StrEnum):
    """Lifecycle state of the PlannerRuntime itself."""

    CREATED = "created"
    READY = "ready"
    PLANNING = "planning"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
