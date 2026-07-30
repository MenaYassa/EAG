"""Model selector for EAG Chief Engineer."""

from eag.chief.intelligence.enums import SelectionReason
from eag.chief.intelligence.errors import NoMatchingModelError
from eag.chief.intelligence.matcher import RequirementMatcher
from eag.chief.intelligence.models import (
    ExecutionRequest,
    ModelProfile,
    ProviderProfile,
    SelectionDecision,
)
from eag.chief.intelligence.scorer import TraitScorer


class ModelSelector:
    """Selects the best AI model for a given execution request."""

    def __init__(
        self, matcher: RequirementMatcher | None = None, scorer: TraitScorer | None = None
    ) -> None:
        self._matcher = matcher or RequirementMatcher()
        self._scorer = scorer or TraitScorer()

    def select(
        self,
        request: ExecutionRequest,
        models: tuple[ModelProfile, ...],
        providers: tuple[ProviderProfile, ...],
    ) -> SelectionDecision:
        candidates: list[tuple[float, ModelProfile, any, any]] = []
        rejections: list[str] = []

        provider_map = {p.id: p for p in providers if p.status == "online"}

        for model in models:
            if model.status != "available":
                continue
            if model.provider_id not in provider_map:
                rejections.append(f"{model.id}: provider offline")
                continue

            match_result = self._matcher.match(request.requirements, model)
            if not match_result.compatible:
                rejections.append(f"{model.id}: {'; '.join(match_result.rejected)}")
                continue

            score_breakdown = self._scorer.score(request.requirements, model, request.policy)
            candidates.append((score_breakdown.total, model, match_result, score_breakdown))

        if not candidates:
            raise NoMatchingModelError(
                "No suitable AI models found matching the requirements.", reasons=rejections
            )

        # Sort by score descending, then by model ID for deterministic tie-breaking
        candidates.sort(key=lambda x: (-x[0], x[1].id))

        best_score, best_model, best_match, best_breakdown = candidates[0]
        best_provider = provider_map[best_model.provider_id]

        reasons = [SelectionReason.TRAIT_MATCH, SelectionReason.POLICY_MATCH]
        alternatives = tuple(c[1] for c in candidates[1:])

        return SelectionDecision(
            model=best_model,
            provider=best_provider,
            confidence=best_score,
            score=best_score,
            reasons=tuple(reasons),
            alternatives=alternatives,
            match_result=best_match,
            score_breakdown=best_breakdown,
        )
