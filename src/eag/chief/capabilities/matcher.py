"""Capability matcher for EAG Chief Engineer."""

from eag.chief.capabilities.models import Capability, CapabilityMatch
from eag.chief.capabilities.registry import CapabilityRegistry
from eag.chief.goals.models import EngineeringGoal


class CapabilityMatcher:
    """Matches goals to candidate capabilities."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def _get_goal_languages(self, goal: EngineeringGoal) -> set[str]:
        """Extracts requested languages from goal requirements."""
        langs = set()
        for req in goal.requirements:
            if req.key == "language" and req.value:
                # Handle constraints like 'python 3' -> 'python'
                lang = req.value.split()[0].lower()
                langs.add(lang)
        return langs

    def match(self, goal: EngineeringGoal) -> list[CapabilityMatch]:
        matches: list[CapabilityMatch] = []
        goal_langs = self._get_goal_languages(goal)
        
        for cap in self._registry.list_active():
            reasons: list[str] = []
            
            # 1. Language Compatibility Check
            if cap.metadata.supported_languages:
                if goal_langs and not any(lang in cap.metadata.supported_languages for lang in goal_langs):
                    continue  # Incompatible language
                reasons.append(f"Language supported ({', '.join(cap.metadata.supported_languages)})")
            
            # 2. Custom Capability Support Logic
            if not cap.supports(goal):
                continue
            reasons.append("Intent matched")
            
            score = cap.score(goal)
            matches.append(CapabilityMatch(
                capability=cap,
                score=score,
                reason=f"Matched: {cap.metadata.name}",
                reason_parts=tuple(reasons)
            ))
            
        return matches