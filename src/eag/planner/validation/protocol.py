"""Validation rule protocol for EAG."""

from typing import Protocol, runtime_checkable

from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.validation.models import ValidationIssue


@runtime_checkable
class PlanValidationRule(Protocol):
    """The contract for a plan validation rule."""

    def validate(self, artifact: EngineeringPlanningArtifact) -> tuple[ValidationIssue, ...]:
        """Evaluate the artifact and return any validation issues."""
        ...