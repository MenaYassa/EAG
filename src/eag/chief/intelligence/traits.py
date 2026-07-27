"""AI Traits for EAG."""

from dataclasses import dataclass

from eag.chief.intelligence.enums import (
    AIContextSize,
    AIReasoningLevel,
    AISpeed,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AITraits:
    """Describes how well a model behaves across graded characteristics."""
    reasoning: AIReasoningLevel = AIReasoningLevel.MEDIUM
    coding: AIReasoningLevel = AIReasoningLevel.MEDIUM
    vision: AIReasoningLevel = AIReasoningLevel.NONE
    embeddings: AIReasoningLevel = AIReasoningLevel.NONE
    context: AIContextSize = AIContextSize.MEDIUM
    speed: AISpeed = AISpeed.MEDIUM
    creativity: AIReasoningLevel = AIReasoningLevel.MEDIUM
    determinism: AIReasoningLevel = AIReasoningLevel.MEDIUM

    def __post_init__(self) -> None:
        if not isinstance(self.reasoning, AIReasoningLevel):
            raise TypeError("reasoning must be an AIReasoningLevel")
        if not isinstance(self.coding, AIReasoningLevel):
            raise TypeError("coding must be an AIReasoningLevel")
        if not isinstance(self.vision, AIReasoningLevel):
            raise TypeError("vision must be an AIReasoningLevel")
        if not isinstance(self.embeddings, AIReasoningLevel):
            raise TypeError("embeddings must be an AIReasoningLevel")
        if not isinstance(self.context, AIContextSize):
            raise TypeError("context must be an AIContextSize")
        if not isinstance(self.speed, AISpeed):
            raise TypeError("speed must be an AISpeed")
        if not isinstance(self.creativity, AIReasoningLevel):
            raise TypeError("creativity must be an AIReasoningLevel")
        if not isinstance(self.determinism, AIReasoningLevel):
            raise TypeError("determinism must be an AIReasoningLevel")