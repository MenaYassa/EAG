"""Approval domain models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from eag.execution.classification import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.models import CommandRequest


class ApprovalStatus(StrEnum):
    """Lifecycle states for an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    RESERVED = "reserved"
    REJECTED = "rejected"
    CONSUMED = "consumed"
    EXPIRED = "expired"


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class ApprovalRequest:
    """Immutable request for human approval."""

    id: str
    command: CommandRequest
    classification: CommandClassification
    policy_outcome: PolicyOutcome
    policy_reason: str
    matched_rule: str
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    consumed_at: datetime | None = None
    decision_reason: str | None = None

    @property
    def is_pending(self) -> bool:
        """Return whether the request awaits a decision."""
        return self.status is ApprovalStatus.PENDING

    @property
    def is_terminal(self) -> bool:
        """Return whether no further lifecycle action is valid."""
        return self.status in {
            ApprovalStatus.REJECTED,
            ApprovalStatus.CONSUMED,
            ApprovalStatus.EXPIRED,
        }

    def is_expired(
        self,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Return whether the request has passed its expiry time."""
        if self.expires_at is None:
            return False

        current_time = now or datetime.now(UTC)
        return current_time >= self.expires_at


def new_approval_request(
    *,
    command: CommandRequest,
    classification: CommandClassification,
    policy_outcome: PolicyOutcome,
    policy_reason: str,
    matched_rule: str,
    expires_at: datetime | None = None,
    now: datetime | None = None,
) -> ApprovalRequest:
    """Create a new pending approval request."""
    created_at = now or datetime.now(UTC)

    if expires_at is not None and expires_at <= created_at:
        raise ValueError("Approval expiry must be later than creation time")

    if policy_outcome is not PolicyOutcome.REQUIRE_APPROVAL:
        raise ValueError("Approval requests require a require_approval policy outcome")

    return ApprovalRequest(
        id=uuid4().hex,
        command=command,
        classification=classification,
        policy_outcome=policy_outcome,
        policy_reason=policy_reason,
        matched_rule=matched_rule,
        status=ApprovalStatus.PENDING,
        created_at=created_at,
        expires_at=expires_at,
    )
