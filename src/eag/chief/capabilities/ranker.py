"""Capability ranker for EAG Chief Engineer."""

from eag.chief.capabilities.enums import CapabilityCost, CapabilityRisk
from eag.chief.capabilities.models import CapabilityMatch


class CapabilityRanker:
    """Ranks matched capabilities by score and penalties."""

    def rank(self, matches: list[CapabilityMatch]) -> list[CapabilityMatch]:
        def calculate_final_score(match: CapabilityMatch) -> float:
            cap = match.capability
            score = match.score

            # Apply risk penalties
            if cap.metadata.estimated_risk == CapabilityRisk.HIGH:
                score -= 0.2
            elif cap.metadata.estimated_risk == CapabilityRisk.MEDIUM:
                score -= 0.1

            # Apply cost penalties
            if cap.metadata.estimated_cost == CapabilityCost.HIGH:
                score -= 0.2
            elif cap.metadata.estimated_cost == CapabilityCost.MEDIUM:
                score -= 0.1

            return max(0.0, score)

        return sorted(matches, key=calculate_final_score, reverse=True)
