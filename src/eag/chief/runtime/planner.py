"""Default deterministic planner for EAG Chief Runtime."""

from eag.benchmark.templates import get_benchmark_plan
from eag.chief.runtime.models import Plan, PlanStep, RunContext


class DefaultPlanner:
    """Translates a goal into a deterministic execution plan."""

    def create_plan(self, context: RunContext) -> Plan:
        # Extract benchmark ID from metadata
        benchmark_id = context.metadata.get("benchmark_id")
        
        # 1. Use the template planner for known benchmark IDs
        if benchmark_id and benchmark_id.startswith("EBS-"):
            try:
                return get_benchmark_plan(benchmark_id)
            except KeyError:
                pass

        # 2. Fallback to goal-text matching (e.g., calculator or EBS-001 default)
        goal = context.goal_text.lower() if context.goal_text else ""

        if "calculator" in goal or benchmark_id == "EBS-001":
            return get_benchmark_plan("EBS-001")

        # 3. Generic fallback for unknown goals
        return Plan(
            steps=(
                PlanStep(
                    step_id="step_1_git_init",
                    name="Initialize Git Repository",
                    capability_id="repository",
                    metadata={"operation": "init"},
                ),
                PlanStep(
                    step_id="step_2_readme",
                    name="Create README.md",
                    capability_id="workspace",
                    dependencies=("step_1_git_init",),
                    metadata={
                        "operation": "write",
                        "path": "README.md",
                        "content": f"# Project\n\n{context.goal_text}",
                    },
                ),
                PlanStep(
                    step_id="step_3_commit",
                    name="Commit Implementation",
                    capability_id="repository",
                    dependencies=("step_2_readme",),
                    metadata={"operation": "commit", "message": "Initial commit"},
                ),
            )
        )