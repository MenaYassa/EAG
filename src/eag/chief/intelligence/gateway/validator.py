"""Strict parser and policy validator for non-executable engineering decisions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from eag.chief.intelligence.gateway.errors import PolicyValidationError, SchemaValidationError
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
    "schema_version",
}
_STEP_FIELDS = {"step_id", "title", "capability_id", "dependencies", "parameters", "expected_evidence"}
_RISK_FIELDS = {"description", "severity", "mitigation"}
_FORBIDDEN_PARAMETER_KEYS = {"command", "shell", "code", "script", "tool_call", "tool_calls"}


def engineering_decision_json_schema() -> dict[str, Any]:
    """Return the provider-neutral strict schema for the public decision contract."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
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
        },
        "required": [
            "interpreted_goal",
            "assumptions",
            "proposed_approach",
            "ordered_plan",
            "required_capabilities",
            "risks",
            "confidence",
            "schema_version",
        ],
    }


def parse_engineering_decision(content: str) -> EngineeringDecision:
    """Parse only a complete strict JSON decision document from provider text."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise SchemaValidationError("provider response is not valid JSON") from error

    if not isinstance(payload, Mapping):
        raise SchemaValidationError("decision response must be a JSON object")
    _require_exact_fields(payload, _DECISION_FIELDS, "decision")

    try:
        steps = tuple(_parse_step(item) for item in _as_list(payload["ordered_plan"], "ordered_plan"))
        risks = tuple(_parse_risk(item) for item in _as_list(payload["risks"], "risks"))
        assumptions = tuple(_as_string(item, "assumptions item") for item in _as_list(payload["assumptions"], "assumptions"))
        required_capabilities = tuple(
            _as_string(item, "required_capabilities item")
            for item in _as_list(payload["required_capabilities"], "required_capabilities")
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
    """Reject valid JSON that attempts an unsupported or unsafe decision shape."""
    if decision.schema_version != ENGINEERING_DECISION_SCHEMA_VERSION:
        raise PolicyValidationError("decision schema version is not accepted")

    allowed = set(request.allowed_capability_ids)
    required = set(decision.required_capabilities)
    if not required.issubset(allowed):
        raise PolicyValidationError("decision requires a capability outside the allowlist")

    step_ids: set[str] = set()
    seen_before: set[str] = set()
    step_capabilities: set[str] = set()
    for step in decision.ordered_plan:
        if step.step_id in step_ids:
            raise PolicyValidationError("decision contains duplicate plan step IDs")
        if step.capability_id not in allowed:
            raise PolicyValidationError("decision proposes a capability outside the allowlist")
        unknown_dependencies = set(step.dependencies) - seen_before
        if unknown_dependencies:
            raise PolicyValidationError("plan dependency must reference an earlier proposed step")
        _validate_parameters(step.parameters)
        step_ids.add(step.step_id)
        seen_before.add(step.step_id)
        step_capabilities.add(step.capability_id)

    if step_capabilities != required:
        raise PolicyValidationError("required capabilities must exactly match proposed step capabilities")


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


def _validate_parameters(parameters: Mapping[str, Any]) -> None:
    for key, value in parameters.items():
        if key.lower() in _FORBIDDEN_PARAMETER_KEYS:
            raise PolicyValidationError("proposed step contains executable parameter semantics")
        if isinstance(value, Mapping):
            _validate_parameters(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    _validate_parameters(item)
