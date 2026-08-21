"""Deterministic contract coverage for the G2.4.1 governed execution ledger."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from eag.events import EventBus
from eag.governed_execution import (
    ExecutionBudget,
    ExecutionEvidenceKind,
    ExecutionEvidenceRef,
    ExecutionTransitionRecord,
    GovernedExecutionContext,
    GovernedExecutionStarted,
    GovernedExecutionState,
    GovernedExecutionStateMachine,
    GovernedExecutionStopped,
    GovernedExecutionStopReason,
    GovernedExecutionTransitioned,
    IllegalTransitionError,
)


def _context(*, budget: ExecutionBudget | None = None) -> GovernedExecutionContext:
    return GovernedExecutionContext(
        run_id="g2.4.1-run",
        goal="Represent a bounded governed execution.",
        budget=budget or ExecutionBudget(max_iterations=2, max_mutations=2, max_verifications=2),
    )


def _transition(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
    target: GovernedExecutionState,
    **kwargs: object,
) -> GovernedExecutionContext:
    result = machine.transition(context, target, **kwargs)
    assert result.accepted is True
    return result.context


def _through_authorizing(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
) -> GovernedExecutionContext:
    context = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(machine, context, GovernedExecutionState.DECIDING)
    context = _transition(machine, context, GovernedExecutionState.PROPOSING)
    return _transition(machine, context, GovernedExecutionState.AUTHORIZING)


def _through_verifying(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
) -> GovernedExecutionContext:
    context = _through_authorizing(machine, context)
    context = _transition(machine, context, GovernedExecutionState.MUTATING)
    return _transition(machine, context, GovernedExecutionState.VERIFYING)


def _through_second_authorizing(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
) -> GovernedExecutionContext:
    context = _through_verifying(machine, context)
    context = _transition(machine, context, GovernedExecutionState.REFLECTING)
    context = _transition(machine, context, GovernedExecutionState.REPLANNING)
    context = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(machine, context, GovernedExecutionState.DECIDING)
    context = _transition(machine, context, GovernedExecutionState.PROPOSING)
    return _transition(machine, context, GovernedExecutionState.AUTHORIZING)


def _valid_context_at(
    machine: GovernedExecutionStateMachine,
    state: GovernedExecutionState,
) -> GovernedExecutionContext:
    context = _context()
    if state is GovernedExecutionState.CREATED:
        return context
    if state is GovernedExecutionState.ABORTED:
        return _transition(
            machine,
            context,
            GovernedExecutionState.ABORTED,
            stop_reason=GovernedExecutionStopReason.USER_ABORTED,
        )
    context = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    if state is GovernedExecutionState.CONTEXT_ASSEMBLING:
        return context
    if state is GovernedExecutionState.FAILED:
        return _transition(
            machine,
            context,
            GovernedExecutionState.FAILED,
            stop_reason=GovernedExecutionStopReason.PROVIDER_FAILED,
        )
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    if state is GovernedExecutionState.PLANNING:
        return context
    context = _transition(machine, context, GovernedExecutionState.DECIDING)
    if state is GovernedExecutionState.DECIDING:
        return context
    context = _transition(machine, context, GovernedExecutionState.PROPOSING)
    if state is GovernedExecutionState.PROPOSING:
        return context
    context = _transition(machine, context, GovernedExecutionState.AUTHORIZING)
    if state is GovernedExecutionState.AUTHORIZING:
        return context
    context = _transition(machine, context, GovernedExecutionState.MUTATING)
    if state is GovernedExecutionState.MUTATING:
        return context
    context = _transition(machine, context, GovernedExecutionState.VERIFYING)
    if state is GovernedExecutionState.VERIFYING:
        return context
    if state is GovernedExecutionState.COMPLETED:
        return _transition(
            machine,
            context,
            GovernedExecutionState.COMPLETED,
            stop_reason=GovernedExecutionStopReason.SUCCESS,
        )
    raise AssertionError(f"unsupported test state: {state}")


def test_initial_context_is_created_with_empty_immutable_ledger() -> None:
    context = _context()

    assert context.state is GovernedExecutionState.CREATED
    assert context.iteration == 0
    assert context.history == ()
    assert context.evidence == ()
    assert context.stop_reason is None
    assert context.budget.iterations_used == 0


def test_valid_serial_governed_lifecycle_is_representable() -> None:
    machine = GovernedExecutionStateMachine()
    context = _through_verifying(machine, _context())
    context = _transition(machine, context, GovernedExecutionState.REFLECTING)
    context = _transition(machine, context, GovernedExecutionState.REPLANNING)
    context = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _transition(machine, context, GovernedExecutionState.PLANNING)

    assert context.state is GovernedExecutionState.PLANNING
    assert context.iteration == 2
    assert context.budget.iterations_used == 2
    assert tuple(record.sequence for record in context.history) == tuple(
        range(1, len(context.history) + 1)
    )
    assert context.history[-1].from_state is GovernedExecutionState.CONTEXT_ASSEMBLING


def test_illegal_transition_returns_unchanged_context_and_budget() -> None:
    context = _context()
    result = GovernedExecutionStateMachine().transition(context, GovernedExecutionState.MUTATING)

    assert result.accepted is False
    assert result.error_code == "illegal_transition"
    assert result.context is context
    assert result.context.budget == context.budget
    assert result.context.history == ()


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (GovernedExecutionState.CREATED, GovernedExecutionState.MUTATING),
        (GovernedExecutionState.PLANNING, GovernedExecutionState.MUTATING),
        (GovernedExecutionState.DECIDING, GovernedExecutionState.COMPLETED),
        (GovernedExecutionState.FAILED, GovernedExecutionState.MUTATING),
        (GovernedExecutionState.COMPLETED, GovernedExecutionState.MUTATING),
        (GovernedExecutionState.ABORTED, GovernedExecutionState.MUTATING),
    ],
)
def test_approved_illegal_transition_examples_are_rejected(
    source: GovernedExecutionState,
    target: GovernedExecutionState,
) -> None:
    machine = GovernedExecutionStateMachine()
    context = _valid_context_at(machine, source)

    result = machine.transition(context, target)

    assert result.accepted is False
    assert result.context is context


def test_strict_transition_raises_typed_error_without_context_mutation() -> None:
    context = _context()
    machine = GovernedExecutionStateMachine()

    with pytest.raises(IllegalTransitionError) as raised:
        machine.transition_or_raise(context, GovernedExecutionState.MUTATING)

    assert raised.value.code == "illegal_transition"
    assert raised.value.from_state is GovernedExecutionState.CREATED
    assert context.state is GovernedExecutionState.CREATED


def test_terminal_completion_requires_success_reason_and_cannot_continue() -> None:
    machine = GovernedExecutionStateMachine()
    context = _through_verifying(machine, _context())
    completed = _transition(
        machine,
        context,
        GovernedExecutionState.COMPLETED,
        stop_reason=GovernedExecutionStopReason.SUCCESS,
    )

    assert completed.state is GovernedExecutionState.COMPLETED
    assert completed.stop_reason is GovernedExecutionStopReason.SUCCESS
    rejected = machine.transition(completed, GovernedExecutionState.MUTATING)
    assert rejected.accepted is False
    assert rejected.context is completed


def test_terminal_abort_requires_user_abort_reason() -> None:
    machine = GovernedExecutionStateMachine()
    context = _context()

    rejected = machine.transition(
        context,
        GovernedExecutionState.ABORTED,
        stop_reason=GovernedExecutionStopReason.PROVIDER_FAILED,
    )
    aborted = _transition(
        machine,
        context,
        GovernedExecutionState.ABORTED,
        stop_reason=GovernedExecutionStopReason.USER_ABORTED,
    )

    assert rejected.accepted is False
    assert rejected.error_code == "invalid_stop_reason"
    assert aborted.stop_reason is GovernedExecutionStopReason.USER_ABORTED


def test_iteration_budget_is_monotonic_and_exhaustion_is_typed() -> None:
    budget = ExecutionBudget(max_iterations=1, max_mutations=1, max_verifications=1)
    machine = GovernedExecutionStateMachine()
    context = _through_verifying(machine, _context(budget=budget))
    context = _transition(machine, context, GovernedExecutionState.REFLECTING)
    context = _transition(machine, context, GovernedExecutionState.REPLANNING)

    exhausted = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)

    assert exhausted.state is GovernedExecutionState.FAILED
    assert exhausted.stop_reason is GovernedExecutionStopReason.ITERATION_BUDGET_EXHAUSTED
    assert exhausted.budget.iterations_used == 1
    assert exhausted.budget.iterations_remaining == 0


def test_mutation_budget_exhaustion_stops_without_a_second_mutation() -> None:
    budget = ExecutionBudget(max_iterations=2, max_mutations=1, max_verifications=1)
    machine = GovernedExecutionStateMachine()
    context = _through_second_authorizing(machine, _context(budget=budget))

    exhausted = _transition(machine, context, GovernedExecutionState.MUTATING)

    assert exhausted.state is GovernedExecutionState.FAILED
    assert exhausted.stop_reason is GovernedExecutionStopReason.MUTATION_BUDGET_EXHAUSTED
    assert exhausted.budget.mutations_used == 1
    assert sum(record.to_state is GovernedExecutionState.MUTATING for record in exhausted.history) == 1


def test_verification_budget_exhaustion_is_typed() -> None:
    budget = ExecutionBudget(max_iterations=2, max_mutations=2, max_verifications=1)
    machine = GovernedExecutionStateMachine()
    context = _through_second_authorizing(machine, _context(budget=budget))
    context = _transition(machine, context, GovernedExecutionState.MUTATING)

    exhausted = _transition(machine, context, GovernedExecutionState.VERIFYING)

    assert exhausted.state is GovernedExecutionState.FAILED
    assert exhausted.stop_reason is GovernedExecutionStopReason.VERIFICATION_BUDGET_EXHAUSTED
    assert exhausted.budget.verifications_used == 1
    assert sum(record.to_state is GovernedExecutionState.VERIFYING for record in exhausted.history) == 1


def test_evidence_and_history_remain_reconstructable_and_redacted() -> None:
    evidence = ExecutionEvidenceRef(
        kind=ExecutionEvidenceKind.DECISION,
        reference_id="decision-1",
        digest="decision-digest",
        metadata={"policy_version": "1.0"},
    )
    machine = GovernedExecutionStateMachine()
    context = _transition(
        machine,
        _context(),
        GovernedExecutionState.CONTEXT_ASSEMBLING,
        evidence=(evidence,),
    )

    assert context.evidence == (evidence,)
    assert context.history[0].evidence == (evidence,)
    assert context.history[0].iteration == 1
    with pytest.raises(TypeError):
        context.evidence[0].metadata["policy_version"] = "tampered"  # type: ignore[index]
    with pytest.raises(TypeError):
        context.metadata["unsafe"] = True  # type: ignore[index]


def test_events_are_emitted_for_valid_transitions_in_deterministic_order() -> None:
    event_bus = EventBus()
    observed: list[str] = []
    event_bus.subscribe(GovernedExecutionStarted, lambda event: observed.append(type(event).__name__))
    event_bus.subscribe(
        GovernedExecutionTransitioned,
        lambda event: observed.append(f"{type(event).__name__}:{event.to_state.value}"),
    )
    event_bus.subscribe(GovernedExecutionStopped, lambda event: observed.append(type(event).__name__))
    machine = GovernedExecutionStateMachine(event_bus)

    context = _transition(machine, _context(), GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(machine, context, GovernedExecutionState.DECIDING)
    context = _transition(machine, context, GovernedExecutionState.PROPOSING)
    context = _transition(machine, context, GovernedExecutionState.AUTHORIZING)
    context = _transition(machine, context, GovernedExecutionState.MUTATING)
    context = _transition(machine, context, GovernedExecutionState.VERIFYING)
    _transition(
        machine,
        context,
        GovernedExecutionState.COMPLETED,
        stop_reason=GovernedExecutionStopReason.SUCCESS,
    )

    assert observed[0:2] == [
        "GovernedExecutionStarted",
        "GovernedExecutionTransitioned:context_assembling",
    ]
    assert observed[-2:] == [
        "GovernedExecutionTransitioned:completed",
        "GovernedExecutionStopped",
    ]


def test_event_delivery_failure_cannot_change_accepted_state() -> None:
    event_bus = EventBus()

    def _raise(_: GovernedExecutionStarted) -> None:
        raise RuntimeError("observer failure")

    event_bus.subscribe(GovernedExecutionStarted, _raise)
    result = GovernedExecutionStateMachine(event_bus).transition(
        _context(),
        GovernedExecutionState.CONTEXT_ASSEMBLING,
    )

    assert result.accepted is True
    assert result.context.state is GovernedExecutionState.CONTEXT_ASSEMBLING
    assert len(result.context.history) == 1


def test_state_machine_has_no_operational_runtime_dependencies() -> None:
    root = Path(__file__).parents[1] / "src" / "eag" / "governed_execution"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))

    forbidden_imports = (
        r"(?:from|import)\s+subprocess",
        r"(?:from|import)\s+requests",
        r"(?:from|import)\s+httpx",
        r"(?:from|import)\s+socket",
        r"from\s+eag\.(?:autonomous|capability|chief\.intelligence\.gateway|workspace)",
        r"from\s+eag\.mutation\s+import\s+.*GovernedMutationRuntime",
    )
    for pattern in forbidden_imports:
        assert re.search(pattern, source) is None
    assert "os.system(" not in source


def _reconstruct(
    context: GovernedExecutionContext,
    **updates: object,
) -> GovernedExecutionContext:
    values: dict[str, object] = {
        "execution_id": context.execution_id,
        "run_id": context.run_id,
        "goal": context.goal,
        "state": context.state,
        "iteration": context.iteration,
        "budget": context.budget,
        "history": context.history,
        "evidence": context.evidence,
        "stop_reason": context.stop_reason,
        "metadata": context.metadata,
    }
    values.update(updates)
    return GovernedExecutionContext(**values)  # type: ignore[arg-type]


def test_non_created_context_with_empty_history_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires a valid transition history"):
        GovernedExecutionContext(
            run_id="reconstructed-run",
            goal="Reject impossible public state.",
            state=GovernedExecutionState.MUTATING,
        )


def test_reconstructed_ledger_rejects_illegal_first_transition() -> None:
    illegal_first = ExecutionTransitionRecord(
        sequence=1,
        iteration=0,
        from_state=GovernedExecutionState.CREATED,
        to_state=GovernedExecutionState.MUTATING,
    )

    with pytest.raises(ValueError, match="illegal transition"):
        GovernedExecutionContext(
            run_id="reconstructed-run",
            goal="Reject an illegal first edge.",
            state=GovernedExecutionState.MUTATING,
            budget=ExecutionBudget(mutations_used=1),
            history=(illegal_first,),
        )


def test_reconstructed_ledger_rejects_disconnected_history() -> None:
    history = (
        ExecutionTransitionRecord(
            sequence=1,
            iteration=1,
            from_state=GovernedExecutionState.CREATED,
            to_state=GovernedExecutionState.CONTEXT_ASSEMBLING,
        ),
        ExecutionTransitionRecord(
            sequence=2,
            iteration=1,
            from_state=GovernedExecutionState.CREATED,
            to_state=GovernedExecutionState.CONTEXT_ASSEMBLING,
        ),
    )

    with pytest.raises(ValueError, match="originate at created and remain contiguous"):
        GovernedExecutionContext(
            run_id="reconstructed-run",
            goal="Reject disconnected history.",
            state=GovernedExecutionState.CONTEXT_ASSEMBLING,
            iteration=1,
            budget=ExecutionBudget(iterations_used=1),
            history=history,
        )


def test_reconstructed_ledger_rejects_history_current_state_mismatch() -> None:
    machine = GovernedExecutionStateMachine()
    assembling = _transition(machine, _context(), GovernedExecutionState.CONTEXT_ASSEMBLING)

    with pytest.raises(ValueError, match="terminal state must equal current state"):
        _reconstruct(assembling, state=GovernedExecutionState.PLANNING)


def test_reconstructed_ledger_rejects_terminal_history_with_additional_transition() -> None:
    machine = GovernedExecutionStateMachine()
    completed = _valid_context_at(machine, GovernedExecutionState.COMPLETED)
    additional = ExecutionTransitionRecord(
        sequence=len(completed.history) + 1,
        iteration=completed.iteration,
        from_state=GovernedExecutionState.COMPLETED,
        to_state=GovernedExecutionState.MUTATING,
    )

    with pytest.raises(ValueError, match="illegal transition"):
        _reconstruct(
            completed,
            state=GovernedExecutionState.MUTATING,
            history=(*completed.history, additional),
            stop_reason=None,
        )


def test_valid_reconstructed_ledger_is_accepted() -> None:
    machine = GovernedExecutionStateMachine()
    original = _through_verifying(machine, _context())

    reconstructed = _reconstruct(original)

    assert reconstructed == original
    assert reconstructed.history == original.history
    assert reconstructed.budget == original.budget


def test_reconstructed_ledger_rejects_fabricated_mutation_counter() -> None:
    machine = GovernedExecutionStateMachine()
    authorizing = _through_authorizing(machine, _context())
    fabricated_budget = ExecutionBudget(
        max_iterations=authorizing.budget.max_iterations,
        max_mutations=authorizing.budget.max_mutations,
        max_verifications=authorizing.budget.max_verifications,
        iterations_used=authorizing.budget.iterations_used,
        mutations_used=1,
    )

    with pytest.raises(ValueError, match="mutation budget must equal legitimate mutating entries"):
        _reconstruct(authorizing, budget=fabricated_budget)


def test_reconstructed_ledger_rejects_fabricated_verification_counter() -> None:
    machine = GovernedExecutionStateMachine()
    mutating = _transition(
        machine,
        _through_authorizing(machine, _context()),
        GovernedExecutionState.MUTATING,
    )
    fabricated_budget = ExecutionBudget(
        max_iterations=mutating.budget.max_iterations,
        max_mutations=mutating.budget.max_mutations,
        max_verifications=mutating.budget.max_verifications,
        iterations_used=mutating.budget.iterations_used,
        mutations_used=mutating.budget.mutations_used,
        verifications_used=1,
    )

    with pytest.raises(ValueError, match="verification budget must equal legitimate verifying entries"):
        _reconstruct(mutating, budget=fabricated_budget)


def test_reconstructed_ledger_rejects_inconsistent_iteration_counter() -> None:
    machine = GovernedExecutionStateMachine()
    planning = _transition(
        machine,
        _transition(machine, _context(), GovernedExecutionState.CONTEXT_ASSEMBLING),
        GovernedExecutionState.PLANNING,
    )
    fabricated_budget = ExecutionBudget(
        max_iterations=2,
        max_mutations=planning.budget.max_mutations,
        max_verifications=planning.budget.max_verifications,
        iterations_used=2,
    )

    with pytest.raises(ValueError, match="history iteration must equal current iteration"):
        _reconstruct(planning, iteration=2, budget=fabricated_budget)


def test_metadata_deep_freeze_prevents_nested_alias_and_mutation() -> None:
    metadata = {
        "nested": {
            "items": [{"name": "original"}],
            "labels": {"governed"},
        }
    }
    context = GovernedExecutionContext(
        run_id="immutability-run",
        goal="Protect nested metadata.",
        metadata=metadata,
    )
    metadata["nested"]["items"][0]["name"] = "tampered"
    metadata["nested"]["labels"].add("external")

    assert context.metadata["nested"]["items"][0]["name"] == "original"
    assert context.metadata["nested"]["labels"] == frozenset({"governed"})
    with pytest.raises(TypeError):
        context.metadata["nested"]["items"][0]["name"] = "blocked"  # type: ignore[index]
    with pytest.raises(AttributeError):
        context.metadata["nested"]["items"].append("blocked")  # type: ignore[union-attr]
    with pytest.raises(AttributeError):
        context.metadata["nested"]["labels"].add("blocked")  # type: ignore[union-attr]


def test_evidence_metadata_is_deeply_immutable_and_alias_safe() -> None:
    metadata = {"proof": {"paths": ["src/example.py"], "tags": {"trusted"}}}
    evidence = ExecutionEvidenceRef(
        kind=ExecutionEvidenceKind.VERIFICATION,
        reference_id="verification-immutable",
        metadata=metadata,
    )
    metadata["proof"]["paths"].append("src/tampered.py")
    metadata["proof"]["tags"].add("external")

    assert evidence.metadata["proof"]["paths"] == ("src/example.py",)
    assert evidence.metadata["proof"]["tags"] == frozenset({"trusted"})
    with pytest.raises(TypeError):
        evidence.metadata["proof"]["paths"] = ()  # type: ignore[index]
    with pytest.raises(AttributeError):
        evidence.metadata["proof"]["paths"].append("blocked")  # type: ignore[union-attr]
    with pytest.raises(AttributeError):
        evidence.metadata["proof"]["tags"].add("blocked")  # type: ignore[union-attr]
