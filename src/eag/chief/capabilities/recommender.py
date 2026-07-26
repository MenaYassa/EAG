"""Capability recommender for EAG Chief Engineer."""

from eag.chief.capabilities.enums import CapabilityRisk
from eag.chief.capabilities.models import CapabilityMatch, CapabilityRecommendation


class Recommender:
    """Produces a final recommendation from ranked matches."""

    def recommend(self, ranked_matches: list[CapabilityMatch]) -> CapabilityRecommendation:
        if not ranked_matches:
            return CapabilityRecommendation(
                winner=None, explanation="No capabilities matched the goal."
            )

        winner = ranked_matches[0]
        alternatives = ranked_matches[1:]

        warnings = []
        if winner.capability.metadata.estimated_risk in (
            CapabilityRisk.HIGH,
            CapabilityRisk.MEDIUM,
        ):
            risk_val = winner.capability.metadata.estimated_risk.value
            warnings.append(f"Selected capability carries {risk_val} risk.")

        if winner.capability.metadata.requires_llm:
            warnings.append("Selected capability requires LLM routing.")

        name = winner.capability.metadata.name
        return CapabilityRecommendation(
            winner=winner,
            alternatives=tuple(alternatives),
            confidence=winner.score,
            explanation=f"Selected {name} as the highest scoring capability.",
            warnings=tuple(warnings),
        )
