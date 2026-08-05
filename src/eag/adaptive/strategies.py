"""Planning strategies for EAG Adaptive Planning."""

from eag.adaptive.enums import PlanningStrategyType, RulePriority
from eag.adaptive.errors import StrategyNotFoundError
from eag.adaptive.models import PlanningRule


class PlanningStrategy:
    """Base class for planning strategies."""

    @property
    def type(self) -> PlanningStrategyType:
        raise NotImplementedError

    def filter_rules(self, rules: tuple[PlanningRule, ...]) -> tuple[PlanningRule, ...]:
        """Filters and sorts rules based on strategy."""
        raise NotImplementedError


class DefaultStrategy(PlanningStrategy):
    """The default strategy that applies all rules by priority."""

    @property
    def type(self) -> PlanningStrategyType:
        return PlanningStrategyType.DEFAULT

    def filter_rules(self, rules: tuple[PlanningRule, ...]) -> tuple[PlanningRule, ...]:
        priority_order = {
            RulePriority.CRITICAL: 4,
            RulePriority.HIGH: 3,
            RulePriority.NORMAL: 2,
            RulePriority.LOW: 1,
        }
        return tuple(
            sorted(rules, key=lambda r: (-priority_order.get(r.priority, 0), -r.confidence, r.id))
        )


class QualityFirstStrategy(PlanningStrategy):
    """Prioritizes testing and review rules."""

    @property
    def type(self) -> PlanningStrategyType:
        return PlanningStrategyType.QUALITY_FIRST

    def filter_rules(self, rules: tuple[PlanningRule, ...]) -> tuple[PlanningRule, ...]:
        return DefaultStrategy().filter_rules(rules)


class CostFirstStrategy(PlanningStrategy):
    """Prioritizes cost-saving rules, ignores low-priority ones."""

    @property
    def type(self) -> PlanningStrategyType:
        return PlanningStrategyType.COST_FIRST

    def filter_rules(self, rules: tuple[PlanningRule, ...]) -> tuple[PlanningRule, ...]:
        filtered = [r for r in rules if r.priority != RulePriority.LOW]
        return DefaultStrategy().filter_rules(tuple(filtered))


class StrategyRegistry:
    """Registry for planning strategies."""

    def __init__(self) -> None:
        self._strategies: dict[PlanningStrategyType, PlanningStrategy] = {}

    def register(self, strategy: PlanningStrategy) -> None:
        if strategy.type in self._strategies:
            raise ValueError(f"Strategy '{strategy.type}' is already registered.")
        self._strategies[strategy.type] = strategy

    def find(self, strategy_type: PlanningStrategyType) -> PlanningStrategy:
        if strategy_type not in self._strategies:
            raise StrategyNotFoundError(f"Strategy '{strategy_type}' not found.")
        return self._strategies[strategy_type]

    def list(self) -> tuple[PlanningStrategy, ...]:
        return tuple(self._strategies.values())
