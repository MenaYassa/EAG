"""Risk validation rules for EAG."""

from eag.planner.enums import RiskLevel
from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.validation.models import ValidationCategory, ValidationIssue, ValidationSeverity


class RiskRule:
    """Validates risk thresholds and approval requirements."""

    def validate(self, artifact: EngineeringPlanningArtifact) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []

        if artifact.risk.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.RISK,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Plan risk is {artifact.risk.overall_risk.value}. "
                        "Approval required before execution."
                    ),
                    affected_tasks=tuple(t.id for t in artifact.tasks),
                )
            )

        return tuple(issues)
