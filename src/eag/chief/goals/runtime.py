"""Goal runtime for EAG Chief Engineer."""

from eag.chief.goals.clarifier import ClarificationEngine
from eag.chief.goals.classifier import GoalClassifier, RuleBasedGoalClassifier
from eag.chief.goals.enums import GoalCategory, GoalIntent
from eag.chief.goals.extractor import RequirementExtractor
from eag.chief.goals.models import ChiefGoal, EngineeringGoal, GoalAnalysis
from eag.chief.goals.normalizer import GoalNormalizer


class GoalRuntime:
    """Orchestrates the goal intelligence pipeline."""

    def __init__(
        self,
        classifier: GoalClassifier | None = None,
        extractor: RequirementExtractor | None = None,
        normalizer: GoalNormalizer | None = None,
        clarifier: ClarificationEngine | None = None,
    ) -> None:
        self._classifier = classifier or RuleBasedGoalClassifier()
        self._extractor = extractor or RequirementExtractor()
        self._normalizer = normalizer or GoalNormalizer()
        self._clarifier = clarifier or ClarificationEngine()

    def analyze(self, raw_text: str, priority: str = "NORMAL") -> EngineeringGoal:
        """Convert raw text into a structured EngineeringGoal."""
        from eag.chief.goals.enums import GoalPriority

        goal = ChiefGoal(raw_text=raw_text, priority=GoalPriority(priority.lower()))

        intents, confidence, is_ambiguous, complexity = self._classifier.classify(goal)
        primary_intent = intents[0] if intents else GoalIntent.UNKNOWN

        requirements, constraints, assumptions = self._extractor.extract(goal, intents)

        analysis = GoalAnalysis(
            goal=goal,
            intents=intents,
            primary_intent=primary_intent,
            confidence=confidence,
            is_ambiguous=is_ambiguous,
            requirements=requirements,
            constraints=constraints,
            assumptions=assumptions,
            complexity=complexity,
        )

        canonical_text = self._normalizer.normalize(analysis)

        missing_reqs = tuple(r for r in requirements if r.is_missing)
        clarifications = self._clarifier.clarify(missing_reqs, intents, is_ambiguous)

        # Determine category
        if GoalIntent.BUILD in intents:
            category = GoalCategory.APPLICATION
        elif GoalIntent.MIGRATION in intents:
            category = GoalCategory.MIGRATION
        elif GoalIntent.DOCUMENTATION in intents:
            category = GoalCategory.DOCUMENTATION
        elif GoalIntent.ANALYSIS in intents or GoalIntent.REVIEW in intents:
            category = GoalCategory.ANALYSIS
        else:
            category = GoalCategory.UNKNOWN

        return EngineeringGoal(
            original_goal=goal,
            canonical_text=canonical_text,
            intents=intents,
            primary_intent=primary_intent,
            category=category,
            complexity=complexity,
            confidence=confidence,
            is_ambiguous=is_ambiguous,
            requirements=requirements,
            constraints=constraints,
            assumptions=assumptions,
            missing_requirements=missing_reqs,
            clarifications=clarifications,
        )
