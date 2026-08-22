"""Deterministic disposable G2.4.4 runtime fixture support for tests and EBS-018."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from eag.adaptive import AdaptivePlanner
from eag.chief.intelligence.gateway import (
    DecisionToChangeProposalTranslator,
    EngineeringContext,
    EngineeringDecision,
    EngineeringDecisionRequest,
    EngineeringDecisionResult,
    EngineeringRisk,
    GatewayTrace,
    MutationIntent,
    MutationIntentPolicy,
    ProposedPlanStep,
    RiskSeverity,
    TrustedWorkspaceState,
)
from eag.chief.intelligence.gateway.context import ContextAssemblyRequest
from eag.chief.intelligence.gateway.mutation_workflow import GovernedDecisionMutationWorkflow
from eag.context import ContextSecurityPolicy
from eag.events import EventBus
from eag.governed_execution import (
    DeterministicVerifier,
    ExecutionBudget,
    GovernedExecutionStateMachine,
    VerificationCheck,
    VerificationSpecification,
)
from eag.governed_runtime import (
    GovernedEngineeringExecutionRuntime,
    GovernedExecutionRequest,
    IterationContextArtifact,
    IterationContextBundle,
)
from eag.mutation import (
    GovernedMutationRuntime,
    MutationAuthorizer,
    MutationPolicySettings,
    MutationPolicyValidator,
)
from eag.reflection.models import ReflectionReport
from eag.reflection.runtime import ReflectionRuntime


@dataclass
class ScriptedGateway:
    contents: tuple[str, ...]
    calls: int = 0

    def decide(self, request: EngineeringDecisionRequest) -> EngineeringDecisionResult:
        content = self.contents[self.calls]
        self.calls += 1
        intent = MutationIntent(
            intent_id=f"intent-{self.calls}",
            step_id="mutate-article",
            target_path="article.py",
            operation="modify_file",
            proposed_content=content,
            rationale="Controlled fixture mutation.",
            grounding_references=("file:article.py",),
        )
        decision = EngineeringDecision(
            interpreted_goal=request.goal,
            assumptions=("fixture exists",),
            proposed_approach="one governed mutation",
            ordered_plan=(
                ProposedPlanStep(
                    step_id="mutate-article",
                    title="Mutate article fixture",
                    capability_id="governed_mutation",
                    expected_evidence=("receipt",),
                ),
            ),
            required_capabilities=("governed_mutation",),
            risks=(
                EngineeringRisk(
                    description="Fixture may be stale.",
                    severity=RiskSeverity.LOW,
                    mitigation="Use governed precondition.",
                ),
            ),
            confidence=0.9,
            grounding_references=("file:article.py",),
            mutation_intents=(intent,),
        )
        return EngineeringDecisionResult(
            success=True,
            decision=decision,
            trace=GatewayTrace(trace_id=f"trace-{self.calls}", request_id=request.request_id),
        )


@dataclass
class ContextFactory:
    workspace: Path
    calls: int = 0

    def assemble(
        self,
        request: ContextAssemblyRequest,
        *,
        iteration: int,
    ) -> IterationContextBundle:
        del request
        self.calls += 1
        snapshot = f"snapshot-{iteration}"
        context_fingerprint = f"context-{iteration}"
        artifact = IterationContextArtifact(
            artifact_id=f"artifact-{iteration}",
            repository_snapshot_fingerprint=snapshot,
            context_fingerprint=context_fingerprint,
            policy_version="mutation-policy-1",
        )
        context = EngineeringContext(
            repository_identity="fixture",
            repository_summary="deterministic fixture",
            truncation_metadata={
                "snapshot_fingerprint": snapshot,
                "context_fingerprint": context_fingerprint,
            },
        )
        return IterationContextBundle(
            context=context,
            artifact=artifact,
            trusted_state=TrustedWorkspaceState(
                workspace_root=self.workspace,
                repository_snapshot_fingerprint=snapshot,
                context_fingerprint=context_fingerprint,
                policy_version="mutation-policy-1",
                sensitivity_policy=ContextSecurityPolicy(),
            ),
        )


@dataclass
class RequestFactory:
    calls: int = 0

    def build(
        self,
        request: GovernedExecutionRequest,
        context: EngineeringContext,
    ) -> EngineeringDecisionRequest:
        self.calls += 1
        return EngineeringDecisionRequest(
            goal=request.goal,
            context=context,
            allowed_capability_ids=request.available_capability_ids,
            mutation_intent_policy=request.mutation_intent_policy,
            policy=request.gateway_policy,
        )


@dataclass
class FirstFailureVerificationFactory:
    fail_first: bool
    calls: int = 0

    def build(self, proposal) -> VerificationSpecification:
        self.calls += 1
        expected = proposal.content_fingerprint
        if self.fail_first and self.calls == 1:
            expected = hashlib.sha256(b"wrong-content").hexdigest()
        return VerificationSpecification(
            specification_id=f"specification-{self.calls}",
            target_path=proposal.target_path,
            check=VerificationCheck.EXPECTED_FINGERPRINT,
            expected_fingerprint=expected,
        )


class ReflectionEngine:
    def reflect(self, context):
        return ReflectionReport(run_id=context.run_id)


def runtime_fixture(
    workspace: Path,
    *,
    contents: tuple[str, str],
    fail_first_only: bool,
) -> tuple[
    GovernedEngineeringExecutionRuntime,
    ScriptedGateway,
    ContextFactory,
    RequestFactory,
    FirstFailureVerificationFactory,
]:
    gateway = ScriptedGateway(contents=contents)
    policy = MutationPolicyValidator(settings=MutationPolicySettings())
    mutation_runtime = GovernedMutationRuntime(
        workspace_root=workspace,
        policy=policy,
        authorizer=MutationAuthorizer(policy_version="mutation-policy-1"),
        event_bus=EventBus(),
    )
    workflow = GovernedDecisionMutationWorkflow(
        gateway=gateway,
        translator=DecisionToChangeProposalTranslator(),
        mutation_runtime=mutation_runtime,
    )
    context_factory = ContextFactory(workspace)
    request_factory = RequestFactory()
    verification_factory = FirstFailureVerificationFactory(fail_first=fail_first_only)
    runtime = GovernedEngineeringExecutionRuntime(
        state_machine=GovernedExecutionStateMachine(EventBus()),
        context_factory=context_factory,
        decision_request_factory=request_factory,
        workflow=workflow,
        verifier=DeterministicVerifier(workspace_root=workspace),
        verification_specification_factory=verification_factory,
        reflection_runtime=ReflectionRuntime(ReflectionEngine(), EventBus()),
        adaptive_planner=AdaptivePlanner(),
    )
    return runtime, gateway, context_factory, request_factory, verification_factory


def governed_request(workspace: Path) -> GovernedExecutionRequest:
    return GovernedExecutionRequest(
        goal="Update the controlled article fixture.",
        workspace_root=workspace,
        repository_path=workspace,
        available_capability_ids=("governed_mutation",),
        mutation_intent_policy=MutationIntentPolicy(),
        execution_id="execution-1",
        run_id="run-1",
        budget=ExecutionBudget(max_iterations=2, max_mutations=2, max_verifications=2),
    )
