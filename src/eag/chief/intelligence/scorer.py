"""Trait scorer for EAG Chief Engineer."""

from eag.chief.intelligence.enums import AICost, AIReasoningLevel, AISpeed, RoutingPolicy
from eag.chief.intelligence.models import AIRequirements, ModelProfile, ScoreBreakdown


class TraitScorer:
    """Scores models based on weighted traits and policies."""

    _POLICY_WEIGHTS = {
        RoutingPolicy.BALANCED: {"reasoning": 0.3, "context": 0.2, "coding": 0.2, "speed": 0.15, "cost": 0.15},
        RoutingPolicy.HIGH_QUALITY: {"reasoning": 0.4, "context": 0.3, "coding": 0.2, "speed": 0.0, "cost": 0.1},
        RoutingPolicy.LOW_COST: {"reasoning": 0.1, "context": 0.1, "coding": 0.1, "speed": 0.2, "cost": 0.5},
        RoutingPolicy.FASTEST: {"reasoning": 0.1, "context": 0.1, "coding": 0.1, "speed": 0.6, "cost": 0.1},
    }

    def score(self, requirements: AIRequirements, model: ModelProfile, policy: RoutingPolicy) -> ScoreBreakdown:
        weights = self._POLICY_WEIGHTS.get(policy, self._POLICY_WEIGHTS[RoutingPolicy.BALANCED])
        
        r_score = self._normalize_reasoning(model.traits.reasoning)
        c_score = self._normalize_context(model.traits.context)
        co_score = 1.0 if model.capabilities.supports_code else 0.0
        s_score = self._normalize_speed(model.traits.speed)
        cost_score = self._normalize_cost(model.estimated_cost, requirements.maximum_cost)

        r_total = r_score * weights["reasoning"]
        c_total = c_score * weights["context"]
        co_total = co_score * weights["coding"]
        s_total = s_score * weights["speed"]
        cost_total = cost_score * weights["cost"]

        total = r_total + c_total + co_total + s_total + cost_total
        total = max(0.0, min(1.0, total))

        return ScoreBreakdown(
            total=total,
            reasoning=r_total,
            context=c_total,
            coding=co_total,
            speed=s_total,
            cost=cost_total
        )

    def _normalize_reasoning(self, level: AIReasoningLevel) -> float:
        return {"none": 0.0, "low": 0.25, "medium": 0.5, "high": 0.75, "extreme": 1.0}.get(level.value, 0.0)

    def _normalize_context(self, size) -> float:
        return {"small": 0.25, "medium": 0.5, "large": 0.75, "huge": 1.0}.get(size.value, 0.0)

    def _normalize_speed(self, speed: AISpeed) -> float:
        return {"slow": 0.25, "medium": 0.5, "fast": 0.75, "realtime": 1.0}.get(speed.value, 0.0)

    def _normalize_cost(self, cost: AICost, max_allowed_cost: AICost) -> float:
        cost_val = {"very_low": 1, "low": 2, "medium": 3, "high": 4, "very_high": 5}.get(cost.value, 5)
        max_val = {"very_low": 1, "low": 2, "medium": 3, "high": 4, "very_high": 5}.get(max_allowed_cost.value, 5)
        if cost_val == 1: return 1.0
        if cost_val >= max_val: return 0.2
        return 1.0 - ((cost_val - 1) * 0.2)