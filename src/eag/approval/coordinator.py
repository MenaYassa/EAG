"""Coordinate policy decisions with approval workflows."""

from dataclasses import dataclass

from eag.approval.manager import ApprovalManager
from eag.approval.models import ApprovalRequest
from eag.execution.classification import (
    PolicyDecision,
    PolicyOutcome,
)


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class ApprovalCoordinationResult:
    """Describe the approval consequence of a policy decision."""

    decision: PolicyDecision
    approval: ApprovalRequest | None = None

    @property
    def approval_created(self) -> bool:
        """Return whether an approval request was created."""
        return self.approval is not None


class ApprovalCoordinator:
    """Translate policy decisions into approval workflows."""

    def __init__(
        self,
        *,
        manager: ApprovalManager,
    ) -> None:
        self._manager = manager

    @property
    def manager(self) -> ApprovalManager:
        """Return the approval manager."""
        return self._manager

    def coordinate(
        self,
        decision: PolicyDecision,
    ) -> ApprovalCoordinationResult:
        """Coordinate the approval consequence of a policy decision."""
        if decision.outcome is not PolicyOutcome.REQUIRE_APPROVAL:
            return ApprovalCoordinationResult(
                decision=decision,
            )

        approval = self._manager.create(
            command=decision.request,
            classification=decision.classification,
            policy_outcome=decision.outcome,
            policy_reason=decision.reason,
            matched_rule=decision.matched_rule,
        )

        return ApprovalCoordinationResult(
            decision=decision,
            approval=approval,
        )
