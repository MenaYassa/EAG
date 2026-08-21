"""G2.4.3 governed reflection and provenance-bound memory evidence contracts.

This module adapts existing reflection services to bounded governed evidence.  It is
not an execution runtime: it cannot choose a state transition, call a gateway,
authorize a proposal, mutate a workspace, invoke a shell, access Git/network, or
claim verification success.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from eag.governed_execution.enums import ExecutionEvidenceKind, GovernedExecutionState
from eag.governed_execution.models import ExecutionEvidenceRef, GovernedExecutionContext
from eag.governed_execution.verification import (
    ObjectiveAssessment,
    ObjectiveStatus,
    VerificationResult,
    VerificationStatus,
)
from eag.memory.experience import ExperienceBuilder
from eag.memory.models import EngineeringExperience
from eag.reflection.models import ReflectionContext, ReflectionReport
from eag.reflection.runtime import ReflectionRuntime

GOVERNED_REFLECTION_CONTRACT_VERSION = "1.0"


class GovernedReflectionError(ValueError):
    """Raised when governed evidence is not eligible for bounded reflection."""


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedReflectionError(f"{field_name} cannot be empty")
    return value


def _freeze_metadata(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    frozen: dict[str, str | int | float | bool | None] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{field_name} keys must be strings")
        if not isinstance(item, (str, int, float, bool, type(None))) or isinstance(item, bytes):
            raise TypeError(f"{field_name} values must be redacted scalar values")
        frozen[key] = item
    return MappingProxyType(frozen)


def _is_receipt_evidence(value: Any) -> bool:
    """Validate the fixed redacted G2.3.1 receipt surface without importing mutation runtime."""
    required = (
        "mutation_id",
        "proposal_id",
        "run_id",
        "authorization_id",
        "result",
        "verification_passed",
    )
    return all(isinstance(getattr(value, field_name, None), str) for field_name in required[:4]) and hasattr(
        value, "result"
    ) and isinstance(getattr(value, "verification_passed", None), bool)


def _receipt_completed(receipt: Any) -> bool:
    result = getattr(receipt, "result", None)
    value = getattr(result, "value", result)
    return value == "completed" and getattr(receipt, "verification_passed", False) is True


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedMemoryProvenance:
    """Trusted redacted identity bindings for planner-visible governed experience."""

    execution_id: str
    run_id: str
    iteration: int
    receipt_id: str
    verification_id: str
    reflection_id: str
    context_artifact_id: str
    context_fingerprint: str
    policy_version: str
    contract_version: str = GOVERNED_REFLECTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "execution_id",
            "run_id",
            "receipt_id",
            "verification_id",
            "reflection_id",
            "context_artifact_id",
            "context_fingerprint",
            "policy_version",
        ):
            object.__setattr__(self, field_name, _non_empty(getattr(self, field_name), field_name))
        if not isinstance(self.iteration, int) or isinstance(self.iteration, bool) or self.iteration < 1:
            raise GovernedReflectionError("iteration must be a positive integer")
        if self.contract_version != GOVERNED_REFLECTION_CONTRACT_VERSION:
            raise GovernedReflectionError("unsupported governed reflection contract version")


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedReflectionInput:
    """Immutable trusted evidence binding one eligible verification failure."""

    execution_context: GovernedExecutionContext
    receipt: Any
    verification: VerificationResult
    objective: ObjectiveAssessment
    context_artifact_id: str
    context_fingerprint: str
    decision_id: str
    proposal_id: str
    authorization_id: str
    policy_version: str
    redacted_metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)
    contract_version: str = GOVERNED_REFLECTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.execution_context, GovernedExecutionContext):
            raise TypeError("execution_context must be a GovernedExecutionContext")
        if not _is_receipt_evidence(self.receipt):
            raise TypeError("receipt must provide immutable mutation receipt evidence")
        if not isinstance(self.verification, VerificationResult):
            raise TypeError("verification must be a VerificationResult")
        if not isinstance(self.objective, ObjectiveAssessment):
            raise TypeError("objective must be an ObjectiveAssessment")
        if self.execution_context.state is not GovernedExecutionState.REFLECTING:
            raise GovernedReflectionError("governed reflection requires the reflecting state")
        if self.execution_context.iteration < 1:
            raise GovernedReflectionError("governed reflection requires an active iteration")
        if self.receipt.run_id != self.execution_context.run_id:
            raise GovernedReflectionError("receipt run_id must match execution context")
        if self.verification.run_id != self.execution_context.run_id:
            raise GovernedReflectionError("verification run_id must match execution context")
        if self.verification.receipt_id != self.receipt.mutation_id:
            raise GovernedReflectionError("verification must bind the same receipt")
        if self.objective.receipt_id != self.receipt.mutation_id:
            raise GovernedReflectionError("objective must bind the same receipt")
        if self.objective.verification_id != self.verification.verification_id:
            raise GovernedReflectionError("objective must bind the same verification")
        if not _receipt_completed(self.receipt):
            raise GovernedReflectionError("governed reflection requires a completed mutation receipt")
        if self.verification.status is not VerificationStatus.FAILED:
            raise GovernedReflectionError("governed reflection requires a failed trusted verification")
        if self.objective.status is not ObjectiveStatus.NOT_SATISFIED:
            raise GovernedReflectionError("governed reflection requires an unsatisfied objective")
        if self.proposal_id != self.receipt.proposal_id:
            raise GovernedReflectionError("proposal_id must match the receipt")
        if self.receipt.authorization_id is None or self.authorization_id != self.receipt.authorization_id:
            raise GovernedReflectionError("authorization_id must match the receipt")
        for field_name in (
            "context_artifact_id",
            "context_fingerprint",
            "decision_id",
            "proposal_id",
            "authorization_id",
            "policy_version",
        ):
            object.__setattr__(self, field_name, _non_empty(getattr(self, field_name), field_name))
        if self.contract_version != GOVERNED_REFLECTION_CONTRACT_VERSION:
            raise GovernedReflectionError("unsupported governed reflection contract version")
        receipt_found = any(
            evidence.kind is ExecutionEvidenceKind.MUTATION_RECEIPT
            and evidence.reference_id == self.receipt.mutation_id
            for evidence in self.execution_context.evidence
        )
        verification_found = any(
            evidence.kind is ExecutionEvidenceKind.VERIFICATION
            and evidence.reference_id == self.verification.verification_id
            for evidence in self.execution_context.evidence
        )
        if not receipt_found or not verification_found:
            raise GovernedReflectionError("execution ledger must contain matching receipt and verification evidence")
        object.__setattr__(
            self,
            "redacted_metadata",
            _freeze_metadata(self.redacted_metadata, "redacted_metadata"),
        )

    @property
    def provenance(self) -> GovernedMemoryProvenance:
        """Return the immutable provenance that follows reflection-derived memory."""
        return GovernedMemoryProvenance(
            execution_id=self.execution_context.execution_id,
            run_id=self.execution_context.run_id,
            iteration=self.execution_context.iteration,
            receipt_id=self.receipt.mutation_id,
            verification_id=self.verification.verification_id,
            reflection_id="pending",
            context_artifact_id=self.context_artifact_id,
            context_fingerprint=self.context_fingerprint,
            policy_version=self.policy_version,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _BoundedReflectionRunResult:
    """Minimal generic reflection view; it intentionally exposes no mutation content."""

    run_id: str
    outcome: str = "failure"
    summary: str = "Objective verification failed after a completed governed mutation."


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedReflectionOutcome:
    """Reflection evidence bound to exactly one governed execution iteration."""

    input: GovernedReflectionInput
    reflection_context: ReflectionContext
    report: ReflectionReport
    provenance: GovernedMemoryProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.input, GovernedReflectionInput):
            raise TypeError("input must be a GovernedReflectionInput")
        if not isinstance(self.reflection_context, ReflectionContext):
            raise TypeError("reflection_context must be a ReflectionContext")
        if not isinstance(self.report, ReflectionReport):
            raise TypeError("report must be a ReflectionReport")
        if not isinstance(self.provenance, GovernedMemoryProvenance):
            raise TypeError("provenance must be a GovernedMemoryProvenance")
        if self.report.run_id != self.input.execution_context.run_id:
            raise GovernedReflectionError("reflection report run_id must match governed execution")
        if self.provenance.execution_id != self.input.execution_context.execution_id:
            raise GovernedReflectionError("reflection provenance execution_id mismatch")
        if self.provenance.iteration != self.input.execution_context.iteration:
            raise GovernedReflectionError("reflection provenance iteration mismatch")
        if self.provenance.receipt_id != self.input.receipt.mutation_id:
            raise GovernedReflectionError("reflection provenance receipt mismatch")
        if self.provenance.verification_id != self.input.verification.verification_id:
            raise GovernedReflectionError("reflection provenance verification mismatch")
        if self.provenance.reflection_id != self.report.id:
            raise GovernedReflectionError("reflection provenance report mismatch")

    @property
    def evidence_ref(self) -> ExecutionEvidenceRef:
        """Return the safe ledger reference for a completed reflection report."""
        return ExecutionEvidenceRef(
            kind=ExecutionEvidenceKind.REFLECTION,
            reference_id=self.report.id,
            metadata={
                "iteration": self.provenance.iteration,
                "verification_id": self.provenance.verification_id,
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedMemoryEvidence:
    """Planner-visible experience with immutable governed provenance only."""

    experience: EngineeringExperience
    provenance: GovernedMemoryProvenance
    reflection_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.experience, EngineeringExperience):
            raise TypeError("experience must be an EngineeringExperience")
        if not isinstance(self.provenance, GovernedMemoryProvenance):
            raise TypeError("provenance must be a GovernedMemoryProvenance")
        object.__setattr__(self, "reflection_id", _non_empty(self.reflection_id, "reflection_id"))
        if self.provenance.reflection_id != self.reflection_id:
            raise GovernedReflectionError("memory evidence reflection_id must match provenance")


class GovernedReflectionAdapter:
    """Adapt governed evidence to the existing reflection runtime without granting authority."""

    def build_context(self, input: GovernedReflectionInput) -> ReflectionContext:
        """Build a bounded generic reflection input from trusted governed evidence."""
        if not isinstance(input, GovernedReflectionInput):
            raise TypeError("input must be a GovernedReflectionInput")
        metadata = {
            "governed_execution_id": input.execution_context.execution_id,
            "iteration": input.execution_context.iteration,
            "receipt_id": input.receipt.mutation_id,
            "verification_id": input.verification.verification_id,
            "objective_status": input.objective.status.value,
            "context_artifact_id": input.context_artifact_id,
            "context_fingerprint": input.context_fingerprint,
            "policy_version": input.policy_version,
            **dict(input.redacted_metadata),
        }
        return ReflectionContext(
            run_id=input.execution_context.run_id,
            run_result=_BoundedReflectionRunResult(run_id=input.execution_context.run_id),
            metadata=metadata,
        )

    def reflect(
        self,
        runtime: ReflectionRuntime,
        input: GovernedReflectionInput,
    ) -> GovernedReflectionOutcome:
        """Generate reflection evidence only; transition selection remains outside this adapter."""
        if not isinstance(runtime, ReflectionRuntime):
            raise TypeError("runtime must be a ReflectionRuntime")
        reflection_context = self.build_context(input)
        report = runtime.reflect(reflection_context)
        provenance = GovernedMemoryProvenance(
            execution_id=input.execution_context.execution_id,
            run_id=input.execution_context.run_id,
            iteration=input.execution_context.iteration,
            receipt_id=input.receipt.mutation_id,
            verification_id=input.verification.verification_id,
            reflection_id=report.id,
            context_artifact_id=input.context_artifact_id,
            context_fingerprint=input.context_fingerprint,
            policy_version=input.policy_version,
        )
        return GovernedReflectionOutcome(
            input=input,
            reflection_context=reflection_context,
            report=report,
            provenance=provenance,
        )

    @staticmethod
    def memory_evidence(outcome: GovernedReflectionOutcome) -> GovernedMemoryEvidence:
        """Build planner-visible experience without calling MemoryRuntime or selecting an action."""
        if not isinstance(outcome, GovernedReflectionOutcome):
            raise TypeError("outcome must be a GovernedReflectionOutcome")
        experience = ExperienceBuilder().build_from_reflection(
            outcome.reflection_context,
            outcome.report,
        )
        return GovernedMemoryEvidence(
            experience=experience,
            provenance=outcome.provenance,
            reflection_id=outcome.report.id,
        )


__all__ = [
    "GOVERNED_REFLECTION_CONTRACT_VERSION",
    "GovernedMemoryEvidence",
    "GovernedMemoryProvenance",
    "GovernedReflectionAdapter",
    "GovernedReflectionError",
    "GovernedReflectionInput",
    "GovernedReflectionOutcome",
]
