"""Deterministic EBS-017 contract for bounded governed failure recovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from eag.adaptive.models import AdaptivePlanningContext, PlanningRule
from eag.adaptive.planner import AdaptivePlanner
from eag.chief.runtime.models import Plan, PlanStep
from eag.events import EventBus
from eag.governed_execution import (
    ExecutionBudget,
    ExecutionEvidenceKind,
    ExecutionEvidenceRef,
    FreshIterationArtifacts,
    GovernedExecutionContext,
    GovernedExecutionState,
    GovernedExecutionStateMachine,
    GovernedExecutionStopReason,
    GovernedReflectionAdapter,
    GovernedReflectionInput,
    ObjectiveAssessment,
    ObjectiveFailureCode,
    ObjectiveStatus,
    ReplanningAction,
    ReplanningInput,
    ReplanningPolicy,
    VerificationFailureCode,
    VerificationResult,
    VerificationStatus,
)
from eag.reflection.models import ReflectionReport
from eag.reflection.runtime import ReflectionRuntime


class _Result(StrEnum):
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class _CompletedReceipt:
    mutation_id: str
    proposal_id: str
    run_id: str
    authorization_id: str
    result: _Result = _Result.COMPLETED
    verification_passed: bool = True


class _DeterministicReflectionEngine:
    def reflect(self, context):
        return ReflectionReport(run_id=context.run_id)


def _transition(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
    target: GovernedExecutionState,
    *,
    evidence: tuple[ExecutionEvidenceRef, ...] = (),
    stop_reason: GovernedExecutionStopReason | None = None,
) -> GovernedExecutionContext:
    result = machine.transition(context, target, evidence=evidence, stop_reason=stop_reason)
    assert result.accepted is True
    return result.context


def _verification(
    *,
    receipt: _CompletedReceipt,
    verification_id: str,
    status: VerificationStatus,
) -> VerificationResult:
    return VerificationResult(
        verification_id=verification_id,
        request_id=f"request-{verification_id}",
        run_id=receipt.run_id,
        receipt_id=receipt.mutation_id,
        specification_id=f"specification-{verification_id}",
        status=status,
        evidence=None,
        failure_code=(
            VerificationFailureCode.ASSERTION_FAILED
            if status is VerificationStatus.FAILED
            else None
        ),
    )


def _first_iteration_to_reflecting() -> tuple[
    GovernedExecutionStateMachine,
    GovernedExecutionContext,
    _CompletedReceipt,
    VerificationResult,
    ObjectiveAssessment,
]:
    machine = GovernedExecutionStateMachine()
    receipt = _CompletedReceipt(
        mutation_id="receipt-1",
        proposal_id="proposal-1",
        run_id="ebs-017-run",
        authorization_id="authorization-1",
    )
    verification = _verification(
        receipt=receipt,
        verification_id="verification-1",
        status=VerificationStatus.FAILED,
    )
    objective = ObjectiveAssessment(
        status=ObjectiveStatus.NOT_SATISFIED,
        verification_id=verification.verification_id,
        receipt_id=receipt.mutation_id,
        failure_code=ObjectiveFailureCode.VERIFICATION_NOT_PASSED,
    )
    context = GovernedExecutionContext(
        execution_id="ebs-017-execution",
        run_id=receipt.run_id,
        goal="Recover only through a fresh governed second iteration.",
        budget=ExecutionBudget(max_iterations=2, max_mutations=2, max_verifications=2),
    )
    context = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(
        machine,
        context,
        GovernedExecutionState.DECIDING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.DECISION, reference_id="decision-1"),),
    )
    context = _transition(machine, context, GovernedExecutionState.PROPOSING)
    context = _transition(machine, context, GovernedExecutionState.AUTHORIZING)
    context = _transition(
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
    context = _transition(
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
    context = _transition(
        machine,
        context,
        GovernedExecutionState.REFLECTING,
        evidence=(verification.evidence_ref,),
    )
    return machine, context, receipt, verification, objective


def _recover_once() -> tuple[GovernedExecutionStateMachine, GovernedExecutionContext]:
    machine, context, receipt, verification, objective = _first_iteration_to_reflecting()
    adapter = GovernedReflectionAdapter()
    reflection = adapter.reflect(
        ReflectionRuntime(_DeterministicReflectionEngine(), EventBus()),
        GovernedReflectionInput(
            execution_context=context,
            receipt=receipt,
            verification=verification,
            objective=objective,
            context_artifact_id="context-1",
            context_fingerprint="context-fingerprint-1",
            decision_id="decision-1",
            proposal_id="proposal-1",
            authorization_id="authorization-1",
            policy_version="policy-1",
        ),
    )
    memory = adapter.memory_evidence(reflection)
    context = _transition(
        machine,
        context,
        GovernedExecutionState.REPLANNING,
        evidence=(reflection.evidence_ref,),
    )
    replanning_input = ReplanningInput(
        execution_context=context,
        reflection=reflection,
        memory=memory,
        previous_decision_id="decision-1",
        previous_proposal_id="proposal-1",
        previous_authorization_id="authorization-1",
        previous_context_artifact_id="context-1",
    )

    base_plan = Plan(plan_id="base-plan", steps=(PlanStep(step_id="base", name="Base mutation"),))
    adaptive_plan, planning_decision = AdaptivePlanner().plan(
        AdaptivePlanningContext(
            goal=context.goal,
            experiences=(memory.experience,),
            rules=(
                PlanningRule(
                    id="experience-rule",
                    condition="experience_count == 1",
                    action="insert_step:Evidence-guided review:review",
                ),
            ),
        ),
        base_plan,
    )
    outcome = ReplanningPolicy.decide(replanning_input, planning_decision_id=planning_decision.id)
    assert outcome.action is ReplanningAction.CONTINUE_WITH_FRESH_DECISION
    assert len(adaptive_plan.final_plan.steps) == len(base_plan.steps) + 1
    assert planning_decision.applied_rules[0].id == "experience-rule"
    ReplanningPolicy.validate_fresh_iteration(
        replanning_input,
        FreshIterationArtifacts(
            context_artifact_id="context-2",
            decision_request_id="decision-request-2",
            decision_id="decision-2",
            proposal_id="proposal-2",
            authorization_id="authorization-2",
            receipt_id="receipt-2",
            verification_id="verification-2",
            context_fingerprint="context-fingerprint-2",
        ),
    )
    context = _transition(
        machine,
        context,
        GovernedExecutionState.CONTEXT_ASSEMBLING,
        evidence=(outcome.evidence_ref,),
    )
    return machine, context


def _second_iteration_to_verifying(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
) -> tuple[GovernedExecutionContext, _CompletedReceipt]:
    receipt = _CompletedReceipt(
        mutation_id="receipt-2",
        proposal_id="proposal-2",
        run_id=context.run_id,
        authorization_id="authorization-2",
    )
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(
        machine,
        context,
        GovernedExecutionState.DECIDING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.DECISION, reference_id="decision-2"),),
    )
    context = _transition(machine, context, GovernedExecutionState.PROPOSING)
    context = _transition(machine, context, GovernedExecutionState.AUTHORIZING)
    context = _transition(
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
    context = _transition(
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
    return context, receipt


def test_ebs_017_deterministic_governed_recovery_completes_with_fresh_iteration() -> None:
    machine, context = _recover_once()
    context, receipt = _second_iteration_to_verifying(machine, context)
    verification = _verification(
        receipt=receipt,
        verification_id="verification-2",
        status=VerificationStatus.PASSED,
    )
    objective = ObjectiveAssessment(
        status=ObjectiveStatus.SATISFIED,
        verification_id=verification.verification_id,
        receipt_id=receipt.mutation_id,
    )
    context = _transition(
        machine,
        context,
        GovernedExecutionState.COMPLETED,
        evidence=(verification.evidence_ref,),
        stop_reason=GovernedExecutionStopReason.SUCCESS,
    )

    assert objective.status is ObjectiveStatus.SATISFIED
    assert context.state is GovernedExecutionState.COMPLETED
    assert context.iteration == 2
    assert context.budget.iterations_used == 2
    assert context.budget.mutations_used == 2
    assert context.budget.verifications_used == 2
    evidence_ids = {evidence.reference_id for evidence in context.evidence}
    assert {"decision-1", "decision-2", "proposal-1", "proposal-2"} <= evidence_ids
    assert {"authorization-1", "authorization-2", "receipt-1", "receipt-2"} <= evidence_ids
    assert {"verification-1", "verification-2"} <= evidence_ids


def test_ebs_017_second_verification_failure_is_terminal_with_no_third_iteration() -> None:
    machine, context = _recover_once()
    context, receipt = _second_iteration_to_verifying(machine, context)
    verification = _verification(
        receipt=receipt,
        verification_id="verification-2",
        status=VerificationStatus.FAILED,
    )
    context = _transition(
        machine,
        context,
        GovernedExecutionState.FAILED,
        evidence=(verification.evidence_ref,),
        stop_reason=GovernedExecutionStopReason.VERIFICATION_FAILED,
    )

    assert context.state is GovernedExecutionState.FAILED
    assert context.stop_reason is GovernedExecutionStopReason.VERIFICATION_FAILED
    assert context.iteration == 2
    assert context.budget.iterations_used == 2
    assert context.budget.mutations_used == 2
    assert context.budget.verifications_used == 2
    rejected = machine.transition(context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    assert rejected.accepted is False
    assert rejected.context is context
