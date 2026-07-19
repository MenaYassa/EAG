"""Approval domain models for EAG."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.planner.approval.enums import ApprovalLevel, ApprovalReason, ApprovalState


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRequest:
    """A request to approve an engineering plan."""

    id: str
    plan_id: str
    requested_by: str = "system"
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    required_level: ApprovalLevel = ApprovalLevel.NONE
    required_roles: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not isinstance(self.plan_id, str) or not self.plan_id.strip():
            raise ValueError("plan_id cannot be empty")
        if not isinstance(self.required_level, ApprovalLevel):
            raise TypeError("required_level must be an ApprovalLevel")
        if not isinstance(self.required_roles, tuple):
            raise TypeError("required_roles must be a tuple")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalDecision:
    """The outcome of an approval evaluation."""

    state: ApprovalState
    reason: ApprovalReason = ApprovalReason.LOW_RISK
    approved_by: str | None = None
    approved_at: datetime | None = None
    comments: str = ""
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, ApprovalState):
            raise TypeError("state must be an ApprovalState")
        if not isinstance(self.reason, ApprovalReason):
            raise TypeError("reason must be an ApprovalReason")


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalFinding:
    """The result of a single approval policy evaluation."""

    policy_name: str
    approved: bool
    requires_manual: bool
    required_level: ApprovalLevel = ApprovalLevel.NONE
    reasons: tuple[ApprovalReason, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.policy_name, str) or not self.policy_name.strip():
            raise ValueError("policy_name cannot be empty")
        if not isinstance(self.approved, bool):
            raise TypeError("approved must be a bool")
        if not isinstance(self.requires_manual, bool):
            raise TypeError("requires_manual must be a bool")
        if not isinstance(self.required_level, ApprovalLevel):
            raise TypeError("required_level must be an ApprovalLevel")
        if not isinstance(self.reasons, tuple):
            raise TypeError("reasons must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalResult:
    """The final, aggregated artifact produced by the ApprovalEngine."""

    approved: bool
    decision: ApprovalDecision
    required_level: ApprovalLevel
    triggered_policies: tuple[str, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.approved, bool):
            raise TypeError("approved must be a bool")
        if not isinstance(self.decision, ApprovalDecision):
            raise TypeError("decision must be an ApprovalDecision")
        if not isinstance(self.required_level, ApprovalLevel):
            raise TypeError("required_level must be an ApprovalLevel")
        if not isinstance(self.triggered_policies, tuple):
            raise TypeError("triggered_policies must be a tuple")
        if not isinstance(self.summary, str):
            raise TypeError("summary must be a str")
