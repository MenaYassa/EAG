"""Approval lifecycle management."""

from dataclasses import replace
from datetime import UTC, datetime

from eag.approval.errors import (
    ApprovalCommandMismatchError,
    ApprovalExpiredError,
    ApprovalInvalidTransitionError,
)
from eag.approval.events import (
    ApprovalApproved,
    ApprovalConsumed,
    ApprovalExpired,
    ApprovalRejected,
    ApprovalReleased,
    ApprovalRequested,
    ApprovalReserved,
)
from eag.approval.models import (
    ApprovalRequest,
    ApprovalStatus,
    new_approval_request,
)
from eag.approval.store import ApprovalStore
from eag.events import Event, EventBus
from eag.execution.classification import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.models import CommandRequest


class ApprovalManager:
    """Manage approval requests and lifecycle transitions."""

    def __init__(
        self,
        *,
        store: ApprovalStore,
        event_bus: EventBus | None = None,
    ) -> None:
        self._store = store
        self._event_bus = event_bus

    def create(
        self,
        *,
        command: CommandRequest,
        classification: CommandClassification,
        policy_outcome: PolicyOutcome,
        policy_reason: str,
        matched_rule: str,
        expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Create and persist a pending approval request."""
        request = new_approval_request(
            command=command,
            classification=classification,
            policy_outcome=policy_outcome,
            policy_reason=policy_reason,
            matched_rule=matched_rule,
            expires_at=expires_at,
            now=now,
        )

        self._store.add(request)

        self._publish(
            ApprovalRequested(
                request=request,
            )
        )

        return request

    def get(
        self,
        approval_id: str,
    ) -> ApprovalRequest:
        """Return an approval request by ID."""
        return self._store.get(approval_id)

    def list(
        self,
        *,
        status: ApprovalStatus | None = None,
    ) -> tuple[ApprovalRequest, ...]:
        """Return approval requests, optionally filtered."""
        return self._store.list(status=status)

    def approve(
        self,
        approval_id: str,
        *,
        reason: str | None = None,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Approve a pending request."""
        request = self._store.get(approval_id)
        current_time = now or datetime.now(UTC)

        request = self._expire_if_needed(
            request,
            now=current_time,
        )

        if request.status is ApprovalStatus.EXPIRED:
            raise ApprovalExpiredError(f"Approval request has expired: '{approval_id}'")

        self._require_status(
            request,
            ApprovalStatus.PENDING,
            action="approve",
        )

        approved = replace(
            request,
            status=ApprovalStatus.APPROVED,
            decided_at=current_time,
            decision_reason=reason,
        )

        self._store.save(approved)

        self._publish(
            ApprovalApproved(
                request=approved,
            )
        )

        return approved

    def reject(
        self,
        approval_id: str,
        *,
        reason: str | None = None,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Reject a pending request."""
        request = self._store.get(approval_id)
        current_time = now or datetime.now(UTC)

        request = self._expire_if_needed(
            request,
            now=current_time,
        )

        if request.status is ApprovalStatus.EXPIRED:
            raise ApprovalExpiredError(f"Approval request has expired: '{approval_id}'")

        self._require_status(
            request,
            ApprovalStatus.PENDING,
            action="reject",
        )

        rejected = replace(
            request,
            status=ApprovalStatus.REJECTED,
            decided_at=current_time,
            decision_reason=reason,
        )

        self._store.save(rejected)

        self._publish(
            ApprovalRejected(
                request=rejected,
            )
        )

        return rejected

    def reserve(
        self,
        approval_id: str,
        *,
        command: CommandRequest,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Atomically reserve approved authorization for execution."""
        request = self._store.get(approval_id)
        current_time = now or datetime.now(UTC)

        request = self._expire_if_needed(
            request,
            now=current_time,
        )

        if request.status is ApprovalStatus.EXPIRED:
            raise ApprovalExpiredError(f"Approval request has expired: '{approval_id}'")

        if request.command != command:
            raise ApprovalCommandMismatchError(
                f"Execution request does not match approval '{approval_id}'"
            )

        reserved = replace(
            request,
            status=ApprovalStatus.RESERVED,
        )

        transitioned = self._store.transition(
            approval_id,
            expected=ApprovalStatus.APPROVED,
            replacement=reserved,
        )

        if not transitioned:
            current = self._store.get(approval_id)
            raise ApprovalInvalidTransitionError(
                "Cannot reserve approval in state "
                f"'{current.status.value}'; expected "
                f"'{ApprovalStatus.APPROVED.value}'"
            )

        self._publish(
            ApprovalReserved(
                request=reserved,
            )
        )

        return reserved

    def release(
        self,
        approval_id: str,
        *,
        command: CommandRequest | None = None,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Release reserved authorization back to approved state."""
        request = self._store.get(approval_id)

        released = replace(
            request,
            status=ApprovalStatus.APPROVED,
        )

        transitioned = self._store.transition(
            approval_id,
            expected=ApprovalStatus.RESERVED,
            replacement=released,
        )

        if not transitioned:
            current = self._store.get(approval_id)
            raise ApprovalInvalidTransitionError(
                "Cannot release approval in state "
                f"'{current.status.value}'; expected "
                f"'{ApprovalStatus.RESERVED.value}'"
            )

        self._publish(
            ApprovalReleased(
                request=released,
            )
        )

        return released

    def consume(
        self,
        approval_id: str,
        *,
        command: CommandRequest,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Consume an approved request for its exact command."""
        request = self._store.get(approval_id)
        current_time = now or datetime.now(UTC)

        request = self._expire_if_needed(
            request,
            now=current_time,
        )

        if request.status is ApprovalStatus.EXPIRED:
            raise ApprovalExpiredError(f"Approval request has expired: '{approval_id}'")

        self._require_status(
            request,
            ApprovalStatus.RESERVED,
            action="consume",
        )

        if request.command != command:
            # Release the reservation before raising
            self.release(approval_id, now=now)
            raise ApprovalCommandMismatchError(
                f"Execution request does not match approval '{approval_id}'"
            )

        consumed = replace(
            request,
            status=ApprovalStatus.CONSUMED,
            consumed_at=current_time,
        )

        transitioned = self._store.transition(
            approval_id,
            expected=ApprovalStatus.RESERVED,
            replacement=consumed,
        )

        if not transitioned:
            current = self._store.get(approval_id)
            raise ApprovalInvalidTransitionError(
                "Cannot consume approval in state "
                f"'{current.status.value}'; expected "
                f"'{ApprovalStatus.RESERVED.value}'"
            )

        self._publish(
            ApprovalConsumed(
                request=consumed,
            )
        )

        return consumed

    def expire(
        self,
        approval_id: str,
        *,
        now: datetime | None = None,
    ) -> ApprovalRequest:
        """Expire a pending or approved request if due."""
        request = self._store.get(approval_id)
        current_time = now or datetime.now(UTC)

        if request.status not in {
            ApprovalStatus.PENDING,
            ApprovalStatus.APPROVED,
        }:
            raise ApprovalInvalidTransitionError(
                f"Cannot expire approval in state '{request.status.value}'"
            )

        if not request.is_expired(now=current_time):
            raise ApprovalInvalidTransitionError(
                f"Approval request is not expired: '{approval_id}'"
            )

        expired = replace(
            request,
            status=ApprovalStatus.EXPIRED,
        )

        self._store.save(expired)

        self._publish(
            ApprovalExpired(
                request=expired,
            )
        )

        return expired

    def _expire_if_needed(
        self,
        request: ApprovalRequest,
        *,
        now: datetime,
    ) -> ApprovalRequest:
        """Persist expiry when an active request is past due."""
        if request.status in {
            ApprovalStatus.PENDING,
            ApprovalStatus.APPROVED,
        } and request.is_expired(now=now):
            expired = replace(
                request,
                status=ApprovalStatus.EXPIRED,
            )
            self._store.save(expired)

            self._publish(
                ApprovalExpired(
                    request=expired,
                )
            )

            return expired

        return request

    @staticmethod
    def _require_status(
        request: ApprovalRequest,
        expected: ApprovalStatus,
        *,
        action: str,
    ) -> None:
        """Require a specific lifecycle state."""
        if request.status is not expected:
            raise ApprovalInvalidTransitionError(
                f"Cannot {action} approval in state "
                f"'{request.status.value}'; expected "
                f"'{expected.value}'"
            )

    def _publish(self, event: Event) -> None:
        """Publish an approval event when an event bus is configured."""
        if self._event_bus is not None:
            self._event_bus.publish(event)
