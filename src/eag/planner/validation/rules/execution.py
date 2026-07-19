"""Execution validation rules for EAG."""

from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.operations import OperationRegistry
from eag.planner.validation.models import ValidationCategory, ValidationIssue, ValidationSeverity


class ExecutionRule:
    """Validates that the plan can actually be executed in the current environment."""

    def __init__(self, registry: OperationRegistry) -> None:
        self._registry = registry

    def validate(self, artifact: EngineeringPlanningArtifact) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []

        try:
            self._registry.find(artifact.engineering_goal)
        except Exception:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.EXECUTION,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Operation {artifact.engineering_goal.operation.value} "
                        "is not supported by the execution registry."
                    ),
                    affected_tasks=tuple(t.id for t in artifact.tasks),
                )
            )

        for task in artifact.tasks:
            if "database.write" in task.required_capabilities:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.EXECUTION,
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Task {task.id} requires 'database.write' capability. "
                            "Ensure environment supports it."
                        ),
                        affected_tasks=(task.id,),
                    )
                )

        return tuple(issues)
