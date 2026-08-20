"""Focused tests for the G2.1 Governed LLM Gateway."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest

from eag.chief.intelligence.enums import AIContextSize, AIReasoningLevel, AISpeed
from eag.chief.intelligence.execution import (
    ExecutionContext,
    ExecutionResult,
    ExecutionRuntime,
    ExecutionState,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderRegistry,
    UsageMetrics,
)
from eag.chief.intelligence.gateway import (
    ENGINEERING_DECISION_SCHEMA_VERSION,
    DecisionToPlanTranslator,
    EngineeringContext,
    EngineeringDecisionRequest,
    EngineeringDecisionResult,
    GatewayError,
    GatewayErrorKind,
    GatewayPolicy,
    GatewayRuntime,
    GatewayTrace,
    GatewayUsage,
    PolicyValidationError,
    SchemaValidationError,
    parse_engineering_decision,
    validate_decision_policy,
)
from eag.chief.intelligence.gateway.events import GatewayCompleted, GatewayFailed
from eag.chief.intelligence.models import AICapabilities, AITraits, ModelProfile, ProviderProfile
from eag.chief.intelligence.runtime import IntelligenceRuntime
from eag.config.settings import GatewaySettings
from eag.events import EventBus


def valid_payload(**overrides: object) -> dict[str, object]:
    """Return a complete schema-valid decision payload for deterministic tests."""
    payload: dict[str, object] = {
        "interpreted_goal": "Add a documented repository planning step.",
        "assumptions": ["Repository capability is available."],
        "proposed_approach": "Inspect the repository before proposing a safe metadata change.",
        "ordered_plan": [
            {
                "step_id": "inspect",
                "title": "Inspect repository state",
                "capability_id": "repository",
                "dependencies": [],
                "parameters": {},
                "expected_evidence": ["Repository summary"],
            },
            {
                "step_id": "document",
                "title": "Document planned change",
                "capability_id": "workspace",
                "dependencies": ["inspect"],
                "parameters": {},
                "expected_evidence": ["Documentation proposal"],
            },
        ],
        "required_capabilities": ["repository", "workspace"],
        "risks": [
            {
                "description": "Requirements may be incomplete.",
                "severity": "medium",
                "mitigation": "Request clarification before execution.",
            }
        ],
        "confidence": 0.75,
        "schema_version": ENGINEERING_DECISION_SCHEMA_VERSION,
    }
    payload.update(overrides)
    return payload


def make_request(**policy_overrides: object) -> EngineeringDecisionRequest:
    policy_values: dict[str, object] = {"max_attempts": 2, "max_total_tokens": 1000}
    policy_values.update(policy_overrides)
    return EngineeringDecisionRequest(
        goal="Safely plan a repository documentation change.",
        context=EngineeringContext(available_capabilities=("repository", "workspace")),
        allowed_capability_ids=("repository", "workspace"),
        policy=GatewayPolicy(**policy_values),
    )


@dataclass
class FakeProvider:
    """Controlled transport fake; gateway still uses actual selection/execution runtimes."""

    responses: dict[str, str | Exception]
    calls: list[str] = field(default_factory=list)

    @property
    def provider_id(self) -> str:
        return "fake"

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        self.calls.append(context.model_id)
        response = self.responses[context.model_id]
        if isinstance(response, Exception):
            raise response
        return ExecutionResult(
            success=True,
            content=response,
            usage=UsageMetrics(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            provider_id="fake",
            model_id=context.model_id,
            state=ExecutionState.SUCCESS,
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider_id="fake", status=ProviderHealthStatus.HEALTHY)

    def models(self) -> tuple[ModelProfile, ...]:
        return ()

    def supports(self, model_id: str) -> bool:
        return model_id in self.responses

    def stream(self, context: ExecutionContext) -> Iterator[object]:
        raise AssertionError("streaming is not part of the governed decision milestone")

    def discover(self) -> object:
        raise AssertionError("discovery is not part of the governed decision milestone")


def make_gateway(
    provider: FakeProvider,
    model_ids: tuple[str, ...] = ("primary",),
    incompatible_models: tuple[str, ...] = (),
) -> tuple[GatewayRuntime, EventBus]:
    event_bus = EventBus()
    intelligence = IntelligenceRuntime(event_bus=event_bus)
    intelligence.providers.register(ProviderProfile(id="fake", name="Fake provider"))
    for model_id in model_ids:
        intelligence.models.register(
            ModelProfile(
                id=model_id,
                provider_id="fake",
                name=model_id,
                traits=AITraits(
                    reasoning=AIReasoningLevel.HIGH,
                    context=AIContextSize.LARGE,
                    speed=AISpeed.MEDIUM,
                ),
                capabilities=AICapabilities(
                    supports_code=True,
                    supports_json_schema=model_id not in incompatible_models,
                    supports_function_calls=False,
                ),
            )
        )
    registry = ProviderRegistry()
    registry.register(provider)
    return GatewayRuntime(intelligence, ExecutionRuntime(registry=registry), event_bus), event_bus


def test_gateway_configuration_is_explicitly_disabled_by_default() -> None:
    settings = GatewaySettings()

    assert settings.enabled is False
    assert settings.provider_id == "litellm"
    assert settings.max_attempts == 2


def test_parser_and_policy_accept_non_executable_allowlisted_decision() -> None:
    request = make_request()
    decision = parse_engineering_decision(json.dumps(valid_payload()))

    validate_decision_policy(decision, request)

    assert decision.required_capabilities == ("repository", "workspace")
    assert decision.ordered_plan[1].dependencies == ("inspect",)


@pytest.mark.parametrize(
    ("payload", "error_match"),
    [
        ("not json", "not valid JSON"),
        (json.dumps(valid_payload(confidence=2.0)), "confidence"),
        (json.dumps(valid_payload(risks=[])), "risks"),
        (json.dumps(valid_payload(ordered_plan=[])), "ordered_plan"),
    ],
)
def test_parser_rejects_malformed_or_incomplete_decisions(payload: str, error_match: str) -> None:
    with pytest.raises(SchemaValidationError, match=error_match):
        parse_engineering_decision(payload)


def test_policy_rejects_capability_outside_allowlist() -> None:
    payload = valid_payload(required_capabilities=["repository", "shell"])
    payload["ordered_plan"] = [
        {
            "step_id": "inspect",
            "title": "Inspect",
            "capability_id": "shell",
            "dependencies": [],
            "parameters": {},
            "expected_evidence": ["Output"],
        }
    ]
    decision = parse_engineering_decision(json.dumps(payload))

    with pytest.raises(PolicyValidationError, match="allowlist"):
        validate_decision_policy(decision, make_request())


def test_policy_rejects_invalid_dependency_graph() -> None:
    payload = valid_payload()
    payload["ordered_plan"] = [
        {
            "step_id": "document",
            "title": "Document",
            "capability_id": "workspace",
            "dependencies": ["inspect"],
            "parameters": {},
            "expected_evidence": ["Proposal"],
        },
        {
            "step_id": "inspect",
            "title": "Inspect",
            "capability_id": "repository",
            "dependencies": [],
            "parameters": {},
            "expected_evidence": ["Summary"],
        },
    ]
    decision = parse_engineering_decision(json.dumps(payload))

    with pytest.raises(PolicyValidationError, match="earlier proposed step"):
        validate_decision_policy(decision, make_request())


def test_gateway_uses_actual_selection_and_execution_layers_with_redacted_trace() -> None:
    provider = FakeProvider(responses={"primary": json.dumps(valid_payload())})
    gateway, event_bus = make_gateway(provider)
    completed: list[GatewayCompleted] = []
    event_bus.subscribe(GatewayCompleted, completed.append)

    result = gateway.decide(make_request())

    assert result.success is True
    assert result.decision is not None
    assert result.selection is not None
    assert result.usage.total_tokens == 30
    assert result.trace.request_id
    assert provider.calls == ["primary"]
    assert len(completed) == 1
    assert "prompt" not in result.trace.event_types


def test_gateway_rejects_schema_valid_but_policy_invalid_output_without_effect() -> None:
    payload = valid_payload()
    payload["ordered_plan"] = [
        {
            "step_id": "run",
            "title": "Run command",
            "capability_id": "repository",
            "dependencies": [],
            "parameters": {"command": "rm -rf /"},
            "expected_evidence": ["Output"],
        }
    ]
    payload["required_capabilities"] = ["repository"]
    provider = FakeProvider(responses={"primary": json.dumps(payload)})
    gateway, event_bus = make_gateway(provider)
    failures: list[GatewayFailed] = []
    event_bus.subscribe(GatewayFailed, failures.append)

    result = gateway.decide(make_request())

    assert result.success is False
    assert result.decision is None
    assert result.error is not None
    assert result.error.kind == GatewayErrorKind.POLICY_REJECTED
    assert provider.calls == ["primary"]
    assert failures[-1].kind == GatewayErrorKind.POLICY_REJECTED


def test_gateway_reports_malformed_provider_output_as_safe_failure() -> None:
    provider = FakeProvider(responses={"primary": "not-json"})
    gateway, _ = make_gateway(provider)

    result = gateway.decide(make_request())

    assert result.success is False
    assert result.error is not None
    assert result.error.kind == GatewayErrorKind.SCHEMA_INVALID


def test_gateway_reports_timeout_with_no_decision() -> None:
    provider = FakeProvider(responses={"primary": TimeoutError("timeout")})
    gateway, _ = make_gateway(provider)

    result = gateway.decide(make_request())

    assert result.success is False
    assert result.decision is None
    assert result.error is not None
    assert result.error.kind == GatewayErrorKind.PROVIDER_TIMEOUT
    assert len(provider.calls) == 2


def test_gateway_uses_compatible_fallback_after_primary_failure() -> None:
    provider = FakeProvider(
        responses={"a_primary": TimeoutError("timeout"), "z_fallback": json.dumps(valid_payload())}
    )
    gateway, _ = make_gateway(provider, model_ids=("a_primary", "z_fallback"))

    result = gateway.decide(make_request())

    assert result.success is True
    assert result.trace.fallback_used is True
    assert provider.calls == ["a_primary", "a_primary", "z_fallback"]


def test_gateway_rejects_incompatible_fallback_for_structured_decisions() -> None:
    provider = FakeProvider(
        responses={"a_primary": TimeoutError("timeout"), "z_incompatible": json.dumps(valid_payload())}
    )
    gateway, _ = make_gateway(
        provider,
        model_ids=("a_primary", "z_incompatible"),
        incompatible_models=("z_incompatible",),
    )

    result = gateway.decide(make_request())

    assert result.success is False
    assert result.error is not None
    assert result.error.kind == GatewayErrorKind.PROVIDER_TIMEOUT
    assert provider.calls == ["a_primary", "a_primary"]


def test_gateway_rejects_budget_exhaustion_without_decision() -> None:
    provider = FakeProvider(responses={"primary": json.dumps(valid_payload())})
    gateway, _ = make_gateway(provider)

    result = gateway.decide(make_request(max_total_tokens=20))

    assert result.success is False
    assert result.error is not None
    assert result.error.kind == GatewayErrorKind.BUDGET_EXCEEDED


def test_decision_to_plan_translation_is_deterministic_and_non_effectful() -> None:
    decision = parse_engineering_decision(json.dumps(valid_payload()))

    plan = DecisionToPlanTranslator().translate(decision)

    assert [step.step_id for step in plan.steps] == ["inspect", "document"]
    assert plan.steps[1].capability_id == "workspace"
    assert plan.steps[1].metadata["expected_evidence"] == ("Documentation proposal",)


def test_fake_gateway_consumer_uses_real_decision_contract() -> None:
    decision = parse_engineering_decision(json.dumps(valid_payload()))
    fake_result = EngineeringDecisionResult(
        success=True,
        decision=decision,
        trace=GatewayTrace(trace_id="trace", request_id="request"),
        usage=GatewayUsage(total_tokens=1),
    )

    plan = DecisionToPlanTranslator().translate(fake_result.decision)

    assert len(plan.steps) == 2
    assert plan.steps[0].capability_id == "repository"


def test_result_requires_safe_failure_shape() -> None:
    with pytest.raises(ValueError, match="requires a GatewayError"):
        EngineeringDecisionResult(
            success=False,
            trace=GatewayTrace(trace_id="trace", request_id="request"),
        )

    error = GatewayError(kind=GatewayErrorKind.REQUEST_INVALID, message="invalid")
    with pytest.raises(ValueError, match="cannot contain an error"):
        EngineeringDecisionResult(
            success=True,
            decision=parse_engineering_decision(json.dumps(valid_payload())),
            error=error,
            trace=GatewayTrace(trace_id="trace", request_id="request"),
        )
