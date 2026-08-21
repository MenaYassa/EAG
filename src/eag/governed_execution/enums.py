"""Typed vocabulary for the deterministic G2.4.1 execution ledger."""

from __future__ import annotations

from enum import StrEnum


class GovernedExecutionState(StrEnum):
    """Lifecycle states representable by the G2.4.1 ledger only."""

    CREATED = "created"
    CONTEXT_ASSEMBLING = "context_assembling"
    PLANNING = "planning"
    DECIDING = "deciding"
    PROPOSING = "proposing"
    APPROVAL_PENDING = "approval_pending"
    AUTHORIZING = "authorizing"
    MUTATING = "mutating"
    VERIFYING = "verifying"
    REFLECTING = "reflecting"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"

    @property
    def is_terminal(self) -> bool:
        """Return whether no further transition is legal from this state."""
        return self in {
            GovernedExecutionState.COMPLETED,
            GovernedExecutionState.FAILED,
            GovernedExecutionState.ABORTED,
        }


class GovernedExecutionStopReason(StrEnum):
    """Safe, deterministic terminal causes independent of provider wording."""

    SUCCESS = "success"
    ITERATION_BUDGET_EXHAUSTED = "iteration_budget_exhausted"
    MUTATION_BUDGET_EXHAUSTED = "mutation_budget_exhausted"
    VERIFICATION_BUDGET_EXHAUSTED = "verification_budget_exhausted"
    POLICY_REJECTED = "policy_rejected"
    AUTHORIZATION_FAILED = "authorization_failed"
    PROVIDER_FAILED = "provider_failed"
    VERIFICATION_FAILED = "verification_failed"
    UNRECOVERABLE = "unrecoverable"
    USER_ABORTED = "user_aborted"


class ExecutionEvidenceKind(StrEnum):
    """Redacted references that later G2.4 milestones can attach to a ledger entry."""

    PLAN = "plan"
    DECISION = "decision"
    PROPOSAL = "proposal"
    AUTHORIZATION = "authorization"
    MUTATION_RECEIPT = "mutation_receipt"
    VERIFICATION = "verification"
    REFLECTION = "reflection"
    MEMORY = "memory"
    REPLANNING = "replanning"


__all__ = [
    "ExecutionEvidenceKind",
    "GovernedExecutionState",
    "GovernedExecutionStopReason",
]
