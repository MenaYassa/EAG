"""Approval domain vocabulary for EAG."""

from enum import StrEnum


class ApprovalState(StrEnum):
    """Lifecycle state of an approval request."""

    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalLevel(StrEnum):
    """The authority level required to approve a plan."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalReason(StrEnum):
    """Deterministic reasons for an approval decision."""

    LOW_RISK = "low_risk"
    HIGH_RISK = "high_risk"
    DANGEROUS_OPERATION = "dangerous_operation"
    VALIDATION_FAILURE = "validation_failure"
    SIMULATION_WARNING = "simulation_warning"
    OWNER_REQUIRED = "owner_required"
    MANUAL_POLICY = "manual_policy"
