"""Immutable domain models for governed engineering decisions."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from eag.chief.intelligence.enums import RoutingPolicy
from eag.chief.intelligence.gateway.errors import GatewayError, PolicyViolation
from eag.chief.intelligence.models import AIRequirements, SelectionDecision

ENGINEERING_DECISION_SCHEMA_VERSION = "1.0"


def _freeze_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    """Copy and freeze a mapping accepted by a public domain model."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


class RiskSeverity(StrEnum):
    """Severity used for an explicitly disclosed engineering risk."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringContext:
    """Bounded factual context supplied to a decision request, not a free-form prompt."""

    repository_identity: str = ""
    repository_summary: str = ""
    source_findings: tuple[str, ...] = ()
    relevant_symbols: tuple[str, ...] = ()
    known_constraints: tuple[str, ...] = ()
    available_capabilities: tuple[str, ...] = ()
    prior_evidence: tuple[str, ...] = ()
    provenance: Mapping[str, str] = field(default_factory=dict, hash=False)
    truncation_metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", _freeze_mapping(self.provenance, "provenance"))
        object.__setattr__(
            self,
            "truncation_metadata",
            _freeze_mapping(self.truncation_metadata, "truncation_metadata"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayPolicy:
    """Non-model-controlled limits for a single governed request."""

    max_attempts: int = 2
    timeout_ms: int = 30_000
    max_total_tokens: int = 8_000
    max_estimated_cost: float = 1.0
    max_schema_repair_attempts: int = 1
    allow_fallback: bool = True
    redact_provider_content: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.timeout_ms < 1:
            raise ValueError("timeout_ms must be positive")
        if self.max_total_tokens < 1:
            raise ValueError("max_total_tokens must be positive")
        if self.max_estimated_cost < 0:
            raise ValueError("max_estimated_cost cannot be negative")
        if self.max_schema_repair_attempts < 0:
            raise ValueError("max_schema_repair_attempts cannot be negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringDecisionRequest:
    """A policy-bounded request for an advisory engineering decision."""

    goal: str
    context: EngineeringContext
    allowed_capability_ids: tuple[str, ...]
    requirements: AIRequirements = field(
        default_factory=lambda: AIRequirements(requires_structured_output=True)
    )
    routing_policy: RoutingPolicy = RoutingPolicy.BALANCED
    policy: GatewayPolicy = field(default_factory=GatewayPolicy)
    schema_version: str = ENGINEERING_DECISION_SCHEMA_VERSION
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise ValueError("goal cannot be empty")
        if not isinstance(self.context, EngineeringContext):
            raise TypeError("context must be EngineeringContext")
        if not self.allowed_capability_ids:
            raise ValueError("allowed_capability_ids cannot be empty")
        if any(not capability_id.strip() for capability_id in self.allowed_capability_ids):
            raise ValueError("allowed_capability_ids cannot contain empty values")
        if len(set(self.allowed_capability_ids)) != len(self.allowed_capability_ids):
            raise ValueError("allowed_capability_ids must be unique")
        if not isinstance(self.requirements, AIRequirements):
            raise TypeError("requirements must be AIRequirements")
        if not self.requirements.requires_structured_output:
            raise ValueError("governed requests must require structured output")
        if not isinstance(self.policy, GatewayPolicy):
            raise TypeError("policy must be GatewayPolicy")
        if self.schema_version != ENGINEERING_DECISION_SCHEMA_VERSION:
            raise ValueError("unsupported engineering-decision schema version")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProposedPlanStep:
    """A non-executable proposed step awaiting deterministic translation and later governance."""

    step_id: str
    title: str
    capability_id: str
    dependencies: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict, hash=False)
    expected_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.step_id.strip():
            raise ValueError("step_id cannot be empty")
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if not self.capability_id.strip():
            raise ValueError("capability_id cannot be empty")
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters, "parameters"))


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringRisk:
    """A risk and mitigation explicitly disclosed by the decision."""

    description: str
    severity: RiskSeverity
    mitigation: str

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("risk description cannot be empty")
        if not self.mitigation.strip():
            raise ValueError("risk mitigation cannot be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringDecision:
    """A validated, advisory decision that is intentionally not an executable plan."""

    interpreted_goal: str
    assumptions: tuple[str, ...]
    proposed_approach: str
    ordered_plan: tuple[ProposedPlanStep, ...]
    required_capabilities: tuple[str, ...]
    risks: tuple[EngineeringRisk, ...]
    confidence: float
    grounding_references: tuple[str, ...] = ()
    schema_version: str = ENGINEERING_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.interpreted_goal.strip():
            raise ValueError("interpreted_goal cannot be empty")
        if not self.proposed_approach.strip():
            raise ValueError("proposed_approach cannot be empty")
        if not self.ordered_plan:
            raise ValueError("ordered_plan cannot be empty")
        if not self.required_capabilities:
            raise ValueError("required_capabilities cannot be empty")
        if not self.risks:
            raise ValueError("risks cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if any(not reference.strip() for reference in self.grounding_references):
            raise ValueError("grounding_references cannot contain empty values")
        if len(set(self.grounding_references)) != len(self.grounding_references):
            raise ValueError("grounding_references must be unique")
        if self.schema_version != ENGINEERING_DECISION_SCHEMA_VERSION:
            raise ValueError("unsupported engineering-decision schema version")


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayUsage:
    """Redacted provider usage and cost data carried to the decision boundary."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayTrace:
    """A redacted summary; raw prompts and raw provider content are never retained here."""

    trace_id: str
    request_id: str
    attempts: int = 0
    fallback_used: bool = False
    event_types: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringDecisionResult:
    """The only public result from the gateway: a validated decision or a safe failure."""

    success: bool
    trace: GatewayTrace
    decision: EngineeringDecision | None = None
    error: GatewayError | None = None
    selection: SelectionDecision | None = None
    usage: GatewayUsage = field(default_factory=GatewayUsage)
    policy_violation: PolicyViolation | None = None

    def __post_init__(self) -> None:
        if self.success and self.decision is None:
            raise ValueError("successful result requires a decision")
        if self.success and self.error is not None:
            raise ValueError("successful result cannot contain an error")
        if not self.success and self.error is None:
            raise ValueError("failed result requires a GatewayError")
        if self.success and self.policy_violation is not None:
            raise ValueError("successful result cannot contain a policy violation")
