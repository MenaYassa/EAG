"""Planning strategy registry for EAG."""

from eag.planner.errors import (
    DuplicatePlanningStrategyError,
    PlanningStrategyNotFoundError,
    PlanningStrategyUnavailableError,
)
from eag.planner.models import PlanningContext, PlanningGoal
from eag.planner.strategy import PlanningStrategy


class PlanningStrategyRegistry:
    """Discovers and manages available planning strategies."""

    def __init__(self) -> None:
        self._strategies: dict[str, PlanningStrategy] = {}

    def register(self, strategy: PlanningStrategy) -> None:
        """Register a new planning strategy.

        Raises:
            DuplicatePlanningStrategyError: If a strategy with the same name exists.
        """
        name = strategy.info.name
        if name in self._strategies:
            raise DuplicatePlanningStrategyError(f"Strategy '{name}' is already registered.")
        self._strategies[name] = strategy

    def unregister(self, name: str) -> bool:
        """Unregister a strategy by name. Returns True if successful."""
        if name in self._strategies:
            del self._strategies[name]
            return True
        return False

    def find(self, goal: PlanningGoal, context: PlanningContext) -> PlanningStrategy:
        """Find the best matching strategy for a goal.

        Evaluates `supports()` on all registered strategies and returns the
        one with the highest priority.

        Raises:
            PlanningStrategyUnavailableError: If no strategy supports the goal.
        """
        matches = [s for s in self._strategies.values() if s.supports(goal, context)]
        if not matches:
            raise PlanningStrategyUnavailableError(f"No strategy supports goal '{goal.title}'.")
        matches.sort(key=lambda s: s.info.priority, reverse=True)
        return matches[0]

    def default(self) -> PlanningStrategy:
        """Return the default strategy (highest priority).

        Raises:
            PlanningStrategyNotFoundError: If no strategies are registered.
        """
        if not self._strategies:
            raise PlanningStrategyNotFoundError("No strategies registered.")
        return max(self._strategies.values(), key=lambda s: s.info.priority)

    def supported(self) -> tuple[str, ...]:
        """Return a sorted tuple of registered strategy names."""
        return tuple(sorted(self._strategies.keys()))

    def all(self) -> tuple[PlanningStrategy, ...]:
        """Return all registered strategies."""
        return tuple(self._strategies.values())
