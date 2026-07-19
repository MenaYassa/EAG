"""Approval policy protocol for EAG."""

from typing import Protocol, runtime_checkable

from eag.planner.approval.models import ApprovalFinding
from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.simulation.models import EngineeringSimulationReport
from eag.planner.validation.models import EngineeringPlanValidationResult


@runtime_checkable
class ApprovalPolicy(Protocol):
    """The contract for an approval governance policy."""

    @property
    def name(self) -> str: ...

    def evaluate(
        self,
        artifact: EngineeringPlanningArtifact,
        validation: EngineeringPlanValidationResult,
        simulation: EngineeringSimulationReport,
    ) -> ApprovalFinding: ...
