"""Built-in approval policies for EAG."""

from eag.planner.approval.enums import ApprovalLevel, ApprovalReason, ApprovalState
from eag.planner.approval.models import ApprovalFinding
from eag.planner.enums import RiskLevel
from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.simulation.models import EngineeringSimulationReport, SimulationStatus
from eag.planner.validation.models import EngineeringPlanValidationResult


class AutomaticApprovalPolicy:
    """Automatically approves plans that are valid, safe, and ready."""

    @property
    def name(self) -> str:
        return "AutomaticApprovalPolicy"

    def evaluate(
        self,
        artifact: EngineeringPlanningArtifact,
        validation: EngineeringPlanValidationResult,
        simulation: EngineeringSimulationReport,
    ) -> ApprovalFinding:
        if (
            validation.valid
            and simulation.status == SimulationStatus.READY
            and artifact.risk.overall_risk in [RiskLevel.NONE, RiskLevel.LOW]
        ):
            return ApprovalFinding(
                policy_name=self.name,
                approved=True,
                requires_manual=False,
                required_level=ApprovalLevel.NONE,
                reasons=(ApprovalReason.LOW_RISK,),
                summary="Plan is safe and automatically approved.",
            )
        return ApprovalFinding(
            policy_name=self.name,
            approved=False,
            requires_manual=False,
            summary="Plan does not meet automatic approval criteria.",
        )


class RiskApprovalPolicy:
    """Requires manual approval for high-risk plans."""

    @property
    def name(self) -> str:
        return "RiskApprovalPolicy"

    def evaluate(
        self,
        artifact: EngineeringPlanningArtifact,
        validation: EngineeringPlanValidationResult,
        simulation: EngineeringSimulationReport,
    ) -> ApprovalFinding:
        risk = artifact.risk.overall_risk
        if risk == RiskLevel.HIGH:
            return ApprovalFinding(
                policy_name=self.name,
                approved=False,
                requires_manual=True,
                required_level=ApprovalLevel.HIGH,
                reasons=(ApprovalReason.HIGH_RISK,),
                summary="High risk detected. Manual approval required.",
            )
        if risk == RiskLevel.CRITICAL:
            return ApprovalFinding(
                policy_name=self.name,
                approved=False,
                requires_manual=True,
                required_level=ApprovalLevel.CRITICAL,
                reasons=(ApprovalReason.HIGH_RISK,),
                summary="Critical risk detected. Executive approval required.",
            )
        return ApprovalFinding(
            policy_name=self.name,
            approved=True,
            requires_manual=False,
            summary="Risk level is acceptable.",
        )


class DangerousOperationPolicy:
    """Requires critical approval for dangerous operations like DELETE or UPGRADE."""

    DANGEROUS_OPS = ["DELETE", "UPGRADE"]

    @property
    def name(self) -> str:
        return "DangerousOperationPolicy"

    def evaluate(
        self,
        artifact: EngineeringPlanningArtifact,
        validation: EngineeringPlanValidationResult,
        simulation: EngineeringSimulationReport,
    ) -> ApprovalFinding:
        op_name = artifact.engineering_goal.operation.name
        if op_name in self.DANGEROUS_OPS:
            return ApprovalFinding(
                policy_name=self.name,
                approved=False,
                requires_manual=True,
                required_level=ApprovalLevel.CRITICAL,
                reasons=(ApprovalReason.DANGEROUS_OPERATION,),
                summary=f"Dangerous operation ({op_name}) detected. Critical approval required.",
            )
        return ApprovalFinding(
            policy_name=self.name,
            approved=True,
            requires_manual=False,
            summary="Operation is not classified as dangerous.",
        )


class OwnershipPolicy:
    """Requires architecture owner approval for repository-wide changes."""

    @property
    def name(self) -> str:
        return "OwnershipPolicy"

    def evaluate(
        self,
        artifact: EngineeringPlanningArtifact,
        validation: EngineeringPlanValidationResult,
        simulation: EngineeringSimulationReport,
    ) -> ApprovalFinding:
        if artifact.engineering_goal.scope.name == "REPOSITORY":
            return ApprovalFinding(
                policy_name=self.name,
                approved=False,
                requires_manual=True,
                required_level=ApprovalLevel.HIGH,
                reasons=(ApprovalReason.OWNER_REQUIRED,),
                summary="Repository-wide change requires Architecture Owner approval.",
            )
        return ApprovalFinding(
            policy_name=self.name,
            approved=True,
            requires_manual=False,
            summary="Change scope is within standard authority.",
        )