"""Planning strategy protocol for EAG.

Defines the contract between the Planner Runtime and concrete planning
strategies.  A strategy owns *only* engineering reasoning — it does not
publish events, build context, validate goals, or execute commands.
"""

from datetime import timedelta
from typing import Protocol, runtime_checkable

from eag.planner.enums import RiskLevel
from eag.planner.models import ExecutionPlan, PlanningContext, PlanningGoal, PlanningStrategyInfo


@runtime_checkable
class PlanningStrategy(Protocol):
    """The contract for a planning strategy.

    Every strategy must implement this interface to be registered with
    the :class:`PlanningStrategyRegistry` and orchestrated by the
    :class:`PlannerRuntime`.

    Methods should be deterministic.  They receive the goal and context
    and return engineering decisions (plans, risks, durations) without
    side effects.
    """

    @property
    def info(self) -> PlanningStrategyInfo:
        """Returns metadata about this strategy."""
        ...

    @property
    def name(self) -> str:
        """The unique name of the strategy (e.g., 'Sequential')."""
        ...

    @property
    def priority(self) -> int:
        """Priority used by the registry to select among multiple matches."""
        ...

    def supports(
        self,
        goal: PlanningGoal,
        context: PlanningContext,
    ) -> bool:
        """Check if this strategy can handle the given goal and context."""
        ...

    def create_plan(
        self,
        goal: PlanningGoal,
        context: PlanningContext,
    ) -> ExecutionPlan:
        """Generate an execution plan for the given goal.

        This is the heart of the strategy.  It must return a valid,
        immutable :class:`ExecutionPlan`.
        """
        ...

    def estimate_risk(
        self,
        goal: PlanningGoal,
        context: PlanningContext,
    ) -> RiskLevel:
        """Estimate the risk level of executing the plan for this goal."""
        ...

    def estimate_duration(
        self,
        goal: PlanningGoal,
        context: PlanningContext,
    ) -> timedelta:
        """Estimate the time required to execute the plan."""
        ...
