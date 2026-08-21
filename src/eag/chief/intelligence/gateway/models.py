"""Immutable domain models for governed engineering decisions."""

from __future__ import annotations

import hashlib
import json
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
MUTATION_INTENT_SCHEMA_VERSION = "1.0"


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
class PreservationRequirement:
    """Trusted immutable leading content that a controlled replacement must retain verbatim.

    The requirement is selected by trusted composition, never by a provider. It is intentionally
    limited to a prefix in this slice: the deterministic system can reject an omission but cannot
    invent, merge, or relocate source content.
    """

    requirement_id: str
    required_prefix: str

    def __post_init__(self) -> None:
        if not self.requirement_id.strip():
            raise ValueError("preservation requirement_id cannot be empty")
        if not self.required_prefix:
            raise ValueError("preservation required_prefix cannot be empty")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.required_prefix.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationIntentPolicy:
    """Trusted opt-in bounds for one provider-declared mutation intent."""

    capability_id: str = "governed_mutation"
    allowed_operations: tuple[str, ...] = ("create_file", "modify_file")
    max_content_bytes: int = 64_000
    preservation_requirements: tuple[PreservationRequirement, ...] = ()
    schema_version: str = MUTATION_INTENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.capability_id.strip():
            raise ValueError("mutation capability_id cannot be empty")
        if not self.allowed_operations or any(not operation.strip() for operation in self.allowed_operations):
            raise ValueError("allowed_operations cannot be empty")
        if len(set(self.allowed_operations)) != len(self.allowed_operations):
            raise ValueError("allowed_operations must be unique")
        if self.max_content_bytes <= 0:
            raise ValueError("max_content_bytes must be positive")
        if any(
            not isinstance(requirement, PreservationRequirement)
            for requirement in self.preservation_requirements
        ):
            raise TypeError("preservation_requirements must contain PreservationRequirement values")
        requirement_ids = tuple(
            requirement.requirement_id for requirement in self.preservation_requirements
        )
        if len(set(requirement_ids)) != len(requirement_ids):
            raise ValueError("preservation requirement IDs must be unique")
        if self.schema_version != MUTATION_INTENT_SCHEMA_VERSION:
            raise ValueError("unsupported mutation-intent schema version")


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
    mutation_intent_policy: MutationIntentPolicy | None = None
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
        if self.mutation_intent_policy is not None:
            if not isinstance(self.mutation_intent_policy, MutationIntentPolicy):
                raise TypeError("mutation_intent_policy must be MutationIntentPolicy or None")
            if self.mutation_intent_policy.capability_id not in self.allowed_capability_ids:
                raise ValueError("mutation capability must be allowlisted by the request")
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
class MutationIntent:
    """Untrusted provider declaration for exactly one future bounded file mutation."""

    intent_id: str
    step_id: str
    target_path: str
    operation: str
    proposed_content: str
    rationale: str
    grounding_references: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    preservation_requirement_ids: tuple[str, ...] = ()
    schema_version: str = MUTATION_INTENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.intent_id.strip() or not self.step_id.strip():
            raise ValueError("intent_id and step_id cannot be empty")
        if not self.target_path.strip() or not self.operation.strip():
            raise ValueError("target_path and operation cannot be empty")
        if not isinstance(self.proposed_content, str):
            raise TypeError("proposed_content must be a string")
        if not self.rationale.strip():
            raise ValueError("rationale cannot be empty")
        if not self.grounding_references or any(not reference.strip() for reference in self.grounding_references):
            raise ValueError("grounding_references cannot be empty")
        if len(set(self.grounding_references)) != len(self.grounding_references):
            raise ValueError("grounding_references must be unique")
        if any(not dependency.strip() for dependency in self.dependencies):
            raise ValueError("dependencies cannot contain empty values")
        if any(not requirement_id.strip() for requirement_id in self.preservation_requirement_ids):
            raise ValueError("preservation_requirement_ids cannot contain empty values")
        if len(set(self.preservation_requirement_ids)) != len(self.preservation_requirement_ids):
            raise ValueError("preservation_requirement_ids must be unique")
        if self.schema_version != MUTATION_INTENT_SCHEMA_VERSION:
            raise ValueError("unsupported mutation-intent schema version")

    @property
    def content_bytes(self) -> int:
        return len(self.proposed_content.encode("utf-8"))


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
    mutation_intents: tuple[MutationIntent, ...] = ()
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
        if any(not isinstance(intent, MutationIntent) for intent in self.mutation_intents):
            raise TypeError("mutation_intents must contain MutationIntent values")
        if len({intent.intent_id for intent in self.mutation_intents}) != len(self.mutation_intents):
            raise ValueError("mutation intent IDs must be unique")
        if self.schema_version != ENGINEERING_DECISION_SCHEMA_VERSION:
            raise ValueError("unsupported engineering-decision schema version")

    @property
    def digest(self) -> str:
        """Return a deterministic content-safe identity for translation and audit binding."""
        payload = {
            "interpreted_goal": self.interpreted_goal,
            "assumptions": self.assumptions,
            "proposed_approach": self.proposed_approach,
            "ordered_plan": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "capability_id": step.capability_id,
                    "dependencies": step.dependencies,
                    "parameters": dict(step.parameters),
                    "expected_evidence": step.expected_evidence,
                }
                for step in self.ordered_plan
            ],
            "required_capabilities": self.required_capabilities,
            "risks": [
                {
                    "description": risk.description,
                    "severity": risk.severity.value,
                    "mitigation": risk.mitigation,
                }
                for risk in self.risks
            ],
            "confidence": self.confidence,
            "grounding_references": self.grounding_references,
            "mutation_intents": [
                {
                    "intent_id": intent.intent_id,
                    "step_id": intent.step_id,
                    "target_path": intent.target_path,
                    "operation": intent.operation,
                    "proposed_content": intent.proposed_content,
                    "rationale": intent.rationale,
                    "grounding_references": intent.grounding_references,
                    "dependencies": intent.dependencies,
                    "preservation_requirement_ids": intent.preservation_requirement_ids,
                    "schema_version": intent.schema_version,
                }
                for intent in self.mutation_intents
            ],
            "schema_version": self.schema_version,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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
