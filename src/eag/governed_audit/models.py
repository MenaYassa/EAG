"""Immutable, redacted, read-only audit contracts for governed execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from eag.governed_execution import (
    ExecutionBudget,
    ExecutionEvidenceKind,
    GovernedExecutionContext,
    GovernedExecutionState,
    GovernedExecutionStopReason,
)

AUDIT_SCHEMA_VERSION = "1.0"


class GovernedAuditError(ValueError):
    """Base error for invalid or unsafe audit data."""


class AuditIntegrityError(GovernedAuditError):
    """Raised when persisted audit data is malformed, tampered, or inconsistent."""


class AuditCollisionError(GovernedAuditError):
    """Raised when an execution ID already maps to a different immutable record."""


class InterruptedExecutionRejected(GovernedAuditError):
    """Raised when a nonterminal audit record is offered as execution input."""


class AuditDisposition(StrEnum):
    """Read-only disposition of an observed governed execution."""

    TERMINAL = "terminal"
    INTERRUPTED = "interrupted"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedAuditError(f"{field_name} cannot be empty")
    return value


def _require_digest(value: str, field_name: str) -> str:
    _require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise AuditIntegrityError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _timestamp_to_text(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise TypeError("occurred_at must be a datetime")
    if value.tzinfo is None:
        raise AuditIntegrityError("occurred_at must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _timestamp_from_text(value: str) -> datetime:
    _require_non_empty(value, "occurred_at")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise AuditIntegrityError("occurred_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None:
        raise AuditIntegrityError("occurred_at must be timezone-aware")
    return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditEvidenceReference:
    """A metadata-free, redacted reference to existing governed evidence."""

    kind: ExecutionEvidenceKind
    reference_id: str
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ExecutionEvidenceKind):
            raise TypeError("kind must be an ExecutionEvidenceKind")
        object.__setattr__(self, "reference_id", _require_non_empty(self.reference_id, "reference_id"))
        if self.digest:
            object.__setattr__(self, "digest", _require_digest(self.digest, "digest"))

    def to_payload(self) -> dict[str, str]:
        return {"digest": self.digest, "kind": self.kind.value, "reference_id": self.reference_id}

    @classmethod
    def from_payload(cls, payload: object) -> AuditEvidenceReference:
        if not isinstance(payload, dict):
            raise AuditIntegrityError("evidence reference must be an object")
        try:
            return cls(
                kind=ExecutionEvidenceKind(payload["kind"]),
                reference_id=payload["reference_id"],
                digest=payload.get("digest", ""),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise AuditIntegrityError("invalid evidence reference") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditTransitionRecord:
    """Redacted immutable audit representation of an accepted lifecycle transition."""

    sequence: int
    iteration: int
    from_state: GovernedExecutionState
    to_state: GovernedExecutionState
    occurred_at: datetime
    reason: GovernedExecutionStopReason | None = None
    evidence: tuple[AuditEvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 1:
            raise GovernedAuditError("sequence must be a positive integer")
        if not isinstance(self.iteration, int) or isinstance(self.iteration, bool) or self.iteration < 0:
            raise GovernedAuditError("iteration must be a non-negative integer")
        if not isinstance(self.from_state, GovernedExecutionState):
            raise TypeError("from_state must be a GovernedExecutionState")
        if not isinstance(self.to_state, GovernedExecutionState):
            raise TypeError("to_state must be a GovernedExecutionState")
        if self.reason is not None and not isinstance(self.reason, GovernedExecutionStopReason):
            raise TypeError("reason must be a GovernedExecutionStopReason or None")
        _timestamp_to_text(self.occurred_at)
        if any(not isinstance(item, AuditEvidenceReference) for item in self.evidence):
            raise TypeError("evidence must contain AuditEvidenceReference values")

    def to_payload(self) -> dict[str, Any]:
        return {
            "evidence": [item.to_payload() for item in self.evidence],
            "from_state": self.from_state.value,
            "iteration": self.iteration,
            "occurred_at": _timestamp_to_text(self.occurred_at),
            "reason": self.reason.value if self.reason is not None else None,
            "sequence": self.sequence,
            "to_state": self.to_state.value,
        }

    @classmethod
    def from_payload(cls, payload: object) -> AuditTransitionRecord:
        if not isinstance(payload, dict):
            raise AuditIntegrityError("transition record must be an object")
        try:
            evidence_payload = payload.get("evidence", [])
            if not isinstance(evidence_payload, list):
                raise AuditIntegrityError("transition evidence must be a list")
            reason = payload.get("reason")
            return cls(
                sequence=payload["sequence"],
                iteration=payload["iteration"],
                from_state=GovernedExecutionState(payload["from_state"]),
                to_state=GovernedExecutionState(payload["to_state"]),
                occurred_at=_timestamp_from_text(payload["occurred_at"]),
                reason=GovernedExecutionStopReason(reason) if reason is not None else None,
                evidence=tuple(AuditEvidenceReference.from_payload(item) for item in evidence_payload),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise AuditIntegrityError("invalid transition record") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionAuditEnvelope:
    """Validated, immutable, metadata-free audit projection of execution state."""

    schema_version: str
    execution_id: str
    run_id: str
    goal_digest: str
    disposition: AuditDisposition
    state: GovernedExecutionState
    iteration: int
    budget: ExecutionBudget
    history: tuple[AuditTransitionRecord, ...]
    evidence: tuple[AuditEvidenceReference, ...]
    record_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "history", tuple(self.history))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if self.schema_version != AUDIT_SCHEMA_VERSION:
            raise AuditIntegrityError("unsupported audit schema version")
        object.__setattr__(self, "execution_id", _require_non_empty(self.execution_id, "execution_id"))
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        object.__setattr__(self, "goal_digest", _require_digest(self.goal_digest, "goal_digest"))
        if not isinstance(self.disposition, AuditDisposition):
            raise TypeError("disposition must be an AuditDisposition")
        if not isinstance(self.state, GovernedExecutionState):
            raise TypeError("state must be a GovernedExecutionState")
        if not isinstance(self.iteration, int) or isinstance(self.iteration, bool) or self.iteration < 0:
            raise GovernedAuditError("iteration must be a non-negative integer")
        if not isinstance(self.budget, ExecutionBudget):
            raise TypeError("budget must be an ExecutionBudget")
        if any(not isinstance(item, AuditTransitionRecord) for item in self.history):
            raise TypeError("history must contain AuditTransitionRecord values")
        if any(not isinstance(item, AuditEvidenceReference) for item in self.evidence):
            raise TypeError("evidence must contain AuditEvidenceReference values")
        self._validate_structure()
        object.__setattr__(self, "record_digest", _require_digest(self.record_digest, "record_digest"))
        if self.record_digest != self.calculate_digest():
            raise AuditIntegrityError("audit record digest does not match canonical payload")

    @property
    def is_terminal(self) -> bool:
        return self.disposition is AuditDisposition.TERMINAL

    def _validate_structure(self) -> None:
        if not self.history:
            raise AuditIntegrityError("audit history cannot be empty")
        expected_sequence = 1
        expected_state = GovernedExecutionState.CREATED
        expected_iteration = 0
        flattened: list[AuditEvidenceReference] = []
        mutation_entries = 0
        verification_entries = 0
        for record in self.history:
            if record.sequence != expected_sequence:
                raise AuditIntegrityError("audit history sequence must be contiguous from one")
            if record.from_state is not expected_state:
                raise AuditIntegrityError("audit history must remain contiguous")
            if record.to_state not in _legal_targets(record.from_state):
                raise AuditIntegrityError("audit history contains an illegal transition")
            if record.to_state is GovernedExecutionState.CONTEXT_ASSEMBLING:
                expected_iteration += 1
            if record.iteration != expected_iteration:
                raise AuditIntegrityError("audit transition iteration is inconsistent")
            if record.to_state is GovernedExecutionState.MUTATING:
                mutation_entries += 1
            if record.to_state is GovernedExecutionState.VERIFYING:
                verification_entries += 1
            flattened.extend(record.evidence)
            expected_sequence += 1
            expected_state = record.to_state
        if expected_state is not self.state:
            raise AuditIntegrityError("audit state must equal final history state")
        if expected_iteration != self.iteration:
            raise AuditIntegrityError("audit iteration must equal final history iteration")
        if self.iteration != self.budget.iterations_used:
            raise AuditIntegrityError("audit iteration must equal consumed iteration budget")
        if mutation_entries != self.budget.mutations_used:
            raise AuditIntegrityError("audit mutation count must equal consumed mutation budget")
        if verification_entries != self.budget.verifications_used:
            raise AuditIntegrityError("audit verification count must equal consumed verification budget")
        if tuple(flattened) != self.evidence:
            raise AuditIntegrityError("audit evidence must exactly flatten transition evidence")
        if self.disposition is AuditDisposition.TERMINAL and not self.state.is_terminal:
            raise AuditIntegrityError("terminal audit disposition requires a terminal state")
        if self.disposition is AuditDisposition.INTERRUPTED and self.state.is_terminal:
            raise AuditIntegrityError("interrupted audit disposition requires a nonterminal state")

    def _payload_without_digest(self) -> dict[str, Any]:
        return {
            "budget": {
                "iterations_used": self.budget.iterations_used,
                "max_iterations": self.budget.max_iterations,
                "max_mutations": self.budget.max_mutations,
                "max_verifications": self.budget.max_verifications,
                "mutations_used": self.budget.mutations_used,
                "verifications_used": self.budget.verifications_used,
            },
            "disposition": self.disposition.value,
            "evidence": [item.to_payload() for item in self.evidence],
            "execution_id": self.execution_id,
            "goal_digest": self.goal_digest,
            "history": [item.to_payload() for item in self.history],
            "iteration": self.iteration,
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "state": self.state.value,
        }

    def calculate_digest(self) -> str:
        encoded = json.dumps(
            self._payload_without_digest(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_payload(self) -> dict[str, Any]:
        return {**self._payload_without_digest(), "record_digest": self.record_digest}

    @classmethod
    def from_context(
        cls,
        context: GovernedExecutionContext,
        *,
        disposition: AuditDisposition | None = None,
    ) -> GovernedExecutionAuditEnvelope:
        if not isinstance(context, GovernedExecutionContext):
            raise TypeError("context must be a GovernedExecutionContext")
        resolved_disposition = disposition or (
            AuditDisposition.TERMINAL if context.state.is_terminal else AuditDisposition.INTERRUPTED
        )
        history = tuple(
            AuditTransitionRecord(
                sequence=record.sequence,
                iteration=record.iteration,
                from_state=record.from_state,
                to_state=record.to_state,
                occurred_at=record.occurred_at,
                reason=record.reason,
                evidence=tuple(
                    AuditEvidenceReference(
                        kind=evidence.kind,
                        reference_id=evidence.reference_id,
                        digest=evidence.digest,
                    )
                    for evidence in record.evidence
                ),
            )
            for record in context.history
        )
        evidence = tuple(item for record in history for item in record.evidence)
        goal_digest = hashlib.sha256(context.goal.encode("utf-8")).hexdigest()
        draft = cls.__new__(cls)
        object.__setattr__(draft, "schema_version", AUDIT_SCHEMA_VERSION)
        object.__setattr__(draft, "execution_id", context.execution_id)
        object.__setattr__(draft, "run_id", context.run_id)
        object.__setattr__(draft, "goal_digest", goal_digest)
        object.__setattr__(draft, "disposition", resolved_disposition)
        object.__setattr__(draft, "state", context.state)
        object.__setattr__(draft, "iteration", context.iteration)
        object.__setattr__(draft, "budget", context.budget)
        object.__setattr__(draft, "history", history)
        object.__setattr__(draft, "evidence", evidence)
        object.__setattr__(draft, "record_digest", "0" * 64)
        digest = draft.calculate_digest()
        return cls(
            schema_version=AUDIT_SCHEMA_VERSION,
            execution_id=context.execution_id,
            run_id=context.run_id,
            goal_digest=goal_digest,
            disposition=resolved_disposition,
            state=context.state,
            iteration=context.iteration,
            budget=context.budget,
            history=history,
            evidence=evidence,
            record_digest=digest,
        )

    @classmethod
    def from_payload(cls, payload: object) -> GovernedExecutionAuditEnvelope:
        if not isinstance(payload, dict):
            raise AuditIntegrityError("audit envelope must be an object")
        try:
            budget_payload = payload["budget"]
            if not isinstance(budget_payload, dict):
                raise AuditIntegrityError("audit budget must be an object")
            history_payload = payload["history"]
            evidence_payload = payload["evidence"]
            if not isinstance(history_payload, list) or not isinstance(evidence_payload, list):
                raise AuditIntegrityError("audit history and evidence must be lists")
            return cls(
                schema_version=payload["schema_version"],
                execution_id=payload["execution_id"],
                run_id=payload["run_id"],
                goal_digest=payload["goal_digest"],
                disposition=AuditDisposition(payload["disposition"]),
                state=GovernedExecutionState(payload["state"]),
                iteration=payload["iteration"],
                budget=ExecutionBudget(
                    max_iterations=budget_payload["max_iterations"],
                    max_mutations=budget_payload["max_mutations"],
                    max_verifications=budget_payload["max_verifications"],
                    iterations_used=budget_payload["iterations_used"],
                    mutations_used=budget_payload["mutations_used"],
                    verifications_used=budget_payload["verifications_used"],
                ),
                history=tuple(AuditTransitionRecord.from_payload(item) for item in history_payload),
                evidence=tuple(AuditEvidenceReference.from_payload(item) for item in evidence_payload),
                record_digest=payload["record_digest"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise AuditIntegrityError("invalid audit envelope") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionInterruptionRecord:
    """Inspectable nonterminal observation with no continuation authority."""

    envelope: GovernedExecutionAuditEnvelope

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, GovernedExecutionAuditEnvelope):
            raise TypeError("envelope must be a GovernedExecutionAuditEnvelope")
        if self.envelope.disposition is not AuditDisposition.INTERRUPTED:
            raise GovernedAuditError("interruption record requires interrupted disposition")


def reject_interrupted_continuation(record: GovernedExecutionInterruptionRecord) -> None:
    """Purely reject use of an observed interruption as executable continuation input."""
    if not isinstance(record, GovernedExecutionInterruptionRecord):
        raise TypeError("record must be a GovernedExecutionInterruptionRecord")
    raise InterruptedExecutionRejected(
        "interrupted governed execution records are read-only observations and cannot be resumed"
    )


def _legal_targets(state: GovernedExecutionState) -> frozenset[GovernedExecutionState]:
    """Import the published legal matrix lazily without operational dependencies."""
    from eag.governed_execution.models import LEGAL_TRANSITIONS

    return LEGAL_TRANSITIONS[state]


__all__ = [
    "AUDIT_SCHEMA_VERSION",
    "AuditCollisionError",
    "AuditDisposition",
    "AuditEvidenceReference",
    "AuditIntegrityError",
    "AuditTransitionRecord",
    "GovernedAuditError",
    "GovernedExecutionAuditEnvelope",
    "GovernedExecutionInterruptionRecord",
    "InterruptedExecutionRejected",
    "reject_interrupted_continuation",
]
