"""Requirement extractor for EAG Chief Engineer."""

from eag.chief.goals.enums import GoalIntent
from eag.chief.goals.models import Assumption, ChiefGoal, Constraint, Requirement


class RequirementExtractor:
    """Extracts requirements, constraints, and assumptions from raw text."""

    _KEYWORDS: dict[str, tuple[str, ...]] = {
        "frontend": ("react", "vue", "angular", "svelte", "frontend"),
        "backend": ("fastapi", "django", "flask", "express", "node", "backend", "api"),
        "database": ("postgres", "mysql", "mongodb", "sqlite", "database", "db"),
        "authentication": ("auth", "oauth", "jwt", "login"),
        "deployment": ("docker", "kubernetes", "aws", "gcp", "azure", "railway"),
    }

    _CONSTRAINT_KEYWORDS: dict[str, tuple[str, ...]] = {
        "language": ("python 3", "python3", "typescript", "golang"),
        "deployment_platform": ("railway", "aws", "gcp", "azure"),
    }

    def extract(
        self, goal: ChiefGoal, intents: tuple[GoalIntent, ...]
    ) -> tuple[tuple[Requirement, ...], tuple[Constraint, ...], tuple[Assumption, ...]]:
        text = goal.raw_text.lower()
        reqs: list[Requirement] = []
        constraints: list[Constraint] = []
        assumptions: list[Assumption] = []

        is_build = GoalIntent.BUILD in intents

        for key, keywords in self._KEYWORDS.items():
            found = False
            for kw in keywords:
                if kw in text:
                    reqs.append(Requirement(key=key, value=kw, is_missing=False, confidence=0.9))
                    found = True
                    break
            if not found and is_build:
                reqs.append(Requirement(key=key, value=None, is_missing=True, confidence=0.0))
                assumptions.append(Assumption(key=key, value="unknown"))

        for key, keywords in self._CONSTRAINT_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    constraints.append(Constraint(key=key, value=kw, confidence=0.95))
                    break

        return tuple(reqs), tuple(constraints), tuple(assumptions)
