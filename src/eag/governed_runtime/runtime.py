"""Opt-in synchronous G2.4.4 serial governed-execution composition."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Protocol

from eag.adaptive import AdaptivePlanner
from eag.adaptive.models import AdaptivePlanningContext
from eag.chief.intelligence.gateway.context import ContextAssemblyRequest
from eag.chief.intelligence.gateway.models import EngineeringContext, EngineeringDecisionRequest
from eag.chief.intelligence.gateway.mutation_translation import TrustedWorkspaceState
from eag.chief.intelligence.gateway.mutation_workflow import (
    GovernedDecisionMutationResult,
    GovernedDecisionMutationWorkflow,
    GovernedMutationFailureStage,
    GovernedMutationLifecycleObserver,
    GovernedWorkflowLifecycleRefused,
)
from eag.chief.runtime.models import Plan, PlanStep
from eag.governed_audit.recorder import (
    AuditPersistenceRequiredError,
    GovernedExecutionAuditObserver,
)
from eag.governed_execution.authority import (
    FreshIterationAuthority,
    validate_fresh_authority,
)
from eag.governed_execution.enums import (
    ExecutionEvidenceKind,
    GovernedExecutionState,
    GovernedExecutionStopReason,
)
from eag.governed_execution.models import ExecutionEvidenceRef, GovernedExecutionContext
from eag.governed_execution.reflection import (
    GovernedMemoryEvidence,
    GovernedReflectionAdapter,
    GovernedReflectionInput,
)
from eag.governed_execution.replanning import (
    FreshIterationArtifacts,
    ReplanningAction,
    ReplanningInput,
    ReplanningPolicy,
)
from eag.governed_execution.state_machine import GovernedExecutionStateMachine
from eag.governed_execution.verification import (
    DeterministicVerifier,
    ObjectiveAssessment,
    ObjectiveCompletionPolicy,
    ObjectiveStatus,
    VerificationRequest,
    VerificationResult,
)
from eag.governed_runtime.models import (
    GovernedExecutionRequest,
    GovernedExecutionResult,
    IterationContextArtifact,
    VerificationSpecificationFactory,
)
from eag.reflection.runtime import ReflectionRuntime


class GovernedExecutionRuntimeError(RuntimeError):
    """Raised for a composition invariant breach before a terminal context exists."""


@dataclass(frozen=True, slots=True, kw_only=True)
class IterationContextBundle:
    """Trusted context, identity, and translator state produced fresh per iteration."""

    context: EngineeringContext
    artifact: IterationContextArtifact
    trusted_state: TrustedWorkspaceState


class IterationContextFactory(Protocol):
    """Assemble fresh trusted repository context without invoking a provider or mutation."""

    def assemble(
        self,
        request: ContextAssemblyRequest,
        *,
        iteration: int,
    ) -> IterationContextBundle: ...


class GovernedDecisionRequestFactory(Protocol):
    """Build a fresh policy-bounded gateway request from trusted context."""

    def build(
        self,
        request: GovernedExecutionRequest,
        context: EngineeringContext,
    ) -> EngineeringDecisionRequest: ...


@dataclass(slots=True)
class _IterationState:
    context_bundle: IterationContextBundle
    request: EngineeringDecisionRequest
    decision_id: str = ""
    workflow_result: GovernedDecisionMutationResult | None = None
    authority: FreshIterationAuthority | None = None
    verification: VerificationResult | None = None


_workspace_locks: dict[str, threading.Lock] = {}
_workspace_locks_guard = threading.Lock()


class GovernedEngineeringExecutionRuntime:
    """Own one bounded serial lifecycle while delegating every substantive authority.

    The runtime performs no direct workspace write, authorization, provider request,
    verification assertion, reflection analysis, replanning decision, or mutation.
    It only sequences existing public seams through the G2.4.1 state machine.
    """

    def __init__(
        self,
        *,
        state_machine: GovernedExecutionStateMachine,
        context_factory: IterationContextFactory,
        decision_request_factory: GovernedDecisionRequestFactory,
        workflow: GovernedDecisionMutationWorkflow,
        verifier: DeterministicVerifier,
        verification_specification_factory: VerificationSpecificationFactory,
        reflection_runtime: ReflectionRuntime,
        adaptive_planner: AdaptivePlanner,
        audit_observer: GovernedExecutionAuditObserver | None = None,
    ) -> None:
        self._state_machine = state_machine
        self._context_factory = context_factory
        self._decision_request_factory = decision_request_factory
        self._workflow = workflow
        self._verifier = verifier
        self._verification_specification_factory = verification_specification_factory
        self._reflection_runtime = reflection_runtime
        self._adaptive_planner = adaptive_planner
        self._audit_observer = audit_observer

    def execute(self, request: GovernedExecutionRequest) -> GovernedExecutionResult:
        """Execute at most two serial governed iterations for one explicit workspace."""
        if not isinstance(request, GovernedExecutionRequest):
            raise TypeError("request must be a GovernedExecutionRequest")
        workspace_key = str(request.workspace_root.resolve())
        if self._audit_observer is not None:
            try:
                self._audit_observer.preflight(request.workspace_root)
            except Exception as error:
                raise AuditPersistenceRequiredError(
                    "required audit observation could not be prepared before execution"
                ) from error
        with self._workspace_lock(workspace_key):
            context = GovernedExecutionContext(
                execution_id=request.execution_id,
                run_id=request.run_id,
                goal=request.goal,
                budget=request.budget,
            )
            artifacts: list[IterationContextArtifact] = []
            previous_authority: FreshIterationAuthority | None = None
            replanning_input: ReplanningInput | None = None

            for iteration in (1, 2):
                context, state = self._execute_iteration(
                    request,
                    context,
                    iteration=iteration,
                    previous_authority=previous_authority,
                )
                if state is not None:
                    artifacts.append(state.context_bundle.artifact)
                if context.state.is_terminal:
                    return self._terminal_result(context, artifacts)
                assert state is not None
                assert state.workflow_result is not None
                assert state.workflow_result.receipt is not None
                assert state.workflow_result.proposal is not None
                assert state.verification is not None
                receipt = state.workflow_result.receipt
                proposal = state.workflow_result.proposal
                objective = ObjectiveCompletionPolicy.assess(receipt, state.verification)

                if objective.status is ObjectiveStatus.SATISFIED:
                    if iteration == 2:
                        self._validate_complete_iteration(replanning_input, state)
                    context = self._transition(
                        context,
                        GovernedExecutionState.COMPLETED,
                        stop_reason=GovernedExecutionStopReason.SUCCESS,
                        evidence=(state.verification.evidence_ref,),
                    )
                    return self._terminal_result(context, artifacts)

                if iteration == 2:
                    self._validate_complete_iteration(replanning_input, state)
                    context = self._transition(
                        context,
                        GovernedExecutionState.FAILED,
                        stop_reason=GovernedExecutionStopReason.VERIFICATION_FAILED,
                        evidence=(state.verification.evidence_ref,),
                    )
                    return self._terminal_result(context, artifacts)

                context, replanning_input = self._recover(
                    request,
                    context,
                    state=state,
                    objective=objective,
                )
                if context.state.is_terminal:
                    return self._terminal_result(context, artifacts)
                previous_authority = state.authority
                if previous_authority is None:
                    context = self._transition(
                        context,
                        GovernedExecutionState.FAILED,
                        stop_reason=GovernedExecutionStopReason.UNRECOVERABLE,
                    )
                    return self._terminal_result(context, artifacts)

            raise GovernedExecutionRuntimeError("serial runtime exceeded the fixed two-iteration bound")

    def _terminal_result(
        self,
        context: GovernedExecutionContext,
        artifacts: list[IterationContextArtifact],
    ) -> GovernedExecutionResult:
        """Return a terminal result only after optional required audit recording succeeds."""
        result = GovernedExecutionResult(context=context, iteration_artifacts=tuple(artifacts))
        if self._audit_observer is not None:
            try:
                self._audit_observer.record_terminal_result(result)
            except Exception as error:
                raise AuditPersistenceRequiredError(
                    "terminal execution result could not be persisted to the required audit store"
                ) from error
        return result

    def _execute_iteration(
        self,
        request: GovernedExecutionRequest,
        context: GovernedExecutionContext,
        *,
        iteration: int,
        previous_authority: FreshIterationAuthority | None,
    ) -> tuple[GovernedExecutionContext, _IterationState | None]:
        context = self._transition(context, GovernedExecutionState.CONTEXT_ASSEMBLING)
        if context.state.is_terminal:
            raise GovernedExecutionRuntimeError("iteration budget exhausted before context assembly")
        assembly_request = ContextAssemblyRequest(
            goal=request.goal,
            repository_path=request.repository_path,
            available_capabilities=request.available_capability_ids,
            known_constraints=request.known_constraints,
        )
        try:
            bundle = self._context_factory.assemble(assembly_request, iteration=iteration)
            decision_request = self._decision_request_factory.build(request, bundle.context)
        except Exception:
            return (
                self._transition(
                    context,
                    GovernedExecutionState.FAILED,
                    stop_reason=GovernedExecutionStopReason.UNRECOVERABLE,
                ),
                None,
            )
        self._validate_iteration_bindings(request, bundle, decision_request, iteration)
        context = self._transition(
            context,
            GovernedExecutionState.PLANNING,
            evidence=(
                ExecutionEvidenceRef(
                    kind=ExecutionEvidenceKind.PLAN,
                    reference_id=bundle.artifact.artifact_id,
                    metadata={"context_fingerprint": bundle.artifact.context_fingerprint},
                ),
            ),
        )
        state = _IterationState(context_bundle=bundle, request=decision_request)
        observer = _LifecycleObserver(
            runtime=self,
            context=context,
            state=state,
            previous_authority=previous_authority,
        )
        try:
            workflow_result = self._workflow.execute(
                decision_request,
                run_id=request.run_id,
                trusted_state=bundle.trusted_state,
                observer=observer,
            )
        except GovernedWorkflowLifecycleRefused:
            return self._transition(
                observer.context,
                GovernedExecutionState.FAILED,
                stop_reason=GovernedExecutionStopReason.UNRECOVERABLE,
            ), state
        state.workflow_result = workflow_result
        context = observer.context
        if not workflow_result.success or workflow_result.proposal is None or workflow_result.receipt is None:
            return self._transition(
                context,
                GovernedExecutionState.FAILED,
                stop_reason=_stop_reason_for_workflow_failure(workflow_result.failure_stage),
            ), state
        context = self._transition(
            context,
            GovernedExecutionState.VERIFYING,
            evidence=(
                ExecutionEvidenceRef(
                    kind=ExecutionEvidenceKind.MUTATION_RECEIPT,
                    reference_id=workflow_result.receipt.mutation_id,
                ),
            ),
        )
        specification = self._verification_specification_factory.build(workflow_result.proposal)
        verification_request = VerificationRequest(
            run_id=request.run_id,
            receipt=workflow_result.receipt,
            specification=specification,
            execution_context=context,
        )
        state.verification = self._verifier.verify(verification_request)
        return context, state

    def _recover(
        self,
        request: GovernedExecutionRequest,
        context: GovernedExecutionContext,
        *,
        state: _IterationState,
        objective: ObjectiveAssessment,
    ) -> tuple[GovernedExecutionContext, ReplanningInput | None]:
        assert state.workflow_result is not None
        assert state.workflow_result.proposal is not None
        assert state.workflow_result.receipt is not None
        assert state.verification is not None
        context = self._transition(
            context,
            GovernedExecutionState.REFLECTING,
            evidence=(state.verification.evidence_ref,),
        )
        try:
            reflection_input = GovernedReflectionInput(
                execution_context=context,
                receipt=state.workflow_result.receipt,
                verification=state.verification,
                objective=objective,
                context_artifact_id=state.context_bundle.artifact.artifact_id,
                context_fingerprint=state.context_bundle.artifact.context_fingerprint,
                decision_id=_decision_id(state.workflow_result),
                proposal_id=state.workflow_result.proposal.proposal_id,
                authorization_id=state.workflow_result.receipt.authorization_id or "",
                policy_version=state.context_bundle.artifact.policy_version,
            )
            adapter = GovernedReflectionAdapter()
            reflection = adapter.reflect(self._reflection_runtime, reflection_input)
            memory = adapter.memory_evidence(reflection)
        except Exception:
            return (
                self._transition(
                    context,
                    GovernedExecutionState.FAILED,
                    stop_reason=GovernedExecutionStopReason.UNRECOVERABLE,
                ),
                None,
            )
        context = self._transition(
            context,
            GovernedExecutionState.REPLANNING,
            evidence=(
                reflection.evidence_ref,
                ExecutionEvidenceRef(
                    kind=ExecutionEvidenceKind.MEMORY,
                    reference_id=memory.reflection_id,
                ),
            ),
        )
        replanning_input = ReplanningInput(
            execution_context=context,
            reflection=reflection,
            memory=memory,
            previous_decision_id=_decision_id(state.workflow_result),
            previous_proposal_id=state.workflow_result.proposal.proposal_id,
            previous_authorization_id=state.workflow_result.receipt.authorization_id or "",
            previous_context_artifact_id=state.context_bundle.artifact.artifact_id,
        )
        try:
            planning_decision_id = self._adaptive_planning_decision(request, memory)
            outcome = ReplanningPolicy.decide(
                replanning_input,
                planning_decision_id=planning_decision_id,
            )
        except Exception:
            return (
                self._transition(
                    context,
                    GovernedExecutionState.FAILED,
                    stop_reason=GovernedExecutionStopReason.UNRECOVERABLE,
                ),
                None,
            )
        if outcome.action is not ReplanningAction.CONTINUE_WITH_FRESH_DECISION:
            return (
                self._transition(
                    context,
                    GovernedExecutionState.FAILED,
                    stop_reason=GovernedExecutionStopReason.VERIFICATION_FAILED,
                    evidence=(outcome.evidence_ref,),
                ),
                replanning_input,
            )
        return context, replanning_input

    def _adaptive_planning_decision(
        self,
        request: GovernedExecutionRequest,
        memory: GovernedMemoryEvidence,
    ) -> str:
        base_plan = Plan(
            steps=(
                PlanStep(
                    name="Governed mutation",
                    capability_id=request.mutation_intent_policy.capability_id,
                ),
            )
        )
        _, decision = self._adaptive_planner.plan(
            AdaptivePlanningContext(
                goal=request.goal,
                experiences=(memory.experience,),
                rules=request.recovery_rules,
            ),
            base_plan,
        )
        return decision.id

    def _validate_complete_iteration(
        self,
        input: ReplanningInput | None,
        state: _IterationState,
    ) -> None:
        if input is None or state.workflow_result is None or state.workflow_result.proposal is None:
            raise GovernedExecutionRuntimeError("second iteration lacks recovery evidence")
        if state.workflow_result.receipt is None or state.verification is None or state.authority is None:
            raise GovernedExecutionRuntimeError("second iteration lacks complete freshness artifacts")
        ReplanningPolicy.validate_fresh_iteration(
            input,
            FreshIterationArtifacts(
                context_artifact_id=state.authority.context_artifact_id,
                decision_request_id=state.authority.decision_request_id,
                decision_id=state.authority.decision_id,
                proposal_id=state.authority.proposal_id,
                authorization_id=state.authority.authorization_id,
                receipt_id=state.workflow_result.receipt.mutation_id,
                verification_id=state.verification.verification_id,
                context_fingerprint=state.authority.context_fingerprint,
            ),
        )

    @staticmethod
    def _validate_iteration_bindings(
        request: GovernedExecutionRequest,
        bundle: IterationContextBundle,
        decision_request: EngineeringDecisionRequest,
        iteration: int,
    ) -> None:
        if not isinstance(bundle, IterationContextBundle):
            raise TypeError("context factory must return IterationContextBundle")
        if decision_request.policy != request.gateway_policy:
            raise GovernedExecutionRuntimeError("decision request must retain the approved one-attempt gateway policy")
        metadata = decision_request.context.truncation_metadata
        if metadata.get("snapshot_fingerprint") != bundle.artifact.repository_snapshot_fingerprint:
            raise GovernedExecutionRuntimeError("decision request snapshot binding does not match fresh context artifact")
        if metadata.get("context_fingerprint") != bundle.artifact.context_fingerprint:
            raise GovernedExecutionRuntimeError("decision request context binding does not match fresh context artifact")
        if decision_request.request_id == "":
            raise GovernedExecutionRuntimeError("decision request identity cannot be empty")
        if iteration < 1:
            raise GovernedExecutionRuntimeError("iteration must be positive")

    def _transition(
        self,
        context: GovernedExecutionContext,
        target: GovernedExecutionState,
        *,
        evidence: tuple[ExecutionEvidenceRef, ...] = (),
        stop_reason: GovernedExecutionStopReason | None = None,
    ) -> GovernedExecutionContext:
        return self._state_machine.transition_or_raise(
            context,
            target,
            evidence=evidence,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _workspace_lock(workspace_key: str) -> threading.Lock:
        with _workspace_locks_guard:
            return _workspace_locks.setdefault(workspace_key, threading.Lock())


@dataclass(slots=True)
class _LifecycleObserver(GovernedMutationLifecycleObserver):
    """Runtime-owned observer that obtains G2.4.1 approval before each workflow effect."""

    runtime: GovernedEngineeringExecutionRuntime
    context: GovernedExecutionContext
    state: _IterationState
    previous_authority: FreshIterationAuthority | None

    def before_deciding(self, request: EngineeringDecisionRequest) -> None:
        self.context = self.runtime._transition(self.context, GovernedExecutionState.DECIDING)

    def before_proposing(
        self,
        request: EngineeringDecisionRequest,
        result: object,
    ) -> None:
        decision_id = _decision_id_from_result(result)
        self.state.decision_id = decision_id
        self.context = self.runtime._transition(
            self.context,
            GovernedExecutionState.PROPOSING,
            evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.DECISION, reference_id=decision_id),),
        )

    def before_authorizing(self, proposal: object) -> None:
        proposal_id = getattr(proposal, "proposal_id", "")
        self.context = self.runtime._transition(
            self.context,
            GovernedExecutionState.AUTHORIZING,
            evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.PROPOSAL, reference_id=proposal_id),),
        )

    def before_mutating(self, proposal: object, authorization: object) -> None:
        authority = FreshIterationAuthority(
            execution_id=self.context.execution_id,
            iteration=self.context.iteration,
            context_artifact_id=self.state.context_bundle.artifact.artifact_id,
            context_fingerprint=self.state.context_bundle.artifact.context_fingerprint,
            decision_request_id=self.state.request.request_id,
            decision_id=self.state.decision_id,
            proposal_id=getattr(proposal, "proposal_id", ""),
            authorization_id=getattr(authorization, "authorization_id", ""),
        )
        if self.previous_authority is not None:
            validate_fresh_authority(self.previous_authority, authority)
        self.state.authority = authority
        self.context = self.runtime._transition(
            self.context,
            GovernedExecutionState.MUTATING,
            evidence=(
                ExecutionEvidenceRef(
                    kind=ExecutionEvidenceKind.AUTHORIZATION,
                    reference_id=authority.authorization_id,
                ),
            ),
        )


def _decision_id(result: GovernedDecisionMutationResult) -> str:
    return _decision_id_from_result(result.gateway_result)


def _decision_id_from_result(result: object) -> str:
    decision = getattr(result, "decision", None)
    value = getattr(decision, "digest", "")
    if not isinstance(value, str) or not value:
        raise GovernedExecutionRuntimeError("successful workflow result requires a decision identity")
    return value


def _stop_reason_for_workflow_failure(
    stage: GovernedMutationFailureStage | None,
) -> GovernedExecutionStopReason:
    if stage in {GovernedMutationFailureStage.DECISION_REJECTED, GovernedMutationFailureStage.POLICY_REJECTED}:
        return GovernedExecutionStopReason.POLICY_REJECTED
    if stage is GovernedMutationFailureStage.AUTHORIZATION_REJECTED:
        return GovernedExecutionStopReason.AUTHORIZATION_FAILED
    if stage in {
        GovernedMutationFailureStage.PROVIDER_TIMEOUT,
        GovernedMutationFailureStage.PROVIDER_FAILURE,
        GovernedMutationFailureStage.SCHEMA_FAILURE,
    }:
        return GovernedExecutionStopReason.PROVIDER_FAILED
    return GovernedExecutionStopReason.UNRECOVERABLE


__all__ = [
    "GovernedDecisionRequestFactory",
    "GovernedEngineeringExecutionRuntime",
    "GovernedExecutionRuntimeError",
    "IterationContextBundle",
    "IterationContextFactory",
]
