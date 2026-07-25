"""Goal classifier for EAG Chief Engineer."""

from eag.chief.goals.enums import GoalComplexity, GoalIntent
from eag.chief.goals.models import ChiefGoal


class GoalClassifier:
    """Protocol for goal classification."""

    def classify(
        self, goal: ChiefGoal
    ) -> tuple[tuple[GoalIntent, ...], float, bool, GoalComplexity]:
        raise NotImplementedError


class RuleBasedGoalClassifier(GoalClassifier):
    """Deterministic rule-based goal classifier."""

    _RULES: dict[GoalIntent, tuple[str, ...]] = {
        GoalIntent.BUILD: ("build", "create", "make", "develop", "generate app", "scaffold"),
        GoalIntent.BUGFIX: ("fix", "bug", "error", "broken", "debug", "crash"),
        GoalIntent.REFACTOR: ("refactor", "rename", "extract", "move", "clean up", "restructure"),
        GoalIntent.REVIEW: ("review", "audit", "check", "analyze code"),
        GoalIntent.MIGRATION: ("upgrade", "migrate", "convert", "port", "update to"),
        GoalIntent.ANALYSIS: ("understand", "analyze", "map", "trace", "investigate"),
        GoalIntent.DOCUMENTATION: ("document", "docs", "readme", "explain"),
    }

    _AMBIGUOUS_TERMS: tuple[str, ...] = ("improve", "optimize", "make better", "enhance")

    _COMPLEXITY_MAP: dict[GoalIntent, GoalComplexity] = {
        GoalIntent.BUILD: GoalComplexity.LARGE,
        GoalIntent.MIGRATION: GoalComplexity.LARGE,
        GoalIntent.REFACTOR: GoalComplexity.MEDIUM,
        GoalIntent.BUGFIX: GoalComplexity.SMALL,
        GoalIntent.REVIEW: GoalComplexity.MEDIUM,
        GoalIntent.ANALYSIS: GoalComplexity.MEDIUM,
        GoalIntent.DOCUMENTATION: GoalComplexity.SMALL,
        GoalIntent.UNKNOWN: GoalComplexity.TRIVIAL,
    }

    def classify(
        self, goal: ChiefGoal
    ) -> tuple[tuple[GoalIntent, ...], float, bool, GoalComplexity]:
        text = goal.raw_text.lower()
        found_intents: list[GoalIntent] = []

        for intent, keywords in self._RULES.items():
            for kw in keywords:
                if kw in text:
                    if intent not in found_intents:
                        found_intents.append(intent)
                    break

        is_ambiguous = any(term in text for term in self._AMBIGUOUS_TERMS)

        if not found_intents:
            return (GoalIntent.UNKNOWN,), 0.0, is_ambiguous, GoalComplexity.TRIVIAL

        # Determine complexity based on the most complex intent found
        complexity = max(
            (self._COMPLEXITY_MAP.get(i, GoalComplexity.MEDIUM) for i in found_intents),
            key=lambda c: list(GoalComplexity).index(c),
        )

        confidence = 1.0 if not is_ambiguous else 0.5
        return tuple(found_intents), confidence, is_ambiguous, complexity
