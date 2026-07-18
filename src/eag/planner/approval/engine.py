"""Approval governance engine for EAG."""

from datetime import UTC, datetime

from eag.planner.approval.enums import ApprovalLevel, ApprovalReason, ApprovalState
from eag.planner.approval.models import (
    ApprovalDecision,
    ApprovalFinding,
    ApprovalResult,
)
from eag.planner.approval.policies import (
    AutomaticApprovalPolicy,
    DangerousOperationPolicy,
    OwnershipPolicy,
    RiskApprovalPolicy,
)
from eag.planner.approval.protocol import ApprovalPolicy
from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.simulation.models import EngineeringSimulationReport
from eag.planner.validation.models import EngineeringPlanValidationResult


class ApprovalEngine:
    """Orchestrates approval policies to produce an ApprovalResult."""

    def __init__(self, policies: list[ApprovalPolicy] | None = None) -> None:
        self._policies = policies or [
            AutomaticApprovalPolicy(),
            RiskApprovalPolicy(),
            DangerousOperationPolicy(),
            OwnershipPolicy(),
        ]

    def evaluate(
        self,
        artifact: EngineeringPlanningArtifact,
        validation: EngineeringPlanValidationResult,
        simulation: EngineeringSimulationReport,
    ) -> ApprovalResult:
        """Run all policies and aggregate their findings into a final decision."""
        findings: list[ApprovalFinding] = []
        for policy in self._policies:
            finding = policy.evaluate(artifact, validation, simulation)
            findings.append(finding)

        # If validation failed, short-circuit to Rejected
        if not validation.valid:
            decision = ApprovalDecision(
                state=ApprovalState.REJECTED,
                reason=ApprovalReason.VALIDATION_FAILURE,
                comments="Plan failed validation.",
            )
            return ApprovalResult(
                approved=False,
                decision=decision,
                required_level=ApprovalLevel.NONE,
                triggered_policies=tuple(f.policy_name for f in findings),
                summary="Plan rejected due to validation failures.",
            )

        # Aggregate policy results
        approved = True
        requires_manual = False
        required_level = ApprovalLevel.NONE
        reasons: list[ApprovalReason] = []
        triggered: list[str] = []
        summaries: list[str] = []

        # Level ordering helper
        level_order = {
            ApprovalLevel.NONE: 0,
            ApprovalLevel.LOW: 1,
            ApprovalLevel.MEDIUM: 2,
            ApprovalLevel.HIGH: 3,
            ApprovalLevel.CRITICAL: 4,
        }

        for finding in findings:
            triggered.append(finding.policy_name)
            if finding.requires_manual:
                requires_manual = True
                approved = False
                summaries.append(finding.summary)
            if not finding.approved and not finding.requires_manual:
                # Policy explicitly denied without manual review (e.g. auto-approve failed)
                # This doesn't necessarily block if another policy approves, 
                # but for governance, we treat it as "not auto-approved"
                approved = False
            
            if level_order.get(finding.required_level, 0) > level_order.get(required_level, 0):
                required_level = finding.required_level
                
            for r in finding.reasons:
                if r not in reasons:
                    reasons.append(r)

        # Determine final state
        if requires_manual:
            state = ApprovalState.PENDING
            reason = reasons[0] if reasons else ApprovalReason.MANUAL_POLICY
            summary = " ".join(summaries) if summaries else "Manual approval required."
        elif approved:
            state = ApprovalState.AUTO_APPROVED
            reason = ApprovalReason.LOW_RISK
            summary = "Plan automatically approved by governance engine."
        else:
            # Fallback if not explicitly manual but not auto-approved
            state = ApprovalState.PENDING
            reason = ApprovalReason.MANUAL_POLICY
            summary = "Plan requires manual review."

        decision = ApprovalDecision(
            state=state,
            reason=reason,
            approved_by="system" if state == ApprovalState.AUTO_APPROVED else None,
            approved_at=datetime.now(UTC) if state == ApprovalState.AUTO_APPROVED else None,
            comments=summary,
        )

        return ApprovalResult(
            approved=(state == ApprovalState.AUTO_APPROVED),
            decision=decision,
            required_level=required_level,
            triggered_policies=tuple(triggered),
            summary=summary,
        )