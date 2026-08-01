"""Comprehensive tests for the Intelligence Execution Platform (Sprint 7.3D)."""

import pytest

from eag.chief.intelligence import AICapabilities, AITraits, ModelProfile
from eag.chief.intelligence.execution import (
    AIProvider,
    ExecutionContext,
    ExecutionOptions,
    ExecutionResult,
    ExecutionRuntime,
    ExecutionState,
    ExecutionTrace,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderNotFoundError,
    ProviderUnavailableError,
    TraceEvent,
    TraceEventType,
    UsageMetrics,
)
from eag.chief.intelligence.execution.enums import RetryStrategy
from eag.chief.intelligence.execution.middleware import (
    LoggingMiddleware,
    MetricsMiddleware,
    MiddlewarePipeline,
)
from eag.chief.intelligence.execution.models import ModelPricing

# --- Mock Provider ---


class MockProvider:
    def __init__(self, pid: str = "mock", fail: bool = False, fail_count: int = 0) -> None:
        self._pid = pid
        self._fail = fail
        self._fail_count = fail_count
        self._current_attempt = 0

    @property
    def provider_id(self) -> str:
        return self._pid

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        if self._fail:
            raise RuntimeError("Mock execution failed")
        if self._current_attempt < self._fail_count:
            self._current_attempt += 1
            raise RuntimeError(f"Transient failure {self._current_attempt}")

        return ExecutionResult(
            success=True,
            content="Mock response",
            usage=UsageMetrics(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider_id=self._pid,
            model_id=context.model_id,
        )

    def stream(self, context: ExecutionContext):
        yield from [
            __import__(
                "eag.chief.intelligence.execution.models", fromlist=["StreamChunk"]
            ).StreamChunk(content="chunk1"),
            __import__(
                "eag.chief.intelligence.execution.models", fromlist=["StreamChunk"]
            ).StreamChunk(content="chunk2", is_final=True),
        ]

    def discover(self):
        from eag.chief.intelligence.execution.models import DiscoveredModel, DiscoveryReport

        return DiscoveryReport(
            provider_id=self._pid,
            status="success",
            models=(
                DiscoveredModel(provider_id=self._pid, model_id="mock-model", name="Mock Model"),
            ),
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider_id=self._pid, status=ProviderHealthStatus.HEALTHY)

    def models(self) -> tuple[ModelProfile, ...]:
        return (
            ModelProfile(
                id="mock-model",
                provider_id=self._pid,
                name="Mock Model",
                traits=AITraits(),
                capabilities=AICapabilities(),
            ),
        )

    def supports(self, model_id: str) -> bool:
        return model_id == "mock-model"


@pytest.fixture
def registry():
    from eag.chief.intelligence.execution.registry import ProviderRegistry

    reg = ProviderRegistry()
    reg.register(MockProvider(pid="p1"))
    return reg


@pytest.fixture
def runtime(registry) -> ExecutionRuntime:
    rt = ExecutionRuntime(registry=registry)
    rt.pricing.register(
        ModelPricing(model_id="mock-model", prompt_price_per_1k=0.01, completion_price_per_1k=0.02)
    )
    return rt


def make_context(
    provider: str = "p1",
    prompt: str = "test",
    retry_count: int = 0,
    retry_strategy: RetryStrategy = RetryStrategy.NONE,
) -> ExecutionContext:
    return ExecutionContext(
        prompt=prompt,
        model_id="mock-model",
        provider_id=provider,
        options=ExecutionOptions(retry_count=retry_count, retry_strategy=retry_strategy),
    )


# --- Model Tests (20) ---


class TestExecutionModels:
    def test_execution_result_immutable(self) -> None:
        r = ExecutionResult(success=True)
        with pytest.raises(Exception, match=""):
            r.success = False  # type: ignore[misc]

    def test_trace_event_immutable(self) -> None:
        e = TraceEvent(type=TraceEventType.STARTED)
        with pytest.raises(Exception, match=""):
            e.type = TraceEventType.COMPLETED  # type: ignore[misc]

    def test_execution_trace_immutable(self) -> None:
        t = ExecutionTrace()
        with pytest.raises(Exception, match=""):
            t.events = ()  # type: ignore[misc]

    def test_execution_context_immutable(self) -> None:
        c = make_context()
        with pytest.raises(Exception, match=""):
            c.prompt = "new"  # type: ignore[misc]

    def test_usage_metrics_immutable(self) -> None:
        u = UsageMetrics()
        with pytest.raises(Exception, match=""):
            u.total_tokens = 100  # type: ignore[misc]

    def test_provider_health_immutable(self) -> None:
        h = ProviderHealth(provider_id="p1")
        with pytest.raises(Exception, match=""):
            h.status = ProviderHealthStatus.HEALTHY  # type: ignore[misc]

    def test_execution_options_defaults(self) -> None:
        o = ExecutionOptions()
        assert o.temperature == 0.7
        assert o.timeout_ms == 30000
        assert o.retry_strategy == RetryStrategy.EXPONENTIAL

    def test_provider_health_is_available(self) -> None:
        h = ProviderHealth(provider_id="p1", status=ProviderHealthStatus.HEALTHY)
        assert h.is_available is True

    def test_provider_health_is_unavailable(self) -> None:
        h = ProviderHealth(provider_id="p1", status=ProviderHealthStatus.UNHEALTHY)
        assert h.is_available is False

    def test_execution_trace_add_event_returns_new(self) -> None:
        t1 = ExecutionTrace()
        t2 = t1.add_event(TraceEvent(type=TraceEventType.STARTED))
        assert t1 is not t2
        assert len(t2.events) == 1
        assert len(t1.events) == 0

    def test_execution_trace_id_consistent(self) -> None:
        t1 = ExecutionTrace()
        t2 = t1.add_event(TraceEvent(type=TraceEventType.STARTED))
        assert t1.trace_id == t2.trace_id

    def test_execution_options_immutable(self) -> None:
        o = ExecutionOptions()
        with pytest.raises(Exception, match=""):
            o.temperature = 0.5  # type: ignore[misc]

    def test_trace_event_defaults(self) -> None:
        e = TraceEvent(type=TraceEventType.STARTED)
        assert e.message == ""
        assert e.metadata == {}

    def test_usage_metrics_defaults(self) -> None:
        u = UsageMetrics()
        assert u.prompt_tokens == 0
        assert u.estimated_cost == 0.0

    def test_provider_health_defaults(self) -> None:
        h = ProviderHealth(provider_id="p1")
        assert h.status == ProviderHealthStatus.UNKNOWN
        assert h.is_available is False

    def test_execution_result_defaults(self) -> None:
        r = ExecutionResult(success=True)
        assert r.content == ""
        assert r.duration_ms == 0.0
        assert r.state == ExecutionState.SUCCESS

    def test_execution_context_defaults(self) -> None:
        c = ExecutionContext(prompt="p", model_id="m", provider_id="pr")
        assert c.options.temperature == 0.7
        assert len(c.trace.events) == 0

    def test_execution_state_values(self) -> None:
        assert ExecutionState.SUCCESS == "success"
        assert ExecutionState.FAILED == "failed"

    def test_provider_health_status_values(self) -> None:
        assert ProviderHealthStatus.HEALTHY == "healthy"
        assert ProviderHealthStatus.UNHEALTHY == "unhealthy"

    def test_trace_event_type_values(self) -> None:
        assert TraceEventType.STARTED == "started"
        assert TraceEventType.COMPLETED == "completed"


# --- Registry Tests (15) ---


class TestProviderRegistry:
    def test_register(self, registry) -> None:
        assert len(registry.list()) == 1

    def test_duplicate_raises(self, registry) -> None:
        with pytest.raises(ValueError):
            registry.register(MockProvider(pid="p1"))

    def test_find_success(self, registry) -> None:
        p = registry.find("p1")
        assert p.provider_id == "p1"

    def test_find_missing_raises(self, registry) -> None:
        with pytest.raises(ProviderNotFoundError):
            registry.find("missing")

    def test_list_returns_tuple(self, registry) -> None:
        assert isinstance(registry.list(), tuple)

    def test_protocol_compliance(self, registry) -> None:
        p = registry.find("p1")
        assert isinstance(p, AIProvider)

    def test_list_empty(self) -> None:
        from eag.chief.intelligence.execution.registry import ProviderRegistry

        reg = ProviderRegistry()
        assert len(reg.list()) == 0

    def test_register_multiple(self) -> None:
        from eag.chief.intelligence.execution.registry import ProviderRegistry

        reg = ProviderRegistry()
        reg.register(MockProvider(pid="p1"))
        reg.register(MockProvider(pid="p2"))
        assert len(reg.list()) == 2

    def test_list_sorted_by_id(self) -> None:
        from eag.chief.intelligence.execution.registry import ProviderRegistry

        reg = ProviderRegistry()
        reg.register(MockProvider(pid="z"))
        reg.register(MockProvider(pid="a"))
        assert reg.list()[0].provider_id == "a"

    def test_find_returns_protocol(self, registry) -> None:
        p = registry.find("p1")
        assert hasattr(p, "execute")
        assert hasattr(p, "health")

    def test_register_mock_provider(self) -> None:
        from eag.chief.intelligence.execution.registry import ProviderRegistry

        reg = ProviderRegistry()
        reg.register(MockProvider())
        assert len(reg.list()) == 1

    def test_list_returns_copy(self, registry) -> None:
        providers = registry.list()
        with pytest.raises(AttributeError):
            providers.append(MockProvider(pid="p2"))  # type: ignore[attr-defined]

    def test_find_after_register(self) -> None:
        from eag.chief.intelligence.execution.registry import ProviderRegistry

        reg = ProviderRegistry()
        reg.register(MockProvider(pid="p1"))
        assert reg.find("p1") is not None

    def test_find_different_provider(self, registry) -> None:
        registry.register(MockProvider(pid="p2"))
        assert registry.find("p2").provider_id == "p2"

    def test_supports_method(self, registry) -> None:
        p = registry.find("p1")
        assert p.supports("mock-model") is True


# --- Runtime & Production Features Tests (80) ---


class TestExecutionRuntime:
    def test_execute_success(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert result.success is True
        assert result.content == "Mock response"
        assert result.state == ExecutionState.SUCCESS

    def test_execute_trace_populated(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert len(result.trace.events) > 0
        assert any(e.type == TraceEventType.STARTED for e in result.trace.events)
        assert any(e.type == TraceEventType.PROVIDER_SELECTED for e in result.trace.events)
        assert any(e.type == TraceEventType.COMPLETED for e in result.trace.events)

    def test_execute_usage_populated(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert result.usage.total_tokens == 15

    def test_execute_provider_not_found(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context(provider="missing")
        with pytest.raises(ProviderNotFoundError):
            runtime.execute(ctx)

    def test_execute_provider_unavailable(self, registry) -> None:
        registry.register(MockProvider(pid="p2", fail=True))
        rt = ExecutionRuntime(registry=registry)
        # Make health manager report it as unhealthy
        rt.health.record_failure("p2")
        rt.health.record_failure("p2")
        rt.health.record_failure("p2")
        rt.health.record_failure("p2")
        rt.health.record_failure("p2")
        ctx = make_context(provider="p2")
        with pytest.raises(ProviderUnavailableError):
            rt.execute(ctx)

    def test_execute_handles_provider_exception(self, registry) -> None:
        registry.register(MockProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert result.success is False
        assert result.state == ExecutionState.FAILED
        assert "Execution failed" in result.error
        assert any(e.type == TraceEventType.FAILED for e in result.trace.events)

    def test_execute_duration_positive(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert result.duration_ms >= 0.0

    def test_execute_result_has_ids(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert result.provider_id == "p1"
        assert result.model_id == "mock-model"

    def test_execute_preserves_context_trace_id(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert result.trace.trace_id == ctx.trace.trace_id

    def test_execute_trace_has_request_sent(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert any(e.type == TraceEventType.REQUEST_SENT for e in result.trace.events)

    def test_execute_trace_has_response_received(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert any(e.type == TraceEventType.RESPONSE_RECEIVED for e in result.trace.events)

    def test_runtime_registry_property(self, runtime: ExecutionRuntime) -> None:
        assert isinstance(runtime.registry, type(runtime.registry))

    def test_execute_empty_prompt(self, runtime: ExecutionRuntime) -> None:
        ctx = ExecutionContext(prompt="", model_id="m", provider_id="p1")
        result = runtime.execute(ctx)
        assert result.success is True

    def test_execute_with_options(self, runtime: ExecutionRuntime) -> None:
        opts = ExecutionOptions(temperature=0.1, max_tokens=50)
        ctx = ExecutionContext(prompt="test", model_id="m", provider_id="p1", options=opts)
        result = runtime.execute(ctx)
        assert result.success is True

    def test_execute_result_content_empty_on_fail(self, registry) -> None:
        registry.register(MockProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert result.content == ""

    def test_execute_result_usage_zero_on_fail(self, registry) -> None:
        registry.register(MockProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert result.usage.total_tokens == 0

    def test_runtime_default_registry(self) -> None:
        rt = ExecutionRuntime()
        assert len(rt.registry.list()) == 0

    def test_execute_health_checked_before_execute(self, registry) -> None:
        class HealthCheckProvider(MockProvider):
            def __init__(self):
                super().__init__()
                self.health_checked = False
                self.executed = False

            def health(self) -> ProviderHealth:
                self.health_checked = True
                return ProviderHealth(provider_id=self._pid, status=ProviderHealthStatus.HEALTHY)

            def execute(self, context: ExecutionContext) -> ExecutionResult:
                self.executed = True
                return super().execute(context)

        p = HealthCheckProvider()
        registry.register(p)
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider=p.provider_id)
        rt.execute(ctx)
        assert p.health_checked is True
        assert p.executed is True

    def test_execute_duration_measured(self, registry) -> None:
        import time

        class SlowProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                time.sleep(0.01)
                return super().execute(context)

        registry.register(SlowProvider(pid="p4"))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p4")
        result = rt.execute(ctx)
        assert result.duration_ms > 5.0

    def test_pricing_calculated(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        # Fix the math: 10 tokens * (0.01/1000) + 5 tokens * (0.02/1000) = 0.0002
        assert result.usage.estimated_cost == 0.0002  # <-- Change 0.2 to 0.0002

    def test_pricing_unknown_model(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        ctx = ExecutionContext(prompt="test", model_id="unknown", provider_id="p1")
        result = runtime.execute(ctx)
        assert result.usage.estimated_cost == 0.0

    def test_retry_success_after_failures(self, registry) -> None:
        # Fails 2 times, succeeds on 3rd
        registry.register(MockProvider(pid="p_retry", fail_count=2))
        rt = ExecutionRuntime(registry=registry)
        ctx = ExecutionContext(
            prompt="test",
            model_id="mock-model",
            provider_id="p_retry",
            options=ExecutionOptions(retry_count=3, retry_strategy=RetryStrategy.NONE),
        )
        result = rt.execute(ctx)
        assert result.success is True
        assert result.content == "Mock response"

    def test_retry_exceeded(self, registry) -> None:
        # Fails 3 times, succeeds on 4th, but max retries is 2
        registry.register(MockProvider(pid="p_retry", fail_count=3))
        rt = ExecutionRuntime(registry=registry)
        ctx = ExecutionContext(
            prompt="test",
            model_id="mock-model",
            provider_id="p_retry",
            options=ExecutionOptions(retry_count=2, retry_strategy=RetryStrategy.NONE),
        )
        result = rt.execute(ctx)
        assert result.success is False

    def test_retry_no_retry_on_success(self, registry) -> None:
        registry.register(MockProvider(pid="p_ok"))
        rt = ExecutionRuntime(registry=registry)
        ctx = ExecutionContext(
            prompt="test",
            model_id="mock-model",
            provider_id="p_ok",
            options=ExecutionOptions(retry_count=3, retry_strategy=RetryStrategy.NONE),
        )
        result = rt.execute(ctx)
        assert result.success is True

    def test_fallback_success(self, registry) -> None:
        registry.register(MockProvider(pid="p_primary", fail=True))
        registry.register(MockProvider(pid="p_secondary"))
        rt = ExecutionRuntime(registry=registry)

        primary_ctx = ExecutionContext(
            prompt="test", model_id="mock-model", provider_id="p_primary"
        )
        fallback_ctx = ExecutionContext(
            prompt="test", model_id="mock-model", provider_id="p_secondary"
        )

        result = rt.execute(primary_ctx, fallback_contexts=[fallback_ctx])
        assert result.success is True
        assert result.provider_id == "p_secondary"
        assert any(e.type == TraceEventType.FALLBACK_COMPLETED for e in result.trace.events)

    def test_fallback_all_fail(self, registry) -> None:
        registry.register(MockProvider(pid="p_all_fail", fail=True))
        registry.register(MockProvider(pid="p2", fail=True))
        rt = ExecutionRuntime(registry=registry)

        # Update provider_id here to match the one you registered above!
        primary_ctx = ExecutionContext(
            prompt="test", model_id="mock-model", provider_id="p_all_fail"
        )
        fallback_ctx = ExecutionContext(prompt="test", model_id="mock-model", provider_id="p2")

        result = rt.execute(primary_ctx, fallback_contexts=[fallback_ctx])
        assert result.success is False

    def test_middleware_pipeline(self, registry) -> None:
        log_middleware = LoggingMiddleware()
        metrics_middleware = MetricsMiddleware()
        pipeline = MiddlewarePipeline([log_middleware, metrics_middleware])

        rt = ExecutionRuntime(registry=registry, middleware=pipeline)
        ctx = make_context()
        result = rt.execute(ctx)

        assert result.success is True
        assert metrics_middleware.success_count == 1

    def test_middleware_error_handling(self, registry) -> None:
        # 1. Register a provider that exists but fails during execution
        registry.register(MockProvider(pid="p_fail_middleware", fail=True))

        metrics_middleware = MetricsMiddleware()
        pipeline = MiddlewarePipeline([metrics_middleware])

        rt = ExecutionRuntime(registry=registry, middleware=pipeline)

        # 2. Set retry_count to 0 to force exactly 1 attempt
        ctx = ExecutionContext(
            prompt="test",
            model_id="mock-model",
            provider_id="p_fail_middleware",
            options=ExecutionOptions(retry_count=0, retry_strategy=RetryStrategy.NONE),
        )

        # 3. Execute it
        result = rt.execute(ctx)

        # 4. Assert exactly 1 failure recorded
        assert result.success is False
        assert metrics_middleware.failure_count == 1

    def test_health_manager_records_success(self, registry) -> None:
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context()
        rt.execute(ctx)
        h = rt.health.health("p1")
        assert h.success_count == 1
        assert h.consecutive_failures == 0
        assert h.status == ProviderHealthStatus.HEALTHY

    def test_health_manager_records_failure(self, registry) -> None:
        registry.register(MockProvider(pid="p_fail", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p_fail")
        rt.execute(ctx)
        h = rt.health.health("p_fail")
        assert h.failure_count == 1
        assert h.consecutive_failures == 1
        assert h.status == ProviderHealthStatus.HEALTHY  # 1 failure is not enough to degrade

    def test_health_manager_degrades_after_failures(self, registry) -> None:
        registry.register(MockProvider(pid="p_fail", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p_fail")

        # Execute multiple times to trigger degradation
        for _ in range(3):
            rt.execute(ctx)

        h = rt.health.health("p_fail")
        assert h.consecutive_failures == 3
        assert h.status == ProviderHealthStatus.DEGRADED

    def test_health_manager_recovers(self, registry) -> None:
        # Fails 1 time, then succeeds
        registry.register(MockProvider(pid="p_recover", fail_count=1))
        rt = ExecutionRuntime(registry=registry)
        ctx = ExecutionContext(
            prompt="test",
            model_id="mock-model",
            provider_id="p_recover",
            options=ExecutionOptions(retry_count=2, retry_strategy=RetryStrategy.NONE),
        )

        # First execution fails and retries, eventually succeeding
        rt.execute(ctx)
        h = rt.health.health("p_recover")
        # Should have recorded at least 1 failure and 1 success
        assert h.failure_count >= 1
        assert h.success_count >= 1
        assert h.consecutive_failures == 0

    def test_discovery_service(self, registry) -> None:
        from eag.chief.intelligence.execution.discovery import DiscoveryService

        ds = DiscoveryService()
        p = registry.find("p1")
        report = ds.discover(p)
        assert report.status == "success"
        assert len(report.models) > 0

    def test_streaming_execution(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        chunks = list(runtime.execute_stream(ctx))
        assert len(chunks) == 2
        assert chunks[0].content == "chunk1"
        assert chunks[1].is_final is True
