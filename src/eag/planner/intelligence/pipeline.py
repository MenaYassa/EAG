"""Engineering Intelligence Pipeline for EAG.

Orchestrates the entire intelligence flow, converting an EngineeringGoal
into a complete EngineeringPlanningArtifact.
"""

from eag.planner.intelligence.dependency_resolver import TaskDependencyResolver
from eag.planner.intelligence.effort_estimator import EffortEstimator
from eag.planner.intelligence.models import (
    EngineeringGoal,
    EngineeringPlanningArtifact,
)
from eag.planner.intelligence.risk_analyzer import RiskAnalyzer
from eag.planner.intelligence.task_decomposer import TaskDecomposer


class EngineeringIntelligencePipeline:
    """A façade over the engineering intelligence components."""

    def analyze(self, eng_goal: EngineeringGoal) -> EngineeringPlanningArtifact:
        """Run the full intelligence pipeline and produce an artifact."""
        tasks = TaskDecomposer().decompose(eng_goal)
        graph = TaskDependencyResolver().build(tasks)
        risk = RiskAnalyzer().analyze(eng_goal, graph)
        enriched_tasks, profile = EffortEstimator().estimate(eng_goal, graph, risk)

        return EngineeringPlanningArtifact(
            goal=eng_goal.planning_goal,
            engineering_goal=eng_goal,
            tasks=enriched_tasks,
            graph=graph,
            risk=risk,
            execution_profile=profile,
        )
