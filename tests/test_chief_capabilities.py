"""Comprehensive tests for the Chief Engineer Capability Discovery (Sprint 7.2)."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from eag.chief.capabilities import (
    Capability,
    CapabilityAnalysis,
    CapabilityCategory,
    CapabilityCost,
    CapabilityMatch,
    CapabilityMetadata,
    CapabilityMetrics,
    CapabilityRegistry,
    CapabilityRisk,
    CapabilityRuntime,
    CapabilityRuntimeState,
    DuplicateCapability,
    Recommender,
)
from eag.chief.capabilities.errors import CapabilityNotFound
from eag.chief.capabilities.matcher import CapabilityMatcher
from eag.chief.capabilities.models import CapabilityRecommendation
from eag.chief.capabilities.ranker import CapabilityRanker
from eag.chief.goals.enums import GoalIntent
from eag.chief.goals.models import EngineeringGoal

# --- Dummy Capabilities for Testing ---


class RenameCapability:
    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="rename_symbol",
            name="Rename Symbol",
            category=CapabilityCategory.TRANSFORMATION,
            supported_languages=("python",),
            estimated_cost=CapabilityCost.TRIVIAL,
            estimated_risk=CapabilityRisk.LOW,
            tags=("rename", "refactor"),
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.primary_intent == GoalIntent.REFACTOR and "rename" in goal.canonical_text

    def score(self, goal: EngineeringGoal) -> float:
        return 1.0 if self.supports(goal) else 0.0

    def requirements(self) -> tuple:
        return ()


class GenerateAppCapability:
    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="generate_app",
            name="Generate Application",
            category=CapabilityCategory.GENERATION,
            supported_languages=("python",),
            estimated_cost=CapabilityCost.HIGH,
            estimated_risk=CapabilityRisk.HIGH,
            requires_llm=True,
            tags=("generate", "build"),
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.primary_intent == GoalIntent.BUILD

    def score(self, goal: EngineeringGoal) -> float:
        return 0.8 if self.supports(goal) else 0.0

    def requirements(self) -> tuple:
        return ()


class FixBugCapability:
    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="fix_bug",
            name="Fix Bug",
            category=CapabilityCategory.TRANSFORMATION,
            supported_languages=("python",),
            estimated_cost=CapabilityCost.MEDIUM,
            estimated_risk=CapabilityRisk.MEDIUM,
            tags=("fix", "bug"),
        )

    def supports(self, goal: EngineeringGoal) -> bool:
        return goal.primary_intent == GoalIntent.BUGFIX

    def score(self, goal: EngineeringGoal) -> float:
        return 0.9 if self.supports(goal) else 0.0

    def requirements(self) -> tuple:
        return ()


@pytest.fixture
def registry() -> CapabilityRegistry:
    reg = CapabilityRegistry()
    reg.register(RenameCapability())
    reg.register(GenerateAppCapability())
    reg.register(FixBugCapability())
    return reg


@dataclass
class MockEventBus:
    """Mock EventBus to record published events for testing."""

    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def runtime(registry: CapabilityRegistry, event_bus: MockEventBus) -> CapabilityRuntime:
    return CapabilityRuntime(registry=registry, event_bus=event_bus)


def make_goal(text: str, intent: GoalIntent = GoalIntent.UNKNOWN) -> EngineeringGoal:
    from eag.chief.goals.models import ChiefGoal, GoalCategory, GoalComplexity

    g = ChiefGoal(raw_text=text)
    return EngineeringGoal(
        original_goal=g,
        canonical_text=text.lower(),
        intents=(intent,),
        primary_intent=intent,
        category=GoalCategory.UNKNOWN,
        complexity=GoalComplexity.SMALL,
        confidence=1.0,
        is_ambiguous=False,
    )


# --- Model Tests (15) ---


class TestCapabilityModels:
    def test_metadata_immutable(self) -> None:
        m = CapabilityMetadata(id="test", name="Test")
        with pytest.raises((AttributeError, TypeError)):
            m.id = "new"  # type: ignore[misc]

    def test_metadata_invalid_id(self) -> None:
        with pytest.raises(ValueError):
            CapabilityMetadata(id="", name="Test")

    def test_metadata_invalid_name(self) -> None:
        with pytest.raises(ValueError):
            CapabilityMetadata(id="test", name="")

    def test_metadata_defaults(self) -> None:
        m = CapabilityMetadata(id="test", name="Test")
        assert m.version == "1.0.0"
        assert m.estimated_cost == CapabilityCost.LOW
        assert m.estimated_risk == CapabilityRisk.LOW
        assert m.supports_preview is True

    def test_match_immutable(self) -> None:
        cap = RenameCapability()
        m = CapabilityMatch(capability=cap, score=1.0)
        with pytest.raises((AttributeError, TypeError)):
            m.score = 0.5  # type: ignore[misc]

    def test_recommendation_immutable(self) -> None:
        rec = CapabilityRecommendation(winner=None, explanation="None")
        with pytest.raises((AttributeError, TypeError)):
            rec.confidence = 1.0  # type: ignore[misc]

    def test_metrics_immutable(self) -> None:
        m = CapabilityMetrics()
        with pytest.raises((AttributeError, TypeError)):
            m.registry_size = 10  # type: ignore[misc]

    def test_analysis_immutable(self) -> None:
        goal = make_goal("test")
        a = CapabilityAnalysis(goal=goal)
        with pytest.raises((AttributeError, TypeError)):
            a.state = CapabilityRuntimeState.FAILED  # type: ignore[misc]

    def test_metadata_tags(self) -> None:
        m = CapabilityMetadata(id="test", name="Test", tags=("a", "b"))
        assert "a" in m.tags

    def test_metadata_supported_languages(self) -> None:
        m = CapabilityMetadata(id="test", name="Test", supported_languages=("python",))
        assert "python" in m.supported_languages

    def test_category_values(self) -> None:
        assert CapabilityCategory.TRANSFORMATION == "transformation"

    def test_cost_values(self) -> None:
        assert CapabilityCost.HIGH == "high"

    def test_risk_values(self) -> None:
        assert CapabilityRisk.MEDIUM == "medium"

    def test_requirement_values(self) -> None:
        from eag.chief.capabilities.enums import CapabilityRequirement

        assert CapabilityRequirement.SOURCE_INDEXED == "source_indexed"

    def test_runtime_state_values(self) -> None:
        assert CapabilityRuntimeState.READY == "ready"


# --- Registry Tests (20) ---


class TestCapabilityRegistry:
    def test_register(self, registry: CapabilityRegistry) -> None:
        assert len(registry.list()) == 3

    def test_duplicate_register_raises(self, registry: CapabilityRegistry) -> None:
        with pytest.raises(DuplicateCapability):
            registry.register(RenameCapability())

    def test_find_success(self, registry: CapabilityRegistry) -> None:
        cap = registry.find("rename_symbol")
        assert isinstance(cap, RenameCapability)

    def test_find_missing_raises(self, registry: CapabilityRegistry) -> None:
        with pytest.raises(CapabilityNotFound):  # <-- Changed here
            registry.find("nonexistent")

    def test_unregister_success(self, registry: CapabilityRegistry) -> None:
        assert registry.unregister("rename_symbol") is True
        assert len(registry.list()) == 2

    def test_unregister_missing(self, registry: CapabilityRegistry) -> None:
        assert registry.unregister("nonexistent") is False

    def test_list_returns_tuple(self, registry: CapabilityRegistry) -> None:
        caps = registry.list()
        assert isinstance(caps, tuple)

    def test_search_by_name(self, registry: CapabilityRegistry) -> None:
        results = registry.search("Rename")
        assert len(results) == 1
        assert results[0].metadata.id == "rename_symbol"

    def test_search_by_id(self, registry: CapabilityRegistry) -> None:
        results = registry.search("generate_app")
        assert len(results) == 1

    def test_search_by_tag(self, registry: CapabilityRegistry) -> None:
        results = registry.search("bug")
        assert len(results) == 1
        assert results[0].metadata.id == "fix_bug"

    def test_search_no_results(self, registry: CapabilityRegistry) -> None:
        results = registry.search("nonexistent")
        assert len(results) == 0

    def test_search_case_insensitive(self, registry: CapabilityRegistry) -> None:
        results = registry.search("RENAME")
        assert len(results) == 1

    def test_empty_registry_list(self) -> None:
        reg = CapabilityRegistry()
        assert reg.list() == ()

    def test_empty_registry_search(self) -> None:
        reg = CapabilityRegistry()
        assert reg.search("test") == ()

    def test_register_multiple(self) -> None:
        reg = CapabilityRegistry()
        reg.register(RenameCapability())
        reg.register(GenerateAppCapability())
        assert len(reg.list()) == 2

    def test_unregister_then_register(self, registry: CapabilityRegistry) -> None:
        registry.unregister("rename_symbol")
        registry.register(RenameCapability())
        assert len(registry.list()) == 3

    def test_find_returns_protocol(self, registry: CapabilityRegistry) -> None:
        cap = registry.find("rename_symbol")
        assert isinstance(cap, Capability)

    def test_list_contains_all(self, registry: CapabilityRegistry) -> None:
        caps = registry.list()
        ids = [c.metadata.id for c in caps]
        assert "rename_symbol" in ids
        assert "generate_app" in ids
        assert "fix_bug" in ids

    def test_search_partial_match(self, registry: CapabilityRegistry) -> None:
        results = registry.search("gen")
        assert len(results) == 1

    def test_search_empty_string(self, registry: CapabilityRegistry) -> None:
        results = registry.search("")
        assert len(results) == 3


# --- Matcher Tests (20) ---


class TestCapabilityMatcher:
    def test_match_rename(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("Rename class Foo to Bar", GoalIntent.REFACTOR)
        matches = matcher.match(goal)
        assert len(matches) == 1
        assert matches[0].capability.metadata.id == "rename_symbol"
        assert matches[0].score == 1.0

    def test_match_build(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("Build an app", GoalIntent.BUILD)
        matches = matcher.match(goal)
        assert len(matches) == 1
        assert matches[0].capability.metadata.id == "generate_app"
        assert matches[0].score == 0.8

    def test_match_bugfix(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("Fix the auth bug", GoalIntent.BUGFIX)
        matches = matcher.match(goal)
        assert len(matches) == 1
        assert matches[0].capability.metadata.id == "fix_bug"
        assert matches[0].score == 0.9

    def test_match_unknown_intent(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("Do something weird", GoalIntent.UNKNOWN)
        matches = matcher.match(goal)
        assert len(matches) == 0

    def test_match_returns_list(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("Build app", GoalIntent.BUILD)
        matches = matcher.match(goal)
        assert isinstance(matches, list)

    def test_match_reason_set(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("Build app", GoalIntent.BUILD)
        matches = matcher.match(goal)
        assert "Supported by" in matches[0].reason

    def test_match_score_0_if_not_supported(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("Do something weird", GoalIntent.UNKNOWN)
        matches = matcher.match(goal)
        assert len(matches) == 0

    def test_match_multiple_capabilities(self) -> None:
        class Cap1:
            @property
            def metadata(self):
                return CapabilityMetadata(id="c1", name="C1")

            def supports(self, g):
                return True

            def score(self, g):
                return 0.5

            def requirements(self):
                return ()

        class Cap2:
            @property
            def metadata(self):
                return CapabilityMetadata(id="c2", name="C2")

            def supports(self, g):
                return True

            def score(self, g):
                return 0.8

            def requirements(self):
                return ()

        reg = CapabilityRegistry()
        reg.register(Cap1())
        reg.register(Cap2())
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        matches = matcher.match(goal)
        assert len(matches) == 2

    def test_match_empty_registry(self) -> None:
        reg = CapabilityRegistry()
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        matches = matcher.match(goal)
        assert len(matches) == 0

    def test_match_determinism(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("Build app", GoalIntent.BUILD)
        m1 = matcher.match(goal)
        m2 = matcher.match(goal)
        assert m1 == m2


# --- Ranker Tests (15) ---


class TestCapabilityRanker:
    def test_rank_sorts_by_score(self) -> None:
        cap1 = RenameCapability()
        cap2 = GenerateAppCapability()
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=0.8)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m2, m1])
        assert ranked[0].score >= ranked[1].score

    def test_rank_applies_risk_penalty(self) -> None:
        class HighRiskCap:
            @property
            def metadata(self):
                return CapabilityMetadata(id="hr", name="HR", estimated_risk=CapabilityRisk.HIGH)

            def supports(self, g):
                return True

            def score(self, g):
                return 1.0

            def requirements(self):
                return ()

        class LowRiskCap:
            @property
            def metadata(self):
                return CapabilityMetadata(id="lr", name="LR", estimated_risk=CapabilityRisk.LOW)

            def supports(self, g):
                return True

            def score(self, g):
                return 1.0

            def requirements(self):
                return ()

        m1 = CapabilityMatch(capability=HighRiskCap(), score=1.0)
        m2 = CapabilityMatch(capability=LowRiskCap(), score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        # Low risk should rank higher due to penalty on high risk
        assert ranked[0].capability.metadata.id == "lr"

    def test_rank_applies_cost_penalty(self) -> None:
        class HighCostCap:
            @property
            def metadata(self):
                return CapabilityMetadata(id="hc", name="HC", estimated_cost=CapabilityCost.HIGH)

            def supports(self, g):
                return True

            def score(self, g):
                return 1.0

            def requirements(self):
                return ()

        class LowCostCap:
            @property
            def metadata(self):
                return CapabilityMetadata(id="lc", name="LC", estimated_cost=CapabilityCost.LOW)

            def supports(self, g):
                return True

            def score(self, g):
                return 1.0

            def requirements(self):
                return ()

        m1 = CapabilityMatch(capability=HighCostCap(), score=1.0)
        m2 = CapabilityMatch(capability=LowCostCap(), score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        assert ranked[0].capability.metadata.id == "lc"

    def test_rank_empty_list(self) -> None:
        ranker = CapabilityRanker()
        assert ranker.rank([]) == []

    def test_rank_single_item(self) -> None:
        cap = RenameCapability()
        m = CapabilityMatch(capability=cap, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m])
        assert len(ranked) == 1

    def test_rank_penalty_does_not_go_negative(self) -> None:
        class BadCap:
            @property
            def metadata(self):
                return CapabilityMetadata(
                    id="bad",
                    name="Bad",
                    estimated_cost=CapabilityCost.HIGH,
                    estimated_risk=CapabilityRisk.HIGH,
                )

            def supports(self, g):
                return True

            def score(self, g):
                return 0.1

            def requirements(self):
                return ()

        m = CapabilityMatch(capability=BadCap(), score=0.1)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m])
        assert ranked[0].score >= 0.0


# --- Recommender Tests (15) ---


class TestRecommender:
    def test_recommend_winner(self) -> None:
        cap = RenameCapability()
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert r.winner is not None
        assert r.winner.capability.metadata.id == "rename_symbol"

    def test_recommend_no_matches(self) -> None:
        rec = Recommender()
        r = rec.recommend([])
        assert r.winner is None
        assert "No capabilities" in r.explanation

    def test_recommend_alternatives(self) -> None:
        cap1 = RenameCapability()
        cap2 = GenerateAppCapability()
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=0.8)
        rec = Recommender()
        r = rec.recommend([m1, m2])
        assert len(r.alternatives) == 1
        assert r.alternatives[0].capability.metadata.id == "generate_app"

    def test_recommend_confidence(self) -> None:
        cap = RenameCapability()
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert r.confidence == 1.0

    def test_recommend_warning_high_risk(self) -> None:
        cap = GenerateAppCapability()  # High risk
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert len(r.warnings) > 0
        assert "risk" in r.warnings[0].lower()

    def test_recommend_warning_llm(self) -> None:
        cap = GenerateAppCapability()  # requires_llm=True
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert any("LLM" in w for w in r.warnings)

    def test_recommend_no_warnings_low_risk(self) -> None:
        cap = RenameCapability()  # Low risk, no LLM
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert len(r.warnings) == 0


# --- Runtime Tests (25) ---


class TestCapabilityRuntime:
    def test_runtime_analyze_build(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build an app", GoalIntent.BUILD)
        analysis = runtime.analyze(goal)
        assert analysis.recommendation is not None
        assert analysis.recommendation.winner is not None
        assert analysis.recommendation.winner.capability.metadata.id == "generate_app"

    def test_runtime_analyze_rename(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Rename class Foo to Bar", GoalIntent.REFACTOR)
        analysis = runtime.analyze(goal)
        assert analysis.recommendation is not None
        assert analysis.recommendation.winner.capability.metadata.id == "rename_symbol"

    def test_runtime_analyze_no_match(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Do something weird", GoalIntent.UNKNOWN)
        analysis = runtime.analyze(goal)
        assert analysis.recommendation is not None
        assert analysis.recommendation.winner is None

    def test_runtime_state_complete(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD)
        runtime.analyze(goal)
        assert runtime.state == CapabilityRuntimeState.COMPLETE

    def test_runtime_metrics_populated(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD)
        analysis = runtime.analyze(goal)
        assert analysis.metrics.registry_size == 3
        assert analysis.metrics.candidates_count == 1
        assert analysis.metrics.matching_time_ms > 0

    def test_runtime_events_published(
        self, runtime: CapabilityRuntime, event_bus: MockEventBus
    ) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD)
        runtime.analyze(goal)
        # EventBus is synchronous, so events should be in the mock list
        assert len(event_bus.published_events) > 0

        # Verify event types
        event_types = [type(e) for e in event_bus.published_events]
        from eag.chief.capabilities.events import (
            CapabilityMatched,
            CapabilityRanked,
            RecommendationProduced,
        )

        assert CapabilityMatched in event_types
        assert CapabilityRanked in event_types
        assert RecommendationProduced in event_types

    def test_runtime_candidates_tuple(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD)
        analysis = runtime.analyze(goal)
        assert isinstance(analysis.candidates, tuple)

    def test_runtime_recommendation_type(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD)
        analysis = runtime.analyze(goal)
        assert analysis.recommendation is not None

    def test_runtime_metrics_type(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD)
        analysis = runtime.analyze(goal)
        assert isinstance(analysis.metrics, CapabilityMetrics)

    def test_runtime_analysis_type(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD)
        analysis = runtime.analyze(goal)
        assert isinstance(analysis, CapabilityAnalysis)
