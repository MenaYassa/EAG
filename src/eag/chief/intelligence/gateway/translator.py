"""Deterministic translation from a validated advisory decision to a Chief Plan."""

from __future__ import annotations

from eag.chief.intelligence.gateway.models import EngineeringDecision
from eag.chief.runtime.models import Plan, PlanStep


class DecisionToPlanTranslator:
    """Maps an already validated decision to existing Plan models without executing it."""

    def translate(self, decision: EngineeringDecision) -> Plan:
        """Create a Plan that still requires Coordinator and CapabilityRuntime governance."""
        steps = tuple(
            PlanStep(
                step_id=step.step_id,
                name=step.title,
                description=decision.proposed_approach,
                capability_id=step.capability_id,
                dependencies=step.dependencies,
                metadata={
                    "parameters": dict(step.parameters),
                    "expected_evidence": step.expected_evidence,
                    "decision_schema_version": decision.schema_version,
                },
            )
            for step in decision.ordered_plan
        )
        return Plan(steps=steps)
