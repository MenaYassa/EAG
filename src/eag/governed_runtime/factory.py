"""Explicit opt-in construction for the G2.4.4 serial governed runtime."""

from __future__ import annotations

from eag.adaptive import AdaptivePlanner
from eag.chief.intelligence.gateway.mutation_workflow import GovernedDecisionMutationWorkflow
from eag.governed_audit.recorder import GovernedExecutionAuditObserver
from eag.governed_execution.state_machine import GovernedExecutionStateMachine
from eag.governed_execution.verification import DeterministicVerifier
from eag.governed_runtime.models import VerificationSpecificationFactory
from eag.governed_runtime.runtime import (
    GovernedDecisionRequestFactory,
    GovernedEngineeringExecutionRuntime,
    IterationContextFactory,
)
from eag.reflection.runtime import ReflectionRuntime


def create_governed_engineering_execution_runtime(
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
) -> GovernedEngineeringExecutionRuntime:
    """Return the explicit G2.4.4 composition; no legacy factory calls this function."""
    return GovernedEngineeringExecutionRuntime(
        state_machine=state_machine,
        context_factory=context_factory,
        decision_request_factory=decision_request_factory,
        workflow=workflow,
        verifier=verifier,
        verification_specification_factory=verification_specification_factory,
        reflection_runtime=reflection_runtime,
        adaptive_planner=adaptive_planner,
        audit_observer=audit_observer,
    )


__all__ = ["create_governed_engineering_execution_runtime"]
