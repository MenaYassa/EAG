#!/usr/bin/env python3
"""Human-readable deterministic manual demonstration of G2.4.3 recovery contracts.

This script uses only public G2.4.1/G2.4.2/G2.4.3 contracts and synthetic,
redacted identifiers. It does not call a provider, mutate a workspace, invoke
the G2.3.2 workflow, execute commands, access Git, use network clients, or
access credentials.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass, replace
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
    GovernedMemoryEvidence,
    GovernedReflectionAdapter,
    GovernedReflectionInput,
    ObjectiveAssessment,
    ObjectiveFailureCode,
    ObjectiveStatus,
    ReplanningAction,
    ReplanningError,
    ReplanningInput,
    ReplanningPolicy,
    VerificationFailureCode,
    VerificationResult,
    VerificationStatus,
)
from eag.reflection.models import ReflectionReport
from eag.reflection.runtime import ReflectionRuntime


class _SyntheticMutationResult(StrEnum):
    """Synthetic completed result matching the read-only receipt evidence surface."""

    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class SyntheticReceipt:
    """Minimal safe receipt evidence; no mutation runtime is invoked."""

    mutation_id: str
    proposal_id: str
    run_id: str
    authorization_id: str
    result: _SyntheticMutationResult = _SyntheticMutationResult.COMPLETED
    verification_passed: bool = True


class DeterministicReflectionEngine:
    """Synthetic reflection engine for demonstration only; it has no external effects."""

    def reflect(self, context: object) -> ReflectionReport:
        return ReflectionReport(run_id=context.run_id)


@dataclass(frozen=True, slots=True)
class RecoveryCycle:
    """Safe in-memory evidence for one completed iteration-one recovery boundary."""

    machine: GovernedExecutionStateMachine
    replanning_context: GovernedExecutionContext
    replanning_input: ReplanningInput
    first_receipt: SyntheticReceipt
    first_verification: VerificationResult
    reflection_id: str


def _show(stage: str, detail: str) -> None:
    print(f"{stage}: {detail}")


def _transition(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
    target: GovernedExecutionState,
    *,
    evidence: tuple[ExecutionEvidenceRef, ...] = (),
    stop_reason: GovernedExecutionStopReason | None = None,
) -> GovernedExecutionContext:
    result = machine.transition(context, target, evidence=evidence, stop_reason=stop_reason)
    if not result.accepted:
        raise RuntimeError(f"unexpected rejected transition to {target.value}: {result.error_code}")
    return result.context


def _verification(
    *,
    receipt: SyntheticReceipt,
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
    SyntheticReceipt,
    VerificationResult,
    ObjectiveAssessment,
]:
    machine = GovernedExecutionStateMachine()
    receipt = SyntheticReceipt(
        mutation_id="receipt-iteration-1",
        proposal_id="proposal-iteration-1",
        run_id="manual-g2-4-3-run",
        authorization_id="authorization-iteration-1",
    )
    verification = _verification(
        receipt=receipt,
        verification_id="verification-iteration-1",
        status=VerificationStatus.FAILED,
    )
    objective = ObjectiveAssessment(
        status=ObjectiveStatus.NOT_SATISFIED,
        verification_id=verification.verification_id,
        receipt_id=receipt.mutation_id,
        failure_code=ObjectiveFailureCode.VERIFICATION_NOT_PASSED,
    )
    context = GovernedExecutionContext(
        execution_id="manual-g2-4-3-execution",
        run_id=receipt.run_id,
        goal="Demonstrate bounded deterministic governed recovery.",
        budget=ExecutionBudget(max_iterations=2, max_mutations=2, max_verifications=2),
    )
    context = _transition(machine, context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(
        machine,
        context,
        GovernedExecutionState.DECIDING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.DECISION, reference_id="decision-iteration-1"),),
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


def _recover_iteration_one(*, verbose: bool) -> RecoveryCycle:
    machine, context, receipt, verification, objective = _first_iteration_to_reflecting()
    if verbose:
        _show("ITERATION 1", "fresh context=context-iteration-1; decision=decision-iteration-1")
        _show("MUTATION", f"completed receipt={receipt.mutation_id}; proposal={receipt.proposal_id}")
        _show("VERIFICATION", f"FAILED id={verification.verification_id}; objective={objective.status.value}")

    adapter = GovernedReflectionAdapter()
    reflection = adapter.reflect(
        ReflectionRuntime(DeterministicReflectionEngine(), EventBus()),
        GovernedReflectionInput(
            execution_context=context,
            receipt=receipt,
            verification=verification,
            objective=objective,
            context_artifact_id="context-iteration-1",
            context_fingerprint="context-fingerprint-iteration-1",
            decision_id="decision-iteration-1",
            proposal_id=receipt.proposal_id,
            authorization_id=receipt.authorization_id,
            policy_version="manual-policy-v1",
        ),
    )
    memory = adapter.memory_evidence(reflection)
    if verbose:
        _show(
            "REFLECTION",
            f"report={reflection.report.id}; provenance=(execution={reflection.provenance.execution_id}, iteration={reflection.provenance.iteration})",
        )
        _show(
            "EXPERIENCE",
            f"reflection={memory.reflection_id}; verification={memory.provenance.verification_id}",
        )

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
        previous_decision_id="decision-iteration-1",
        previous_proposal_id=receipt.proposal_id,
        previous_authorization_id=receipt.authorization_id,
        previous_context_artifact_id="context-iteration-1",
    )
    return RecoveryCycle(
        machine=machine,
        replanning_context=context,
        replanning_input=replanning_input,
        first_receipt=receipt,
        first_verification=verification,
        reflection_id=reflection.report.id,
    )


def _adaptive_replanning(cycle: RecoveryCycle, *, verbose: bool) -> GovernedExecutionContext:
    base_plan = Plan(
        plan_id="base-plan",
        steps=(PlanStep(step_id="base-step", name="Base governed intent"),),
    )
    adaptive_plan, planning_decision = AdaptivePlanner().plan(
        AdaptivePlanningContext(
            goal=cycle.replanning_context.goal,
            experiences=(cycle.replanning_input.memory.experience,),
            rules=(
                PlanningRule(
                    id="evidence-guided-review",
                    condition="experience_count == 1",
                    action="insert_step:Evidence-guided review:review",
                ),
            ),
        ),
        base_plan,
    )
    outcome = ReplanningPolicy.decide(
        cycle.replanning_input,
        planning_decision_id=planning_decision.id,
    )
    if outcome.action is not ReplanningAction.CONTINUE_WITH_FRESH_DECISION:
        raise RuntimeError(f"unexpected replanning action: {outcome.action.value}")
    if len(adaptive_plan.final_plan.steps) <= len(base_plan.steps):
        raise RuntimeError("adaptive planning did not apply supplied experience")
    if verbose:
        _show(
            "ADAPTIVE PLANNING",
            f"applied_rule={planning_decision.applied_rules[0].id}; steps={len(base_plan.steps)}→{len(adaptive_plan.final_plan.steps)}",
        )
        _show("REPLANNING", f"{outcome.action.value}; reason={outcome.reason_code.value}")

    artifacts = FreshIterationArtifacts(
        context_artifact_id="context-iteration-2",
        decision_request_id="decision-request-iteration-2",
        decision_id="decision-iteration-2",
        proposal_id="proposal-iteration-2",
        authorization_id="authorization-iteration-2",
        receipt_id="receipt-iteration-2",
        verification_id="verification-iteration-2",
        context_fingerprint="context-fingerprint-iteration-2",
    )
    ReplanningPolicy.validate_fresh_iteration(cycle.replanning_input, artifacts)
    if verbose:
        _show(
            "FRESH ITERATION 2",
            "context, decision request, decision, proposal, authorization, receipt, verification, and fingerprint are all new",
        )
    return _transition(
        cycle.machine,
        cycle.replanning_context,
        GovernedExecutionState.CONTEXT_ASSEMBLING,
        evidence=(outcome.evidence_ref,),
    )


def _second_iteration_to_verifying(
    machine: GovernedExecutionStateMachine,
    context: GovernedExecutionContext,
) -> tuple[GovernedExecutionContext, SyntheticReceipt]:
    receipt = SyntheticReceipt(
        mutation_id="receipt-iteration-2",
        proposal_id="proposal-iteration-2",
        run_id=context.run_id,
        authorization_id="authorization-iteration-2",
    )
    context = _transition(machine, context, GovernedExecutionState.PLANNING)
    context = _transition(
        machine,
        context,
        GovernedExecutionState.DECIDING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.DECISION, reference_id="decision-iteration-2"),),
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


def run_success() -> None:
    print("=== G2.4.3 DETERMINISTIC RECOVERY DEMO: SUCCESS ===")
    cycle = _recover_iteration_one(verbose=True)
    context = _adaptive_replanning(cycle, verbose=True)
    context, receipt = _second_iteration_to_verifying(cycle.machine, context)
    verification = _verification(
        receipt=receipt,
        verification_id="verification-iteration-2",
        status=VerificationStatus.PASSED,
    )
    objective = ObjectiveAssessment(
        status=ObjectiveStatus.SATISFIED,
        verification_id=verification.verification_id,
        receipt_id=receipt.mutation_id,
    )
    context = _transition(
        cycle.machine,
        context,
        GovernedExecutionState.COMPLETED,
        evidence=(verification.evidence_ref,),
        stop_reason=GovernedExecutionStopReason.SUCCESS,
    )
    _show(
        "ITERATION 2",
        f"decision=decision-iteration-2; proposal={receipt.proposal_id}; authorization={receipt.authorization_id}",
    )
    _show("VERIFICATION", f"PASSED id={verification.verification_id}; objective={objective.status.value}")
    _show("FINAL", f"{context.state.value.upper()}({context.stop_reason.value}); iterations={context.iteration}")


def run_negative() -> None:
    print("=== G2.4.3 DETERMINISTIC RECOVERY DEMO: BOUNDED NEGATIVE ===")
    cycle = _recover_iteration_one(verbose=True)
    context = _adaptive_replanning(cycle, verbose=True)
    context, receipt = _second_iteration_to_verifying(cycle.machine, context)
    verification = _verification(
        receipt=receipt,
        verification_id="verification-iteration-2",
        status=VerificationStatus.FAILED,
    )
    context = _transition(
        cycle.machine,
        context,
        GovernedExecutionState.FAILED,
        evidence=(verification.evidence_ref,),
        stop_reason=GovernedExecutionStopReason.VERIFICATION_FAILED,
    )
    _show("ITERATION 2", f"verification=FAILED id={verification.verification_id}")
    _show("FINAL", f"{context.state.value.upper()}({context.stop_reason.value}); iterations={context.iteration}")
    third = cycle.machine.transition(context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    if third.accepted:
        raise RuntimeError("terminal context unexpectedly accepted a third iteration")
    print("THIRD ITERATION = REJECTED")


def _expect_rejection(label: str, attempt: Callable[[], object]) -> None:
    try:
        attempt()
    except (ReplanningError, ValueError, TypeError) as error:
        print(f"{label}: EXPECTED REJECTION: PASS ({type(error).__name__})")
        return
    raise RuntimeError(f"{label}: expected deterministic rejection was not raised")


def run_adversarial() -> None:
    print("=== G2.4.3 DETERMINISTIC RECOVERY DEMO: ADVERSARIAL ===")
    cycle = _recover_iteration_one(verbose=False)
    fresh_values = {
        "context_artifact_id": "context-iteration-2",
        "decision_request_id": "decision-request-iteration-2",
        "decision_id": "decision-iteration-2",
        "proposal_id": "proposal-iteration-2",
        "authorization_id": "authorization-iteration-2",
        "receipt_id": "receipt-iteration-2",
        "verification_id": "verification-iteration-2",
        "context_fingerprint": "context-fingerprint-iteration-2",
    }
    stale_values = {
        "previous proposal": ("proposal_id", "proposal-iteration-1"),
        "previous authorization": ("authorization_id", "authorization-iteration-1"),
        "previous decision": ("decision_id", "decision-iteration-1"),
        "previous receipt": ("receipt_id", "receipt-iteration-1"),
        "previous verification result": ("verification_id", "verification-iteration-1"),
        "previous context artifact": ("context_artifact_id", "context-iteration-1"),
        "previous context fingerprint": ("context_fingerprint", "context-fingerprint-iteration-1"),
    }
    for label, (field_name, stale_value) in stale_values.items():
        def reuse(field_name: str = field_name, stale_value: str = stale_value) -> None:
            values = dict(fresh_values)
            values[field_name] = stale_value
            ReplanningPolicy.validate_fresh_iteration(
                cycle.replanning_input,
                FreshIterationArtifacts(**values),
            )

        _expect_rejection(label, reuse)

    second_context = _transition(
        cycle.machine,
        cycle.replanning_context,
        GovernedExecutionState.CONTEXT_ASSEMBLING,
    )
    _expect_rejection(
        "reflection from another iteration",
        lambda: ReplanningInput(
            execution_context=second_context,
            reflection=cycle.replanning_input.reflection,
            memory=cycle.replanning_input.memory,
            previous_decision_id="decision-iteration-1",
            previous_proposal_id="proposal-iteration-1",
            previous_authorization_id="authorization-iteration-1",
            previous_context_artifact_id="context-iteration-1",
        ),
    )

    memory_from_another_execution = GovernedMemoryEvidence(
        experience=cycle.replanning_input.memory.experience,
        provenance=replace(cycle.replanning_input.memory.provenance, execution_id="other-execution"),
        reflection_id=cycle.replanning_input.memory.reflection_id,
    )
    _expect_rejection(
        "memory from another execution",
        lambda: ReplanningInput(
            execution_context=cycle.replanning_context,
            reflection=cycle.replanning_input.reflection,
            memory=memory_from_another_execution,
            previous_decision_id="decision-iteration-1",
            previous_proposal_id="proposal-iteration-1",
            previous_authorization_id="authorization-iteration-1",
            previous_context_artifact_id="context-iteration-1",
        ),
    )

    fabricated_verification = VerificationResult(
        verification_id="verification-iteration-1",
        request_id="fabricated-request",
        run_id=cycle.first_receipt.run_id,
        receipt_id=cycle.first_receipt.mutation_id,
        specification_id="fabricated-specification",
        status=VerificationStatus.PASSED,
        evidence=None,
    )
    fabricated_objective = ObjectiveAssessment(
        status=ObjectiveStatus.SATISFIED,
        verification_id=fabricated_verification.verification_id,
        receipt_id=cycle.first_receipt.mutation_id,
    )
    _expect_rejection(
        "fabricated successful verification",
        lambda: GovernedReflectionInput(
            execution_context=cycle.replanning_input.reflection.input.execution_context,
            receipt=cycle.first_receipt,
            verification=fabricated_verification,
            objective=fabricated_objective,
            context_artifact_id="context-iteration-1",
            context_fingerprint="context-fingerprint-iteration-1",
            decision_id="decision-iteration-1",
            proposal_id="proposal-iteration-1",
            authorization_id="authorization-iteration-1",
            policy_version="manual-policy-v1",
        ),
    )

    negative_cycle = _recover_iteration_one(verbose=False)
    negative_context = _adaptive_replanning(negative_cycle, verbose=False)
    negative_context, receipt = _second_iteration_to_verifying(negative_cycle.machine, negative_context)
    negative_context = _transition(
        negative_cycle.machine,
        negative_context,
        GovernedExecutionState.FAILED,
        evidence=(
            _verification(
                receipt=receipt,
                verification_id="verification-iteration-2",
                status=VerificationStatus.FAILED,
            ).evidence_ref,
        ),
        stop_reason=GovernedExecutionStopReason.VERIFICATION_FAILED,
    )
    third = negative_cycle.machine.transition(negative_context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    if third.accepted:
        raise RuntimeError("continue after iteration 2 unexpectedly succeeded")
    print("continue after iteration 2: EXPECTED REJECTION: PASS (IllegalTransitionError)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--negative", action="store_true", help="show bounded second-verification failure")
    mode.add_argument("--adversarial", action="store_true", help="show deterministic contract rejections")
    args = parser.parse_args()

    if args.negative:
        run_negative()
    elif args.adversarial:
        run_adversarial()
    else:
        run_success()


if __name__ == "__main__":
    main()
