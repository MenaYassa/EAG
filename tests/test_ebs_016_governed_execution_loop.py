"""Deterministic EBS-016 contract for the G2.4.1 execution-state foundation."""

from __future__ import annotations

from dataclasses import dataclass

from eag.governed_execution import (
    DeterministicVerifier,
    ExecutionBudget,
    ExecutionEvidenceKind,
    ExecutionEvidenceRef,
    GovernedExecutionContext,
    GovernedExecutionState,
    GovernedExecutionStateMachine,
    GovernedExecutionStopReason,
    ObjectiveCompletionPolicy,
    ObjectiveStatus,
    VerificationCheck,
    VerificationRequest,
    VerificationSpecification,
    VerificationStatus,
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


def test_ebs_016_deterministic_governed_execution_ledger_contract() -> None:
    """Represent two future governed iterations without invoking their integrations."""
    machine = GovernedExecutionStateMachine()
    context = GovernedExecutionContext(
        run_id="ebs-016-run",
        goal="Represent a bounded verification-driven engineering lifecycle.",
        budget=ExecutionBudget(max_iterations=2, max_mutations=2, max_verifications=2),
    )

    # Iteration one: only references are recorded; no decision, mutation, verifier,
    # reflection, or replanner is actually invoked by this state-machine contract.
    context = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(
        machine,
        context,
        GovernedExecutionState.DECIDING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.PLAN, reference_id="plan-1"),),
    )
    context = _transition(
        machine,
        context,
        GovernedExecutionState.PROPOSING,
        evidence=(
            ExecutionEvidenceRef(kind=ExecutionEvidenceKind.DECISION, reference_id="decision-1"),
        ),
    )
    context = _transition(machine, context, GovernedExecutionState.AUTHORIZING)
    context = _transition(
        machine,
        context,
        GovernedExecutionState.MUTATING,
        evidence=(
            ExecutionEvidenceRef(kind=ExecutionEvidenceKind.PROPOSAL, reference_id="proposal-1"),
            ExecutionEvidenceRef(
                kind=ExecutionEvidenceKind.AUTHORIZATION,
                reference_id="authorization-1",
            ),
        ),
    )
    context = _transition(
        machine,
        context,
        GovernedExecutionState.VERIFYING,
        evidence=(
            ExecutionEvidenceRef(
                kind=ExecutionEvidenceKind.MUTATION_RECEIPT,
                reference_id="receipt-1",
            ),
        ),
    )
    context = _transition(
        machine,
        context,
        GovernedExecutionState.REFLECTING,
        evidence=(
            ExecutionEvidenceRef(kind=ExecutionEvidenceKind.VERIFICATION, reference_id="verification-1"),
        ),
    )
    context = _transition(
        machine,
        context,
        GovernedExecutionState.REPLANNING,
        evidence=(
            ExecutionEvidenceRef(kind=ExecutionEvidenceKind.REFLECTION, reference_id="reflection-1"),
        ),
    )

    # Iteration two is represented as a fresh serial lifecycle and reaches a typed success stop.
    context = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(machine, context, GovernedExecutionState.DECIDING)
    context = _transition(machine, context, GovernedExecutionState.PROPOSING)
    context = _transition(machine, context, GovernedExecutionState.AUTHORIZING)
    context = _transition(machine, context, GovernedExecutionState.MUTATING)
    context = _transition(machine, context, GovernedExecutionState.VERIFYING)
    context = _transition(
        machine,
        context,
        GovernedExecutionState.COMPLETED,
        stop_reason=GovernedExecutionStopReason.SUCCESS,
    )

    assert context.state is GovernedExecutionState.COMPLETED
    assert context.stop_reason is GovernedExecutionStopReason.SUCCESS
    assert context.iteration == 2
    assert context.budget.iterations_used == 2
    assert context.budget.mutations_used == 2
    assert context.budget.verifications_used == 2
    assert len(context.history) == 17
    assert tuple(record.sequence for record in context.history) == tuple(range(1, 18))
    assert {evidence.kind for evidence in context.evidence} == {
        ExecutionEvidenceKind.PLAN,
        ExecutionEvidenceKind.DECISION,
        ExecutionEvidenceKind.PROPOSAL,
        ExecutionEvidenceKind.AUTHORIZATION,
        ExecutionEvidenceKind.MUTATION_RECEIPT,
        ExecutionEvidenceKind.VERIFICATION,
        ExecutionEvidenceKind.REFLECTION,
    }


class _CompletedMutation:
    value = "completed"


@dataclass(frozen=True, slots=True)
class _CompletedReceiptFixture:
    """Minimal immutable G2.3.1 receipt evidence surface consumed by G2.4.2."""

    mutation_id: str
    run_id: str
    target_path: str
    result: _CompletedMutation
    verification_passed: bool = True


def test_ebs_016_mutation_success_does_not_establish_objective_success(tmp_path) -> None:
    """A bounded trusted assertion, not an LLM claim, decides objective success."""
    (tmp_path / "article.txt").write_text("draft\\n", encoding="utf-8")
    receipt = _CompletedReceiptFixture(
        mutation_id="receipt-016",
        run_id="ebs-016-verification",
        target_path="article.txt",
        result=_CompletedMutation(),
    )
    request = VerificationRequest(
        run_id=receipt.run_id,
        receipt=receipt,
        specification=VerificationSpecification(
            target_path="article.txt",
            check=VerificationCheck.EXACT_CONTENT,
            expected_content="published\\n",
        ),
    )

    result = DeterministicVerifier(workspace_root=tmp_path).verify(request)
    objective = ObjectiveCompletionPolicy.assess(receipt, result)

    assert receipt.verification_passed is True
    assert result.status is VerificationStatus.FAILED
    assert objective.status is ObjectiveStatus.NOT_SATISFIED
