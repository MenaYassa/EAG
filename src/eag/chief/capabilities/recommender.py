"""Capability recommender for EAG Chief Engineer."""

from eag.chief.capabilities.enums import CapabilityRisk
from eag.chief.capabilities.models import CapabilityMatch, CapabilityRecommendation


class Recommender:
    """Produces a final recommendation from ranked matches."""

    def recommend(self, ranked_matches: list[CapabilityMatch]) -> CapabilityRecommendation:
        if not ranked_matches:
            return CapabilityRecommendation(
                winner=None,
                explanation="No capabilities matched the goal."
            )

        # 1. Sort matches to guarantee the winner has the highest score
        sorted_matches = sorted(
            ranked_matches, 
            key=lambda m: (-m.score, m.capability.metadata.id)
        )

        winner = sorted_matches[0]
        alternatives = sorted_matches[1:]
        
        warnings = []
        if winner.capability.metadata.estimated_risk in (CapabilityRisk.HIGH, CapabilityRisk.MEDIUM):
            warnings.append(f"Selected capability carries {winner.capability.metadata.estimated_risk.value} risk.")
        if winner.capability.metadata.requires_llm:
            warnings.append("Selected capability requires LLM routing.")
        if winner.capability.metadata.dependencies:
            warnings.append(f"Requires dependencies: {', '.join(winner.capability.metadata.dependencies)}")
            
        # 2. Base explanation string
        explanation = f"Selected {winner.capability.metadata.name} (Score: {winner.score:.2f})."
        
        # 3. Only append reasons if there are actually reasons to append
        if winner.reason_parts:
            reason_str = "; ".join(winner.reason_parts)
            explanation += f" Reasons: {reason_str}."
            
        return CapabilityRecommendation(
            winner=winner,
            alternatives=tuple(alternatives),
            confidence=winner.score,
            explanation=explanation,
            warnings=tuple(warnings)
        )