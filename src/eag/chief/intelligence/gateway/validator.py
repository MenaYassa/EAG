"""Strict parser and policy validator for non-executable engineering decisions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from eag.chief.intelligence.gateway.errors import (
    PolicyValidationError,
    PolicyViolation,
    PolicyViolationCode,
    SchemaValidationError,
)
from eag.chief.intelligence.gateway.models import (
    ENGINEERING_DECISION_SCHEMA_VERSION,
    EngineeringDecision,
    EngineeringDecisionRequest,
    EngineeringRisk,
    MutationIntent,
    MutationIntentPolicy,
    ProposedPlanStep,
    RiskSeverity,
)

_DECISION_FIELDS = {
    "interpreted_goal",
    "assumptions",
    "proposed_approach",
    "ordered_plan",
    "required_capabilities",
    "risks",
    "confidence",
    "grounding_references",
    "schema_version",
    "mutation_intents",
}
_STEP_FIELDS = {"step_id", "title", "capability_id", "dependencies", "parameters", "expected_evidence"}
_RISK_FIELDS = {"description", "severity", "mitigation"}
_MUTATION_INTENT_FIELDS = {
    "intent_id",
    "step_id",
    "target_path",
    "operation",
    "proposed_content",
    "rationale",
    "grounding_references",
    "dependencies",
    "preservation_requirement_ids",
    "schema_version",
}
_FORBIDDEN_PARAMETER_KEYS = {"command", "shell", "code", "script", "tool_call", "tool_calls"}


def engineering_decision_json_schema(
    *,
    require_grounding_references: bool = False,
    mutation_intent_policy: MutationIntentPolicy | None = None,
) -> dict[str, Any]:
    """Return the strict decision schema, optionally requiring G2.2 provenance citations."""
    properties: dict[str, Any] = {
        "interpreted_goal": {"type": "string", "minLength": 1},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "proposed_approach": {"type": "string", "minLength": 1},
        "ordered_plan": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "step_id": {"type": "string", "minLength": 1},
                    "title": {"type": "string", "minLength": 1},
                    "capability_id": {"type": "string", "minLength": 1},
                    "dependencies": {"type": "array", "items": {"type": "string"}},
                    "expected_evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "step_id",
                    "title",
                    "capability_id",
                    "dependencies",
                    "expected_evidence",
                ],
            },
        },
        "required_capabilities": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "risks": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "description": {"type": "string", "minLength": 1},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "mitigation": {"type": "string", "minLength": 1},
                },
                "required": ["description", "severity", "mitigation"],
            },
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "schema_version": {"type": "string", "const": ENGINEERING_DECISION_SCHEMA_VERSION},
    }
    required = [
        "interpreted_goal",
        "assumptions",
        "proposed_approach",
        "ordered_plan",
        "required_capabilities",
        "risks",
        "confidence",
        "schema_version",
    ]
    if require_grounding_references:
        properties["grounding_references"] = {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        }
        required.append("grounding_references")
    if mutation_intent_policy is not None:
        properties["mutation_intents"] = {
            "type": "array",
            "minItems": 1,
            "maxItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "intent_id": {"type": "string", "minLength": 1},
                    "step_id": {"type": "string", "minLength": 1},
                    "target_path": {"type": "string", "minLength": 1},
                    "operation": {"type": "string", "enum": list(mutation_intent_policy.allowed_operations)},
                    "proposed_content": {"type": "string"},
                    "rationale": {"type": "string", "minLength": 1},
                    "grounding_references": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "dependencies": {"type": "array", "maxItems": 0, "items": {"type": "string"}},
                    "preservation_requirement_ids": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                requirement.requirement_id
                                for requirement in mutation_intent_policy.preservation_requirements
                            ],
                        },
                    },
                    "schema_version": {"type": "string", "const": mutation_intent_policy.schema_version},
                },
                "required": [
                    "intent_id",
                    "step_id",
                    "target_path",
                    "operation",
                    "proposed_content",
                    "rationale",
                    "grounding_references",
                    "dependencies",
                    "preservation_requirement_ids",
                    "schema_version",
                ],
            },
        }
        required.append("mutation_intents")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


def parse_engineering_decision(content: str) -> EngineeringDecision:
    """Parse only a complete strict JSON decision document from provider text."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise SchemaValidationError("provider response is not valid JSON") from error

    if not isinstance(payload, Mapping):
        raise SchemaValidationError("decision response must be a JSON object")
    _require_fields(
        payload,
        required=_DECISION_FIELDS - {"grounding_references", "mutation_intents"},
        allowed=_DECISION_FIELDS,
        name="decision",
    )

    try:
        steps = tuple(_parse_step(item) for item in _as_list(payload["ordered_plan"], "ordered_plan"))
        risks = tuple(_parse_risk(item) for item in _as_list(payload["risks"], "risks"))
        mutation_intents = tuple(
            _parse_mutation_intent(item)
            for item in _as_list(payload.get("mutation_intents", []), "mutation_intents")
        )
        assumptions = tuple(_as_string(item, "assumptions item") for item in _as_list(payload["assumptions"], "assumptions"))
        required_capabilities = tuple(
            _as_string(item, "required_capabilities item")
            for item in _as_list(payload["required_capabilities"], "required_capabilities")
        )
        grounding_references = tuple(
            _as_string(item, "grounding_references item")
            for item in _as_list(payload.get("grounding_references", []), "grounding_references")
        )
        confidence = payload["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise SchemaValidationError("confidence must be a numeric value")
        return EngineeringDecision(
            interpreted_goal=_as_string(payload["interpreted_goal"], "interpreted_goal"),
            assumptions=assumptions,
            proposed_approach=_as_string(payload["proposed_approach"], "proposed_approach"),
            ordered_plan=steps,
            required_capabilities=required_capabilities,
            risks=risks,
            confidence=float(confidence),
            grounding_references=grounding_references,
            mutation_intents=mutation_intents,
            schema_version=_as_string(payload["schema_version"], "schema_version"),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, SchemaValidationError):
            raise
        raise SchemaValidationError(str(error)) from error


def validate_decision_policy(
    decision: EngineeringDecision,
    request: EngineeringDecisionRequest,
) -> None:
    """Reject unsafe decision shapes while retaining only safe structured violation metadata."""
    if decision.schema_version != ENGINEERING_DECISION_SCHEMA_VERSION:
        raise _policy_error(
            code=PolicyViolationCode.DECISION_SCHEMA_VERSION_UNACCEPTED,
            message="decision schema version is not accepted",
            decision=decision,
        )

    allowed = set(request.allowed_capability_ids)
    required = set(decision.required_capabilities)
    if not required.issubset(allowed):
        raise _policy_error(
            code=PolicyViolationCode.REQUIRED_CAPABILITY_OUTSIDE_ALLOWLIST,
            message="decision requires a capability outside the allowlist",
            decision=decision,
        )

    step_positions: dict[str, int] = {}
    for index, step in enumerate(decision.ordered_plan):
        step_positions.setdefault(step.step_id, index)

    step_ids: set[str] = set()
    seen_before: set[str] = set()
    step_capabilities: set[str] = set()
    for step_index, step in enumerate(decision.ordered_plan):
        if step.step_id in step_ids:
            raise _policy_error(
                code=PolicyViolationCode.DUPLICATE_STEP_ID,
                message="decision contains duplicate plan step IDs",
                decision=decision,
                step_id=step.step_id,
                step_index=step_index,
            )
        if step.capability_id not in allowed:
            raise _policy_error(
                code=PolicyViolationCode.STEP_CAPABILITY_OUTSIDE_ALLOWLIST,
                message="decision proposes a capability outside the allowlist",
                decision=decision,
                step_id=step.step_id,
                step_index=step_index,
            )
        dependency = next(
            (item for item in step.dependencies if item not in seen_before),
            None,
        )
        if dependency is not None:
            raise _policy_error(
                code=PolicyViolationCode.DEPENDENCY_NOT_EARLIER_STEP,
                message="plan dependency must reference an earlier proposed step",
                decision=decision,
                step_id=step.step_id,
                dependency_step_id=dependency,
                step_index=step_index,
                dependency_index=step_positions.get(dependency),
            )
        _validate_parameters(
            step.parameters,
            decision=decision,
            step_id=step.step_id,
            step_index=step_index,
        )
        step_ids.add(step.step_id)
        seen_before.add(step.step_id)
        step_capabilities.add(step.capability_id)

    if step_capabilities != required:
        raise _policy_error(
            code=PolicyViolationCode.REQUIRED_CAPABILITIES_MISMATCH,
            message="required capabilities must exactly match proposed step capabilities",
            decision=decision,
        )

    known_provenance = set(request.context.provenance)
    requires_grounding = "snapshot_fingerprint" in request.context.truncation_metadata
    if requires_grounding and not decision.grounding_references:
        raise _policy_error(
            code=PolicyViolationCode.GROUNDING_REFERENCES_REQUIRED,
            message="repository-aware decision requires grounding references",
            decision=decision,
        )
    if decision.grounding_references and not set(decision.grounding_references).issubset(known_provenance):
        raise _policy_error(
            code=PolicyViolationCode.GROUNDING_REFERENCE_UNKNOWN,
            message="decision grounding reference is absent from supplied context provenance",
            decision=decision,
        )
    _validate_mutation_intents(decision, request, known_provenance)


def _policy_error(
    *,
    code: PolicyViolationCode,
    message: str,
    decision: EngineeringDecision,
    step_id: str | None = None,
    dependency_step_id: str | None = None,
    step_index: int | None = None,
    dependency_index: int | None = None,
) -> PolicyValidationError:
    return PolicyValidationError(
        PolicyViolation(
            code=code,
            stage="policy_validation",
            message=message,
            step_id=step_id,
            dependency_step_id=dependency_step_id,
            step_index=step_index,
            dependency_index=dependency_index,
            schema_version=decision.schema_version,
        )
    )


def _parse_step(value: object) -> ProposedPlanStep:
    if not isinstance(value, Mapping):
        raise SchemaValidationError("ordered_plan items must be JSON objects")
    _require_fields(
        value,
        required=_STEP_FIELDS - {"parameters"},
        allowed=_STEP_FIELDS,
        name="proposed plan step",
    )
    parameters = value.get("parameters", {})
    if not isinstance(parameters, Mapping):
        raise SchemaValidationError("step parameters must be a JSON object")
    return ProposedPlanStep(
        step_id=_as_string(value["step_id"], "step_id"),
        title=_as_string(value["title"], "title"),
        capability_id=_as_string(value["capability_id"], "capability_id"),
        dependencies=tuple(
            _as_string(item, "dependency") for item in _as_list(value["dependencies"], "dependencies")
        ),
        parameters=dict(parameters),
        expected_evidence=tuple(
            _as_string(item, "expected evidence")
            for item in _as_list(value["expected_evidence"], "expected_evidence")
        ),
    )


def _parse_mutation_intent(value: object) -> MutationIntent:
    if not isinstance(value, Mapping):
        raise SchemaValidationError("mutation intent must be a JSON object")
    _require_exact_fields(value, _MUTATION_INTENT_FIELDS, "mutation intent")
    return MutationIntent(
        intent_id=_as_string(value["intent_id"], "mutation intent id"),
        step_id=_as_string(value["step_id"], "mutation intent step id"),
        target_path=_as_string(value["target_path"], "mutation intent target path"),
        operation=_as_string(value["operation"], "mutation intent operation"),
        proposed_content=_as_string(value["proposed_content"], "mutation intent proposed content"),
        rationale=_as_string(value["rationale"], "mutation intent rationale"),
        grounding_references=tuple(
            _as_string(item, "mutation intent grounding reference")
            for item in _as_list(value["grounding_references"], "mutation intent grounding references")
        ),
        dependencies=tuple(
            _as_string(item, "mutation intent dependency")
            for item in _as_list(value["dependencies"], "mutation intent dependencies")
        ),
        preservation_requirement_ids=tuple(
            _as_string(item, "mutation intent preservation requirement")
            for item in _as_list(
                value["preservation_requirement_ids"],
                "mutation intent preservation requirements",
            )
        ),
        schema_version=_as_string(value["schema_version"], "mutation intent schema version"),
    )


def _parse_risk(value: object) -> EngineeringRisk:
    if not isinstance(value, Mapping):
        raise SchemaValidationError("risk items must be JSON objects")
    _require_exact_fields(value, _RISK_FIELDS, "risk")
    try:
        severity = RiskSeverity(_as_string(value["severity"], "risk severity"))
    except ValueError as error:
        raise SchemaValidationError("risk severity is invalid") from error
    return EngineeringRisk(
        description=_as_string(value["description"], "risk description"),
        severity=severity,
        mitigation=_as_string(value["mitigation"], "risk mitigation"),
    )


def _require_exact_fields(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    _require_fields(value, required=expected, allowed=expected, name=name)


def _require_fields(
    value: Mapping[str, Any],
    *,
    required: set[str],
    allowed: set[str],
    name: str,
) -> None:
    actual = set(value)
    missing = required - actual
    unknown = actual - allowed
    if missing or unknown:
        raise SchemaValidationError(
            f"{name} fields do not match schema: missing={sorted(missing)}, unknown={sorted(unknown)}"
        )


def _as_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise SchemaValidationError(f"{field_name} must be an array")
    return value


def _as_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{field_name} must be a non-empty string")
    return value


def _validate_mutation_intents(
    decision: EngineeringDecision,
    request: EngineeringDecisionRequest,
    known_provenance: set[str],
) -> None:
    policy = request.mutation_intent_policy
    intents = decision.mutation_intents
    if policy is None:
        if intents:
            raise _policy_error(
                code=PolicyViolationCode.MUTATION_INTENT_CAPABILITY_MISMATCH,
                message="mutation intent mode is not enabled for this request",
                decision=decision,
            )
        return
    if len(intents) != 1:
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_COUNT_INVALID,
            message="mutation intent mode requires exactly one mutation intent",
            decision=decision,
        )
    intent = intents[0]
    steps = {step.step_id: step for step in decision.ordered_plan}
    step = steps.get(intent.step_id)
    if step is None:
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_STEP_UNKNOWN,
            message="mutation intent must reference an existing proposed step",
            decision=decision,
            step_id=intent.step_id,
        )
    if step.capability_id != policy.capability_id:
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_CAPABILITY_MISMATCH,
            message="mutation intent step must use the configured mutation capability",
            decision=decision,
            step_id=intent.step_id,
        )
    if step.dependencies or intent.dependencies:
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_STEP_DEPENDENCIES_FORBIDDEN,
            message="mutation intent dependencies are not supported in the first slice",
            decision=decision,
            step_id=intent.step_id,
        )
    if intent.operation not in policy.allowed_operations:
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_OPERATION_UNSUPPORTED,
            message="mutation intent operation is not allowed",
            decision=decision,
            step_id=intent.step_id,
        )
    _validate_mutation_target(intent, decision)
    _validate_preservation_bindings(intent, decision, policy)
    if intent.content_bytes > policy.max_content_bytes:
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_CONTENT_TOO_LARGE,
            message="mutation intent proposed content exceeds the configured limit",
            decision=decision,
            step_id=intent.step_id,
        )
    if not set(intent.grounding_references).issubset(known_provenance):
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_GROUNDING_UNKNOWN,
            message="mutation intent grounding reference is absent from supplied context provenance",
            decision=decision,
            step_id=intent.step_id,
        )


def _validate_preservation_bindings(
    intent: MutationIntent,
    decision: EngineeringDecision,
    policy: MutationIntentPolicy,
) -> None:
    required_ids = {requirement.requirement_id for requirement in policy.preservation_requirements}
    declared_ids = set(intent.preservation_requirement_ids)
    if not declared_ids.issubset(required_ids):
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_PRESERVATION_BINDING_INVALID,
            message="mutation intent declares an unknown preservation requirement",
            decision=decision,
            step_id=intent.step_id,
        )
    if declared_ids != required_ids:
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_PRESERVATION_BINDING_MISSING,
            message="mutation intent must declare every configured preservation requirement",
            decision=decision,
            step_id=intent.step_id,
        )


def _validate_mutation_target(intent: MutationIntent, decision: EngineeringDecision) -> None:
    raw = intent.target_path
    path = PurePosixPath(raw)
    if (
        Path(raw).is_absolute()
        or path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or "\x00" in raw
        or any("\\" in part for part in path.parts)
    ):
        raise _policy_error(
            code=PolicyViolationCode.MUTATION_INTENT_TARGET_INVALID,
            message="mutation intent target path is invalid",
            decision=decision,
            step_id=intent.step_id,
        )


def _validate_parameters(
    parameters: Mapping[str, Any],
    *,
    decision: EngineeringDecision,
    step_id: str,
    step_index: int,
) -> None:
    for key, value in parameters.items():
        if key.lower() in _FORBIDDEN_PARAMETER_KEYS:
            raise _policy_error(
                code=PolicyViolationCode.EXECUTABLE_PARAMETER_FORBIDDEN,
                message="proposed step contains executable parameter semantics",
                decision=decision,
                step_id=step_id,
                step_index=step_index,
            )
        if isinstance(value, Mapping):
            _validate_parameters(
                value,
                decision=decision,
                step_id=step_id,
                step_index=step_index,
            )
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    _validate_parameters(
                        item,
                        decision=decision,
                        step_id=step_id,
                        step_index=step_index,
                    )
