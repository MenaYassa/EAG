"""Comprehensive tests for the AI Intelligence Domain (Sprint 7.3A)."""

import pytest
from unittest.mock import MagicMock
from eag.chief.intelligence import (
    AICapabilities,
    AIContextSize,
    AICost,
    AIReasoningLevel,
    AIRequirements,
    AISpeed,
    AITraits,
    ExecutionRequest,
    IntelligenceError,
    IntelligenceMetrics,
    IntelligenceRuntime,
    ModelNotFoundError,
    ModelProfile,
    ModelStatus,
    NoMatchingModelError,
    ProviderError,
    ProviderProfile,
    ProviderStatus,
    RoutingPolicy,
    RoutingPolicyError,
    RuntimeState,
    SelectionDecision,
    SelectionReason,
)
from eag.chief.intelligence.errors import ProviderNotFoundError, SelectionError

# --- Enum Tests (15) ---


class TestEnums:
    def test_reasoning_level_values(self) -> None:
        assert AIReasoningLevel.HIGH == "high"
        assert AIReasoningLevel.NONE == "none"

    def test_speed_values(self) -> None:
        assert AISpeed.FAST == "fast"
        assert AISpeed.REALTIME == "realtime"

    def test_cost_values(self) -> None:
        assert AICost.VERY_LOW == "very_low"
        assert AICost.VERY_HIGH == "very_high"

    def test_context_size_values(self) -> None:
        assert AIContextSize.HUGE == "huge"
        assert AIContextSize.SMALL == "small"

    def test_model_status_values(self) -> None:
        assert ModelStatus.AVAILABLE == "available"
        assert ModelStatus.DEPRECATED == "deprecated"

    def test_provider_status_values(self) -> None:
        assert ProviderStatus.ONLINE == "online"
        assert ProviderStatus.OFFLINE == "offline"

    def test_routing_policy_values(self) -> None:
        assert RoutingPolicy.BALANCED == "balanced"
        assert RoutingPolicy.LOCAL_ONLY == "local_only"

    def test_selection_reason_values(self) -> None:
        assert SelectionReason.EXACT_MATCH == "exact_match"
        assert SelectionReason.FALLBACK == "fallback"

    def test_runtime_state_values(self) -> None:
        assert RuntimeState.READY == "ready"
        assert RuntimeState.FAILED == "failed"

    def test_reasoning_level_order(self) -> None:
        levels = list(AIReasoningLevel)
        assert levels.index(AIReasoningLevel.NONE) < levels.index(AIReasoningLevel.HIGH)

    def test_speed_order(self) -> None:
        speeds = list(AISpeed)
        assert speeds.index(AISpeed.SLOW) < speeds.index(AISpeed.FAST)

    def test_cost_order(self) -> None:
        costs = list(AICost)
        assert costs.index(AICost.VERY_LOW) < costs.index(AICost.HIGH)

    def test_context_size_order(self) -> None:
        ctx = list(AIContextSize)
        assert ctx.index(AIContextSize.SMALL) < ctx.index(AIContextSize.HUGE)

    def test_enum_count(self) -> None:
        assert len(AIReasoningLevel) == 5
        assert len(RoutingPolicy) == 7

    def test_enum_immutable(self) -> None:
        with pytest.raises(AttributeError):
            AIReasoningLevel.HIGH = "very_high"  # type: ignore[misc]


# --- Traits & Capabilities Tests (25) ---


class TestTraitsAndCapabilities:
    def test_traits_immutable(self) -> None:
        t = AITraits(reasoning=AIReasoningLevel.HIGH)
        with pytest.raises(Exception):
            t.reasoning = AIReasoningLevel.LOW  # type: ignore[misc]

    def test_traits_defaults(self) -> None:
        t = AITraits()
        assert t.reasoning == AIReasoningLevel.MEDIUM
        assert t.vision == AIReasoningLevel.NONE

    def test_capabilities_immutable(self) -> None:
        c = AICapabilities(supports_code=True)
        with pytest.raises(Exception):
            c.supports_code = False  # type: ignore[misc]

    def test_capabilities_defaults(self) -> None:
        c = AICapabilities()
        assert c.supports_text is True
        assert c.supports_code is False

    def test_traits_creation(self) -> None:
        t = AITraits(
            reasoning=AIReasoningLevel.EXTREME,
            coding=AIReasoningLevel.EXTREME,
            context=AIContextSize.HUGE,
            speed=AISpeed.FAST,
        )
        assert t.reasoning == AIReasoningLevel.EXTREME

    def test_capabilities_creation(self) -> None:
        c = AICapabilities(supports_code=True, supports_images=True, supports_function_calls=True)
        assert c.supports_code is True

    def test_traits_equality(self) -> None:
        t1 = AITraits(reasoning=AIReasoningLevel.HIGH)
        t2 = AITraits(reasoning=AIReasoningLevel.HIGH)
        assert t1 == t2

    def test_traits_inequality(self) -> None:
        t1 = AITraits(reasoning=AIReasoningLevel.HIGH)
        t2 = AITraits(reasoning=AIReasoningLevel.LOW)
        assert t1 != t2

    def test_capabilities_equality(self) -> None:
        c1 = AICapabilities(supports_code=True)
        c2 = AICapabilities(supports_code=True)
        assert c1 == c2

    def test_traits_invalid_type(self) -> None:
        with pytest.raises(TypeError):
            AITraits(reasoning="high")  # type: ignore[arg-type]


# --- Model Tests (40) ---


class TestIntelligenceModels:
    def test_provider_profile_immutable(self) -> None:
        p = ProviderProfile(id="openai", name="OpenAI")
        with pytest.raises(Exception):
            p.id = "anthropic"  # type: ignore[misc]

    def test_provider_profile_invalid_id(self) -> None:
        with pytest.raises(ValueError):
            ProviderProfile(id="", name="Test")

    def test_provider_profile_invalid_name(self) -> None:
        with pytest.raises(ValueError):
            ProviderProfile(id="test", name="")

    def test_provider_profile_defaults(self) -> None:
        p = ProviderProfile(id="test", name="Test")
        assert p.status == ProviderStatus.ONLINE
        assert p.latency_ms == 0.0

    def test_model_profile_immutable(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="gpt-4", provider_id="openai", name="GPT-4", traits=t, capabilities=c)
        with pytest.raises(Exception):
            m.id = "claude"  # type: ignore[misc]

    def test_model_profile_invalid_id(self) -> None:
        t = AITraits()
        c = AICapabilities()
        with pytest.raises(ValueError):
            ModelProfile(id="", provider_id="p", name="M", traits=t, capabilities=c)

    def test_model_profile_invalid_provider(self) -> None:
        t = AITraits()
        c = AICapabilities()
        with pytest.raises(ValueError):
            ModelProfile(id="m", provider_id="", name="M", traits=t, capabilities=c)

    def test_model_profile_invalid_traits(self) -> None:
        c = AICapabilities()
        with pytest.raises(TypeError):
            ModelProfile(id="m", provider_id="p", name="M", traits="bad", capabilities=c)  # type: ignore[arg-type]

    def test_model_profile_invalid_capabilities(self) -> None:
        t = AITraits()
        with pytest.raises(TypeError):
            ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities="bad")  # type: ignore[arg-type]

    def test_model_profile_defaults(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        assert m.status == "available"
        assert m.estimated_cost == AICost.MEDIUM

    def test_ai_requirements_immutable(self) -> None:
        r = AIRequirements()
        with pytest.raises(Exception):
            r.minimum_reasoning = AIReasoningLevel.HIGH  # type: ignore[misc]

    def test_ai_requirements_defaults(self) -> None:
        r = AIRequirements()
        assert r.minimum_reasoning == AIReasoningLevel.LOW
        assert r.requires_structured_output is False

    def test_execution_request_immutable(self) -> None:
        r = AIRequirements()
        req = ExecutionRequest(capability="test", requirements=r)
        with pytest.raises(Exception):
            req.capability = "new"  # type: ignore[misc]

    def test_execution_request_invalid_capability(self) -> None:
        r = AIRequirements()
        with pytest.raises(ValueError):
            ExecutionRequest(capability="", requirements=r)

    def test_execution_request_invalid_requirements(self) -> None:
        with pytest.raises(TypeError):
            ExecutionRequest(capability="test", requirements="bad")  # type: ignore[arg-type]

    def test_execution_request_defaults(self) -> None:
        r = AIRequirements()
        req = ExecutionRequest(capability="test", requirements=r)
        assert req.policy == RoutingPolicy.BALANCED
        assert req.estimated_tokens == 0

    def test_selection_decision_immutable(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        p = ProviderProfile(id="p", name="P")
        d = SelectionDecision(model=m, provider=p, confidence=0.9, score=0.9)
        with pytest.raises(Exception):
            d.confidence = 1.0  # type: ignore[misc]

    def test_selection_decision_invalid_confidence(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        p = ProviderProfile(id="p", name="P")
        with pytest.raises(ValueError):
            SelectionDecision(model=m, provider=p, confidence=1.5, score=0.9)

    def test_selection_decision_defaults(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        p = ProviderProfile(id="p", name="P")
        d = SelectionDecision(model=m, provider=p, confidence=0.9, score=0.9)
        assert d.reasons == ()
        assert d.alternatives == ()

    def test_provider_profile_metadata(self) -> None:
        p = ProviderProfile(id="p", name="P", metadata={"key": "value"})
        assert p.metadata["key"] == "value"

    def test_model_profile_metadata(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(
            id="m", provider_id="p", name="M", traits=t, capabilities=c, metadata={"key": "value"}
        )
        assert m.metadata["key"] == "value"

    def test_provider_profile_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            ProviderProfile(id="p", name="P", metadata="bad")  # type: ignore[arg-type]

    def test_model_profile_invalid_metadata(self) -> None:
        t = AITraits()
        c = AICapabilities()
        with pytest.raises(TypeError):
            ModelProfile(
                id="m", provider_id="p", name="M", traits=t, capabilities=c, metadata="bad"
            )  # type: ignore[arg-type]

    def test_execution_request_policy(self) -> None:
        r = AIRequirements()
        req = ExecutionRequest(capability="test", requirements=r, policy=RoutingPolicy.FASTEST)
        assert req.policy == RoutingPolicy.FASTEST

    def test_execution_request_estimated_tokens(self) -> None:
        r = AIRequirements()
        req = ExecutionRequest(capability="test", requirements=r, estimated_tokens=1000)
        assert req.estimated_tokens == 1000


# --- Validation & State Tests (20) ---


class TestValidationAndState:
    def test_model_not_found_error(self) -> None:
        with pytest.raises(ModelNotFoundError):
            raise ModelNotFoundError("Not found")

    def test_no_matching_model_error(self) -> None:
        with pytest.raises(NoMatchingModelError):
            raise NoMatchingModelError("No match")

    def test_provider_not_found_error(self) -> None:
        with pytest.raises(ProviderNotFoundError):
            raise ProviderNotFoundError("Not found")

    def test_provider_error(self) -> None:
        with pytest.raises(ProviderError):
            raise ProviderError("Provider failed")

    def test_routing_policy_error(self) -> None:
        with pytest.raises(RoutingPolicyError):
            raise RoutingPolicyError("Bad policy")

    def test_selection_error(self) -> None:
        with pytest.raises(SelectionError):
            raise SelectionError("Selection failed")

    def test_error_hierarchy(self) -> None:
        assert issubclass(ModelNotFoundError, IntelligenceError)
        assert issubclass(NoMatchingModelError, IntelligenceError)
        assert issubclass(ProviderNotFoundError, IntelligenceError)
        assert issubclass(ProviderError, IntelligenceError)
        assert issubclass(RoutingPolicyError, IntelligenceError)
        assert issubclass(SelectionError, IntelligenceError)

    def test_runtime_initial_state(self) -> None:
        rt = IntelligenceRuntime(event_bus=MagicMock())
        assert rt.state == RuntimeState.UNINITIALIZED

    def test_runtime_initialize(self) -> None:
        rt = IntelligenceRuntime(event_bus=MagicMock())
        rt.initialize()
        assert rt.state == RuntimeState.READY

    def test_runtime_metrics_defaults(self) -> None:
        rt = IntelligenceRuntime(event_bus=MagicMock())
        assert rt.metrics.registered_models == 0
        assert rt.metrics.average_confidence == 0.0

    def test_runtime_metrics_immutable(self) -> None:
        m = IntelligenceMetrics()
        with pytest.raises(Exception):
            m.registered_models = 10  # type: ignore[misc]

    def test_confidence_boundary_low(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        p = ProviderProfile(id="p", name="P")
        with pytest.raises(ValueError):
            SelectionDecision(model=m, provider=p, confidence=-0.1, score=0.9)

    def test_confidence_boundary_high(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        p = ProviderProfile(id="p", name="P")
        with pytest.raises(ValueError):
            SelectionDecision(model=m, provider=p, confidence=1.1, score=0.9)

    def test_confidence_zero_allowed(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        p = ProviderProfile(id="p", name="P")
        d = SelectionDecision(model=m, provider=p, confidence=0.0, score=0.0)
        assert d.confidence == 0.0

    def test_confidence_one_allowed(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        p = ProviderProfile(id="p", name="P")
        d = SelectionDecision(model=m, provider=p, confidence=1.0, score=1.0)
        assert d.confidence == 1.0

    def test_state_values(self) -> None:
        assert RuntimeState.UNINITIALIZED == "uninitialized"
        assert RuntimeState.COMPLETE == "complete"

    def test_provider_status_values(self) -> None:
        assert ProviderStatus.DEGRADED == "degraded"
        assert ProviderStatus.MAINTENANCE == "maintenance"

    def test_model_status_values(self) -> None:
        assert ModelStatus.EXPERIMENTAL == "experimental"
        assert ModelStatus.DISABLED == "disabled"

    def test_routing_policy_values(self) -> None:
        assert RoutingPolicy.LOW_COST == "low_cost"
        assert RoutingPolicy.HIGH_QUALITY == "high_quality"


# --- Serialization & Determinism Tests (10) ---


class TestSerializationAndDeterminism:
    def test_traits_determinism(self) -> None:
        t1 = AITraits(reasoning=AIReasoningLevel.HIGH)
        t2 = AITraits(reasoning=AIReasoningLevel.HIGH)
        assert t1 == t2

    def test_capabilities_determinism(self) -> None:
        c1 = AICapabilities(supports_code=True)
        c2 = AICapabilities(supports_code=True)
        assert c1 == c2

    def test_provider_profile_determinism(self) -> None:
        p1 = ProviderProfile(id="p", name="P")
        p2 = ProviderProfile(id="p", name="P")
        assert p1 == p2

    def test_model_profile_determinism(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m1 = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        m2 = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        assert m1 == m2

    def test_requirements_determinism(self) -> None:
        r1 = AIRequirements(minimum_reasoning=AIReasoningLevel.HIGH)
        r2 = AIRequirements(minimum_reasoning=AIReasoningLevel.HIGH)
        assert r1 == r2

    def test_execution_request_determinism(self) -> None:
        r = AIRequirements()
        req1 = ExecutionRequest(capability="test", requirements=r)
        req2 = ExecutionRequest(capability="test", requirements=r)
        assert req1 == req2

    def test_traits_hashable(self) -> None:
        t = AITraits()
        assert hash(t) is not None

    def test_capabilities_hashable(self) -> None:
        c = AICapabilities()
        assert hash(c) is not None

    def test_model_profile_hashable(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        assert hash(m) is not None

    def test_selection_decision_hashable(self) -> None:
        t = AITraits()
        c = AICapabilities()
        m = ModelProfile(id="m", provider_id="p", name="M", traits=t, capabilities=c)
        p = ProviderProfile(id="p", name="P")
        d = SelectionDecision(model=m, provider=p, confidence=0.9, score=0.9)
        assert hash(d) is not None
