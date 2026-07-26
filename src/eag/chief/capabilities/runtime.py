"""Capability runtime for EAG Chief Engineer."""

import time

from eag.chief.capabilities.enums import CapabilityRuntimeState
from eag.chief.capabilities.events import (
    CapabilityMatched,
    CapabilityRanked,
    RecommendationProduced,
)
from eag.chief.capabilities.matcher import CapabilityMatcher
from eag.chief.capabilities.models import CapabilityAnalysis, CapabilityMetrics
from eag.chief.capabilities.ranker import CapabilityRanker
from eag.chief.capabilities.recommender import Recommender
from eag.chief.capabilities.registry import CapabilityRegistry
from eag.chief.goals.models import EngineeringGoal
from eag.events import EventBus


class CapabilityRuntime:
    """Orchestrates the capability discovery pipeline."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        event_bus: EventBus,
        matcher: CapabilityMatcher | None = None,
        ranker: CapabilityRanker | None = None,
        recommender: Recommender | None = None,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus
        self._matcher = matcher or CapabilityMatcher(registry)
        self._ranker = ranker or CapabilityRanker()
        self._recommender = recommender or Recommender()
        self._state = CapabilityRuntimeState.READY

    @property
    def state(self) -> CapabilityRuntimeState:
        return self._state

    def analyze(self, goal: EngineeringGoal) -> CapabilityAnalysis:
        """Analyze a goal and produce a capability recommendation."""
        start_time = time.monotonic()

        # 1. Matching
        self._state = CapabilityRuntimeState.MATCHING
        matches = self._matcher.match(goal)
        for m in matches:
            self._event_bus.publish(
                CapabilityMatched(
                    goal_id=goal.id, capability_id=m.capability.metadata.id, score=m.score
                )
            )

        match_time = (time.monotonic() - start_time) * 1000

        # 2. Ranking
        self._state = CapabilityRuntimeState.RANKING
        rank_start = time.monotonic()
        ranked = self._ranker.rank(matches)
        rank_time = (time.monotonic() - rank_start) * 1000
        self._event_bus.publish(CapabilityRanked(goal_id=goal.id, ranked_count=len(ranked)))

        # 3. Recommendation
        rec_start = time.monotonic()
        recommendation = self._recommender.recommend(ranked)
        rec_time = (time.monotonic() - rec_start) * 1000

        winner_id = recommendation.winner.capability.metadata.id if recommendation.winner else None
        self._event_bus.publish(
            RecommendationProduced(
                goal_id=goal.id, winner_id=winner_id, confidence=recommendation.confidence
            )
        )

        metrics = CapabilityMetrics(
            registry_size=len(self._registry.list()),
            matching_time_ms=match_time,
            ranking_time_ms=rank_time,
            recommendation_time_ms=rec_time,
            candidates_count=len(ranked),
            rejected_count=0,  # Not tracking explicitly rejected in this simplified flow
            confidence=recommendation.confidence,
        )

        self._state = CapabilityRuntimeState.COMPLETE
        return CapabilityAnalysis(
            goal=goal,
            candidates=tuple(ranked),
            recommendation=recommendation,
            metrics=metrics,
            state=self._state,
        )
