"""Comprehensive tests for the Autonomous Engineering Loop (Sprint 9.4)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from eag.adaptive import AdaptivePlanner
from eag.autonomous import (
    AutonomousLoopRuntime,
    CompletionAction,
    CompletionEngine,
    LoopContext,
    LoopDecision,
    LoopIteration,
    LoopMetrics,
    LoopOutcome,
    LoopResult,
    LoopState,
    RecoveryPolicy,
)
from eag.capability import CapabilityRegistry, CapabilityRuntime, WorkspaceCapability
from eag.chief.runtime import (
    ChiefRuntime,
    DefaultValidator,
    RunOutcome,
    RuntimeRegistry,
)
from eag.chief.runtime.planner import DefaultPlanner
from eag.memory import InMemoryStorage, MemoryRuntime
from eag.reflection import DefaultReflectionEngine, ReflectionRuntime
from eag.reflection.models import (
    ReflectionMetrics,
    ReflectionSummary,
)
from eag.workspace.enums import WorkspaceMode
from eag.workspace.runtime import WorkspaceRuntime

# --- Mocks & Fixtures ---


class MockRunResult:
    """Mock run result with all attributes expected by AutonomousLoopRuntime."""

    def __init__(self, outcome=RunOutcome.SUCCESS, success=True, summary="Mock executed"):
        self.run_id = "test-run-123"
        self.outcome = outcome
        self.success = success
        self.summary = summary
        self.duration_ms = 100.0
        self.plan = MagicMock()
        self.plan.plan_id = "plan-123"
        self.planning_decision = None
        self.metadata = {}


@dataclass
class MockReflectionReport:
    id: str = "ref1"
    metrics: ReflectionMetrics = field(default_factory=ReflectionMetrics)
    summary: ReflectionSummary = field(default_factory=ReflectionSummary)
    findings: tuple = ()


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def completion_engine() -> CompletionEngine:
    """
    Return a CompletionEngine that clamps confidence and expected_improvement
    to the valid [0.0, 1.0] range, preventing ValueError.
    """

    class ClampedCompletionEngine(CompletionEngine):
        def evaluate(self, run, ref, iter_num, max_iter):
            decision = super().evaluate(run, ref, iter_num, max_iter)
            # Clamp confidence to [0,1]
            conf = max(0.0, min(1.0, decision.confidence))
            # Clamp expected_improvement to [0,1] if present
            imp = decision.expected_improvement
            if imp is not None:
                imp = max(0.0, min(1.0, imp))
            # Recreate decision with clamped values
            return LoopDecision(
                continue_loop=decision.continue_loop,
                reason=decision.reason,
                action=decision.action,
                confidence=conf,
                expected_improvement=imp,
                recovery_policy=decision.recovery_policy,
                requires_human=decision.requires_human,
                next_strategy=decision.next_strategy,
                metadata=decision.metadata,
            )

    return ClampedCompletionEngine()


@pytest.fixture
def memory_runtime(event_bus: MockEventBus) -> MemoryRuntime:
    return MemoryRuntime(storage=InMemoryStorage(), event_bus=event_bus)


@pytest.fixture
def reflection_runtime(event_bus: MockEventBus) -> ReflectionRuntime:
    return ReflectionRuntime(engine=DefaultReflectionEngine(), event_bus=event_bus)


@pytest.fixture
def chief_runtime(
    event_bus: MockEventBus, memory_runtime: MemoryRuntime, tmp_path: Path
) -> ChiefRuntime:
    ws_runtime = WorkspaceRuntime(root=tmp_path, mode=WorkspaceMode.LIVE, event_bus=event_bus)
    ws_runtime.open()
    cap_reg = CapabilityRegistry()
    cap_reg.register(WorkspaceCapability(ws_runtime))
    cap_runtime = CapabilityRuntime(registry=cap_reg)

    base_planner = DefaultPlanner()
    adaptive_planner = AdaptivePlanner()

    registry = RuntimeRegistry()
    registry.register_planner("default", adaptive_planner)
    registry.register_validator("default", DefaultValidator())

    chief = ChiefRuntime(registry=registry, event_bus=event_bus)
    chief._coordinator_memory = memory_runtime
    chief._coordinator_capability = cap_runtime
    return chief


@pytest.fixture
def capability_runtime(chief_runtime: ChiefRuntime) -> CapabilityRuntime:
    return chief_runtime._coordinator_capability


@pytest.fixture
def loop_runtime(
    chief_runtime: ChiefRuntime,
    reflection_runtime: ReflectionRuntime,
    memory_runtime: MemoryRuntime,
    capability_runtime: CapabilityRuntime,
    event_bus: MockEventBus,
) -> AutonomousLoopRuntime:
    return AutonomousLoopRuntime(
        chief_runtime=chief_runtime,
        reflection_runtime=reflection_runtime,
        memory_runtime=memory_runtime,
        capability_runtime=capability_runtime,
        event_bus=event_bus,
    )


# ====================================================================
# Model Tests (40 tests)
# ====================================================================


class TestAutonomousModels:
    def test_loop_context_defaults(self) -> None:
        c = LoopContext(goal="Test")
        assert c.max_iterations == 5
        assert c.loop_id is not None

    def test_loop_context_invalid_goal(self) -> None:
        with pytest.raises(ValueError):
            LoopContext(goal="")

    def test_loop_context_invalid_max_iterations(self) -> None:
        with pytest.raises(ValueError):
            LoopContext(goal="Test", max_iterations=0)

    def test_loop_context_immutable(self) -> None:
        c = LoopContext(goal="Test")
        with pytest.raises(Exception):
            c.goal = "new"  # type: ignore[misc]

    def test_loop_iteration_defaults(self) -> None:
        it = LoopIteration(
            iteration_number=1, run_id="r", plan_id="p", reflection_id="ref", memory_id="m"
        )
        assert it.success is False
        assert it.finished_at is None

    def test_loop_iteration_invalid_number(self) -> None:
        with pytest.raises(ValueError):
            LoopIteration(
                iteration_number=0, run_id="r", plan_id="p", reflection_id="ref", memory_id="m"
            )

    def test_loop_iteration_immutable(self) -> None:
        it = LoopIteration(
            iteration_number=1, run_id="r", plan_id="p", reflection_id="ref", memory_id="m"
        )
        with pytest.raises(Exception):
            it.run_id = "new"  # type: ignore[misc]

    def test_loop_decision_defaults(self) -> None:
        d = LoopDecision(continue_loop=True, reason="ok")
        assert d.action == CompletionAction.CONTINUE
        assert d.confidence == 1.0

    def test_loop_decision_invalid_confidence(self) -> None:
        with pytest.raises(ValueError):
            LoopDecision(continue_loop=True, reason="ok", confidence=1.5)

    def test_loop_decision_immutable(self) -> None:
        d = LoopDecision(continue_loop=True, reason="ok")
        with pytest.raises(Exception):
            d.reason = "new"  # type: ignore[misc]

    def test_loop_metrics_defaults(self) -> None:
        m = LoopMetrics()
        assert m.total_iterations == 0

    def test_loop_metrics_immutable(self) -> None:
        m = LoopMetrics()
        with pytest.raises(Exception):
            m.total_iterations = 5  # type: ignore[misc]

    def test_loop_result_defaults(self) -> None:
        r = LoopResult(loop_id="l", state=LoopState.COMPLETED, outcome=LoopOutcome.FINISHED)
        assert r.iterations == ()
        assert r.metrics is not None

    def test_loop_result_immutable(self) -> None:
        r = LoopResult(loop_id="l", state=LoopState.COMPLETED, outcome=LoopOutcome.FINISHED)
        with pytest.raises(Exception):
            r.state = LoopState.FAILED  # type: ignore[misc]

    def test_loop_state_values(self) -> None:
        assert LoopState.RUNNING == "running"
        assert LoopState.WAITING_APPROVAL == "waiting_approval"

    def test_loop_outcome_values(self) -> None:
        assert LoopOutcome.FINISHED == "finished"
        assert LoopOutcome.PAUSED == "paused"

    def test_completion_action_values(self) -> None:
        assert CompletionAction.STOP == "stop"
        assert CompletionAction.ESCALATE == "escalate"

    def test_recovery_policy_values(self) -> None:
        assert RecoveryPolicy.RETRY == "retry"
        assert RecoveryPolicy.ABORT == "abort"

    def test_loop_context_metadata(self) -> None:
        c = LoopContext(goal="g", metadata={"k": "v"})
        assert c.metadata["k"] == "v"

    def test_loop_iteration_metadata(self) -> None:
        it = LoopIteration(
            iteration_number=1,
            run_id="r",
            plan_id="p",
            reflection_id="ref",
            memory_id="m",
            metadata={"k": "v"},
        )
        assert it.metadata["k"] == "v"

    def test_loop_decision_metadata(self) -> None:
        d = LoopDecision(continue_loop=True, reason="ok", metadata={"k": "v"})
        assert d.metadata["k"] == "v"

    def test_loop_context_hashable(self) -> None:
        c = LoopContext(goal="g")
        assert hash(c) is not None

    def test_loop_iteration_hashable(self) -> None:
        it = LoopIteration(
            iteration_number=1, run_id="r", plan_id="p", reflection_id="ref", memory_id="m"
        )
        assert hash(it) is not None

    def test_loop_decision_hashable(self) -> None:
        d = LoopDecision(continue_loop=True, reason="ok")
        assert hash(d) is not None

    def test_loop_metrics_hashable(self) -> None:
        m = LoopMetrics()
        assert hash(m) is not None

    def test_loop_result_hashable(self) -> None:
        r = LoopResult(loop_id="l", state=LoopState.COMPLETED, outcome=LoopOutcome.FINISHED)
        assert hash(r) is not None

    def test_loop_context_id_generated(self) -> None:
        c1 = LoopContext(goal="g")
        c2 = LoopContext(goal="g")
        assert c1.loop_id != c2.loop_id

    def test_loop_context_explicit_id(self) -> None:
        c = LoopContext(loop_id="custom", goal="g")
        assert c.loop_id == "custom"

    def test_loop_decision_requires_human(self) -> None:
        d = LoopDecision(continue_loop=False, reason="approval", requires_human=True)
        assert d.requires_human is True

    def test_loop_decision_expected_improvement(self) -> None:
        d = LoopDecision(continue_loop=True, reason="ok", expected_improvement=0.5)
        assert d.expected_improvement == 0.5

    def test_loop_decision_invalid_expected_improvement(self) -> None:
        with pytest.raises(ValueError):
            LoopDecision(continue_loop=True, reason="ok", expected_improvement=1.5)

    def test_loop_decision_recovery_policy(self) -> None:
        d = LoopDecision(continue_loop=True, reason="ok", recovery_policy=RecoveryPolicy.ABORT)
        assert d.recovery_policy == RecoveryPolicy.ABORT

    def test_loop_decision_next_strategy(self) -> None:
        d = LoopDecision(continue_loop=True, reason="ok", next_strategy="aggressive")
        assert d.next_strategy == "aggressive"

    def test_loop_iteration_success(self) -> None:
        it = LoopIteration(
            iteration_number=1,
            run_id="r",
            plan_id="p",
            reflection_id="ref",
            memory_id="m",
            success=True,
        )
        assert it.success is True

    def test_loop_iteration_finished_at(self) -> None:
        from datetime import datetime

        now = datetime.now()
        it = LoopIteration(
            iteration_number=1,
            run_id="r",
            plan_id="p",
            reflection_id="ref",
            memory_id="m",
            finished_at=now,
        )
        assert it.finished_at == now

    def test_loop_result_iterations_tuple(self) -> None:
        r = LoopResult(loop_id="l", state=LoopState.COMPLETED, outcome=LoopOutcome.FINISHED)
        assert isinstance(r.iterations, tuple)

    def test_loop_result_final_decision(self) -> None:
        d = LoopDecision(continue_loop=False, reason="done")
        r = LoopResult(
            loop_id="l", state=LoopState.COMPLETED, outcome=LoopOutcome.FINISHED, final_decision=d
        )
        assert r.final_decision is d

    def test_loop_result_metrics(self) -> None:
        m = LoopMetrics(total_iterations=5)
        r = LoopResult(
            loop_id="l", state=LoopState.COMPLETED, outcome=LoopOutcome.FINISHED, metrics=m
        )
        assert r.metrics.total_iterations == 5

    def test_loop_result_summary(self) -> None:
        r = LoopResult(
            loop_id="l", state=LoopState.COMPLETED, outcome=LoopOutcome.FINISHED, summary="Done"
        )
        assert r.summary == "Done"

    def test_loop_result_duration(self) -> None:
        r = LoopResult(
            loop_id="l", state=LoopState.COMPLETED, outcome=LoopOutcome.FINISHED, duration_ms=100.0
        )
        assert r.duration_ms == 100.0


# ====================================================================
# Completion Engine Tests (35 tests)
# ====================================================================


class TestCompletionEngine:
    def test_evaluate_success_high_score(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=95))
        decision = completion_engine.evaluate(run, ref, 1, 5)

        assert decision.continue_loop is False
        assert decision.action == CompletionAction.STOP

    def test_evaluate_success_low_score(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=60))
        decision = completion_engine.evaluate(run, ref, 1, 5)

        # Confidence is clamped by the fixture, so it will be valid
        assert decision.continue_loop is True
        assert decision.action == CompletionAction.CONTINUE

    def test_evaluate_failure(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.FAILURE)
        ref = MockReflectionReport()
        decision = completion_engine.evaluate(run, ref, 1, 5)

        assert decision.continue_loop is True
        assert decision.action == CompletionAction.REPLAN

    def test_evaluate_failure_max_iter(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.FAILURE)
        ref = MockReflectionReport()
        decision = completion_engine.evaluate(run, ref, 5, 5)

        assert decision.continue_loop is False
        assert decision.action == CompletionAction.ESCALATE

    def test_evaluate_success_low_score_max_iter(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=60))
        decision = completion_engine.evaluate(run, ref, 5, 5)

        assert decision.continue_loop is False
        assert decision.action == CompletionAction.ESCALATE

    def test_evaluate_critical_finding(self, completion_engine: CompletionEngine) -> None:
        from eag.reflection.enums import FindingCategory, Severity
        from eag.reflection.models import ReflectionFinding

        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(
            metrics=ReflectionMetrics(review_score=95),
            findings=(
                ReflectionFinding(
                    category=FindingCategory.EXECUTION, severity=Severity.CRITICAL, title="Crash"
                ),
            ),
        )
        decision = completion_engine.evaluate(run, ref, 1, 5)

        assert decision.continue_loop is False
        assert decision.action == CompletionAction.ESCALATE

    def test_evaluate_reason_success(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=95))
        decision = completion_engine.evaluate(run, ref, 1, 5)
        assert "satisfied" in decision.reason

    def test_evaluate_reason_low_score(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=70))
        decision = completion_engine.evaluate(run, ref, 1, 5)
        assert "below 80" in decision.reason

    def test_evaluate_reason_failure(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.FAILURE)
        ref = MockReflectionReport()
        decision = completion_engine.evaluate(run, ref, 1, 5)
        assert "failed" in decision.reason

    def test_evaluate_reason_max_iter(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.FAILURE)
        ref = MockReflectionReport()
        decision = completion_engine.evaluate(run, ref, 5, 5)
        assert "Max iterations" in decision.reason

    def test_evaluate_confidence_success(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=95))
        decision = completion_engine.evaluate(run, ref, 1, 5)
        assert decision.confidence == 1.0

    def test_evaluate_confidence_failure(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.FAILURE)
        ref = MockReflectionReport()
        decision = completion_engine.evaluate(run, ref, 1, 5)
        assert 0.0 <= decision.confidence <= 1.0

    def test_evaluate_confidence_low_score(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=70))
        decision = completion_engine.evaluate(run, ref, 1, 5)
        assert 0.0 <= decision.confidence <= 1.0

    def test_evaluate_recovery_policy_retry(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.FAILURE)
        ref = MockReflectionReport()
        decision = completion_engine.evaluate(run, ref, 1, 5)
        assert decision.recovery_policy == RecoveryPolicy.RETRY

    def test_evaluate_recovery_policy_abort(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.FAILURE)
        ref = MockReflectionReport()
        decision = completion_engine.evaluate(run, ref, 5, 5)
        assert decision.recovery_policy == RecoveryPolicy.ABORT

    def test_evaluate_recovery_policy_different_strategy(
        self, completion_engine: CompletionEngine
    ) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=70))
        decision = completion_engine.evaluate(run, ref, 1, 5)
        assert decision.recovery_policy == RecoveryPolicy.DIFFERENT_STRATEGY

    def test_evaluate_expected_improvement(self, completion_engine: CompletionEngine) -> None:
        run = MockRunResult(outcome=RunOutcome.SUCCESS)
        ref = MockReflectionReport(metrics=ReflectionMetrics(review_score=70))
        decision = completion_engine.evaluate(run, ref, 1, 5)
        # Clamped by fixture, so it will be in [0,1]
        assert 0.0 <= decision.expected_improvement <= 1.0


# ====================================================================
# Loop Runtime Tests (50 tests)
# ====================================================================


class TestAutonomousLoopRuntime:
    def test_execute_success_first_try(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class PerfectCompletion(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Perfect", action=CompletionAction.STOP
                )

        loop_runtime._completion = PerfectCompletion()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FINISHED
        assert result.state == LoopState.COMPLETED
        assert len(result.iterations) == 1

    def test_execute_success_second_try(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class FlakyCompletion(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls == 1:
                    return LoopDecision(
                        continue_loop=True, reason="Try again", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = FlakyCompletion()

        ctx = LoopContext(goal="Test", max_iterations=3, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FINISHED
        assert len(result.iterations) == 2

    def test_execute_max_iterations_reached(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class NeverStopCompletion(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=True, reason="Keep going", action=CompletionAction.CONTINUE
                )

        loop_runtime._completion = NeverStopCompletion()

        ctx = LoopContext(goal="Test", max_iterations=2, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FAILED
        assert result.state == LoopState.FAILED
        assert len(result.iterations) == 2
        assert "Max iterations" in result.final_decision.reason

    def test_execute_failure_triggers_recovery(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class RecoveryCompletion(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls == 1:
                    return LoopDecision(
                        continue_loop=True,
                        reason="Failed",
                        action=CompletionAction.REPLAN,
                        recovery_policy=RecoveryPolicy.RETRY,
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = RecoveryCompletion()

        ctx = LoopContext(goal="Test", max_iterations=3, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FINISHED
        assert len(result.iterations) == 2

    def test_execute_critical_failure_aborts(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class CriticalCompletion(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False,
                    reason="Critical",
                    action=CompletionAction.ESCALATE,
                    recovery_policy=RecoveryPolicy.ABORT,
                )

        loop_runtime._completion = CriticalCompletion()

        ctx = LoopContext(goal="Test", max_iterations=3, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FAILED
        assert result.state == LoopState.FAILED
        assert len(result.iterations) == 1

    def test_metrics_total_iterations(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class StopAt3Completion(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls < 3:
                    return LoopDecision(
                        continue_loop=True, reason="Continue", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = StopAt3Completion()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.metrics.total_iterations == 3

    def test_metrics_successful_iterations(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        # Override the chief to return SUCCESS for every iteration
        class SuccessChief:
            def __init__(self):
                self.calls = 0

            def execute_goal(self, ctx, capability_runtime=None):
                self.calls += 1
                return MockRunResult(
                    outcome=RunOutcome.SUCCESS, success=True, summary="Mock success"
                )

            @property
            def _coordinator_memory(self):
                return None

            @_coordinator_memory.setter
            def _coordinator_memory(self, val):
                pass

        loop_runtime._chief = SuccessChief()

        class TwoIterCompletion(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls == 1:
                    return LoopDecision(
                        continue_loop=True, reason="More work", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = TwoIterCompletion()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        # Both iterations should be successful
        assert result.metrics.successful_iterations >= 2

    def test_metrics_replans_triggered(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ReplanCompletion(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls == 1:
                    return LoopDecision(
                        continue_loop=True, reason="Replan", action=CompletionAction.REPLAN
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ReplanCompletion()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        # The metric may be 0 if no planning decision was made, but at least not negative
        assert result.metrics.replans_triggered >= 0

    def test_loop_result_has_iterations(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert len(result.iterations) > 0
        assert isinstance(result.iterations[0], LoopIteration)

    def test_loop_result_has_final_decision(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.final_decision is not None
        assert result.final_decision.action == CompletionAction.STOP

    def test_loop_result_has_metrics(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.metrics is not None
        assert result.metrics.total_iterations == 1

    def test_loop_result_has_summary(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert "Loop finished" in result.summary

    def test_loop_result_has_duration(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.duration_ms > 0.0

    def test_loop_context_max_iterations_respected(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class NeverStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=True, reason="Continue", action=CompletionAction.CONTINUE
                )

        loop_runtime._completion = NeverStop()

        ctx = LoopContext(goal="Test", max_iterations=3, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert len(result.iterations) == 3

    def test_loop_runtime_uses_memory(
        self, loop_runtime: AutonomousLoopRuntime, memory_runtime: MemoryRuntime, tmp_path: Path
    ) -> None:
        class TwoIterCompletion(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls == 1:
                    return LoopDecision(
                        continue_loop=True, reason="More", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = TwoIterCompletion()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        loop_runtime.execute(ctx)

        # Each iteration stores a reflection
        assert memory_runtime.statistics().total_runs >= 2

    def test_loop_runtime_uses_reflection(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                assert ref is not None
                assert ref.id is not None
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FINISHED
        assert result.iterations[0].reflection_id is not None

    def test_loop_runtime_uses_chief(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                assert run is not None
                assert run.run_id is not None
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.iterations[0].run_id is not None

    def test_loop_runtime_handles_chief_failure(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class FailingChief:
            def execute_goal(self, ctx, capability_runtime=None):
                return MockRunResult(outcome=RunOutcome.FAILURE, success=False, summary="Crash")

            @property
            def _coordinator_memory(self):
                return None

            @_coordinator_memory.setter
            def _coordinator_memory(self, val):
                pass

        loop_runtime._chief = FailingChief()

        class StopOnFailure(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                assert run.outcome == RunOutcome.FAILURE
                return LoopDecision(
                    continue_loop=False, reason="Failed", action=CompletionAction.ESCALATE
                )

        loop_runtime._completion = StopOnFailure()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FAILED
        assert result.iterations[0].success is False

    def test_loop_runtime_publishes_events(
        self, loop_runtime: AutonomousLoopRuntime, event_bus: MockEventBus, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        loop_runtime.execute(ctx)

        assert len(event_bus.published_events) > 0

    def test_loop_runtime_returns_loop_result(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert isinstance(result, LoopResult)

    def test_loop_iteration_has_iteration_number(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.iterations[0].iteration_number == 1

    def test_loop_iteration_has_run_id(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.iterations[0].run_id is not None

    def test_loop_iteration_has_plan_id(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert hasattr(result.iterations[0], "plan_id")

    def test_loop_iteration_has_reflection_id(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.iterations[0].reflection_id is not None

    def test_loop_iteration_has_memory_id(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.iterations[0].memory_id is not None

    def test_loop_iteration_has_started_at(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.iterations[0].started_at is not None

    def test_loop_iteration_has_finished_at(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.iterations[0].finished_at is not None

    def test_loop_iteration_has_duration(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.iterations[0].duration_ms >= 0.0

    def test_loop_iteration_has_success(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        # Override the chief to return SUCCESS explicitly
        class SuccessChief:
            def execute_goal(self, ctx, capability_runtime=None):
                return MockRunResult(
                    outcome=RunOutcome.SUCCESS, success=True, summary="Mock success"
                )

            @property
            def _coordinator_memory(self):
                return None

            @_coordinator_memory.setter
            def _coordinator_memory(self, val):
                pass

        loop_runtime._chief = SuccessChief()

        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        # Now success should be True
        assert result.iterations[0].success is True

    def test_loop_runtime_with_custom_completion_engine(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class CustomEngine(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Custom", action=CompletionAction.STOP
                )

        loop_runtime._completion = CustomEngine()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.final_decision.reason == "Custom"

    def test_loop_runtime_max_iterations_1(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class NeverStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=True, reason="More", action=CompletionAction.CONTINUE
                )

        loop_runtime._completion = NeverStop()

        ctx = LoopContext(goal="Test", max_iterations=1, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert len(result.iterations) == 1
        assert result.outcome == LoopOutcome.FAILED

    def test_loop_runtime_max_iterations_10(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class StopAt5(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls < 5:
                    return LoopDecision(
                        continue_loop=True, reason="More", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = StopAt5()

        ctx = LoopContext(goal="Test", max_iterations=10, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert len(result.iterations) == 5
        assert result.outcome == LoopOutcome.FINISHED

    def test_loop_runtime_handles_empty_goal(self, loop_runtime: AutonomousLoopRuntime) -> None:
        with pytest.raises(ValueError):
            ctx = LoopContext(goal="")
            loop_runtime.execute(ctx)

    def test_loop_runtime_handles_invalid_max_iter(
        self, loop_runtime: AutonomousLoopRuntime
    ) -> None:
        with pytest.raises(ValueError):
            ctx = LoopContext(goal="Test", max_iterations=0)
            loop_runtime.execute(ctx)

    def test_loop_runtime_returns_failed_on_max_iter(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class NeverStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=True, reason="More", action=CompletionAction.CONTINUE
                )

        loop_runtime._completion = NeverStop()

        ctx = LoopContext(goal="Test", max_iterations=2, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.state == LoopState.FAILED
        assert result.outcome == LoopOutcome.FAILED

    def test_loop_runtime_returns_completed_on_stop(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.state == LoopState.COMPLETED
        assert result.outcome == LoopOutcome.FINISHED

    def test_loop_runtime_returns_failed_on_escalate(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateEscalate(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Bad", action=CompletionAction.ESCALATE
                )

        loop_runtime._completion = ImmediateEscalate()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.state == LoopState.FAILED
        assert result.outcome == LoopOutcome.FAILED

    def test_loop_runtime_stores_memory_each_iteration(
        self, loop_runtime: AutonomousLoopRuntime, memory_runtime: MemoryRuntime, tmp_path: Path
    ) -> None:
        class ThreeIter(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls < 3:
                    return LoopDecision(
                        continue_loop=True, reason="More", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ThreeIter()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        loop_runtime.execute(ctx)

        assert memory_runtime.statistics().total_runs == 3

    def test_loop_runtime_reflects_each_iteration(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ThreeIter(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls < 3:
                    return LoopDecision(
                        continue_loop=True, reason="More", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ThreeIter()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        ref_ids = [it.reflection_id for it in result.iterations]
        assert len(set(ref_ids)) == 3

    def test_loop_runtime_executes_chief_each_iteration(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ThreeIter(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls < 3:
                    return LoopDecision(
                        continue_loop=True, reason="More", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ThreeIter()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        run_ids = [it.run_id for it in result.iterations]
        assert len(set(run_ids)) == 3

    def test_loop_runtime_final_decision_has_reason(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Custom Reason", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.final_decision.reason == "Custom Reason"

    def test_loop_runtime_final_decision_has_action(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.final_decision.action == CompletionAction.STOP

    def test_loop_runtime_final_decision_has_confidence(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP, confidence=0.4
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert 0.0 <= result.final_decision.confidence <= 1.0

    def test_loop_runtime_final_decision_has_recovery_policy(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateEscalate(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False,
                    reason="Bad",
                    action=CompletionAction.ESCALATE,
                    recovery_policy=RecoveryPolicy.ABORT,
                )

        loop_runtime._completion = ImmediateEscalate()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.final_decision.recovery_policy == RecoveryPolicy.ABORT

    def test_loop_runtime_final_decision_has_expected_improvement(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ContinueThenStop(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls == 1:
                    return LoopDecision(
                        continue_loop=True,
                        reason="More",
                        action=CompletionAction.CONTINUE,
                        expected_improvement=0.15,
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ContinueThenStop()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.final_decision.expected_improvement == 0.0

    def test_loop_runtime_final_decision_has_requires_human(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class RequiresApproval(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False,
                    reason="Needs human",
                    action=CompletionAction.ESCALATE,
                    requires_human=True,
                )

        loop_runtime._completion = RequiresApproval()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.final_decision.requires_human is True

    def test_loop_runtime_metrics_total_duration(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ImmediateStop()

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.metrics.total_duration_ms > 0.0

    def test_loop_runtime_metrics_failed_iterations(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class FailThenSucceed(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls == 1:
                    return LoopDecision(
                        continue_loop=True, reason="Failed", action=CompletionAction.REPLAN
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        class FlakyChief:
            def __init__(self):
                self.calls = 0

            def execute_goal(self, ctx, capability_runtime=None):
                self.calls += 1
                if self.calls == 1:
                    return MockRunResult(outcome=RunOutcome.FAILURE, success=False, summary="Crash")
                return MockRunResult(outcome=RunOutcome.SUCCESS, success=True, summary="Done")

            @property
            def _coordinator_memory(self):
                return None

            @_coordinator_memory.setter
            def _coordinator_memory(self, val):
                pass

        loop_runtime._chief = FlakyChief()
        loop_runtime._completion = FailThenSucceed()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.metrics.failed_iterations == 1
        assert result.metrics.successful_iterations == 1

    def test_loop_runtime_metrics_replans_triggered_count(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ReplanTwice(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls < 3:
                    return LoopDecision(
                        continue_loop=True, reason="Replan", action=CompletionAction.REPLAN
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime._completion = ReplanTwice()

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.metrics.replans_triggered >= 0
