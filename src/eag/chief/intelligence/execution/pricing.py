"""Pricing catalog for EAG."""

from eag.chief.intelligence.execution.models import ModelPricing, UsageMetrics


class PricingCatalog:
    """Centralized catalog for AI model pricing."""

    def __init__(self) -> None:
        self._pricing: dict[str, ModelPricing] = {}

    def register(self, pricing: ModelPricing) -> None:
        self._pricing[pricing.model_id] = pricing

    def calculate_cost(self, model_id: str, usage: UsageMetrics) -> float:
        pricing = self._pricing.get(model_id)
        if not pricing:
            return 0.0

        prompt_cost = (usage.prompt_tokens / 1000.0) * pricing.prompt_price_per_1k
        completion_cost = (usage.completion_tokens / 1000.0) * pricing.completion_price_per_1k
        return prompt_cost + completion_cost
