"""G2.4.3 pure bounded replanning and anti-reuse contracts.

The policy in this module consumes immutable evidence and emits an explainable
next-action outcome.  It never creates a decision, proposal, authorization, or
mutation and never calls a provider, workspace, shell, Git, network, or memory
runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from eag.governed_execution.enums import ExecutionEvidenceKind, GovernedExecutionState
from eag.governed_execution.models import ExecutionEvidenceRef, GovernedExecutionContext
from eag.governed_execution.reflection import (
    GovernedMemoryEvidence,
    GovernedReflectionOutcome,
)
from eag.governed_execution.verification import ObjectiveStatus, VerificationStatus

REPLANNING_CONTRACT_VERSION = "1.0"


class ReplanningError(ValueError):
    """Raised when evidence cannot safely support a fresh recovery iteration."""


class ReplanningAction(StrEnum):
    """The only controller-selected outcomes for the first bounded recovery slice."""

    CONTINUE_WITH_FRESH_DECISION = "continue_with_fresh_decision"
    FAIL = "fail"
    ABORT = "abort"


class ReplanningReasonCode(StrEnum):
    """Stable deterministic reasons independent of LLM wording."""

    ELIGIBLE_VERIFICATION_FAILURE = "eligible_verification_failure"
    SECOND_ITERATION_VERIFICATION_FAILURE = "second_iteration_verification_failure"
    ITERATION_LIMIT = "iteration_limit"
    MUTATION_CAPACITY = "mutation_capacity"
    VERIFICATION_CAPACITY = "verification_capacity"
    TERMINAL_CONTEXT = "terminal_context"
    INVALID_REFLECTION_PROVENANCE = "invalid_reflection_provenance"
    INVALID_MEMORY_PROVENANCE = "invalid_memory_provenance"
    STALE_ARTIFACT = "stale_artifact"
    INELIGIBLE_VERIFICATION = "ineligible_verification"


@dataclass(frozen=True, slots=True, kw_only=True)
class ReplanningInput:
    """Trusted immutable evidence needed to decide whether recovery may continue."""

    execution_context: GovernedExecutionContext
    reflection: GovernedReflectionOutcome
    memory: GovernedMemoryEvidence
    previous_decision_id: str
    previous_proposal_id: str
    previous_authorization_id: str
    previous_context_artifact_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.execution_context, GovernedExecutionContext):
            raise TypeError("execution_context must be a GovernedExecutionContext")
        if not isinstance(self.reflection, GovernedReflectionOutcome):
            raise TypeError("reflection must be a GovernedReflectionOutcome")
        if not isinstance(self.memory, GovernedMemoryEvidence):
            raise TypeError("memory must be a GovernedMemoryEvidence")
        if self.execution_context.state is not GovernedExecutionState.REPLANNING:
            raise ReplanningError("replanning input requires the replanning state")
        for field_name in (
            "previous_decision_id",
            "previous_proposal_id",
            "previous_authorization_id",
            "previous_context_artifact_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ReplanningError(f"{field_name} cannot be empty")
        provenance = self.reflection.provenance
        if provenance.execution_id != self.execution_context.execution_id:
            raise ReplanningError("reflection belongs to another execution")
        if provenance.run_id != self.execution_context.run_id:
            raise ReplanningError("reflection belongs to another run")
        if provenance.iteration != self.execution_context.iteration:
            raise ReplanningError("reflection belongs to an incompatible iteration")
        if self.memory.provenance != provenance:
            raise ReplanningError("memory provenance must exactly match reflection provenance")
        if self.memory.reflection_id != self.reflection.report.id:
            raise ReplanningError("memory evidence must bind the reflection report")
        governed_input = self.reflection.input
        if self.previous_decision_id != governed_input.decision_id:
            raise ReplanningError("previous decision identity does not match reflection evidence")
        if self.previous_proposal_id != governed_input.proposal_id:
            raise ReplanningError("previous proposal identity does not match reflection evidence")
        if self.previous_authorization_id != governed_input.authorization_id:
            raise ReplanningError("previous authorization identity does not match reflection evidence")
        if self.previous_context_artifact_id != provenance.context_artifact_id:
            raise ReplanningError("previous context artifact does not match reflection provenance")


@dataclass(frozen=True, slots=True, kw_only=True)
class FreshIterationArtifacts:
    """Identifiers a future execution owner must produce before iteration two mutates."""

    context_artifact_id: str
    decision_request_id: str
    decision_id: str
    proposal_id: str
    authorization_id: str
    receipt_id: str
    verification_id: str
    context_fingerprint: str

    def __post_init__(self) -> None:
        for field_name in (
            "context_artifact_id",
            "decision_request_id",
            "decision_id",
            "proposal_id",
            "authorization_id",
            "receipt_id",
            "verification_id",
            "context_fingerprint",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ReplanningError(f"{field_name} cannot be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReplanningOutcome:
    """Explainable deterministic policy result; it carries no executable authority."""

    action: ReplanningAction
    reason_code: ReplanningReasonCode
    execution_id: str
    iteration: int
    reflection_id: str
    planning_decision_id: str = ""
    version: str = REPLANNING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.action, ReplanningAction):
            raise TypeError("action must be a ReplanningAction")
        if not isinstance(self.reason_code, ReplanningReasonCode):
            raise TypeError("reason_code must be a ReplanningReasonCode")
        for field_name in ("execution_id", "reflection_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ReplanningError(f"{field_name} cannot be empty")
        if not isinstance(self.iteration, int) or isinstance(self.iteration, bool) or self.iteration < 1:
            raise ReplanningError("iteration must be a positive integer")
        if not isinstance(self.planning_decision_id, str):
            raise TypeError("planning_decision_id must be a string")
        if self.version != REPLANNING_CONTRACT_VERSION:
            raise ReplanningError("unsupported replanning contract version")

    @property
    def evidence_ref(self) -> ExecutionEvidenceRef:
        """Return a redacted ledger reference for the deterministic policy result."""
        return ExecutionEvidenceRef(
            kind=ExecutionEvidenceKind.REPLANNING,
            reference_id=f"{self.execution_id}:{self.iteration}:{self.action.value}",
            metadata={
                "action": self.action.value,
                "reason_code": self.reason_code.value,
                "reflection_id": self.reflection_id,
                "planning_decision_id": self.planning_decision_id,
            },
        )


class ReplanningPolicy:
    """Pure first-slice policy for one recovery after iteration-one verification failure."""

    @staticmethod
    def decide(input: ReplanningInput, *, planning_decision_id: str = "") -> ReplanningOutcome:
        """Return a deterministic action without consuming a budget or changing state."""
        if not isinstance(input, ReplanningInput):
            raise TypeError("input must be a ReplanningInput")
        if not isinstance(planning_decision_id, str):
            raise TypeError("planning_decision_id must be a string")

        context = input.execution_context
        governed_input = input.reflection.input
        action = ReplanningAction.FAIL
        reason = ReplanningReasonCode.INELIGIBLE_VERIFICATION

        if context.state.is_terminal:
            reason = ReplanningReasonCode.TERMINAL_CONTEXT
        elif governed_input.verification.status is not VerificationStatus.FAILED or governed_input.objective.status is not ObjectiveStatus.NOT_SATISFIED:
            reason = ReplanningReasonCode.INELIGIBLE_VERIFICATION
        elif context.iteration >= 2:
            reason = ReplanningReasonCode.SECOND_ITERATION_VERIFICATION_FAILURE
        elif context.budget.iterations_remaining < 1:
            reason = ReplanningReasonCode.ITERATION_LIMIT
        elif context.budget.mutations_remaining < 1:
            reason = ReplanningReasonCode.MUTATION_CAPACITY
        elif context.budget.verifications_remaining < 1:
            reason = ReplanningReasonCode.VERIFICATION_CAPACITY
        else:
            action = ReplanningAction.CONTINUE_WITH_FRESH_DECISION
            reason = ReplanningReasonCode.ELIGIBLE_VERIFICATION_FAILURE

        return ReplanningOutcome(
            action=action,
            reason_code=reason,
            execution_id=context.execution_id,
            iteration=context.iteration,
            reflection_id=input.reflection.report.id,
            planning_decision_id=planning_decision_id,
        )

    @staticmethod
    def validate_fresh_iteration(
        input: ReplanningInput,
        artifacts: FreshIterationArtifacts,
    ) -> None:
        """Reject stale authorities before a future owner enters iteration-two mutation flow."""
        if not isinstance(input, ReplanningInput):
            raise TypeError("input must be a ReplanningInput")
        if not isinstance(artifacts, FreshIterationArtifacts):
            raise TypeError("artifacts must be a FreshIterationArtifacts")
        provenance = input.reflection.provenance
        forbidden = {
            "context_artifact_id": input.previous_context_artifact_id,
            "decision_id": input.previous_decision_id,
            "proposal_id": input.previous_proposal_id,
            "authorization_id": input.previous_authorization_id,
            "receipt_id": provenance.receipt_id,
            "verification_id": provenance.verification_id,
            "context_fingerprint": provenance.context_fingerprint,
        }
        for field_name, stale_value in forbidden.items():
            if getattr(artifacts, field_name) == stale_value:
                raise ReplanningError(f"fresh iteration reuses stale {field_name}")


__all__ = [
    "FreshIterationArtifacts",
    "REPLANNING_CONTRACT_VERSION",
    "ReplanningAction",
    "ReplanningError",
    "ReplanningInput",
    "ReplanningOutcome",
    "ReplanningPolicy",
    "ReplanningReasonCode",
]
