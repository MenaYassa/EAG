"""Strict parser and policy validator for non-executable engineering decisions."""

from __future__ import annotations

import json
from collections.abc import Mapping
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
}
_STEP_FIELDS = {"step_id", "title", "capability_id", "dependencies", "parameters", "expected_evidence"}
_RISK_FIELDS = {"description", "severity", "mitigation"}
_FORBIDDEN_PARAMETER_KEYS = {"command", "shell", "code", "script", "tool_call", "tool_calls"}


def engineering_decision_json_schema(
    *,
    require_grounding_references: bool = False,
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
        required=_DECISION_FIELDS - {"grounding_references"},
        allowed=_DECISION_FIELDS,
        name="decision",
    )

    try:
        steps = tuple(_parse_step(item) for item in _as_list(payload["ordered_plan"], "ordered_plan"))
        risks = tuple(_parse_risk(item) for item in _as_list(payload["risks"], "risks"))
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
