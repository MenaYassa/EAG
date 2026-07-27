"""Plan validation engine for EAG."""

from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.operations import OperationRegistry, default_operation_registry
from eag.planner.validation.models import (
    EngineeringPlanValidationResult,
    ValidationIssue,
    ValidationSeverity,
)
from eag.planner.validation.protocol import PlanValidationRule
from eag.planner.validation.rules import (
    DependencyRule,
    ExecutionRule,
    RiskRule,
    SafetyRule,
    StructureRule,
)


class PlanValidator:
    """Orchestrates validation rules against an engineering planning artifact."""

    def __init__(self, operation_registry: OperationRegistry | None = None) -> None:
        self._rules: list[PlanValidationRule] = [
            StructureRule(),
            DependencyRule(),
            SafetyRule(),
            RiskRule(),
            ExecutionRule(operation_registry or default_operation_registry()),
        ]

    def validate(self, artifact: EngineeringPlanningArtifact) -> EngineeringPlanValidationResult:
        """Run all validation rules and aggregate the results."""
        all_issues: list[ValidationIssue] = []
        for rule in self._rules:
            all_issues.extend(rule.validate(artifact))

        errors = sum(1 for i in all_issues if i.severity == ValidationSeverity.ERROR)
        critical = sum(1 for i in all_issues if i.severity == ValidationSeverity.CRITICAL)
        warnings = sum(1 for i in all_issues if i.severity == ValidationSeverity.WARNING)

        valid = errors == 0 and critical == 0
        requires_approval = artifact.risk.requires_approval

        summary = self._build_summary(valid, errors, warnings, critical)

        return EngineeringPlanValidationResult(
            valid=valid,
            issues=tuple(all_issues),
            warnings=warnings,
            errors=errors,
            critical=critical,
            requires_approval=requires_approval,
            summary=summary,
        )

    def _build_summary(self, valid: bool, errors: int, warnings: int, critical: int) -> str:
        if valid and warnings == 0 and critical == 0:
            return "Plan validation passed with no issues."
        if valid:
            return f"Plan validation passed with {warnings} warnings."
        return f"Plan validation failed with {errors} errors and {critical} critical issues."
