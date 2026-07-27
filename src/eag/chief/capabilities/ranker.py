"""Capability ranker for EAG Chief Engineer."""

from eag.chief.capabilities.enums import CapabilityCost, CapabilityRisk
from eag.chief.capabilities.models import CapabilityMatch


class CapabilityRanker:
    """Ranks matched capabilities by score, penalties, and deterministic tie-breaking."""

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

            # Apply token/latency cost weighting (minor impact)
            score -= cap.metadata.token_cost * 0.01
            score -= cap.metadata.latency_ms * 0.001

            return max(0.0, score)

        # Replace the final return statement with this:
        updated_matches = [
            CapabilityMatch(capability=m.capability, score=calculate_final_score(m))
            for m in matches
        ]

        return sorted(updated_matches, key=lambda m: (-m.score, m.capability.metadata.id))
