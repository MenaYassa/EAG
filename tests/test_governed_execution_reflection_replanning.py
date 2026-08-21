"""Deterministic G2.4.3 contracts for governed reflection and replanning evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

import pytest

from eag.events import EventBus
from eag.governed_execution import (
    ExecutionBudget,
    ExecutionEvidenceKind,
    ExecutionEvidenceRef,
    FreshIterationArtifacts,
    GovernedExecutionContext,
    GovernedExecutionState,
    GovernedExecutionStateMachine,
    GovernedMemoryEvidence,
    GovernedReflectionAdapter,
    GovernedReflectionError,
    GovernedReflectionInput,
    ObjectiveAssessment,
    ObjectiveFailureCode,
    ObjectiveStatus,
    ReplanningAction,
    ReplanningError,
    ReplanningInput,
    ReplanningPolicy,
    ReplanningReasonCode,
    VerificationFailureCode,
    VerificationResult,
    VerificationStatus,
)
from eag.reflection.models import ReflectionReport
from eag.reflection.runtime import ReflectionRuntime


class _Result(StrEnum):
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class _Receipt:
    mutation_id: str
    proposal_id: str
    run_id: str
    authorization_id: str
    result: _Result = _Result.COMPLETED
    verification_passed: bool = True


class _DeterministicReflectionEngine:
    def reflect(self, context):
        return ReflectionReport(run_id=context.run_id)


def _move(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
    target: GovernedExecutionState,
    *,
    evidence: tuple[ExecutionEvidenceRef, ...] = (),
) -> GovernedExecutionContext:
    result = machine.transition(context, target, evidence=evidence)
    assert result.accepted is True
    return result.context


def _reflecting_context(receipt: _Receipt, verification: VerificationResult) -> GovernedExecutionContext:
    machine = GovernedExecutionStateMachine()
    context = GovernedExecutionContext(
        execution_id="execution-1",
        run_id=receipt.run_id,
        goal="Produce a bounded governed recovery fixture.",
        budget=ExecutionBudget(max_iterations=2, max_mutations=2, max_verifications=2),
    )
    context = _move(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _move(machine, context, GovernedExecutionState.PLANNING)
    context = _move(
        machine,
        context,
        GovernedExecutionState.DECIDING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.DECISION, reference_id="decision-1"),),
    )
    context = _move(machine, context, GovernedExecutionState.PROPOSING)
    context = _move(machine, context, GovernedExecutionState.AUTHORIZING)
    context = _move(
        machine,
        context,
        GovernedExecutionState.MUTATING,
        evidence=(
            ExecutionEvidenceRef(kind=ExecutionEvidenceKind.PROPOSAL, reference_id=receipt.proposal_id),
            ExecutionEvidenceRef(
                kind=ExecutionEvidenceKind.AUTHORIZATION,
                reference_id=receipt.authorization_id,
            ),
        ),
    )
    context = _move(
        machine,
        context,
        GovernedExecutionState.VERIFYING,
        evidence=(
            ExecutionEvidenceRef(
                kind=ExecutionEvidenceKind.MUTATION_RECEIPT,
                reference_id=receipt.mutation_id,
            ),
        ),
    )
    return _move(
        machine,
        context,
        GovernedExecutionState.REFLECTING,
        evidence=(verification.evidence_ref,),
    )


def _evidence_bundle() -> tuple[_Receipt, VerificationResult, ObjectiveAssessment]:
    receipt = _Receipt(
        mutation_id="receipt-1",
        proposal_id="proposal-1",
        run_id="run-1",
        authorization_id="authorization-1",
    )
    verification = VerificationResult(
        verification_id="verification-1",
        request_id="verification-request-1",
        run_id=receipt.run_id,
        receipt_id=receipt.mutation_id,
        specification_id="specification-1",
        status=VerificationStatus.FAILED,
        evidence=None,
        failure_code=VerificationFailureCode.ASSERTION_FAILED,
    )
    objective = ObjectiveAssessment(
        status=ObjectiveStatus.NOT_SATISFIED,
        verification_id=verification.verification_id,
        receipt_id=receipt.mutation_id,
        failure_code=ObjectiveFailureCode.VERIFICATION_NOT_PASSED,
    )
    return receipt, verification, objective


def _reflection_input() -> GovernedReflectionInput:
    receipt, verification, objective = _evidence_bundle()
    return GovernedReflectionInput(
        execution_context=_reflecting_context(receipt, verification),
        receipt=receipt,
        verification=verification,
        objective=objective,
        context_artifact_id="context-1",
        context_fingerprint="context-fingerprint-1",
        decision_id="decision-1",
        proposal_id=receipt.proposal_id,
        authorization_id=receipt.authorization_id,
        policy_version="policy-1",
        redacted_metadata={"failure_class": "objective_verification"},
    )


def _replanning_input() -> ReplanningInput:
    governed_input = _reflection_input()
    adapter = GovernedReflectionAdapter()
    outcome = adapter.reflect(
        ReflectionRuntime(_DeterministicReflectionEngine(), EventBus()),
        governed_input,
    )
    memory = adapter.memory_evidence(outcome)
    machine = GovernedExecutionStateMachine()
    context = _move(
        machine,
        governed_input.execution_context,
        GovernedExecutionState.REPLANNING,
        evidence=(outcome.evidence_ref,),
    )
    return ReplanningInput(
        execution_context=context,
        reflection=outcome,
        memory=memory,
        previous_decision_id=governed_input.decision_id,
        previous_proposal_id=governed_input.proposal_id,
        previous_authorization_id=governed_input.authorization_id,
        previous_context_artifact_id=governed_input.context_artifact_id,
    )


def test_governed_reflection_is_provenance_bound_and_redacted() -> None:
    governed_input = _reflection_input()
    outcome = GovernedReflectionAdapter().reflect(
        ReflectionRuntime(_DeterministicReflectionEngine(), EventBus()),
        governed_input,
    )

    assert outcome.provenance.execution_id == "execution-1"
    assert outcome.provenance.iteration == 1
    assert outcome.provenance.receipt_id == "receipt-1"
    assert outcome.provenance.verification_id == "verification-1"
    assert outcome.reflection_context.run_result.outcome == "failure"
    assert outcome.reflection_context.metadata["objective_status"] == "not_satisfied"
    assert outcome.evidence_ref.kind is ExecutionEvidenceKind.REFLECTION


def test_memory_experience_is_bound_to_same_governed_reflection_provenance() -> None:
    governed_input = _reflection_input()
    adapter = GovernedReflectionAdapter()
    outcome = adapter.reflect(ReflectionRuntime(_DeterministicReflectionEngine(), EventBus()), governed_input)
    memory = adapter.memory_evidence(outcome)

    assert memory.provenance == outcome.provenance
    assert memory.reflection_id == outcome.report.id
    assert memory.experience.source_entries == (governed_input.execution_context.run_id,)


def test_replanning_policy_allows_only_iteration_one_with_remaining_existing_budget() -> None:
    outcome = ReplanningPolicy.decide(_replanning_input(), planning_decision_id="planning-decision-2")

    assert outcome.action is ReplanningAction.CONTINUE_WITH_FRESH_DECISION
    assert outcome.reason_code is ReplanningReasonCode.ELIGIBLE_VERIFICATION_FAILURE
    assert outcome.planning_decision_id == "planning-decision-2"
    assert outcome.evidence_ref.kind is ExecutionEvidenceKind.REPLANNING


@pytest.mark.parametrize(
    ("field_name", "stale_value"),
    [
        ("context_artifact_id", "context-1"),
        ("decision_id", "decision-1"),
        ("proposal_id", "proposal-1"),
        ("authorization_id", "authorization-1"),
        ("receipt_id", "receipt-1"),
        ("verification_id", "verification-1"),
        ("context_fingerprint", "context-fingerprint-1"),
    ],
)
def test_fresh_iteration_rejects_every_stale_authority(field_name: str, stale_value: str) -> None:
    input = _replanning_input()
    values = {
        "context_artifact_id": "context-2",
        "decision_request_id": "request-2",
        "decision_id": "decision-2",
        "proposal_id": "proposal-2",
        "authorization_id": "authorization-2",
        "receipt_id": "receipt-2",
        "verification_id": "verification-2",
        "context_fingerprint": "context-fingerprint-2",
    }
    values[field_name] = stale_value

    with pytest.raises(ReplanningError, match="stale"):
        ReplanningPolicy.validate_fresh_iteration(input, FreshIterationArtifacts(**values))


def test_fresh_iteration_accepts_all_new_authorities() -> None:
    input = _replanning_input()
    artifacts = FreshIterationArtifacts(
        context_artifact_id="context-2",
        decision_request_id="request-2",
        decision_id="decision-2",
        proposal_id="proposal-2",
        authorization_id="authorization-2",
        receipt_id="receipt-2",
        verification_id="verification-2",
        context_fingerprint="context-fingerprint-2",
    )

    ReplanningPolicy.validate_fresh_iteration(input, artifacts)


def test_stale_reflection_and_memory_evidence_are_rejected() -> None:
    input = _replanning_input()
    stale_input = _reflection_input()
    stale_context = replace(stale_input.execution_context, execution_id="execution-other")
    stale_input = replace(stale_input, execution_context=stale_context)

    with pytest.raises(ReplanningError, match="reflection belongs to another execution"):
        ReplanningInput(
            execution_context=input.execution_context,
            reflection=GovernedReflectionAdapter().reflect(
                ReflectionRuntime(_DeterministicReflectionEngine(), EventBus()),
                stale_input,
            ),
            memory=input.memory,
            previous_decision_id=input.previous_decision_id,
            previous_proposal_id=input.previous_proposal_id,
            previous_authorization_id=input.previous_authorization_id,
            previous_context_artifact_id=input.previous_context_artifact_id,
        )

    with pytest.raises(GovernedReflectionError, match="reflection_id"):
        GovernedMemoryEvidence(
            experience=input.memory.experience,
            provenance=input.reflection.provenance,
            reflection_id="other-reflection",
        )


def test_mismatched_receipt_verification_and_iteration_are_rejected() -> None:
    receipt, verification, objective = _evidence_bundle()
    mismatched_verification = VerificationResult(
        verification_id=verification.verification_id,
        request_id=verification.request_id,
        run_id=verification.run_id,
        receipt_id="different-receipt",
        specification_id=verification.specification_id,
        status=verification.status,
        evidence=None,
        failure_code=verification.failure_code,
    )
    with pytest.raises(GovernedReflectionError, match="same receipt"):
        GovernedReflectionInput(
            execution_context=_reflecting_context(receipt, verification),
            receipt=receipt,
            verification=mismatched_verification,
            objective=objective,
            context_artifact_id="context-1",
            context_fingerprint="fingerprint-1",
            decision_id="decision-1",
            proposal_id="proposal-1",
            authorization_id="authorization-1",
            policy_version="policy-1",
        )


def test_budget_exhaustion_rejects_recovery_without_reset() -> None:
    input = _replanning_input()
    exhausted_context = replace(
        input.execution_context,
        budget=ExecutionBudget(
            max_iterations=1,
            max_mutations=2,
            max_verifications=2,
            iterations_used=1,
            mutations_used=1,
            verifications_used=1,
        ),
    )
    exhausted_input = replace(input, execution_context=exhausted_context)

    outcome = ReplanningPolicy.decide(exhausted_input)

    assert outcome.action is ReplanningAction.FAIL
    assert outcome.reason_code is ReplanningReasonCode.ITERATION_LIMIT


def test_terminal_state_cannot_enter_recovery_path() -> None:
    input = _replanning_input()
    machine = GovernedExecutionStateMachine()
    failed = machine.transition(
        input.execution_context,
        GovernedExecutionState.FAILED,
        stop_reason=None,
    )
    assert failed.accepted is False
    assert failed.context is input.execution_context


def test_reflection_runtime_failure_is_propagated_without_replanning() -> None:
    class _FailingEngine:
        def reflect(self, context):
            raise RuntimeError("deterministic reflection failure")

    with pytest.raises(Exception, match="Reflection failed"):
        GovernedReflectionAdapter().reflect(
            ReflectionRuntime(_FailingEngine(), EventBus()),
            _reflection_input(),
        )


def test_second_iteration_policy_failure_is_bounded_and_noncontinuing() -> None:
    input = _replanning_input()
    machine = GovernedExecutionStateMachine()
    context = _move(machine, input.execution_context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _move(machine, context, GovernedExecutionState.PLANNING)
    context = _move(machine, context, GovernedExecutionState.DECIDING)
    context = _move(machine, context, GovernedExecutionState.PROPOSING)
    context = _move(machine, context, GovernedExecutionState.AUTHORIZING)
    context = _move(machine, context, GovernedExecutionState.MUTATING)
    context = _move(machine, context, GovernedExecutionState.VERIFYING)
    context = _move(machine, context, GovernedExecutionState.REFLECTING)
    context = _move(machine, context, GovernedExecutionState.REPLANNING)
    with pytest.raises(ReplanningError, match="incompatible iteration"):
        replace(input, execution_context=context)


def test_new_modules_have_no_operational_mutation_imports() -> None:
    import eag.governed_execution.reflection as reflection_module
    import eag.governed_execution.replanning as replanning_module

    assert "eag.mutation" not in reflection_module.__dict__
    assert "eag.mutation" not in replanning_module.__dict__
