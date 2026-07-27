"""Structural validation rules for EAG."""

from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.validation.models import ValidationCategory, ValidationIssue, ValidationSeverity


class StructureRule:
    """Validates the basic structural integrity of the plan."""

    def validate(self, artifact: EngineeringPlanningArtifact) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []

        if not artifact.tasks:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.STRUCTURE,
                    severity=ValidationSeverity.ERROR,
                    message="Plan must contain at least one task.",
                )
            )

        for task in artifact.tasks:
            if not task.title.strip():
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.STRUCTURE,
                        severity=ValidationSeverity.ERROR,
                        message="Task title cannot be empty.",
                        affected_tasks=(task.id,),
                    )
                )

        if not artifact.graph.nodes:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.STRUCTURE,
                    severity=ValidationSeverity.ERROR,
                    message="Dependency graph is empty.",
                )
            )

        return tuple(issues)
