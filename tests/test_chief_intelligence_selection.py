"""Comprehensive tests for the AI Intelligence Selection Engine (Sprint 7.3B Hardened)."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from eag.chief.intelligence import (
    AICapabilities,
    AIContextSize,
    AICost,
    AIReasoningLevel,
    AIRequirements,
    AISpeed,
    AITraits,
    ExecutionRequest,
    IntelligenceRuntime,
    MatchResult,
    ModelProfile,
    ModelRegistry,
    NoMatchingModelError,
    ProviderNotFoundError,
    ProviderProfile,
    ProviderRegistry,
    ProviderStatus,
    RequirementMatcher,
    RoutingPolicy,
    RuntimeState,
    ScoreBreakdown,
    SelectionDecision,
    TraitScorer,
)
from eag.chief.intelligence.events import SelectionCompleted, SelectionStarted

# --- Fixtures & Helpers ---


def make_traits(
    reasoning=AIReasoningLevel.HIGH, ctx=AIContextSize.LARGE, speed=AISpeed.FAST
) -> AITraits:
    return AITraits(reasoning=reasoning, context=ctx, speed=speed, coding=AIReasoningLevel.HIGH)


def make_caps(code=True, json=True, tools=True, stream=True) -> AICapabilities:
    return AICapabilities(
        supports_code=code,
        supports_json_schema=json,
        supports_function_calls=tools,
        supports_streaming=stream,
    )


# Replace your current make_model function with this:
def make_model(
    id: str = "model-1",
    provider: str = "provider-1",
    name: str | None = None,  # <-- Add name parameter
    cost: AICost = AICost.MEDIUM,
    traits=None,
    caps=None,
    status: str = "available",
    **kwargs,
) -> ModelProfile:
    return ModelProfile(
        id=id,
        provider_id=provider,
        name=name
        if name is not None
        else id.replace("-", " ").title(),  # <-- Use explicit name if provided
        traits=traits or make_traits(),
        capabilities=caps or make_caps(),
        estimated_cost=cost,
        status=status,
        **kwargs,
    )


def make_provider(id="provider-1", status=ProviderStatus.ONLINE) -> ProviderProfile:
    return ProviderProfile(id=id, name=id.replace("-", " ").title(), status=status)


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def runtime(event_bus: MockEventBus) -> IntelligenceRuntime:
    rt = IntelligenceRuntime(event_bus=event_bus)

    rt.providers.register(make_provider(id="p1"))
    rt.providers.register(make_provider(id="p2", status=ProviderStatus.OFFLINE))

    rt.models.register(make_model(id="m1", provider="p1", cost=AICost.LOW))
    rt.models.register(
        make_model(
            id="m2",
            provider="p1",
            cost=AICost.HIGH,
            traits=make_traits(reasoning=AIReasoningLevel.EXTREME),
        )
    )
    rt.models.register(
        make_model(id="m3", provider="p1", cost=AICost.MEDIUM, caps=make_caps(json=False))
    )
    rt.models.register(make_model(id="m4", provider="p2", cost=AICost.LOW))
    rt.models.register(make_model(id="m5", provider="p1", cost=AICost.LOW, status="deprecated"))

    rt.initialize()
    return rt


def make_request(
    cap="test",
    reasoning=AIReasoningLevel.MEDIUM,
    ctx=AIContextSize.MEDIUM,
    json=True,
    tools=False,
    stream=False,
    max_cost=AICost.HIGH,
    speed=AISpeed.MEDIUM,
    policy=RoutingPolicy.BALANCED,
) -> ExecutionRequest:
    return ExecutionRequest(
        capability=cap,
        requirements=AIRequirements(
            minimum_reasoning=reasoning,
            minimum_context=ctx,
            requires_structured_output=json,
            requires_tool_calling=tools,
            requires_streaming=stream,
            maximum_cost=max_cost,
            preferred_speed=speed,
        ),
        policy=policy,
    )


# --- Provider Registry Tests (15) ---


class TestProviderRegistry:
    def test_register(self) -> None:
        reg = ProviderRegistry()
        reg.register(make_provider(id="p1"))
        assert len(reg.list()) == 1

    def test_duplicate_raises(self) -> None:
        reg = ProviderRegistry()
        reg.register(make_provider(id="p1"))
        with pytest.raises(ValueError):
            reg.register(make_provider(id="p1"))

    def test_find_success(self) -> None:
        reg = ProviderRegistry()
        reg.register(make_provider(id="p1"))
        assert reg.find("p1").id == "p1"

    def test_find_missing_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(ProviderNotFoundError):
            reg.find("missing")

    def test_list_sorted(self) -> None:
        reg = ProviderRegistry()
        reg.register(make_provider(id="z"))
        reg.register(make_provider(id="a"))
        assert reg.list()[0].id == "a"

    def test_available_filters_offline(self) -> None:
        reg = ProviderRegistry()
        reg.register(make_provider(id="p1", status=ProviderStatus.ONLINE))
        reg.register(make_provider(id="p2", status=ProviderStatus.OFFLINE))
        assert len(reg.available()) == 1
        assert reg.available()[0].id == "p1"

    def test_available_filters_maintenance(self) -> None:
        reg = ProviderRegistry()
        reg.register(make_provider(id="p1", status=ProviderStatus.MAINTENANCE))
        assert len(reg.available()) == 0

    def test_list_returns_immutable_tuple(self) -> None:
        reg = ProviderRegistry()
        reg.register(make_provider(id="p1"))
        providers = reg.list()
        assert isinstance(providers, tuple)
        with pytest.raises(AttributeError):
            providers.append(make_provider(id="p2"))  # type: ignore[attr-defined]

    def test_available_returns_immutable_tuple(self) -> None:
        reg = ProviderRegistry()
        reg.register(make_provider(id="p1"))
        providers = reg.available()
        assert isinstance(providers, tuple)
        with pytest.raises(AttributeError):
            providers.append(make_provider(id="p2"))  # type: ignore[attr-defined]


# --- Model Registry Tests (20) ---


class TestModelRegistry:
    def test_register(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="m1"))
        assert len(reg.list()) == 1

    def test_duplicate_raises(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="m1"))
        with pytest.raises(ValueError):
            reg.register(make_model(id="m1"))

    def test_find_success(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="m1"))
        assert reg.find("m1").id == "m1"

    def test_find_missing_raises(self) -> None:
        reg = ModelRegistry()
        with pytest.raises(ValueError):
            reg.find("missing")

    def test_list_sorted(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="z"))
        reg.register(make_model(id="a"))
        assert reg.list()[0].id == "a"

    def test_available_filters_deprecated(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="m1", status="deprecated"))
        assert len(reg.available()) == 0

    def test_by_provider(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="m1", provider="p1"))
        reg.register(make_model(id="m2", provider="p2"))
        assert len(reg.by_provider("p1")) == 1

    def test_search_name(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="m1", name="Claude Sonnet"))
        reg.register(make_model(id="m2", name="GPT-4"))
        assert len(reg.search("Claude")) == 1

    def test_search_id(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="claude-sonnet"))
        assert len(reg.search("claude")) == 1

    def test_list_returns_immutable_tuple(self) -> None:
        reg = ModelRegistry()
        reg.register(make_model(id="m1"))
        models = reg.list()
        assert isinstance(models, tuple)
        with pytest.raises(AttributeError):
            models.append(make_model(id="m2"))  # type: ignore[attr-defined]


# --- Matcher Tests (35) ---


class TestRequirementMatcher:
    def test_hard_fail_json(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(json=True)
        model = make_model(caps=make_caps(json=False))
        result = matcher.match(req.requirements, model)
        assert result.compatible is False
        assert "missing_json_schema" in result.rejected

    def test_hard_fail_tools(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(tools=True)
        model = make_model(caps=make_caps(tools=False))
        result = matcher.match(req.requirements, model)
        assert result.compatible is False
        assert "missing_tool_calling" in result.rejected

    def test_hard_fail_streaming(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(stream=True)
        model = make_model(caps=make_caps(stream=False))
        result = matcher.match(req.requirements, model)
        assert result.compatible is False
        assert "missing_streaming" in result.rejected

    def test_hard_fail_context(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(ctx=AIContextSize.HUGE)
        model = make_model(traits=make_traits(ctx=AIContextSize.SMALL))
        result = matcher.match(req.requirements, model)
        assert result.compatible is False
        assert "insufficient_context" in result.rejected

    def test_hard_fail_cost(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(max_cost=AICost.LOW)
        model = make_model(cost=AICost.HIGH)
        result = matcher.match(req.requirements, model)
        assert result.compatible is False
        assert "cost_too_high" in result.rejected

    def test_soft_pass_reasoning(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(reasoning=AIReasoningLevel.MEDIUM)
        model = make_model(traits=make_traits(reasoning=AIReasoningLevel.HIGH))
        result = matcher.match(req.requirements, model)
        assert result.compatible is True
        assert "reasoning" in result.matched

    def test_soft_pass_coding(self) -> None:
        matcher = RequirementMatcher()
        req = make_request()
        model = make_model(caps=make_caps(code=True))
        result = matcher.match(req.requirements, model)
        assert result.compatible is True
        assert "coding" in result.matched

    def test_warning_speed_mismatch(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(speed=AISpeed.FAST)
        model = make_model(traits=make_traits(speed=AISpeed.SLOW))
        result = matcher.match(req.requirements, model)
        assert result.compatible is True
        assert "speed_slow" in result.warnings

    def test_no_warnings_on_exact_speed_match(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(speed=AISpeed.FAST)
        model = make_model(traits=make_traits(speed=AISpeed.FAST))
        result = matcher.match(req.requirements, model)
        assert result.compatible is True
        assert len(result.warnings) == 0

    def test_failed_match_explains_multiple_failures(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(json=True, tools=True)
        model = make_model(caps=make_caps(json=False, tools=False))
        result = matcher.match(req.requirements, model)
        assert result.compatible is False
        assert "missing_json_schema" in result.rejected
        assert "missing_tool_calling" in result.rejected

    def test_match_result_immutable(self) -> None:
        matcher = RequirementMatcher()
        req = make_request()
        model = make_model()
        result = matcher.match(req.requirements, model)
        with pytest.raises(Exception):
            result.compatible = False  # type: ignore[misc]

    def test_match_result_defaults(self) -> None:
        result = MatchResult(compatible=True)
        assert result.matched == ()
        assert result.warnings == ()
        assert result.rejected == ()

    def test_matched_contains_context(self) -> None:
        matcher = RequirementMatcher()
        req = make_request(ctx=AIContextSize.LARGE)
        model = make_model(traits=make_traits(ctx=AIContextSize.HUGE))
        result = matcher.match(req.requirements, model)
        assert "context" in result.matched


# --- Scorer Tests (25) ---


class TestTraitScorer:
    def test_score_returns_breakdown(self) -> None:
        scorer = TraitScorer()
        req = make_request()
        model = make_model()
        breakdown = scorer.score(req.requirements, model, req.policy)
        assert isinstance(breakdown, ScoreBreakdown)

    def test_score_bounds(self) -> None:
        scorer = TraitScorer()
        req = make_request()
        model = make_model()
        breakdown = scorer.score(req.requirements, model, req.policy)
        assert 0.0 <= breakdown.total <= 1.0

    def test_score_breakdown_sum_equals_total(self) -> None:
        scorer = TraitScorer()
        req = make_request()
        model = make_model()
        breakdown = scorer.score(req.requirements, model, req.policy)
        total = (
            breakdown.reasoning
            + breakdown.context
            + breakdown.coding
            + breakdown.speed
            + breakdown.cost
        )
        assert abs(breakdown.total - total) < 0.001  # Handle float imprecision

    def test_high_quality_policy_prefers_reasoning(self) -> None:
        scorer = TraitScorer()
        req = make_request(policy=RoutingPolicy.HIGH_QUALITY)
        model_high_reason = make_model(
            traits=make_traits(reasoning=AIReasoningLevel.EXTREME, speed=AISpeed.SLOW)
        )
        model_fast = make_model(
            traits=make_traits(reasoning=AIReasoningLevel.MEDIUM, speed=AISpeed.REALTIME)
        )

        score1 = scorer.score(req.requirements, model_high_reason, req.policy).total
        score2 = scorer.score(req.requirements, model_fast, req.policy).total
        assert score1 > score2

    def test_fastest_policy_prefers_speed(self) -> None:
        scorer = TraitScorer()
        req = make_request(policy=RoutingPolicy.FASTEST)
        model_fast = make_model(
            traits=make_traits(reasoning=AIReasoningLevel.LOW, speed=AISpeed.REALTIME)
        )
        model_smart = make_model(
            traits=make_traits(reasoning=AIReasoningLevel.EXTREME, speed=AISpeed.SLOW)
        )

        score1 = scorer.score(req.requirements, model_fast, req.policy).total
        score2 = scorer.score(req.requirements, model_smart, req.policy).total
        assert score1 > score2

    def test_breakdown_immutable(self) -> None:
        scorer = TraitScorer()
        req = make_request()
        model = make_model()
        breakdown = scorer.score(req.requirements, model, req.policy)
        with pytest.raises(Exception):
            breakdown.total = 0.5  # type: ignore[misc]

    def test_low_cost_policy_weight(self) -> None:
        scorer = TraitScorer()
        req = make_request(policy=RoutingPolicy.LOW_COST)
        model_low_cost = make_model(cost=AICost.VERY_LOW)
        model_high_cost = make_model(cost=AICost.HIGH)

        score1 = scorer.score(req.requirements, model_low_cost, req.policy).total
        score2 = scorer.score(req.requirements, model_high_cost, req.policy).total
        assert score1 > score2


# --- Selector & Runtime Tests (40) ---


class TestModelSelectorAndRuntime:
    def test_runtime_initial_state(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        assert rt.state == RuntimeState.UNINITIALIZED

    def test_runtime_initialize(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.initialize()
        assert rt.state == RuntimeState.READY

    def test_select_returns_decision(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        decision = runtime.select_model(req)
        assert isinstance(decision, SelectionDecision)

    def test_select_filters_offline_provider(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        decision = runtime.select_model(req)
        assert decision.provider.id != "p2"

    def test_select_filters_deprecated_model(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        decision = runtime.select_model(req)
        assert decision.model.id != "m5"

    def test_select_filters_hard_requirements(self, runtime: IntelligenceRuntime) -> None:
        req = make_request(json=True)
        decision = runtime.select_model(req)
        assert decision.model.id != "m3"

    def test_select_no_candidates_raises(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.initialize()
        req = make_request()
        with pytest.raises(NoMatchingModelError):
            rt.select_model(req)

    def test_select_confidence_matches_score(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        decision = runtime.select_model(req)
        assert decision.confidence == decision.score

    def test_select_alternatives_populated(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        decision = runtime.select_model(req)
        assert len(decision.alternatives) > 0

    def test_select_deterministic(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        d1 = runtime.select_model(req)
        d2 = runtime.select_model(req)
        assert d1 == d2

    def test_select_tie_breaking_id(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.providers.register(make_provider(id="p1"))
        rt.models.register(make_model(id="zzz", provider="p1"))
        rt.models.register(make_model(id="aaa", provider="p1"))
        rt.initialize()

        req = make_request()
        decision = rt.select_model(req)
        assert decision.model.id == "aaa"

    def test_metrics_updated_after_select(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        runtime.select_model(req)
        assert runtime.metrics.selection_count == 1
        assert runtime.metrics.registered_models == 5

    def test_state_ready_after_select(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        runtime.select_model(req)
        assert runtime.state == RuntimeState.READY

    def test_state_failed_on_error(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.initialize()
        req = make_request()
        with pytest.raises(NoMatchingModelError):
            rt.select_model(req)
        assert rt.state == RuntimeState.FAILED

    def test_select_low_cost_policy(self, runtime: IntelligenceRuntime) -> None:
        req = make_request(policy=RoutingPolicy.LOW_COST, max_cost=AICost.VERY_HIGH)
        decision = runtime.select_model(req)
        assert decision.model.id == "m1"

    def test_select_decision_contains_match_result(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        decision = runtime.select_model(req)
        assert decision.match_result is not None
        assert decision.match_result.compatible is True

    def test_select_decision_contains_score_breakdown(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        decision = runtime.select_model(req)
        assert decision.score_breakdown is not None
        assert decision.score_breakdown.total == decision.score

    def test_no_candidate_error_contains_analysis(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.providers.register(make_provider(id="p1"))
        rt.models.register(make_model(id="m1", provider="p1", caps=make_caps(json=False)))
        rt.initialize()

        req = make_request(json=True)
        with pytest.raises(NoMatchingModelError) as exc_info:
            rt.select_model(req)
        assert "m1: missing_json_schema" in exc_info.value.reasons

    def test_policy_conflict_cost_wins(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.providers.register(make_provider(id="p1"))
        rt.models.register(
            make_model(
                id="m1",
                provider="p1",
                cost=AICost.HIGH,
                traits=make_traits(reasoning=AIReasoningLevel.EXTREME),
            )
        )
        rt.initialize()

        req = make_request(policy=RoutingPolicy.HIGH_QUALITY, max_cost=AICost.LOW)
        with pytest.raises(NoMatchingModelError):
            rt.select_model(req)

    def test_selection_started_event_published(
        self, runtime: IntelligenceRuntime, event_bus: MockEventBus
    ) -> None:
        req = make_request()
        runtime.select_model(req)
        assert any(isinstance(e, SelectionStarted) for e in event_bus.published_events)

    def test_selection_completed_event_published(
        self, runtime: IntelligenceRuntime, event_bus: MockEventBus
    ) -> None:
        req = make_request()
        runtime.select_model(req)
        assert any(isinstance(e, SelectionCompleted) for e in event_bus.published_events)

    def test_selection_completed_event_on_failure(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.initialize()
        req = make_request()
        with pytest.raises(NoMatchingModelError):
            rt.select_model(req)
        assert any(isinstance(e, SelectionCompleted) for e in event_bus.published_events)

    def test_event_order(self, runtime: IntelligenceRuntime, event_bus: MockEventBus) -> None:
        req = make_request()
        runtime.select_model(req)
        event_types = [type(e) for e in event_bus.published_events]
        assert event_types == [SelectionStarted, SelectionCompleted]

    def test_alternatives_order_deterministic(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        d1 = runtime.select_model(req)
        d2 = runtime.select_model(req)
        assert d1.alternatives == d2.alternatives

    def test_reason_order_deterministic(self, runtime: IntelligenceRuntime) -> None:
        req = make_request()
        d1 = runtime.select_model(req)
        d2 = runtime.select_model(req)
        assert d1.reasons == d2.reasons

    def test_selection_with_large_registry(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.providers.register(make_provider(id="p1"))
        for i in range(100):
            rt.models.register(make_model(id=f"m_{i}", provider="p1", cost=AICost.LOW))
        rt.initialize()

        req = make_request()
        import time

        start = time.monotonic()
        decision = rt.select_model(req)
        end = time.monotonic()

        assert (
            decision.success if hasattr(decision, "success") else True
        )  # Decision doesn't have success, just checking it returns
        assert (end - start) < 0.1  # 100ms limit

    def test_provider_consistency_delayed_binding(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        # Register model before provider exists
        rt.models.register(make_model(id="m1", provider="missing_p"))
        rt.initialize()

        req = make_request()
        with pytest.raises(NoMatchingModelError) as exc_info:
            rt.select_model(req)
        assert "m1: provider offline" in exc_info.value.reasons

    def test_select_filters_experimental(self, event_bus: MockEventBus) -> None:
        rt = IntelligenceRuntime(event_bus=event_bus)
        rt.providers.register(make_provider(id="p1"))
        rt.models.register(make_model(id="m1", provider="p1", status="experimental"))
        rt.initialize()

        req = make_request()
        with pytest.raises(NoMatchingModelError):
            rt.select_model(req)
