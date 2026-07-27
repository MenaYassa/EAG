"""Tests for the LiteLLM Provider Integration (Sprint 7.3D)."""
import os
import pytest
from unittest.mock import patch, MagicMock

# Add this import to check if litellm is installed
try:
    import litellm
except ImportError:
    litellm = None

from eag.chief.intelligence import AICapabilities, AITraits, ModelProfile
from eag.chief.intelligence.execution import (
    ExecutionContext,
    ExecutionOptions,
    ExecutionResult,
    ExecutionState,
    ProviderHealthStatus,
    ProviderRegistry,
    ExecutionRuntime,
)
from eag.chief.intelligence.execution.errors import ExecutionFailedError
from eag.chief.intelligence.execution.providers import LiteLLMProvider


@pytest.fixture
def provider() -> LiteLLMProvider:
    return LiteLLMProvider(api_key="test_key")

@pytest.fixture
def registry(provider: LiteLLMProvider) -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(provider)
    return reg

@pytest.fixture
def runtime(registry: ProviderRegistry) -> ExecutionRuntime:
    return ExecutionRuntime(registry=registry)

def make_context(provider_id: str = "litellm", model_id: str = "gpt-4o") -> ExecutionContext:
    return ExecutionContext(prompt="Hello", model_id=model_id, provider_id=provider_id)

def mock_litellm_response():
    """Creates a mock response mimicking litellm.completion output."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Hi there!"
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 5
    mock_resp.usage.completion_tokens = 3
    mock_resp.usage.total_tokens = 8
    return mock_resp


class TestLiteLLMProvider:
    def test_provider_id(self, provider: LiteLLMProvider) -> None:
        assert provider.provider_id == "litellm"

    def test_models_returns_tuple(self, provider: LiteLLMProvider) -> None:
        models = provider.models()
        assert isinstance(models, tuple)
        assert len(models) > 0

    def test_models_contain_gpt4o(self, provider: LiteLLMProvider) -> None:
        models = provider.models()
        assert any(m.id == "gpt-4o" for m in models)

    def test_supports_gpt4o(self, provider: LiteLLMProvider) -> None:
        assert provider.supports("gpt-4o") is True

    def test_does_not_support_unknown(self, provider: LiteLLMProvider) -> None:
        assert provider.supports("unknown-model") is False

    def test_health_returns_healthy(self, provider: LiteLLMProvider) -> None:
        health = provider.health()
        assert health.status == ProviderHealthStatus.HEALTHY
        assert health.provider_id == "litellm"

    @patch("eag.chief.intelligence.execution.providers.litellm_provider.litellm")
    def test_execute_success(self, mock_litellm, provider: LiteLLMProvider) -> None:
        mock_litellm.completion.return_value = mock_litellm_response()
        
        ctx = make_context()
        result = provider.execute(ctx)
        
        assert result.success is True
        assert result.content == "Hi there!"
        assert result.state == ExecutionState.SUCCESS
        assert result.usage.total_tokens == 8
        assert result.provider_id == "litellm"
        assert result.model_id == "gpt-4o"
        
        # Verify litellm was called correctly
        mock_litellm.completion.assert_called_once_with(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=1000,
            api_key="test_key"
        )

    @patch("eag.chief.intelligence.execution.providers.litellm_provider.litellm")
    def test_execute_failure_raises(self, mock_litellm, provider: LiteLLMProvider) -> None:
        mock_litellm.completion.side_effect = Exception("API Error")
        
        ctx = make_context()
        with pytest.raises(ExecutionFailedError) as exc_info:
            provider.execute(ctx)
            
        assert "API Error" in str(exc_info.value)

    @patch("eag.chief.intelligence.execution.providers.litellm_provider.litellm")
    def test_execute_passes_options(self, mock_litellm, provider: LiteLLMProvider) -> None:
        mock_litellm.completion.return_value = mock_litellm_response()
        
        opts = ExecutionOptions(temperature=0.1, max_tokens=50)
        ctx = ExecutionContext(prompt="Test", model_id="gpt-4o", provider_id="litellm", options=opts)
        provider.execute(ctx)
        
        _, kwargs = mock_litellm.completion.call_args
        assert kwargs["temperature"] == 0.1
        assert kwargs["max_tokens"] == 50

    @patch("eag.chief.intelligence.execution.providers.litellm_provider.litellm")
    def test_runtime_integration_success(self, mock_litellm, runtime: ExecutionRuntime) -> None:
        mock_litellm.completion.return_value = mock_litellm_response()
        
        ctx = make_context()
        result = runtime.execute(ctx)
        
        assert result.success is True
        assert result.content == "Hi there!"
        assert len(result.trace.events) > 0

    @patch("eag.chief.intelligence.execution.providers.litellm_provider.litellm")
    def test_runtime_integration_failure(self, mock_litellm, runtime: ExecutionRuntime) -> None:
        mock_litellm.completion.side_effect = Exception("API Error")
        
        ctx = make_context()
        result = runtime.execute(ctx)
        
        # Runtime catches the exception and returns a failed result
        assert result.success is False
        assert result.state == ExecutionState.FAILED
        assert "API Error" in result.error
        assert any(e.type == "failed" for e in result.trace.events)

    def test_provider_registers_in_registry(self, registry: ProviderRegistry) -> None:
        assert registry.find("litellm") is not None

    # --- Real Integration Test ---
    # This test makes a real network call to the provided LiteLLM endpoint.
    @pytest.mark.integration
    def test_real_litellm_integration(self) -> None:
        if litellm is None:
            pytest.fail("litellm package is not installed. Please run `uv add litellm`.")
        
        # Pull secrets from the environment
        api_key = os.getenv("LITELLM_TEST_API_KEY")
        api_base = os.getenv("LITELLM_TEST_API_BASE")

        # Gracefully skip if credentials aren't present (e.g., in CI/CD pipelines)
        if not api_key or not api_base:
            pytest.skip("Integration credentials not found in environment. Skipping.")
            
        provider = LiteLLMProvider(
            api_key=api_key,
            api_base=api_base
        )
        
        ctx = ExecutionContext(
            prompt="Say 'Hello EAG!' and nothing else.",
            model_id="z-ai/glm-5.2",
            provider_id="litellm",
            options=ExecutionOptions(max_tokens=50, temperature=1.0)
        )
        
        # We let the test fail loudly to see the exact API error
        result = provider.execute(ctx)
        
        assert result.success is True
        assert "Hello EAG!" in result.content
        assert result.usage.total_tokens > 0
        print(f"\nReal LLM Response: {result.content}")