"""Immutable public contracts for the opt-in G2.4.4 serial composition."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from eag.adaptive.models import PlanningRule
from eag.chief.intelligence.gateway.models import GatewayPolicy, MutationIntentPolicy
from eag.governed_execution.enums import GovernedExecutionState
from eag.governed_execution.models import ExecutionBudget, GovernedExecutionContext
from eag.governed_execution.verification import VerificationCheck, VerificationSpecification
from eag.mutation.models import ChangeProposal

GOVERNED_RUNTIME_CONTRACT_VERSION = "1.0"


class GovernedRuntimeContractError(ValueError):
    """Raised when serial-runtime inputs are incomplete or unsafe."""


@dataclass(frozen=True, slots=True, kw_only=True)
class IterationContextArtifact:
    """Trusted identity for one freshly assembled execution context."""

    artifact_id: str
    repository_snapshot_fingerprint: str
    context_fingerprint: str
    policy_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "artifact_id",
            "repository_snapshot_fingerprint",
            "context_fingerprint",
            "policy_version",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise GovernedRuntimeContractError(f"{field_name} cannot be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionRequest:
    """Explicit caller-controlled request for one bounded serial execution."""

    goal: str
    workspace_root: Path
    repository_path: Path
    available_capability_ids: tuple[str, ...]
    mutation_intent_policy: MutationIntentPolicy
    known_constraints: tuple[str, ...] = ()
    recovery_rules: tuple[PlanningRule, ...] = ()
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    budget: ExecutionBudget = field(
        default_factory=lambda: ExecutionBudget(
            max_iterations=2,
            max_mutations=2,
            max_verifications=2,
        )
    )
    gateway_policy: GatewayPolicy = field(
        default_factory=lambda: GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            max_schema_repair_attempts=0,
        )
    )
    contract_version: str = GOVERNED_RUNTIME_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise GovernedRuntimeContractError("goal cannot be empty")
        for field_name in ("execution_id", "run_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise GovernedRuntimeContractError(f"{field_name} cannot be empty")
        if not isinstance(self.workspace_root, Path) or not isinstance(self.repository_path, Path):
            raise TypeError("workspace_root and repository_path must be Path values")
        if self.workspace_root.resolve() != self.repository_path.resolve():
            raise GovernedRuntimeContractError("workspace_root and repository_path must resolve to the same root")
        if not self.available_capability_ids or any(
            not isinstance(item, str) or not item.strip() for item in self.available_capability_ids
        ):
            raise GovernedRuntimeContractError("available_capability_ids cannot be empty")
        if len(set(self.available_capability_ids)) != len(self.available_capability_ids):
            raise GovernedRuntimeContractError("available_capability_ids must be unique")
        if not isinstance(self.mutation_intent_policy, MutationIntentPolicy):
            raise TypeError("mutation_intent_policy must be a MutationIntentPolicy")
        if self.mutation_intent_policy.capability_id not in self.available_capability_ids:
            raise GovernedRuntimeContractError("mutation capability must be allowlisted")
        if any(not isinstance(rule, PlanningRule) for rule in self.recovery_rules):
            raise TypeError("recovery_rules must contain PlanningRule values")
        if not isinstance(self.budget, ExecutionBudget):
            raise TypeError("budget must be an ExecutionBudget")
        if (
            self.budget.max_iterations != 2
            or self.budget.max_mutations != 2
            or self.budget.max_verifications != 2
        ):
            raise GovernedRuntimeContractError("G2.4.4 requires two iteration, mutation, and verification capacities")
        if not isinstance(self.gateway_policy, GatewayPolicy):
            raise TypeError("gateway_policy must be a GatewayPolicy")
        if (
            self.gateway_policy.max_attempts != 1
            or self.gateway_policy.allow_fallback
            or self.gateway_policy.max_schema_repair_attempts != 0
        ):
            raise GovernedRuntimeContractError("G2.4.4 requires one attempt, no fallback, and no schema repair")
        if self.contract_version != GOVERNED_RUNTIME_CONTRACT_VERSION:
            raise GovernedRuntimeContractError("unsupported governed runtime contract version")


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionResult:
    """Redacted terminal runtime output; state-machine context remains authoritative."""

    context: GovernedExecutionContext
    iteration_artifacts: tuple[IterationContextArtifact, ...]
    contract_version: str = GOVERNED_RUNTIME_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.context, GovernedExecutionContext):
            raise TypeError("context must be a GovernedExecutionContext")
        if not self.context.state.is_terminal:
            raise GovernedRuntimeContractError("result requires a terminal context")
        if any(not isinstance(item, IterationContextArtifact) for item in self.iteration_artifacts):
            raise TypeError("iteration_artifacts must contain IterationContextArtifact values")
        if len(self.iteration_artifacts) != self.context.iteration:
            raise GovernedRuntimeContractError("iteration artifacts must match context iteration")
        if self.contract_version != GOVERNED_RUNTIME_CONTRACT_VERSION:
            raise GovernedRuntimeContractError("unsupported governed runtime contract version")

    @property
    def succeeded(self) -> bool:
        return self.context.state is GovernedExecutionState.COMPLETED


class VerificationSpecificationFactory(Protocol):
    """Build one trusted bounded verification specification from a translated proposal."""

    def build(self, proposal: ChangeProposal) -> VerificationSpecification: ...


@dataclass(frozen=True, slots=True)
class ProposalPostconditionVerificationFactory:
    """Map the existing trusted proposal postcondition to one fingerprint assertion."""

    max_bytes: int = 64_000

    def build(self, proposal: ChangeProposal) -> VerificationSpecification:
        if not isinstance(proposal, ChangeProposal):
            raise TypeError("proposal must be a ChangeProposal")
        expected_fingerprint = proposal.expected_postcondition.expected_fingerprint
        if expected_fingerprint is None:
            raise GovernedRuntimeContractError("proposal requires a trusted expected postcondition fingerprint")
        return VerificationSpecification(
            specification_id=f"verification-specification:{proposal.proposal_id}",
            target_path=proposal.target_path,
            check=VerificationCheck.EXPECTED_FINGERPRINT,
            expected_fingerprint=expected_fingerprint,
            max_bytes=self.max_bytes,
        )


__all__ = [
    "GOVERNED_RUNTIME_CONTRACT_VERSION",
    "GovernedExecutionRequest",
    "GovernedExecutionResult",
    "GovernedRuntimeContractError",
    "IterationContextArtifact",
    "ProposalPostconditionVerificationFactory",
    "VerificationSpecificationFactory",
]
