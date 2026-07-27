"""Requirement matcher for EAG Chief Engineer."""

from eag.chief.intelligence.models import AIRequirements, MatchResult, ModelProfile


class RequirementMatcher:
    """Matches AI requirements against model profiles."""

    _CONTEXT_ORDER = ["small", "medium", "large", "huge"]
    _COST_ORDER = ["very_low", "low", "medium", "high", "very_high"]
    _REASONING_ORDER = ["none", "low", "medium", "high", "extreme"]

    def match(self, requirements: AIRequirements, model: ModelProfile) -> MatchResult:
        matched: list[str] = []
        warnings: list[str] = []
        rejected: list[str] = []

        # 1. Hard Capability Checks
        if requirements.requires_structured_output and not model.capabilities.supports_json_schema:
            rejected.append("missing_json_schema")
        if requirements.requires_tool_calling and not model.capabilities.supports_function_calls:
            rejected.append("missing_tool_calling")
        if requirements.requires_streaming and not model.capabilities.supports_streaming:
            rejected.append("missing_streaming")

        # 2. Hard Context Check
        req_ctx_idx = self._get_idx(self._CONTEXT_ORDER, requirements.minimum_context.value)
        model_ctx_idx = self._get_idx(self._CONTEXT_ORDER, model.traits.context.value)
        if model_ctx_idx < req_ctx_idx:
            rejected.append("insufficient_context")

        # 3. Hard Cost Check
        req_max_cost_idx = self._get_idx(self._COST_ORDER, requirements.maximum_cost.value)
        model_cost_idx = self._get_idx(self._COST_ORDER, model.estimated_cost.value)
        if model_cost_idx > req_max_cost_idx:
            rejected.append("cost_too_high")

        if rejected:
            return MatchResult(compatible=False, matched=tuple(), warnings=tuple(), rejected=tuple(rejected))

        # 4. Soft Trait Checks (Warnings)
        if model.traits.speed != requirements.preferred_speed:
            warnings.append(f"speed_{model.traits.speed.value}")

        # 5. Matched Traits
        req_reasoning_idx = self._get_idx(self._REASONING_ORDER, requirements.minimum_reasoning.value)
        model_reasoning_idx = self._get_idx(self._REASONING_ORDER, model.traits.reasoning.value)
        if model_reasoning_idx >= req_reasoning_idx:
            matched.append("reasoning")
        
        if model.capabilities.supports_code:
            matched.append("coding")
        if model_ctx_idx >= req_ctx_idx:
            matched.append("context")

        return MatchResult(compatible=True, matched=tuple(matched), warnings=tuple(warnings), rejected=tuple())

    def _get_idx(self, order_list: list[str], value: str) -> int:
        try:
            return order_list.index(value)
        except ValueError:
            return -1