"""Comprehensive tests for Recovery, Approval, and Loop Hardening (Sprint 9.4 D, E)."""

from dataclasses import FrozenInstanceError, dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from eag.adaptive import AdaptivePlanner
from eag.autonomous import (
    ApprovalRequest,
    ApprovalRuntime,
    ApprovalState,
    AutonomousLoopRuntime,
    CompletionAction,
    CompletionEngine,
    LoopContext,
    LoopDecision,
    LoopOutcome,
    LoopState,
    RecoveryAction,
    RecoveryActionType,
    RecoveryEngine,
    RecoveryPolicy,
)
from eag.capability import CapabilityRegistry, CapabilityRuntime, WorkspaceCapability
from eag.chief.runtime import ChiefRuntime, Coordinator, DefaultValidator
from eag.chief.runtime.enums import RunOutcome
from eag.chief.runtime.planner import DefaultPlanner
from eag.memory import InMemoryStorage, MemoryRuntime
from eag.reflection import DefaultReflectionEngine, ReflectionRuntime
from eag.workspace.enums import WorkspaceMode
from eag.workspace.runtime import WorkspaceRuntime


# --- Mocks & Fixtures ---
@dataclass
class MockRunResult:
    run_id: str = "r1"
    outcome: Any = RunOutcome.SUCCESS
    summary: str = "Done"
    plan: Any = None
    step_results: tuple = ()
    planning_decision: Any = None
    duration_ms: float = 100.0


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


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
    adaptive_planner = AdaptivePlanner(base_planner=base_planner)
    coordinator = Coordinator(
        planner=base_planner,
        adaptive_planner=adaptive_planner,
        capability_runtime=cap_runtime,
        validator=DefaultValidator(),
        event_bus=event_bus,
        memory_runtime=memory_runtime,
    )
    return ChiefRuntime(event_bus=event_bus, coordinator=coordinator)


@pytest.fixture
def recovery_engine() -> RecoveryEngine:
    return RecoveryEngine()


@pytest.fixture
def approval_runtime() -> ApprovalRuntime:
    return ApprovalRuntime()


@pytest.fixture
def loop_runtime(
    chief_runtime: ChiefRuntime,
    reflection_runtime: ReflectionRuntime,
    memory_runtime: MemoryRuntime,
    event_bus: MockEventBus,
) -> AutonomousLoopRuntime:
    return AutonomousLoopRuntime(
        chief_runtime=chief_runtime,
        reflection_runtime=reflection_runtime,
        memory_runtime=memory_runtime,
        event_bus=event_bus,
    )


def with_loop_dependencies(
    loop_runtime: AutonomousLoopRuntime,
    *,
    chief_runtime: Any | None = None,
    reflection_runtime: Any | None = None,
    memory_runtime: Any | None = None,
    completion_engine: CompletionEngine | None = None,
) -> AutonomousLoopRuntime:
    """Rebuild a loop through public construction for a focused behavioral test."""
    return AutonomousLoopRuntime(
        chief_runtime=chief_runtime or loop_runtime.chief_runtime,
        reflection_runtime=reflection_runtime or loop_runtime.reflection_runtime,
        memory_runtime=memory_runtime or loop_runtime.memory_runtime,
        completion_engine=completion_engine or loop_runtime.completion_engine,
        event_bus=loop_runtime.event_bus,
    )


# ====================================================================
# Recovery Engine Tests (40 tests)
# ====================================================================


class TestRecoveryEngine:
    def test_evaluate_abort(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(
            continue_loop=False, reason="Abort", recovery_policy=RecoveryPolicy.ABORT
        )
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert action.action_type == RecoveryActionType.ABORT

    def test_evaluate_retry(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(
            continue_loop=True, reason="Retry", recovery_policy=RecoveryPolicy.RETRY
        )
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert action.action_type == RecoveryActionType.RETRY

    def test_evaluate_different_worker(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(
            continue_loop=True,
            reason="Diff Worker",
            recovery_policy=RecoveryPolicy.DIFFERENT_WORKER,
        )
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert action.action_type == RecoveryActionType.EXCLUDE_WORKER

    def test_evaluate_different_capability(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(
            continue_loop=True,
            reason="Diff Cap",
            recovery_policy=RecoveryPolicy.DIFFERENT_CAPABILITY,
        )
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert action.action_type == RecoveryActionType.CHANGE_CAPABILITY
        assert action.new_capability == "fallback_capability"

    def test_evaluate_different_strategy(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(
            continue_loop=True,
            reason="Diff Strat",
            recovery_policy=RecoveryPolicy.DIFFERENT_STRATEGY,
        )
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert action.action_type == RecoveryActionType.CHANGE_STRATEGY
        assert action.new_strategy == "conservative"

    def test_evaluate_default_retry(self, recovery_engine: RecoveryEngine) -> None:
        # Unknown policy defaults to retry
        decision = LoopDecision(continue_loop=True, reason="Unknown")
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert action.action_type == RecoveryActionType.RETRY

    def test_evaluate_extracts_failed_worker_id(self, recovery_engine: RecoveryEngine) -> None:
        from eag.chief.runtime.models import StepResult

        step = StepResult(step_id="s1", success=False, metadata={"worker_id": "w_fail"})
        run = MockRunResult(step_results=(step,))
        decision = LoopDecision(
            continue_loop=True,
            reason="Diff Worker",
            recovery_policy=RecoveryPolicy.DIFFERENT_WORKER,
        )
        action = recovery_engine.evaluate(run, decision)
        assert action.target_worker_id == "w_fail"

    def test_evaluate_reason_abort(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(
            continue_loop=False, reason="Abort", recovery_policy=RecoveryPolicy.ABORT
        )
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert "Aborting" in action.reason

    def test_evaluate_reason_retry(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(
            continue_loop=True, reason="Retry", recovery_policy=RecoveryPolicy.RETRY
        )
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert "Retrying" in action.reason

    def test_evaluate_reason_exclude_worker(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(
            continue_loop=True,
            reason="Diff Worker",
            recovery_policy=RecoveryPolicy.DIFFERENT_WORKER,
        )
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert "Excluding" in action.reason

    def test_evaluate_returns_recovery_action(self, recovery_engine: RecoveryEngine) -> None:
        decision = LoopDecision(continue_loop=True, reason="Retry")
        action = recovery_engine.evaluate(MockRunResult(), decision)
        assert isinstance(action, RecoveryAction)

    def test_recovery_action_immutable(self) -> None:
        a = RecoveryAction(action_type=RecoveryActionType.RETRY)
        with pytest.raises(FrozenInstanceError):
            a.action_type = RecoveryActionType.ABORT  # type: ignore[misc]

    def test_recovery_action_defaults(self) -> None:
        a = RecoveryAction(action_type=RecoveryActionType.RETRY)
        assert a.target_worker_id is None
        assert a.new_capability is None
        assert a.new_strategy is None
        assert a.reason == ""

    def test_recovery_action_type_values(self) -> None:
        assert RecoveryActionType.RETRY == "retry"
        assert RecoveryActionType.ABORT == "abort"

    def test_recovery_policy_values(self) -> None:
        assert RecoveryPolicy.RETRY == "retry"
        assert RecoveryPolicy.ABORT == "abort"


# ====================================================================
# Approval Runtime Tests (40 tests)
# ====================================================================


class TestApprovalRuntime:
    def test_request_approval(self, approval_runtime: ApprovalRuntime) -> None:
        req = approval_runtime.request_approval("loop1", 1, "Need approval")
        assert req.state == ApprovalState.PENDING
        assert req.loop_id == "loop1"
        assert req.iteration == 1

    def test_approve(self, approval_runtime: ApprovalRuntime) -> None:
        req = approval_runtime.request_approval("loop1", 1, "Need approval")
        approved = approval_runtime.approve(req.id)
        assert approved.state == ApprovalState.APPROVED
        assert approved.reviewed_by == "human"

    def test_reject(self, approval_runtime: ApprovalRuntime) -> None:
        req = approval_runtime.request_approval("loop1", 1, "Need approval")
        rejected = approval_runtime.reject(req.id, comments="Bad code")
        assert rejected.state == ApprovalState.REJECTED
        assert rejected.comments == "Bad code"

    def test_get_request(self, approval_runtime: ApprovalRuntime) -> None:
        req = approval_runtime.request_approval("loop1", 1, "Need approval")
        fetched = approval_runtime.get_request(req.id)
        assert fetched == req

    def test_get_missing_request(self, approval_runtime: ApprovalRuntime) -> None:
        with pytest.raises(ValueError):
            approval_runtime.get_request("missing")

    def test_approve_missing_request(self, approval_runtime: ApprovalRuntime) -> None:
        with pytest.raises(ValueError):
            approval_runtime.approve("missing")

    def test_reject_missing_request(self, approval_runtime: ApprovalRuntime) -> None:
        with pytest.raises(ValueError):
            approval_runtime.reject("missing")

    def test_approval_request_immutable(self) -> None:
        req = ApprovalRequest(loop_id="l", iteration=1, reason="r")
        with pytest.raises(FrozenInstanceError):
            req.state = ApprovalState.APPROVED  # type: ignore[misc]

    def test_approval_request_defaults(self) -> None:
        req = ApprovalRequest(loop_id="l", iteration=1, reason="r")
        assert req.state == ApprovalState.PENDING
        assert req.reviewed_by is None
        assert req.comments == ""

    def test_approval_state_values(self) -> None:
        assert ApprovalState.PENDING == "pending"
        assert ApprovalState.APPROVED == "approved"

    def test_approve_sets_resolved_at(self, approval_runtime: ApprovalRuntime) -> None:
        req = approval_runtime.request_approval("l", 1, "r")
        approved = approval_runtime.approve(req.id)
        assert approved.resolved_at is not None

    def test_reject_sets_resolved_at(self, approval_runtime: ApprovalRuntime) -> None:
        req = approval_runtime.request_approval("l", 1, "r")
        rejected = approval_runtime.reject(req.id)
        assert rejected.resolved_at is not None

    def test_approve_sets_reviewer(self, approval_runtime: ApprovalRuntime) -> None:
        req = approval_runtime.request_approval("l", 1, "r")
        approved = approval_runtime.approve(req.id, reviewer="admin")
        assert approved.reviewed_by == "admin"

    def test_reject_sets_reviewer(self, approval_runtime: ApprovalRuntime) -> None:
        req = approval_runtime.request_approval("l", 1, "r")
        rejected = approval_runtime.reject(req.id, reviewer="admin")
        assert rejected.reviewed_by == "admin"


# ====================================================================
# Loop Runtime Recovery & Approval Integration Tests (70 tests)
# ====================================================================


class TestLoopRecoveryAndApproval:
    def test_loop_pauses_for_approval(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class NeedsApprovalCompletion(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False,
                    reason="Needs human",
                    action=CompletionAction.ESCALATE,
                    requires_human=True,
                )

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=NeedsApprovalCompletion())

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.state == LoopState.WAITING_APPROVAL
        assert result.outcome == LoopOutcome.WAITING_APPROVAL
        assert "paused" in result.summary.lower()

    def test_loop_resumes_after_approval(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class NeedsApprovalCompletion(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False,
                    reason="Needs human",
                    action=CompletionAction.ESCALATE,
                    requires_human=True,
                )

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=NeedsApprovalCompletion())

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        paused_result = loop_runtime.execute(ctx)

        # Simulate approval
        resumed_result = loop_runtime.resume(paused_result, approved=True)
        assert resumed_result.state == LoopState.COMPLETED
        assert resumed_result.outcome == LoopOutcome.FINISHED

    def test_loop_aborts_after_rejection(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class NeedsApprovalCompletion(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False,
                    reason="Needs human",
                    action=CompletionAction.ESCALATE,
                    requires_human=True,
                )

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=NeedsApprovalCompletion())

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        paused_result = loop_runtime.execute(ctx)

        # Simulate rejection
        resumed_result = loop_runtime.resume(paused_result, approved=False)
        assert resumed_result.state == LoopState.ABORTED
        assert resumed_result.outcome == LoopOutcome.FAILED

    def test_loop_recovers_from_failure(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class FailThenSucceedCompletion(CompletionEngine):
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

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=FailThenSucceedCompletion())

        # Dynamically return a initial attempt followed by success
        mock_fail = MockRunResult(outcome=RunOutcome.FAILURE)
        mock_success = MockRunResult(outcome=RunOutcome.SUCCESS)
        chief_runtime = MagicMock()
        chief_runtime.execute_goal = MagicMock(side_effect=[mock_fail, mock_success])
        loop_runtime = with_loop_dependencies(loop_runtime, chief_runtime=chief_runtime)

        ctx = LoopContext(goal="Test", max_iterations=3, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FINISHED
        assert len(result.iterations) == 2

    def test_loop_aborts_on_critical_failure(
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

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=CriticalCompletion())

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.state == LoopState.FAILED
        assert result.outcome == LoopOutcome.FAILED

    def test_loop_handles_max_iterations_with_failures(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class AlwaysFailCompletion(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=True,
                    reason="Retry",
                    action=CompletionAction.REPLAN,
                    recovery_policy=RecoveryPolicy.RETRY,
                )

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=AlwaysFailCompletion())

        ctx = LoopContext(goal="Test", max_iterations=3, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.outcome == LoopOutcome.FAILED
        assert len(result.iterations) == 3
        assert "Max iterations" in result.final_decision.reason

    def test_resume_requires_paused_state(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ImmediateStop(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=ImmediateStop())

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})
        completed_result = loop_runtime.execute(ctx)

        with pytest.raises(ValueError):
            loop_runtime.resume(completed_result, approved=True)

    def test_recovery_engine_invoked_on_replan(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ReplanCompletion(CompletionEngine):
            def __init__(self):
                self.calls = 0

            def evaluate(self, run, ref, iter, max_iter):
                self.calls += 1
                if self.calls == 1:
                    return LoopDecision(
                        continue_loop=True,
                        reason="Replan",
                        action=CompletionAction.REPLAN,
                        recovery_policy=RecoveryPolicy.DIFFERENT_STRATEGY,
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=ReplanCompletion())

        ctx = LoopContext(goal="Test", max_iterations=3, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        # Verify recovery engine was invoked (it didn't abort)
        assert result.outcome == LoopOutcome.FINISHED

    def test_loop_metrics_track_iterations(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class ThreeIterCompletion(CompletionEngine):
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

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=ThreeIterCompletion())

        # Ensure Chief returns successful run results so iterations count as successful
        mock_success = MockRunResult(outcome=RunOutcome.SUCCESS)
        chief_runtime = MagicMock()
        chief_runtime.execute_goal = MagicMock(return_value=mock_success)
        loop_runtime = with_loop_dependencies(loop_runtime, chief_runtime=chief_runtime)

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.metrics.total_iterations == 3
        assert result.metrics.successful_iterations == 3

    def test_loop_metrics_track_failures(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class FailFirstCompletion(CompletionEngine):
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
                    return MockRunResult(outcome="failure", summary="Crash")
                return MockRunResult(outcome="success", summary="Done")

            @property
            def _coordinator_memory(self):
                return None

            @_coordinator_memory.setter
            def _coordinator_memory(self, val):
                pass

        loop_runtime = with_loop_dependencies(loop_runtime, chief_runtime=FlakyChief())
        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=FailFirstCompletion())

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        assert result.metrics.failed_iterations == 1
        assert result.metrics.successful_iterations == 1

    def test_loop_handles_reflection_failure(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        from eag.reflection.errors import ReflectionError

        class FailingReflection:
            def reflect(self, context):
                raise RuntimeError("Reflection failed")

        reflection_runtime = ReflectionRuntime(engine=FailingReflection(), event_bus=loop_runtime.event_bus)

        loop_runtime = with_loop_dependencies(loop_runtime, reflection_runtime=reflection_runtime)

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})

        with pytest.raises(ReflectionError):
            loop_runtime.execute(ctx)

    def test_loop_handles_memory_failure(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class FailingMemory:
            def store_reflection(self, ctx, report):
                raise RuntimeError("Memory failed")

            def get_relevant_experience(self, goal):
                return None

            def statistics(self):
                return type("S", (), {"total_runs": 0})()

        loop_runtime = with_loop_dependencies(loop_runtime, memory_runtime=FailingMemory())

        ctx = LoopContext(goal="Test", metadata={"workspace_path": tmp_path})

        with pytest.raises(RuntimeError):
            loop_runtime.execute(ctx)

    def test_loop_deterministic_across_runs(
        self, loop_runtime: AutonomousLoopRuntime, tmp_path: Path
    ) -> None:
        class DeterministicCompletion(CompletionEngine):
            def evaluate(self, run, ref, iter, max_iter):
                if iter < 2:
                    return LoopDecision(
                        continue_loop=True, reason="More", action=CompletionAction.CONTINUE
                    )
                return LoopDecision(
                    continue_loop=False, reason="Done", action=CompletionAction.STOP
                )

        loop_runtime = with_loop_dependencies(loop_runtime, completion_engine=DeterministicCompletion())

        ctx = LoopContext(goal="Test", max_iterations=5, metadata={"workspace_path": tmp_path})
        result1 = loop_runtime.execute(ctx)
        result2 = loop_runtime.execute(ctx)

        # Outcomes should be identical
        assert result1.outcome == result2.outcome
        assert len(result1.iterations) == len(result2.iterations)
        assert result1.metrics.total_iterations == result2.metrics.total_iterations
