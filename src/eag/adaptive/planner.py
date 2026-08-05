"""Adaptive Planner for EAG."""

from eag.adaptive.enums import PlanningStrategyType
from eag.adaptive.models import (
    AdaptivePlan,
    AdaptivePlanningContext,
    PlanningDecision,
    PlanningRule,
)
from eag.adaptive.strategies import DefaultStrategy, StrategyRegistry
from eag.chief.runtime.models import Plan, PlanStep, RunContext
from eag.chief.runtime.planner import DefaultPlanner


class AdaptivePlanner:
    """Wraps a base planner and applies rules from engineering experience."""

    def __init__(self, base_planner=None, registry: StrategyRegistry | None = None) -> None:
        self._base_planner = base_planner if base_planner is not None else DefaultPlanner()
        self._registry = registry or StrategyRegistry()
        self._registry.register(DefaultStrategy())

    def create_plan(self, context: RunContext) -> Plan:
        """Delegates base plan generation to the wrapped planner."""
        return self._base_planner.create_plan(context)

    def plan(
        self,
        context: AdaptivePlanningContext,
        base_plan: Plan,
        strategy_type: PlanningStrategyType = PlanningStrategyType.DEFAULT,
    ) -> tuple[AdaptivePlan, PlanningDecision]:
        """Generates an adaptive plan by applying rules to the base plan."""

        strategy = self._registry.find(strategy_type)
        sorted_rules = strategy.filter_rules(context.rules)

        applied_rules: list[PlanningRule] = []
        ignored_rules: list[PlanningRule] = []
        current_steps: list[PlanStep] = list(base_plan.steps)

        reasoning_parts: list[str] = []

        for rule in sorted_rules:
            if self._matches_condition(rule.condition, context):
                success = self._apply_action(rule.action, current_steps, context)
                if success:
                    applied_rules.append(rule)
                    reasoning_parts.append(f"Applied rule '{rule.id}': {rule.action}")
                else:
                    ignored_rules.append(rule)
            else:
                ignored_rules.append(rule)

        final_plan = Plan(steps=tuple(current_steps))

        adaptive_plan = AdaptivePlan(
            base_plan=base_plan,
            final_plan=final_plan,
            applied_rules=tuple(applied_rules),
            ignored_rules=tuple(ignored_rules),
            confidence=0.9,
        )

        decision = PlanningDecision(
            goal=context.goal,
            selected_strategy=strategy.type,
            applied_rules=tuple(applied_rules),
            ignored_rules=tuple(ignored_rules),
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No rules applied.",
            confidence=0.9,
        )

        return adaptive_plan, decision

    def _matches_condition(self, condition: str, context: AdaptivePlanningContext) -> bool:
        """Evaluates a simple condition string against the context."""
        try:
            if "==" in condition:
                key, val = condition.split("==")
                key = key.strip()
                val = val.strip().strip("'\"")

                if key == "goal":
                    return val.lower() in context.goal.lower()
                elif key == "experience_count":
                    return len(context.experiences) == int(val)
                elif key == "has_insights":
                    return (len(context.insights) > 0) == (val.lower() == "true")

            return False
        except Exception:
            return False

    def _apply_action(
        self, action: str, steps: list[PlanStep], context: AdaptivePlanningContext
    ) -> bool:
        """Applies an action to the plan steps."""
        parts = action.split(":")
        if not parts:
            return False

        cmd = parts[0]

        if cmd == "insert_worker" and len(parts) > 1:
            cap = parts[1]
            insert_idx = len(steps) - 1 if len(steps) > 0 else 0
            new_step = PlanStep(name=f"Adaptive {cap} Worker", capability_id=cap)
            steps.insert(insert_idx, new_step)
            return True

        elif cmd == "insert_step" and len(parts) > 2:
            title = parts[1]
            cap = parts[2]
            new_step = PlanStep(name=title, capability_id=cap)
            steps.append(new_step)
            return True

        return False