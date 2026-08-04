"""Experience builder for EAG."""

from eag.memory.enums import MemoryCategory
from eag.memory.models import EngineeringExperience, LessonLearned, MemoryEntry
from eag.reflection.models import ReflectionContext, ReflectionReport


class ExperienceBuilder:
    """Transforms reflections and memory entries into normalized EngineeringExperiences."""

    def build_from_reflection(
        self, context: ReflectionContext, report: ReflectionReport
    ) -> EngineeringExperience:
        """Builds an experience directly from a reflection report."""

        # Safely extract the summary text
        raw_goal = getattr(context.run_result, "summary", "") or ""

        project_type = "unknown"
        if "fastapi" in raw_goal.lower():
            project_type = "fastapi"
        elif "flask" in raw_goal.lower():
            project_type = "flask"
        elif "calculator" in raw_goal.lower():
            project_type = "calculator"

        # Convert findings to lessons
        lessons = []
        for finding in report.findings:
            # Safely extract the string value and cast to MemoryCategory Enum
            cat_val = (
                finding.category.value if hasattr(finding.category, "value") else finding.category
            )

            lessons.append(
                LessonLearned(
                    category=MemoryCategory(cat_val),
                    description=finding.description,
                    evidence=finding.evidence,
                    confidence=finding.confidence,
                    recommendation=next(
                        (
                            r.action
                            for r in report.recommendations
                            if getattr(r.priority, "value", r.priority) == "high"
                        ),
                        "",
                    ),
                )
            )

        return EngineeringExperience(
            project_type=project_type,
            outcome="success" if report.metrics.overall_score > 50 else "failure",
            benchmark_score=float(report.metrics.overall_score),
            confidence=0.9,
            lessons=tuple(lessons),
            source_entries=(context.run_id,),
        )

    def build_from_entries(self, entries: tuple[MemoryEntry, ...]) -> EngineeringExperience:
        """Aggregates multiple memory entries into a single experience."""
        if not entries:
            raise ValueError("Cannot build experience from empty entries")

        # Safely extract project type, falling back to 'unknown' if missing or blank
        raw_goal = getattr(entries[0], "goal", "") or ""
        project_type = raw_goal.split()[0].lower() if raw_goal.strip() else "unknown"

        all_lessons = []
        for entry in entries:
            all_lessons.extend(entry.lessons)

        scores = [e.metadata.get("score", 0) for e in entries]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        return EngineeringExperience(
            project_type=project_type,
            outcome="success" if avg_score > 50 else "failure",
            benchmark_score=avg_score,
            confidence=0.8,
            lessons=tuple(all_lessons),
            source_entries=tuple(e.id for e in entries),
        )
