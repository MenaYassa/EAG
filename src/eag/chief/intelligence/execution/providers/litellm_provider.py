"""LiteLLM provider implementation for EAG."""

import time

try:
    import litellm
except ImportError:
    litellm = None  # Allow module to load if not installed, but fail on execution

from eag.chief.intelligence.enums import AIContextSize, AIReasoningLevel, AISpeed
from eag.chief.intelligence.execution.enums import (
    ExecutionState,
    ProviderHealthStatus,
    TraceEventType,
)
from eag.chief.intelligence.execution.errors import ExecutionFailedError
from eag.chief.intelligence.execution.models import (
    ExecutionContext,
    ExecutionResult,
    ProviderHealth,
    TraceEvent,
    UsageMetrics,
)
from eag.chief.intelligence.models import AICapabilities, AITraits, ModelProfile


class LiteLLMProvider:
    """Concrete AIProvider implementation using the LiteLLM library."""

    def __init__(self, api_key: str | None = None, api_base: str | None = None) -> None:
        self._api_key = api_key
        self._api_base = api_base
        self._models: list[ModelProfile] = self._initialize_models()

    @property
    def provider_id(self) -> str:
        return "litellm"

    def _initialize_models(self) -> list[ModelProfile]:
        """Returns the static list of models exposed via LiteLLM."""
        return [
            ModelProfile(
                id="gpt-5.5-free",
                provider_id="litellm",
                name="GPT-5.5 Free",
                traits=AITraits(
                    reasoning=AIReasoningLevel.HIGH, context=AIContextSize.LARGE, speed=AISpeed.FAST
                ),
                capabilities=AICapabilities(
                    supports_code=True, supports_json_schema=True, supports_function_calls=True
                ),
                estimated_cost="very_low",
            ),
            ModelProfile(
                id="gpt-4o",
                provider_id="litellm",
                name="GPT-4o",
                traits=AITraits(
                    reasoning=AIReasoningLevel.HIGH, context=AIContextSize.LARGE, speed=AISpeed.FAST
                ),
                capabilities=AICapabilities(
                    supports_code=True, supports_json_schema=True, supports_function_calls=True
                ),
                estimated_cost="medium",
            ),
            ModelProfile(
                id="claude-3-5-sonnet-20240620",
                provider_id="litellm",
                name="Claude 3.5 Sonnet",
                traits=AITraits(
                    reasoning=AIReasoningLevel.EXTREME,
                    context=AIContextSize.LARGE,
                    speed=AISpeed.FAST,
                ),
                capabilities=AICapabilities(
                    supports_code=True, supports_json_schema=True, supports_function_calls=True
                ),
                estimated_cost="medium",
            ),
        ]

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Executes a completion request via LiteLLM."""
        if litellm is None:
            raise ExecutionFailedError("litellm package is not installed.")

        start_time = time.monotonic()

        try:
            kwargs = {
                "model": context.model_id,
                "messages": [{"role": "user", "content": context.prompt}],
                "temperature": context.options.temperature,
                "max_tokens": context.options.max_tokens,
                "timeout": context.options.timeout_ms / 1000,
            }

            if context.options.response_schema is not None:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "engineering_decision",
                        "strict": True,
                        "schema": dict(context.options.response_schema),
                    },
                }

            if self._api_key:
                kwargs["api_key"] = self._api_key
            if self._api_base:
                kwargs["api_base"] = self._api_base
                # Crucial: Tell LiteLLM to treat this as an OpenAI-compatible endpoint
                # so it doesn't try to guess the provider from the model name.
                kwargs["custom_llm_provider"] = "openai"

            response = litellm.completion(**kwargs)

            duration = (time.monotonic() - start_time) * 1000

            # Safeguard against empty or None content (e.g., thinking models or token limits)
            message = response.choices[0].message
            content = message.content or getattr(message, "reasoning_content", "") or ""
            usage = response.usage

            return ExecutionResult(
                success=True,
                content=content,
                usage=UsageMetrics(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                ),
                duration_ms=duration,
                provider_id=self.provider_id,
                model_id=context.model_id,
                state=ExecutionState.SUCCESS,
                trace=context.trace.add_event(TraceEvent(type=TraceEventType.COMPLETED)),
            )

        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            raise ExecutionFailedError(f"LiteLLM execution failed: {e}") from e

    def health(self) -> ProviderHealth:
        """Checks the health of the LiteLLM proxy/service."""
        return ProviderHealth(
            provider_id=self.provider_id, status=ProviderHealthStatus.HEALTHY, latency_ms=50.0
        )

    def models(self) -> tuple[ModelProfile, ...]:
        """Returns the models supported by this provider."""
        return tuple(self._models)

    def supports(self, model_id: str) -> bool:
        """Checks if a specific model is supported."""
        return any(m.id == model_id for m in self._models)
