"""Dependency validation rules for EAG."""

from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.validation.models import ValidationCategory, ValidationIssue, ValidationSeverity


class DependencyRule:
    """Validates the task dependency graph for cycles, orphans, and missing links."""

    def validate(self, artifact: EngineeringPlanningArtifact) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        task_ids = {t.id for t in artifact.tasks}

        for task in artifact.tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.DEPENDENCY,
                        severity=ValidationSeverity.ERROR,
                        message=f"Task {task.id} depends on missing task {dep_id}.",
                        affected_tasks=(task.id,)
                    ))

        if artifact.graph.statistics.cyclic:
            issues.append(ValidationIssue(
                category=ValidationCategory.DEPENDENCY,
                severity=ValidationSeverity.CRITICAL,
                message="Circular dependency detected in task graph."
            ))

        if len(artifact.tasks) > 1:
            for node in artifact.graph.nodes.values():
                if not node.incoming and not node.outgoing:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.DEPENDENCY,
                        severity=ValidationSeverity.WARNING,
                        message=f"Task {node.task.id} is disconnected from the plan.",
                        affected_tasks=(node.task.id,)
                    ))

        return tuple(issues)