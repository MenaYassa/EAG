"""EBS-012: Multi-Goal Memory Benchmark."""

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
    LoopOutcome,
)
from eag.capability import CapabilityRegistry, CapabilityRuntime, WorkspaceCapability
from eag.chief.runtime import ChiefRuntime, Coordinator, DefaultValidator, RuntimeRegistry, RunResult
from eag.chief.runtime.enums import RunOutcome
from eag.chief.runtime.planner import DefaultPlanner
from eag.memory import InMemoryStorage, MemoryRuntime
from eag.reflection import DefaultReflectionEngine, ReflectionRuntime
from eag.workspace.enums import WorkspaceMode
from eag.workspace.runtime import WorkspaceRuntime


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


class ImmediateStopCompletion(CompletionEngine):
    def evaluate(self, run, ref, iter, max_iter):
        return LoopDecision(continue_loop=False, reason="Done", action=CompletionAction.STOP)


class TestEBS012MultiGoal:
    """Validates that memory persists and is queryable across different goals."""

    def test_multi_goal_memory_persistence(self, tmp_path: Path):
        event_bus = MockEventBus()
        ws_runtime = WorkspaceRuntime(root=tmp_path, mode=WorkspaceMode.LIVE, event_bus=event_bus)
        ws_runtime.open()
        cap_reg = CapabilityRegistry()
        cap_reg.register(WorkspaceCapability(ws_runtime))
        cap_runtime = CapabilityRuntime(registry=cap_reg)

        memory_runtime = MemoryRuntime(storage=InMemoryStorage(), event_bus=event_bus)
        reflection_runtime = ReflectionRuntime(engine=DefaultReflectionEngine(), event_bus=event_bus)

        base_planner = DefaultPlanner()
        adaptive_planner = AdaptivePlanner()
        validator = DefaultValidator()

        coordinator = Coordinator(
            planner=base_planner,
            adaptive_planner=adaptive_planner,
            capability_runtime=cap_runtime,
            validator=validator,
            event_bus=event_bus,
            memory_runtime=memory_runtime,
        )

        registry = RuntimeRegistry()
        registry._components["planner:default"] = base_planner
        registry._components["planner:adaptive"] = adaptive_planner
        registry._components["validator:default"] = validator

        chief_runtime = ChiefRuntime(registry=registry, event_bus=event_bus)
        chief_runtime._coordinator = coordinator
        chief_runtime._coordinator_memory = memory_runtime
        chief_runtime._coordinator_capability = cap_runtime

        # Mock successful execution output for both goal runs
        mock_success = RunResult(
            run_id="run-1",
            outcome=RunOutcome.SUCCESS,
            summary="Completed goal",
            plan=None,
            step_results=(),
            planning_decision=None,
            duration_ms=10.0,
        )
        chief_runtime.execute_goal = MagicMock(return_value=mock_success)

        loop_runtime = AutonomousLoopRuntime(
            chief_runtime=chief_runtime,
            reflection_runtime=reflection_runtime,
            memory_runtime=memory_runtime,
            capability_runtime=cap_runtime,
            completion_engine=ImmediateStopCompletion(),
            event_bus=event_bus,
        )

        # Goal 1: Build API
        ctx1 = LoopContext(goal="Build FastAPI", max_iterations=1, metadata={"workspace_path": tmp_path})
        result1 = loop_runtime.execute(ctx1)

        assert result1.outcome == LoopOutcome.FINISHED
        assert memory_runtime.statistics().total_runs == 1

        # Goal 2: Build CLI Tool
        ctx2 = LoopContext(goal="Build CLI Tool", max_iterations=1, metadata={"workspace_path": tmp_path})
        result2 = loop_runtime.execute(ctx2)

        assert result2.outcome == LoopOutcome.FINISHED
        assert memory_runtime.statistics().total_runs == 2

        # Verify entries exist in storage statistics
        stats = memory_runtime.statistics()
        assert stats.total_runs == 2