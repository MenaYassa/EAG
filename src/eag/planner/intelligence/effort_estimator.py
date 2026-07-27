"""Engineering Effort Estimator for EAG."""

from eag.planner.enums import RiskLevel
from eag.planner.intelligence.models import (
    EngineeringExecutionProfile,
    EngineeringGoal,
    EngineeringRiskAssessment,
    EngineeringScope,
    TaskDependencyGraph,
)
from eag.planner.models import EngineeringTask


class EffortEstimator:
    """Estimates engineering effort and execution metrics from a task graph."""

    _BASE_DURATIONS = {
        "locate": 1.0,
        "analyze": 2.0,
        "modify": 3.0,
        "update": 2.0,
        "validate": 2.0,
        "review": 1.0,
        "reproduce": 1.0,
        "implement": 3.0,
        "test": 2.0,
        "document": 2.0,
        "design": 2.0,
        "gather": 2.0,
        "report": 1.0,
        "identify": 1.0,
        "check": 1.0,
        "remove": 1.0,
        "move": 2.0,
        "write": 2.0,
        "fix": 3.0,
        "upgrade": 3.0,
        "create": 3.0,
        "rename": 2.0,
    }

    _SCOPE_MULTIPLIERS = {
        EngineeringScope.SYMBOL: 1.0,
        EngineeringScope.FILE: 2.0,
        EngineeringScope.MODULE: 3.0,
        EngineeringScope.PACKAGE: 5.0,
        EngineeringScope.REPOSITORY: 8.0,
        EngineeringScope.SYSTEM: 12.0,
    }

    _RISK_MULTIPLIERS = {
        RiskLevel.NONE: 1.0,
        RiskLevel.LOW: 1.1,
        RiskLevel.MEDIUM: 1.25,
        RiskLevel.HIGH: 1.5,
        RiskLevel.CRITICAL: 2.0,
    }

    def estimate(
        self,
        goal: EngineeringGoal,
        graph: TaskDependencyGraph,
        risk_assessment: EngineeringRiskAssessment,
    ) -> tuple[tuple[EngineeringTask, ...], EngineeringExecutionProfile]:
        """Estimate effort and return enriched tasks along with the execution profile."""
        scope_mult = self._SCOPE_MULTIPLIERS.get(goal.scope, 2.0)
        risk_mult = self._RISK_MULTIPLIERS.get(risk_assessment.overall_risk, 1.0)

        enriched_tasks = []
        task_durations = {}

        for node in graph.nodes.values():
            task = node.task
            base = self._get_base_duration(task.title)
            duration = base * scope_mult * risk_mult

            # Explicitly added "validation" keyword to cleanly capture "Run Validation"
            is_validation = any(
                kw in task.title.lower() for kw in ["validate", "validation", "test", "verify"]
            )
            is_review = any(kw in task.title.lower() for kw in ["document", "review", "report"])

            est_val = duration if is_validation else 0.0
            est_rev = duration if is_review else 0.0

            enriched_task = EngineeringTask(
                id=task.id,
                title=task.title,
                description=task.description,
                priority=task.priority,
                dependencies=task.dependencies,
                required_capabilities=task.required_capabilities,
                risk_level=task.risk_level,
                estimated_duration=duration,
                estimated_validation=est_val,
                estimated_review=est_rev,
                parallelizable=not node.outgoing and len(node.incoming) > 1,
                blocking=bool(node.outgoing),
                optional=task.optional,
                metadata=task.metadata,
            )
            enriched_tasks.append(enriched_task)
            task_durations[task.id] = duration

        critical_path = self._compute_critical_path(graph, task_durations)
        total_time = sum(task_durations.values())
        parallel_savings = max(0.0, total_time - critical_path)

        active_work = sum(
            t.estimated_duration - t.estimated_validation - t.estimated_review
            for t in enriched_tasks
        )
        total_val = sum(t.estimated_validation for t in enriched_tasks)
        total_rev = sum(t.estimated_review for t in enriched_tasks)

        confidence = self._compute_confidence(goal)
        summary = self._build_summary(total_time, critical_path, parallel_savings, confidence)

        profile = EngineeringExecutionProfile(
            total_engineering_time=total_time,
            critical_path_duration=critical_path,
            parallel_savings=parallel_savings,
            estimated_active_work=active_work,
            estimated_validation=total_val,
            estimated_review=total_rev,
            confidence=confidence,
            summary=summary,
        )

        # Correctly map the topological order
        ordered_tasks = tuple(graph.nodes[t.id].task for t in graph.ordered_tasks())
        enriched_map = {t.id: t for t in enriched_tasks}
        ordered_enriched = tuple(enriched_map[t.id] for t in ordered_tasks)

        return ordered_enriched, profile

    def _get_base_duration(self, title: str) -> float:
        title_lower = title.lower()
        for keyword, duration in self._BASE_DURATIONS.items():
            if keyword in title_lower:
                return float(duration)
        return 2.0  # Default

    def _compute_critical_path(
        self, graph: TaskDependencyGraph, durations: dict[str, float]
    ) -> float:
        cache: dict[str, float] = {}

        def get_longest(node_id: str) -> float:
            if node_id in cache:
                return cache[node_id]

            node = graph.nodes[node_id]
            if not node.outgoing:
                cache[node_id] = durations[node_id]
            else:
                cache[node_id] = durations[node_id] + float(
                    max(get_longest(pred) for pred in node.outgoing)
                )
            return cache[node_id]

        if not graph.nodes:
            return 0.0
        return max(get_longest(nid) for nid in graph.nodes)

    def _compute_confidence(self, goal: EngineeringGoal) -> float:
        if goal.scope == EngineeringScope.REPOSITORY:
            return 0.95
        if goal.operation.name == "UPGRADE":
            return 0.90
        return 1.0

    def _build_summary(self, total: float, critical: float, parallel: float, conf: float) -> str:
        return (
            f"Estimated engineering effort: {total:.1f} minutes. "
            f"Critical path: {critical:.1f} minutes. "
            f"Parallelizable work: {parallel:.1f} minutes. "
            f"Confidence: {conf * 100:.0f}%."
        )
