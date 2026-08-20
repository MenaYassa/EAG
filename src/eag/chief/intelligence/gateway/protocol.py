"""Public protocol for the governed LLM gateway."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from eag.chief.intelligence.gateway.models import (
    EngineeringDecisionRequest,
    EngineeringDecisionResult,
)


@runtime_checkable
class GovernedLLMGateway(Protocol):
    """Produces a validated advisory decision and never an executable effect."""

    def decide(self, request: EngineeringDecisionRequest) -> EngineeringDecisionResult: ...
