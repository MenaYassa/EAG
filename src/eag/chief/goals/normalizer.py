"""Goal normalizer for EAG Chief Engineer."""

from eag.chief.goals.models import GoalAnalysis


class GoalNormalizer:
    """Normalizes goal text to a canonical representation."""

    _SYNONYMS: dict[str, str] = {
        "app": "application",
        "frontend": "web_frontend",
        "backend": "api_backend",
        "db": "database",
    }

    def normalize(self, analysis: GoalAnalysis) -> str:
        text = analysis.goal.raw_text.lower()
        for syn, canonical in self._SYNONYMS.items():
            text = text.replace(syn, canonical)
        return text
