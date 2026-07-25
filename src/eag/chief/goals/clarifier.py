"""Clarification engine for EAG Chief Engineer."""

from eag.chief.goals.enums import GoalIntent
from eag.chief.goals.models import Clarification, Requirement


class ClarificationEngine:
    """Generates clarifications for missing requirements and ambiguity."""

    _QUESTIONS: dict[str, str] = {
        "frontend": "Which frontend framework should be used?",
        "backend": "Which backend framework should be used?",
        "database": "Which database should be used?",
        "authentication": "What authentication method should be used?",
        "deployment": "What deployment platform should be used?",
    }

    def clarify(
        self,
        missing_reqs: tuple[Requirement, ...],
        intents: tuple[GoalIntent, ...],
        is_ambiguous: bool,
    ) -> tuple[Clarification, ...]:
        clarifications: list[Clarification] = []

        for req in missing_reqs:
            q = self._QUESTIONS.get(req.key, f"Please specify the requirement for {req.key}.")
            clarifications.append(
                Clarification(
                    question=q,
                    intent=intents[0] if intents else GoalIntent.UNKNOWN,
                    priority=1,
                    related_requirement=req.key,
                )
            )

        if is_ambiguous:
            clarifications.append(
                Clarification(
                    question=(
                        "The goal is ambiguous. "
                        "Could you provide more specific engineering details?"
                    ),
                    intent=intents[0] if intents else GoalIntent.UNKNOWN,
                    priority=10,
                )
            )

        return tuple(clarifications)
