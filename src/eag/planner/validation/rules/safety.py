"""Safety validation rules for EAG."""

from eag.planner.intelligence.models import EngineeringComplexity, EngineeringPlanningArtifact
from eag.planner.validation.models import ValidationCategory, ValidationIssue, ValidationSeverity


class SafetyRule:
    """Validates safety constraints, such as rollback strategies for dangerous ops."""

    def validate(self, artifact: EngineeringPlanningArtifact) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        
        dangerous_ops = ["DELETE", "UPGRADE"]
        
        if artifact.engineering_goal.operation.name in dangerous_ops:
            if artifact.risk.rollback_complexity == EngineeringComplexity.EXTREME:
                issues.append(ValidationIssue(
                    category=ValidationCategory.SAFETY,
                    severity=ValidationSeverity.CRITICAL,
                    message="Critical operation with extreme rollback complexity. Rollback strategy required.",
                    affected_tasks=tuple(t.id for t in artifact.tasks)
                ))
            else:
                issues.append(ValidationIssue(
                    category=ValidationCategory.SAFETY,
                    severity=ValidationSeverity.WARNING,
                    message="Dangerous operation detected. Rollback strategy recommended.",
                    affected_tasks=tuple(t.id for t in artifact.tasks)
                ))

        return tuple(issues)