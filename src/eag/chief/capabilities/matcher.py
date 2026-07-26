"""Capability matcher for EAG Chief Engineer."""

from eag.chief.capabilities.models import CapabilityMatch
from eag.chief.capabilities.registry import CapabilityRegistry
from eag.chief.goals.models import EngineeringGoal


class CapabilityMatcher:
    """Matches goals to candidate capabilities."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def match(self, goal: EngineeringGoal) -> list[CapabilityMatch]:
        matches: list[CapabilityMatch] = []
        for cap in self._registry.list():
            if cap.supports(goal):
                score = cap.score(goal)
                matches.append(
                    CapabilityMatch(
                        capability=cap, score=score, reason=f"Supported by {cap.metadata.name}"
                    )
                )
        return matches
