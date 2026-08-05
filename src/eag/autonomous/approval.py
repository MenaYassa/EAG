"""Approval Runtime for EAG Autonomous Loop."""

from datetime import UTC, datetime

from eag.autonomous.enums import ApprovalState
from eag.autonomous.models import ApprovalRequest


class ApprovalRuntime:
    """Manages human approval gates for the autonomous loop."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def request_approval(self, loop_id: str, iteration: int, reason: str) -> ApprovalRequest:
        """Creates a pending approval request."""
        req = ApprovalRequest(loop_id=loop_id, iteration=iteration, reason=reason)
        self._requests[req.id] = req
        return req

    def approve(self, request_id: str, reviewer: str = "human") -> ApprovalRequest:
        """Approves a pending request."""
        if request_id not in self._requests:
            raise ValueError(f"Approval request '{request_id}' not found.")

        old_req = self._requests[request_id]
        new_req = ApprovalRequest(
            id=old_req.id,
            loop_id=old_req.loop_id,
            iteration=old_req.iteration,
            reason=old_req.reason,
            state=ApprovalState.APPROVED,
            reviewed_by=reviewer,
            comments=old_req.comments,
            created_at=old_req.created_at,
            resolved_at=datetime.now(UTC),
        )
        self._requests[request_id] = new_req
        return new_req

    def reject(
        self, request_id: str, reviewer: str = "human", comments: str = ""
    ) -> ApprovalRequest:
        """Rejects a pending request."""
        if request_id not in self._requests:
            raise ValueError(f"Approval request '{request_id}' not found.")

        old_req = self._requests[request_id]
        new_req = ApprovalRequest(
            id=old_req.id,
            loop_id=old_req.loop_id,
            iteration=old_req.iteration,
            reason=old_req.reason,
            state=ApprovalState.REJECTED,
            reviewed_by=reviewer,
            comments=comments,
            created_at=old_req.created_at,
            resolved_at=datetime.now(UTC),
        )
        self._requests[request_id] = new_req
        return new_req

    def get_request(self, request_id: str) -> ApprovalRequest:
        if request_id not in self._requests:
            raise ValueError(f"Approval request '{request_id}' not found.")
        return self._requests[request_id]

    def record_decision(self, approval_id: str, approved: bool, reviewer: str = "system") -> None:
        """Helper method to record an approval or rejection decision."""
        if approved:
            self.approve(approval_id, reviewer=reviewer)
        else:
            self.reject(approval_id, reviewer=reviewer)
