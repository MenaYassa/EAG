"""Immutable public models and validated ledger invariants for G2.4.1."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Final

from eag.governed_execution.enums import (
    ExecutionEvidenceKind,
    GovernedExecutionState,
    GovernedExecutionStopReason,
)

LEGAL_TRANSITIONS: Final[Mapping[GovernedExecutionState, frozenset[GovernedExecutionState]]] = (
    MappingProxyType(
        {
            GovernedExecutionState.CREATED: frozenset(
                {GovernedExecutionState.CONTEXT_ASSEMBLING, GovernedExecutionState.ABORTED}
            ),
            GovernedExecutionState.CONTEXT_ASSEMBLING: frozenset(
                {GovernedExecutionState.PLANNING, GovernedExecutionState.FAILED}
            ),
            GovernedExecutionState.PLANNING: frozenset(
                {
                    GovernedExecutionState.DECIDING,
                    GovernedExecutionState.FAILED,
                    GovernedExecutionState.ABORTED,
                }
            ),
            GovernedExecutionState.DECIDING: frozenset(
                {GovernedExecutionState.PROPOSING, GovernedExecutionState.FAILED}
            ),
            GovernedExecutionState.PROPOSING: frozenset(
                {
                    GovernedExecutionState.APPROVAL_PENDING,
                    GovernedExecutionState.AUTHORIZING,
                    GovernedExecutionState.FAILED,
                }
            ),
            GovernedExecutionState.APPROVAL_PENDING: frozenset(
                {GovernedExecutionState.AUTHORIZING, GovernedExecutionState.ABORTED}
            ),
            GovernedExecutionState.AUTHORIZING: frozenset(
                {GovernedExecutionState.MUTATING, GovernedExecutionState.FAILED}
            ),
            GovernedExecutionState.MUTATING: frozenset(
                {GovernedExecutionState.VERIFYING, GovernedExecutionState.FAILED}
            ),
            GovernedExecutionState.VERIFYING: frozenset(
                {
                    GovernedExecutionState.COMPLETED,
                    GovernedExecutionState.REFLECTING,
                    GovernedExecutionState.FAILED,
                }
            ),
            GovernedExecutionState.REFLECTING: frozenset(
                {GovernedExecutionState.REPLANNING, GovernedExecutionState.FAILED}
            ),
            GovernedExecutionState.REPLANNING: frozenset(
                {GovernedExecutionState.CONTEXT_ASSEMBLING, GovernedExecutionState.FAILED}
            ),
            GovernedExecutionState.COMPLETED: frozenset(),
            GovernedExecutionState.FAILED: frozenset(),
            GovernedExecutionState.ABORTED: frozenset(),
        }
    )
)


def _freeze_metadata_value(value: Any, field_name: str) -> Any:
    """Recursively convert the supported redacted metadata shape to immutable values."""
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{field_name} mapping keys must be strings")
            frozen[key] = _freeze_metadata_value(item, field_name)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_metadata_value(item, field_name) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_metadata_value(item, field_name) for item in value)
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, (str, int, float, bool, bytes, type(None), datetime, Enum)):
        return value
    raise TypeError(
        f"{field_name} contains unsupported mutable or non-deterministic value type "
        f"{type(value).__name__}"
    )


def _freeze_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    frozen = _freeze_metadata_value(value, field_name)
    if not isinstance(frozen, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return frozen


def _freeze_tuple(value: object, field_name: str) -> tuple[Any, ...]:
    try:
        return tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise TypeError(f"{field_name} must be iterable") from error


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value


def _validate_terminal_stop_reason(
    target: GovernedExecutionState,
    stop_reason: GovernedExecutionStopReason | None,
) -> None:
    """Validate the terminal reason contract shared by transitions and reconstruction."""
    if not target.is_terminal and stop_reason is not None:
        raise ValueError("stop_reason is only legal for a terminal state")
    if not target.is_terminal:
        return
    if stop_reason is None:
        raise ValueError("terminal transition requires a stop_reason")
    if target is GovernedExecutionState.COMPLETED and stop_reason is not GovernedExecutionStopReason.SUCCESS:
        raise ValueError("completed state requires success stop reason")
    if target is GovernedExecutionState.ABORTED and stop_reason is not GovernedExecutionStopReason.USER_ABORTED:
        raise ValueError("aborted state requires user_aborted stop reason")
    if target is GovernedExecutionState.FAILED and stop_reason in {
        GovernedExecutionStopReason.SUCCESS,
        GovernedExecutionStopReason.USER_ABORTED,
    }:
        raise ValueError("failed state requires a failure stop reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionBudget:
    """Trusted, bounded limits and monotonic counters for one execution."""

    max_iterations: int = 1
    max_mutations: int = 1
    max_verifications: int = 1
    iterations_used: int = 0
    mutations_used: int = 0
    verifications_used: int = 0

    def __post_init__(self) -> None:
        for field_name in ("max_iterations", "max_mutations", "max_verifications"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{field_name} must be a positive integer")
        for field_name in ("iterations_used", "mutations_used", "verifications_used"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.iterations_used > self.max_iterations:
            raise ValueError("iterations_used cannot exceed max_iterations")
        if self.mutations_used > self.max_mutations:
            raise ValueError("mutations_used cannot exceed max_mutations")
        if self.verifications_used > self.max_verifications:
            raise ValueError("verifications_used cannot exceed max_verifications")

    @property
    def iterations_remaining(self) -> int:
        return self.max_iterations - self.iterations_used

    @property
    def mutations_remaining(self) -> int:
        return self.max_mutations - self.mutations_used

    @property
    def verifications_remaining(self) -> int:
        return self.max_verifications - self.verifications_used

    def consume_iteration(self) -> ExecutionBudget:
        if self.iterations_remaining == 0:
            raise ValueError("iteration budget is exhausted")
        return ExecutionBudget(
            max_iterations=self.max_iterations,
            max_mutations=self.max_mutations,
            max_verifications=self.max_verifications,
            iterations_used=self.iterations_used + 1,
            mutations_used=self.mutations_used,
            verifications_used=self.verifications_used,
        )

    def consume_mutation(self) -> ExecutionBudget:
        if self.mutations_remaining == 0:
            raise ValueError("mutation budget is exhausted")
        return ExecutionBudget(
            max_iterations=self.max_iterations,
            max_mutations=self.max_mutations,
            max_verifications=self.max_verifications,
            iterations_used=self.iterations_used,
            mutations_used=self.mutations_used + 1,
            verifications_used=self.verifications_used,
        )

    def consume_verification(self) -> ExecutionBudget:
        if self.verifications_remaining == 0:
            raise ValueError("verification budget is exhausted")
        return ExecutionBudget(
            max_iterations=self.max_iterations,
            max_mutations=self.max_mutations,
            max_verifications=self.max_verifications,
            iterations_used=self.iterations_used,
            mutations_used=self.mutations_used,
            verifications_used=self.verifications_used + 1,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionEvidenceRef:
    """One redacted immutable reference to a future execution artifact."""

    kind: ExecutionEvidenceKind
    reference_id: str
    digest: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ExecutionEvidenceKind):
            raise TypeError("kind must be an ExecutionEvidenceKind")
        object.__setattr__(self, "reference_id", _require_non_empty(self.reference_id, "reference_id"))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionTransitionRecord:
    """Append-only evidence of one accepted deterministic state transition."""

    sequence: int
    iteration: int
    from_state: GovernedExecutionState
    to_state: GovernedExecutionState
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: GovernedExecutionStopReason | None = None
    evidence: tuple[ExecutionEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", _freeze_tuple(self.evidence, "evidence"))
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 1:
            raise ValueError("sequence must be a positive integer")
        if not isinstance(self.iteration, int) or isinstance(self.iteration, bool) or self.iteration < 0:
            raise ValueError("iteration must be a non-negative integer")
        if not isinstance(self.from_state, GovernedExecutionState):
            raise TypeError("from_state must be a GovernedExecutionState")
        if not isinstance(self.to_state, GovernedExecutionState):
            raise TypeError("to_state must be a GovernedExecutionState")
        if self.reason is not None and not isinstance(self.reason, GovernedExecutionStopReason):
            raise TypeError("reason must be a GovernedExecutionStopReason or None")
        if any(not isinstance(item, ExecutionEvidenceRef) for item in self.evidence):
            raise TypeError("evidence must contain ExecutionEvidenceRef values")


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionContext:
    """Immutable validated state and append-only audit ledger for one serial execution."""

    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    goal: str
    state: GovernedExecutionState = GovernedExecutionState.CREATED
    iteration: int = 0
    budget: ExecutionBudget = field(default_factory=ExecutionBudget)
    history: tuple[ExecutionTransitionRecord, ...] = ()
    evidence: tuple[ExecutionEvidenceRef, ...] = ()
    stop_reason: GovernedExecutionStopReason | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "history", _freeze_tuple(self.history, "history"))
        object.__setattr__(self, "evidence", _freeze_tuple(self.evidence, "evidence"))
        object.__setattr__(self, "execution_id", _require_non_empty(self.execution_id, "execution_id"))
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        object.__setattr__(self, "goal", _require_non_empty(self.goal, "goal"))
        if not isinstance(self.state, GovernedExecutionState):
            raise TypeError("state must be a GovernedExecutionState")
        if not isinstance(self.iteration, int) or isinstance(self.iteration, bool) or self.iteration < 0:
            raise ValueError("iteration must be a non-negative integer")
        if not isinstance(self.budget, ExecutionBudget):
            raise TypeError("budget must be an ExecutionBudget")
        if any(not isinstance(item, ExecutionTransitionRecord) for item in self.history):
            raise TypeError("history must contain ExecutionTransitionRecord values")
        if any(not isinstance(item, ExecutionEvidenceRef) for item in self.evidence):
            raise TypeError("evidence must contain ExecutionEvidenceRef values")
        if self.stop_reason is not None and not isinstance(
            self.stop_reason, GovernedExecutionStopReason
        ):
            raise TypeError("stop_reason must be a GovernedExecutionStopReason or None")
        self._validate_history()
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))

    def _validate_history(self) -> None:
        """Validate a reconstructed ledger against the same static state contract."""
        if not self.history:
            self._validate_initial_context()
            return

        expected_state = GovernedExecutionState.CREATED
        expected_iteration = 0
        mutation_entries = 0
        verification_entries = 0
        ledger_evidence: list[ExecutionEvidenceRef] = []

        for expected_sequence, record in enumerate(self.history, start=1):
            if record.sequence != expected_sequence:
                raise ValueError("history sequence must be contiguous and start at one")
            if record.from_state is not expected_state:
                raise ValueError("history transitions must originate at created and remain contiguous")
            if record.to_state not in LEGAL_TRANSITIONS[record.from_state]:
                raise ValueError("history contains an illegal transition")
            if expected_state.is_terminal:
                raise ValueError("terminal history state cannot have additional transitions")
            if record.to_state is GovernedExecutionState.CONTEXT_ASSEMBLING:
                expected_iteration += 1
            if record.iteration != expected_iteration:
                raise ValueError("history iteration must match the recorded lifecycle")
            _validate_terminal_stop_reason(record.to_state, record.reason)
            if record.to_state is GovernedExecutionState.MUTATING:
                mutation_entries += 1
            if record.to_state is GovernedExecutionState.VERIFYING:
                verification_entries += 1
            ledger_evidence.extend(record.evidence)
            expected_state = record.to_state

        if expected_state is not self.state:
            raise ValueError("history terminal state must equal current state")
        if expected_iteration != self.iteration:
            raise ValueError("history iteration must equal current iteration")
        if self.iteration != self.budget.iterations_used:
            raise ValueError("iteration must equal the consumed iteration budget")
        if mutation_entries != self.budget.mutations_used:
            raise ValueError("mutation budget must equal legitimate mutating entries")
        if verification_entries != self.budget.verifications_used:
            raise ValueError("verification budget must equal legitimate verifying entries")
        if tuple(ledger_evidence) != self.evidence:
            raise ValueError("context evidence must exactly equal flattened ledger evidence")
        if self.state.is_terminal:
            if self.stop_reason is not self.history[-1].reason:
                raise ValueError("terminal context stop_reason must match the final ledger record")
        elif self.stop_reason is not None:
            raise ValueError("stop_reason requires a terminal state")

    def _validate_initial_context(self) -> None:
        if self.state is not GovernedExecutionState.CREATED:
            raise ValueError("non-created context requires a valid transition history")
        if self.iteration != 0 or self.budget.iterations_used != 0:
            raise ValueError("created context cannot consume iteration budget")
        if self.budget.mutations_used != 0:
            raise ValueError("created context cannot consume mutation budget")
        if self.budget.verifications_used != 0:
            raise ValueError("created context cannot consume verification budget")
        if self.evidence:
            raise ValueError("created context cannot contain ledger evidence")
        if self.stop_reason is not None:
            raise ValueError("created context cannot have a stop_reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class TransitionResult:
    """Typed outcome of a pure state-machine transition request."""

    accepted: bool
    context: GovernedExecutionContext
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.context, GovernedExecutionContext):
            raise TypeError("context must be a GovernedExecutionContext")
        if self.accepted and self.error_code is not None:
            raise ValueError("accepted transition cannot have error_code")
        if not self.accepted and not self.error_code:
            raise ValueError("rejected transition requires error_code")


__all__ = [
    "ExecutionBudget",
    "ExecutionEvidenceRef",
    "ExecutionTransitionRecord",
    "GovernedExecutionContext",
    "TransitionResult",
]
