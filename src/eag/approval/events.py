"""Approval lifecycle events."""

from dataclasses import dataclass

from eag.approval.models import ApprovalRequest
from eag.events import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRequested(Event):
    """Published when an approval request is created."""

    request: ApprovalRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalApproved(Event):
    """Published when an approval request is approved."""

    request: ApprovalRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRejected(Event):
    """Published when an approval request is rejected."""

    request: ApprovalRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalExpired(Event):
    """Published when an approval request expires."""

    request: ApprovalRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalConsumed(Event):
    """Published when an approval authorization is consumed."""

    request: ApprovalRequest
