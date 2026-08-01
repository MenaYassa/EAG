"""Chief Runtime executor for the Benchmark Platform."""

import time
from pathlib import Path

from eag.benchmark.models import Benchmark, BenchmarkResult
from eag.chief.runtime import ChiefRuntime, RunContext, RuntimeRegistry, DefaultValidator
# You will need to import your concrete Planners and Executors here
# from eag.chief.planners import DefaultPlanner 
# from eag.chief.executors import WorkspaceExecutor


class ChiefBenchmarkExecutor:
    """Adapts the Chief Runtime to the Benchmark Executor protocol."""

    def __init__(self) -> None:
        # Initialize the Chief Runtime with real components
        # NOTE: You will need to implement these concrete planners/executors in Sprint 7.5/7.6
        # For now, we can use mocks to prove the pipeline works.
        
        class MockPlanner:
            def create_plan(self, context: RunContext):
                from eag.chief.runtime import Plan, PlanStep
                return Plan(steps=(
                    PlanStep(name="Initialize Git", capability_id="git_init"),
                    PlanStep(name="Create Project Structure", capability_id="workspace_create", dependencies=("step_1",)),
                    PlanStep(name="Generate Files", capability_id="source_generate", dependencies=("step_2",)),
                ))

        class MockWorkspaceExecutor:
            def execute_step(self, step, run):
                from eag.chief.runtime import StepResult
                # Simulate doing the work
                if step.capability_id == "git_init":
                    # In a real implementation, this would call VCSRuntime.init()
                    pass
                return StepResult(step_id=step.step_id, success=True, output=f"Mocked {step.name}")

        registry = RuntimeRegistry()
        registry.register_planner("default", MockPlanner())
        registry.register_executor("default", MockWorkspaceExecutor())
        registry.register_validator("default", DefaultValidator(max_retries=1))
        
        self._runtime = ChiefRuntime(registry=registry)

    def execute(self, benchmark: Benchmark, workspace: Path) -> BenchmarkResult:
        """Executes the benchmark using the Chief Runtime."""
        print(f"\n[Chief Executor] Starting benchmark {benchmark.id} in {workspace}")
        
        context = RunContext(
            goal_text=benchmark.goal,
            metadata={"workspace": str(workspace), "benchmark_id": benchmark.id}
        )
        
        start_time = time.monotonic()
        
        try:
            run_result = self._runtime.execute_goal(context)
            duration = (time.monotonic() - start_time) * 1000
            
            # In a real implementation, we would inspect the workspace here
            # to verify files were created, tests pass, etc.
            metadata = {
                "tests_pass": True,      # Placeholder: run pytest in workspace
                "readme_exists": True,   # Placeholder: check if README.md exists
                "valid_structure": True  # Placeholder: check if pyproject.toml exists
            }
            
            return BenchmarkResult(
                run_id=context.run_id,
                benchmark_id=benchmark.id,
                success=run_result.outcome == "success",
                duration_ms=duration,
                metadata=metadata
            )
            
        except Exception as e:
            return BenchmarkResult(
                run_id=context.run_id,
                benchmark_id=benchmark.id,
                success=False,
                duration_ms=(time.monotonic() - start_time) * 1000,
                logs=(str(e),)
            )