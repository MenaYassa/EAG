"""Comprehensive tests for the Intelligence Execution Platform (Sprint 7.3C)."""

import pytest
from datetime import datetime, UTC
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
    ProviderRegistry,
    ProviderUnavailableError,
    TraceEvent,
    TraceEventType,
    UsageMetrics,
)


# --- Mock Provider ---

# Update the MockProvider class in tests/test_chief_intelligence_execution.py

class MockProvider:
    def __init__(self, pid: str = "mock", fail: bool = False, unhealthy: bool = False) -> None:
        self._pid = pid
        self._fail = fail
        self._unhealthy = unhealthy

    @property
    def provider_id(self) -> str:
        return self._pid

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        if self._fail:
            raise RuntimeError("Mock execution failed")
        return ExecutionResult(
            success=True,
            content="Mock response",
            usage=UsageMetrics(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider_id=self._pid,
            model_id=context.model_id
        )

    def health(self) -> ProviderHealth:
        # Report unhealthy only if the unhealthy flag is set
        status = ProviderHealthStatus.UNHEALTHY if self._unhealthy else ProviderHealthStatus.HEALTHY
        return ProviderHealth(
            provider_id=self._pid,
            status=status
        )

    def models(self) -> tuple[ModelProfile, ...]:
        return (
            ModelProfile(
                id="mock-model",
                provider_id=self._pid,
                name="Mock Model",
                traits=AITraits(),
                capabilities=AICapabilities()
            ),
        )

    def supports(self, model_id: str) -> bool:
        return model_id == "mock-model"


@pytest.fixture
def registry() -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(MockProvider(pid="p1"))
    return reg

@pytest.fixture
def runtime(registry: ProviderRegistry) -> ExecutionRuntime:
    return ExecutionRuntime(registry=registry)

def make_context(provider: str = "p1", prompt: str = "test") -> ExecutionContext:
    return ExecutionContext(prompt=prompt, model_id="mock-model", provider_id=provider)


# --- Model Tests (20) ---

class TestExecutionModels:
    def test_execution_result_immutable(self) -> None:
        r = ExecutionResult(success=True)
        with pytest.raises(Exception):
            r.success = False  # type: ignore[misc]

    def test_trace_event_immutable(self) -> None:
        e = TraceEvent(type=TraceEventType.STARTED)
        with pytest.raises(Exception):
            e.type = TraceEventType.COMPLETED  # type: ignore[misc]

    def test_execution_trace_immutable(self) -> None:
        t = ExecutionTrace()
        with pytest.raises(Exception):
            t.events = ()  # type: ignore[misc]

    def test_execution_context_immutable(self) -> None:
        c = make_context()
        with pytest.raises(Exception):
            c.prompt = "new"  # type: ignore[misc]

    def test_usage_metrics_immutable(self) -> None:
        u = UsageMetrics()
        with pytest.raises(Exception):
            u.total_tokens = 100  # type: ignore[misc]

    def test_provider_health_immutable(self) -> None:
        h = ProviderHealth(provider_id="p1")
        with pytest.raises(Exception):
            h.status = ProviderHealthStatus.HEALTHY  # type: ignore[misc]

    def test_execution_options_defaults(self) -> None:
        o = ExecutionOptions()
        assert o.temperature == 0.7
        assert o.timeout_ms == 30000

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
        with pytest.raises(Exception):
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
    def test_register(self, registry: ProviderRegistry) -> None:
        assert len(registry.list()) == 1

    def test_duplicate_raises(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ValueError):
            registry.register(MockProvider(pid="p1"))

    def test_find_success(self, registry: ProviderRegistry) -> None:
        p = registry.find("p1")
        assert p.provider_id == "p1"

    def test_find_missing_raises(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ProviderNotFoundError):
            registry.find("missing")

    def test_list_returns_tuple(self, registry: ProviderRegistry) -> None:
        assert isinstance(registry.list(), tuple)

    def test_protocol_compliance(self, registry: ProviderRegistry) -> None:
        p = registry.find("p1")
        assert isinstance(p, AIProvider)

    def test_list_empty(self) -> None:
        reg = ProviderRegistry()
        assert len(reg.list()) == 0

    def test_register_multiple(self) -> None:
        reg = ProviderRegistry()
        reg.register(MockProvider(pid="p1"))
        reg.register(MockProvider(pid="p2"))
        assert len(reg.list()) == 2

    def test_list_sorted_by_id(self) -> None:
        reg = ProviderRegistry()
        reg.register(MockProvider(pid="z"))
        reg.register(MockProvider(pid="a"))
        assert reg.list()[0].provider_id == "a"

    def test_find_returns_protocol(self, registry: ProviderRegistry) -> None:
        p = registry.find("p1")
        assert hasattr(p, "execute")
        assert hasattr(p, "health")

    def test_register_mock_provider(self) -> None:
        reg = ProviderRegistry()
        reg.register(MockProvider())
        assert len(reg.list()) == 1

    def test_register_custom_provider(self) -> None:
        class CustomProvider:
            @property
            def provider_id(self) -> str: return "custom"
            def execute(self, c): pass
            def health(self): pass
            def models(self): return ()
            def supports(self, m): return False
            
        reg = ProviderRegistry()
        reg.register(CustomProvider())
        assert len(reg.list()) == 1

    def test_list_returns_copy(self, registry: ProviderRegistry) -> None:
        providers = registry.list()
        with pytest.raises(AttributeError):
            providers.append(MockProvider(pid="p2"))  # type: ignore[attr-defined]

    def test_find_after_register(self) -> None:
        reg = ProviderRegistry()
        reg.register(MockProvider(pid="p1"))
        assert reg.find("p1") is not None

    def test_find_different_provider(self, registry: ProviderRegistry) -> None:
        registry.register(MockProvider(pid="p2"))
        assert registry.find("p2").provider_id == "p2"


# --- Runtime Tests (30) ---

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

# Update the test_execute_provider_unavailable test in TestExecutionRuntime

    def test_execute_provider_unavailable(self, registry: ProviderRegistry) -> None:
        registry.register(MockProvider(pid="p2", unhealthy=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p2")
        with pytest.raises(ProviderUnavailableError):
            rt.execute(ctx)

    def test_execute_handles_provider_exception(self, registry: ProviderRegistry) -> None:
        class FailProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                raise RuntimeError("Boom")
                
        registry.register(FailProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert result.success is False
        assert result.state == ExecutionState.FAILED
        assert "Boom" in result.error
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

    def test_execute_failed_trace_no_response_received(self, registry: ProviderRegistry) -> None:
        class FailProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                raise RuntimeError("Boom")
                
        registry.register(FailProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert not any(e.type == TraceEventType.RESPONSE_RECEIVED for e in result.trace.events)

    def test_runtime_registry_property(self, runtime: ExecutionRuntime) -> None:
        assert isinstance(runtime.registry, ProviderRegistry)

    def test_execute_empty_prompt(self, runtime: ExecutionRuntime) -> None:
        ctx = ExecutionContext(prompt="", model_id="m", provider_id="p1")
        result = runtime.execute(ctx)
        assert result.success is True

    def test_execute_with_options(self, runtime: ExecutionRuntime) -> None:
        opts = ExecutionOptions(temperature=0.1, max_tokens=50)
        ctx = ExecutionContext(prompt="test", model_id="m", provider_id="p1", options=opts)
        result = runtime.execute(ctx)
        assert result.success is True

    def test_execute_result_content_empty_on_fail(self, registry: ProviderRegistry) -> None:
        class FailProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                raise RuntimeError("Boom")
                
        registry.register(FailProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert result.content == ""

    def test_execute_result_usage_zero_on_fail(self, registry: ProviderRegistry) -> None:
        class FailProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                raise RuntimeError("Boom")
                
        registry.register(FailProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert result.usage.total_tokens == 0

    def test_runtime_default_registry(self) -> None:
        rt = ExecutionRuntime()
        assert isinstance(rt.registry, ProviderRegistry)
        assert len(rt.registry.list()) == 0

    def test_execute_health_checked_before_execute(self, registry: ProviderRegistry) -> None:
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

    def test_execute_health_checked_and_blocks(self, registry: ProviderRegistry) -> None:
        class UnhealthyProvider(MockProvider):
            def __init__(self):
                super().__init__()
                self.executed = False
                
            def health(self) -> ProviderHealth:
                return ProviderHealth(provider_id=self._pid, status=ProviderHealthStatus.UNHEALTHY)
                
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                self.executed = True
                return super().execute(context)
                
        p = UnhealthyProvider()
        registry.register(p)
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider=p.provider_id)
        with pytest.raises(ProviderUnavailableError):
            rt.execute(ctx)
        assert p.executed is False

    def test_execute_trace_has_provider_id(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        provider_selected_event = next(e for e in result.trace.events if e.type == TraceEventType.PROVIDER_SELECTED)
        assert provider_selected_event.metadata["provider"] == "p1"

    def test_execute_trace_has_error_message(self, registry: ProviderRegistry) -> None:
        class FailProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                raise RuntimeError("Specific error message")
                
        registry.register(FailProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        failed_event = next(e for e in result.trace.events if e.type == TraceEventType.FAILED)
        assert "Specific error message" in failed_event.message

    def test_execute_duration_measured(self, runtime: ExecutionRuntime) -> None:
        import time
        class SlowProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                time.sleep(0.01)
                return super().execute(context)
                
        runtime.registry.register(SlowProvider(pid="p4"))
        ctx = make_context(provider="p4")
        result = runtime.execute(ctx)
        assert result.duration_ms > 5.0  # > 5ms

    def test_execute_result_state_success(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert result.state == ExecutionState.SUCCESS

    def test_execute_result_state_failed(self, registry: ProviderRegistry) -> None:
        class FailProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                raise RuntimeError("Boom")
                
        registry.register(FailProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert result.state == ExecutionState.FAILED

    def test_execute_result_error_none_on_success(self, runtime: ExecutionRuntime) -> None:
        ctx = make_context()
        result = runtime.execute(ctx)
        assert result.error is None

    def test_execute_result_error_set_on_failure(self, registry: ProviderRegistry) -> None:
        class FailProvider(MockProvider):
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                raise RuntimeError("Boom")
                
        registry.register(FailProvider(pid="p3", fail=True))
        rt = ExecutionRuntime(registry=registry)
        ctx = make_context(provider="p3")
        result = rt.execute(ctx)
        assert result.error is not None

    def test_execute_options_passed_to_provider(self, registry: ProviderRegistry) -> None:
        class OptionsCheckProvider(MockProvider):
            def __init__(self):
                super().__init__()
                self.received_options = None
                
            def execute(self, context: ExecutionContext) -> ExecutionResult:
                self.received_options = context.options
                return super().execute(context)
                
        p = OptionsCheckProvider()
        registry.register(p)
        rt = ExecutionRuntime(registry=registry)
        opts = ExecutionOptions(temperature=0.9)
        ctx = ExecutionContext(prompt="test", model_id="m", provider_id=p.provider_id, options=opts)
        rt.execute(ctx)
        assert p.received_options.temperature == 0.9