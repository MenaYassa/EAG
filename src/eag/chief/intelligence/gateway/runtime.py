"""Governed LLM Gateway runtime; it returns validated decisions and never executes capabilities."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from eag.chief.intelligence.enums import AIContextSize, AIReasoningLevel, AISpeed
from eag.chief.intelligence.execution import (
    ExecutionContext,
    ExecutionOptions,
    ExecutionRuntime,
    ExecutionState,
)
from eag.chief.intelligence.execution import (
    ProviderRegistry as ExecutionProviderRegistry,
)
from eag.chief.intelligence.execution.providers import LiteLLMProvider
from eag.chief.intelligence.gateway.errors import (
    GatewayError,
    GatewayErrorKind,
    PolicyValidationError,
    PolicyViolation,
    SchemaValidationError,
)
from eag.chief.intelligence.gateway.events import (
    GatewayAttemptFailed,
    GatewayAttemptStarted,
    GatewayCompleted,
    GatewayContextAssembled,
    GatewayFailed,
    GatewayFallbackTriggered,
    GatewayPolicyRejected,
    GatewayRequestStarted,
    GatewayResponseValidated,
    GatewayRoutingSelected,
)
from eag.chief.intelligence.gateway.models import (
    EngineeringDecisionRequest,
    EngineeringDecisionResult,
    GatewayTrace,
    GatewayUsage,
)
from eag.chief.intelligence.gateway.validator import (
    engineering_decision_json_schema,
    parse_engineering_decision,
    validate_decision_policy,
)
from eag.chief.intelligence.models import (
    AICapabilities,
    AIRequirements,
    AITraits,
    ExecutionRequest,
    ModelProfile,
    ProviderProfile,
)
from eag.chief.intelligence.runtime import IntelligenceRuntime
from eag.config.settings import GatewaySettings
from eag.events import EventBus


class GatewayRuntime:
    """Coordinates governed decision semantics above existing routing and transport layers."""

    def __init__(
        self,
        intelligence_runtime: IntelligenceRuntime,
        execution_runtime: ExecutionRuntime,
        event_bus: EventBus,
    ) -> None:
        self._intelligence = intelligence_runtime
        self._execution = execution_runtime
        self._event_bus = event_bus

    def decide(self, request: EngineeringDecisionRequest) -> EngineeringDecisionResult:
        """Return a validated advisory decision or an explicit safe failure."""
        trace_id = _trace_id(request.request_id)
        self._event_bus.publish(
            GatewayRequestStarted(
                request_id=request.request_id,
                trace_id=trace_id,
                schema_version=request.schema_version,
            )
        )
        self._event_bus.publish(
            GatewayContextAssembled(
                request_id=request.request_id,
                trace_id=trace_id,
                context_fingerprint=_context_fingerprint(request),
                available_capability_count=len(request.allowed_capability_ids),
            )
        )

        try:
            selection = self._select(request)
        except Exception as error:
            return self._failure(
                request,
                trace_id,
                GatewayErrorKind.ROUTING_UNAVAILABLE,
                "No compatible routed model is available for a governed structured decision.",
                error=error,
            )

        self._event_bus.publish(
            GatewayRoutingSelected(
                request_id=request.request_id,
                trace_id=trace_id,
                provider_id=selection.provider.id,
                model_id=selection.model.id,
                confidence=selection.confidence,
            )
        )
        self._event_bus.publish(
            GatewayAttemptStarted(
                request_id=request.request_id,
                trace_id=trace_id,
                attempt=1,
                provider_id=selection.provider.id,
                model_id=selection.model.id,
            )
        )

        primary = self._execution_context(request, selection.provider.id, selection.model.id)
        fallbacks = self._fallback_contexts(request, selection)
        if fallbacks:
            self._event_bus.publish(
                GatewayFallbackTriggered(
                    request_id=request.request_id,
                    trace_id=trace_id,
                    primary_model_id=selection.model.id,
                    fallback_model_id=fallbacks[0].model_id,
                )
            )

        try:
            execution = self._execution.execute(primary, fallback_contexts=fallbacks or None)
        except Exception as error:
            return self._failure(
                request,
                trace_id,
                _classify_provider_error(error),
                "Provider execution could not produce a governed decision.",
                selection=selection,
                error=error,
            )

        usage = GatewayUsage(
            prompt_tokens=execution.usage.prompt_tokens,
            completion_tokens=execution.usage.completion_tokens,
            total_tokens=execution.usage.total_tokens,
            estimated_cost=execution.usage.estimated_cost,
            duration_ms=execution.duration_ms,
        )
        trace = GatewayTrace(
            trace_id=trace_id,
            request_id=request.request_id,
            attempts=max(execution.attempts, 1),
            fallback_used=(
                execution.fallback_used or execution.model_id != selection.model.id
            ),
            event_types=tuple(str(event.type) for event in execution.trace.events),
        )

        if not execution.success or execution.state != ExecutionState.SUCCESS:
            return self._failure(
                request,
                trace_id,
                _classify_execution_failure(execution.error),
                "Provider execution did not return a successful governed response.",
                selection=selection,
                usage=usage,
                trace=trace,
            )
        if usage.total_tokens > request.policy.max_total_tokens:
            return self._failure(
                request,
                trace_id,
                GatewayErrorKind.BUDGET_EXCEEDED,
                "Gateway token budget was exceeded.",
                selection=selection,
                usage=usage,
                trace=trace,
            )
        if usage.estimated_cost > request.policy.max_estimated_cost:
            return self._failure(
                request,
                trace_id,
                GatewayErrorKind.BUDGET_EXCEEDED,
                "Gateway estimated-cost budget was exceeded.",
                selection=selection,
                usage=usage,
                trace=trace,
            )

        try:
            decision = parse_engineering_decision(execution.content)
        except SchemaValidationError as error:
            return self._failure(
                request,
                trace_id,
                GatewayErrorKind.SCHEMA_INVALID,
                "Provider response did not satisfy the engineering-decision schema.",
                selection=selection,
                usage=usage,
                trace=trace,
                error=error,
            )

        try:
            validate_decision_policy(decision, request)
        except PolicyValidationError as error:
            self._event_bus.publish(
                GatewayPolicyRejected(
                    request_id=request.request_id,
                    trace_id=trace_id,
                    reason=str(error),
                    violation=error.violation,
                )
            )
            return self._failure(
                request,
                trace_id,
                GatewayErrorKind.POLICY_REJECTED,
                "Validated provider response was rejected by deterministic decision policy.",
                selection=selection,
                usage=usage,
                trace=trace,
                error=error,
                policy_violation=error.violation,
            )

        self._event_bus.publish(
            GatewayResponseValidated(
                request_id=request.request_id,
                trace_id=trace_id,
                plan_step_count=len(decision.ordered_plan),
                required_capability_count=len(decision.required_capabilities),
            )
        )
        self._event_bus.publish(
            GatewayCompleted(
                request_id=request.request_id,
                trace_id=trace_id,
                total_tokens=usage.total_tokens,
                estimated_cost=usage.estimated_cost,
            )
        )
        return EngineeringDecisionResult(
            success=True,
            decision=decision,
            selection=selection,
            usage=usage,
            trace=trace,
        )

    def _select(self, request: EngineeringDecisionRequest):
        if self._intelligence.state.value == "uninitialized":
            self._intelligence.initialize()
        requirements = AIRequirements(
            minimum_reasoning=request.requirements.minimum_reasoning,
            minimum_context=request.requirements.minimum_context,
            requires_structured_output=True,
            requires_tool_calling=False,
            requires_streaming=False,
            maximum_cost=request.requirements.maximum_cost,
            preferred_speed=request.requirements.preferred_speed,
        )
        return self._intelligence.select_model(
            ExecutionRequest(
                capability="engineering_decision",
                requirements=requirements,
                policy=request.routing_policy,
                estimated_tokens=request.policy.max_total_tokens,
            )
        )

    def _execution_context(
        self,
        request: EngineeringDecisionRequest,
        provider_id: str,
        model_id: str,
    ) -> ExecutionContext:
        return ExecutionContext(
            prompt=_prompt_for(request),
            model_id=model_id,
            provider_id=provider_id,
            options=ExecutionOptions(
                temperature=1.0,
                max_tokens=request.policy.max_total_tokens,
                timeout_ms=request.policy.timeout_ms,
                retry_count=request.policy.max_attempts - 1,
                response_schema=engineering_decision_json_schema(
                    require_grounding_references=(
                        "snapshot_fingerprint" in request.context.truncation_metadata
                    ),
                ),
                metadata={"request_id": request.request_id, "schema_version": request.schema_version},
            ),
        )

    def _fallback_contexts(self, request: EngineeringDecisionRequest, selection) -> list[ExecutionContext]:
        if not request.policy.allow_fallback:
            return []
        return [
            self._execution_context(request, model.provider_id, model.id)
            for model in selection.alternatives
        ]

    def _failure(
        self,
        request: EngineeringDecisionRequest,
        trace_id: str,
        kind: GatewayErrorKind,
        message: str,
        *,
        selection=None,
        usage: GatewayUsage | None = None,
        trace: GatewayTrace | None = None,
        error: Exception | None = None,
        policy_violation: PolicyViolation | None = None,
    ) -> EngineeringDecisionResult:
        provider_id = selection.provider.id if selection is not None else None
        model_id = selection.model.id if selection is not None else None
        failure_trace = trace or GatewayTrace(trace_id=trace_id, request_id=request.request_id)
        gateway_error = GatewayError(
            kind=kind,
            message=message,
            retryable=kind
            in {GatewayErrorKind.PROVIDER_TIMEOUT, GatewayErrorKind.PROVIDER_TRANSIENT_FAILURE},
            provider_id=provider_id,
            model_id=model_id,
            attempts=failure_trace.attempts,
            trace_id=trace_id,
        )
        self._event_bus.publish(
            GatewayAttemptFailed(
                request_id=request.request_id,
                trace_id=trace_id,
                attempt=failure_trace.attempts,
                kind=kind,
            )
        )
        self._event_bus.publish(
            GatewayFailed(
                request_id=request.request_id,
                trace_id=trace_id,
                kind=kind,
                attempts=failure_trace.attempts,
            )
        )
        return EngineeringDecisionResult(
            success=False,
            error=gateway_error,
            selection=selection,
            usage=usage or GatewayUsage(),
            trace=failure_trace,
            policy_violation=policy_violation,
        )


def create_configured_gateway(settings: GatewaySettings, event_bus: EventBus) -> GatewayRuntime:
    """Compose a configured LiteLLM-backed gateway without altering default planner wiring."""
    if settings.provider_id != "litellm":
        raise ValueError("only the configured LiteLLM provider is supported by the initial gateway")
    if not settings.enabled:
        raise ValueError("gateway must be explicitly enabled before composition")

    api_key = settings.api_key.get_secret_value() if settings.api_key else None
    provider = LiteLLMProvider(api_key=api_key, api_base=settings.api_base)
    intelligence = IntelligenceRuntime(event_bus=event_bus)
    intelligence.providers.register(ProviderProfile(id="litellm", name="LiteLLM"))
    intelligence.models.register(
        ModelProfile(
            id=settings.model_id,
            provider_id="litellm",
            name=settings.model_id,
            traits=AITraits(
                reasoning=AIReasoningLevel.HIGH,
                context=AIContextSize.LARGE,
                speed=AISpeed.MEDIUM,
            ),
            capabilities=AICapabilities(
                supports_code=True,
                supports_json_schema=True,
                supports_function_calls=False,
            ),
        )
    )
    provider_registry = ExecutionProviderRegistry()
    provider_registry.register(provider)
    execution = ExecutionRuntime(registry=provider_registry)
    return GatewayRuntime(
        intelligence_runtime=intelligence,
        execution_runtime=execution,
        event_bus=event_bus,
    )


def _prompt_for(request: EngineeringDecisionRequest) -> str:
    """Render bounded factual request data; policy remains outside untrusted provider output."""
    context = {
        "repository_identity": request.context.repository_identity,
        "repository_summary": request.context.repository_summary,
        "source_findings": request.context.source_findings,
        "relevant_symbols": request.context.relevant_symbols,
        "known_constraints": request.context.known_constraints,
        "available_capabilities": request.allowed_capability_ids,
        "prior_evidence": request.context.prior_evidence,
        "provenance": request.context.provenance,
        "truncation_metadata": request.context.truncation_metadata,
        "schema_version": request.schema_version,
    }
    grounding_instruction = ""
    if "snapshot_fingerprint" in request.context.truncation_metadata:
        grounding_instruction = (
            "This is repository-aware context. Include the required grounding_references array using "
            "only provenance IDs supplied in Context.provenance; never invent a provenance ID.\n"
        )
    return (
        "Return only JSON matching the supplied schema. You are producing an advisory engineering "
        "decision, not executable instructions. Do not include commands, source code, tool calls, or "
        "capabilities outside the supplied allowlist.\n"
        f"{grounding_instruction}"
        f"Goal: {request.goal}\n"
        f"Context: {json.dumps(context, sort_keys=True, default=_json_default)}"
    )


def _json_default(value: object) -> object:
    """Serialize immutable context mappings without retaining any unsupported raw objects."""
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"unsupported context value: {type(value).__name__}")


def _trace_id(request_id: str) -> str:
    return f"gateway-{request_id}"


def _context_fingerprint(request: EngineeringDecisionRequest) -> str:
    precomputed = request.context.truncation_metadata.get("context_fingerprint")
    if isinstance(precomputed, str) and precomputed:
        return precomputed
    safe_context = {
        "repository_identity": request.context.repository_identity,
        "available_capabilities": request.allowed_capability_ids,
        "schema_version": request.schema_version,
    }
    return hashlib.sha256(json.dumps(safe_context, sort_keys=True).encode()).hexdigest()[:16]


def _classify_provider_error(error: Exception) -> GatewayErrorKind:
    if "timeout" in str(error).lower():
        return GatewayErrorKind.PROVIDER_TIMEOUT
    return GatewayErrorKind.PROVIDER_TRANSIENT_FAILURE


def _classify_execution_failure(error: str | None) -> GatewayErrorKind:
    if error and "timeout" in error.lower():
        return GatewayErrorKind.PROVIDER_TIMEOUT
    return GatewayErrorKind.ALL_ATTEMPTS_FAILED
