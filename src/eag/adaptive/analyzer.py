"""Experience Analyzer for EAG Adaptive Planning."""

from collections import Counter

from eag.adaptive.enums import InsightCategory
from eag.adaptive.models import PlanningInsight
from eag.memory.models import EngineeringExperience


class ExperienceAnalyzer:
    """Analyzes engineering experiences to generate planning insights."""

    def analyze(
        self, experiences: tuple[EngineeringExperience, ...]
    ) -> tuple[PlanningInsight, ...]:
        """Extracts insights from a collection of experiences."""
        if not experiences:
            return ()

        insights: list[PlanningInsight] = []

        lesson_counts = Counter()
        lesson_experiences = {}

        for exp in experiences:
            for lesson in exp.lessons:
                key = (str(lesson.category.value), lesson.description[:20])
                lesson_counts[key] += 1
                lesson_experiences[key] = lesson

        # Sort keys deterministically before processing
        # Sort keys deterministically before processing
        for category, desc_prefix in sorted(lesson_counts.keys()):
            count = lesson_counts[(category, desc_prefix)]
            if count >= 2:
                lesson = lesson_experiences[(category, desc_prefix)]
                confidence = min(1.0, 0.5 + (count * 0.1))

                insights.append(
                    PlanningInsight(
                        source="ExperienceAnalyzer",
                        category=InsightCategory(category),
                        description=f"Recurring issue: {lesson.description}",
                        confidence=confidence,
                        evidence=f"Observed in {count} out of {len(experiences)} experiences.",
                        recommendation=lesson.recommendation
                        if lesson.recommendation
                        else f"Address {category} issues early.",
                    )
                )

        scores = [e.benchmark_score for e in experiences if e.benchmark_score > 0]
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score < 80.0:
                insights.append(
                    PlanningInsight(
                        source="ExperienceAnalyzer",
                        category=InsightCategory.BENCHMARKS,
                        description=f"Low average benchmark score: {avg_score:.1f}",
                        confidence=0.8,
                        evidence=f"Average score across {len(scores)} runs.",
                        recommendation="Review common failure modes and adjust planning.",
                    )
                )

        # Tie-break across confidence (descending), category, and description
        insights.sort(
            key=lambda i: (-i.confidence, str(i.category.value), i.description, i.evidence)
        )
        return tuple(insights)
