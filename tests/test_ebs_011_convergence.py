"""EBS-011: Long-Running Convergence Benchmark."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from eag.adaptive import AdaptivePlanner
from eag.autonomous import (
    AutonomousLoopRuntime,
    CompletionAction,
    CompletionEngine,
    LoopContext,
    LoopDecision,
    LoopOutcome,
    LoopState,
)
from eag.capability import CapabilityRegistry, CapabilityRuntime, WorkspaceCapability
from eag.chief.runtime import (
    ChiefRuntime,
    Coordinator,
    DefaultValidator,
    RunResult,
)
from eag.chief.runtime.enums import RunOutcome
from eag.chief.runtime.planner import DefaultPlanner
from eag.memory import InMemoryStorage, MemoryRuntime
from eag.reflection import ReflectionRuntime
from eag.reflection.models import ReflectionMetrics, ReflectionReport, ReflectionSummary
from eag.workspace.enums import WorkspaceMode
from eag.workspace.runtime import WorkspaceRuntime


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


class ConvergenceReflectionEngine:
    """Provides dynamic reflection reports with improving scores over iterations."""

    def __init__(self):
        self.calls = 0
        self.scores = [60, 75, 85, 95]

    def reflect(self, context):
        score = self.scores[min(self.calls, len(self.scores) - 1)]
        self.calls += 1
        return ReflectionReport(
            id=f"ref-{context.run_id}",
            run_id=context.run_id,
            metrics=ReflectionMetrics(review_score=score),
            summary=ReflectionSummary(
                strengths=("Fast execution",),
                weaknesses=("None identified",),
                risks=(),
                opportunities=(),
            ),
        )


class ConvergenceCompletionEngine(CompletionEngine):
    """Evaluates termination based on the reflection report score."""

    def evaluate(self, run, ref, iter, max_iter):
        score = ref.metrics.review_score if ref and ref.metrics else 0

        if score < 90:
            return LoopDecision(
                continue_loop=True,
                reason=f"Score {score} is below 90. Continuing.",
                action=CompletionAction.CONTINUE,
            )
        return LoopDecision(
            continue_loop=False,
            reason=f"Score {score} achieved. Goal satisfied.",
            action=CompletionAction.STOP,
        )


class TestEBS011Convergence:
    """Validates that the autonomous loop converges over multiple iterations."""

    def test_loop_converges_and_grows_memory(self, tmp_path: Path):
        event_bus = MockEventBus()
        ws_runtime = WorkspaceRuntime(root=tmp_path, mode=WorkspaceMode.LIVE, event_bus=event_bus)
        ws_runtime.open()
        cap_reg = CapabilityRegistry()
        cap_reg.register(WorkspaceCapability(ws_runtime))
        cap_runtime = CapabilityRuntime(registry=cap_reg)

        memory_runtime = MemoryRuntime(storage=InMemoryStorage(), event_bus=event_bus)
        reflection_engine = ConvergenceReflectionEngine()
        reflection_runtime = ReflectionRuntime(engine=reflection_engine, event_bus=event_bus)

        base_planner = DefaultPlanner()
        adaptive_planner = AdaptivePlanner(base_planner=base_planner)
        validator = DefaultValidator()

        coordinator = Coordinator(
            planner=base_planner,
            adaptive_planner=adaptive_planner,
            capability_runtime=cap_runtime,
            validator=validator,
            event_bus=event_bus,
            memory_runtime=memory_runtime,
        )

        chief_runtime = ChiefRuntime(event_bus=event_bus, coordinator=coordinator)

        iteration_counter = [0]

        def side_effect_execute(ctx, capability_runtime=None):
            iteration_counter[0] += 1
            i = iteration_counter[0]
            
            # CRITICAL FIX: Make a unique plan signature per iteration
            # to avoid triggering the A-B-A-B oscillation detector!
            mock_step = MagicMock()
            mock_step.capability_id = f"cap-{i}"
            
            mock_plan = MagicMock()
            mock_plan.plan_id = f"plan-{i}"
            mock_plan.steps = [mock_step]
            
            return RunResult(
                run_id=f"run-{i}",
                outcome=RunOutcome.SUCCESS,
                summary="Iteration successful",
                plan=mock_plan,
                step_results=(),
                planning_decision=None,
                duration_ms=10.0,
            )

        chief_runtime.execute_goal = MagicMock(side_effect=side_effect_execute)

        loop_runtime = AutonomousLoopRuntime(
            chief_runtime=chief_runtime,
            reflection_runtime=reflection_runtime,
            memory_runtime=memory_runtime,
            completion_engine=ConvergenceCompletionEngine(),
            event_bus=event_bus,
        )

        ctx = LoopContext(goal="Converge on API", max_iterations=5, metadata={"workspace_path": tmp_path})
        result = loop_runtime.execute(ctx)

        # Verify termination and success
        assert result.state == LoopState.COMPLETED
        assert result.outcome == LoopOutcome.FINISHED

        # Verify it took exactly 4 iterations
        assert len(result.iterations) == 4

        # Verify memory grew monotonically
        assert memory_runtime.statistics().total_runs == 4