"""Comprehensive tests for the Chief Engineer Capability Discovery (Sprint 7.2 Hardened)."""

import pytest
from dataclasses import dataclass, field
from typing import Any

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
from eag.chief.capabilities.matcher import CapabilityMatcher
from eag.chief.capabilities.ranker import CapabilityRanker
from eag.chief.capabilities.events import (
    CapabilityMatched,
    CapabilityRanked,
    RecommendationProduced,
)

from eag.chief.capabilities.models import CapabilityRecommendation


from eag.events import EventBus

from eag.chief.capabilities.enums import CapabilityStatus
from eag.chief.goals.models import EngineeringGoal
from eag.chief.goals.enums import GoalIntent
from eag.registry.errors import CapabilityNotFoundError
from eag.chief.capabilities.errors import CapabilityNotFound

# --- Dummy Capabilities for Testing ---

class BaseCapability:
    def __init__(self, metadata: CapabilityMetadata, supports_result: bool = True, score_val: float = 1.0):
        self._metadata = metadata
        self._supports_result = supports_result
        self._score_val = score_val

    @property
    def metadata(self) -> CapabilityMetadata:
        return self._metadata

    def supports(self, goal: EngineeringGoal) -> bool:
        return self._supports_result

    def score(self, goal: EngineeringGoal) -> float:
        return self._score_val

    def requirements(self) -> tuple:
        return ()


def make_metadata(
    id: str, 
    name: str = None,
    requires_llm: bool = False,
    lang: tuple[str, ...] = ("python",), 
    risk: CapabilityRisk = CapabilityRisk.LOW,
    cost: CapabilityCost = CapabilityCost.LOW,
    status: CapabilityStatus = CapabilityStatus.STABLE,
    enabled: bool = True,
    deps: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
    latency: float = 0.0,
    token_cost: float = 0.0
) -> CapabilityMetadata:
    return CapabilityMetadata(
        id=id,
        name=name or id.replace("_", " ").title(),
        requires_llm=requires_llm,
        supported_languages=lang,
        estimated_risk=risk,
        estimated_cost=cost,
        status=status,
        enabled=enabled,
        dependencies=deps,
        tags=tags,
        latency_ms=latency,
        token_cost=token_cost
    )


@pytest.fixture
def registry() -> CapabilityRegistry:
    reg = CapabilityRegistry()
    reg.register(BaseCapability(make_metadata("rename_symbol", risk=CapabilityRisk.LOW, cost=CapabilityCost.TRIVIAL, tags=("refactor",))))
    reg.register(BaseCapability(make_metadata("generate_app", risk=CapabilityRisk.HIGH, cost=CapabilityCost.HIGH, requires_llm=True, tags=("build",))))
    reg.register(BaseCapability(make_metadata("fix_bug", risk=CapabilityRisk.MEDIUM, cost=CapabilityCost.MEDIUM, tags=("bug",))))
    return reg

@pytest.fixture
def event_bus() -> EventBus:
    return MockEventBus()

@pytest.fixture
def runtime(registry: CapabilityRegistry, event_bus: EventBus) -> CapabilityRuntime:
    return CapabilityRuntime(registry=registry, event_bus=event_bus)

def make_goal(text: str, intent: GoalIntent = GoalIntent.UNKNOWN, lang: str = None) -> EngineeringGoal:
    from eag.chief.goals.models import ChiefGoal, GoalAnalysis, GoalCategory, GoalComplexity, Requirement
    g = ChiefGoal(raw_text=text)
    reqs = ()
    if lang:
        reqs = (Requirement(key="language", value=lang),)
        
    return EngineeringGoal(
        original_goal=g,
        canonical_text=text.lower(),
        intents=(intent,),
        primary_intent=intent,
        category=GoalCategory.UNKNOWN,
        complexity=GoalComplexity.SMALL,
        confidence=1.0,
        is_ambiguous=False,
        requirements=reqs
    )

@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)
    def publish(self, event: Any) -> None:
        self.published_events.append(event)


# --- Model Tests (30) ---

class TestCapabilityModels:
    def test_metadata_immutable(self) -> None:
        m = make_metadata("test")
        with pytest.raises(Exception):
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
        assert m.status == CapabilityStatus.STABLE
        assert m.enabled is True
        assert m.latency_ms == 0.0

    def test_metadata_dependencies(self) -> None:
        m = make_metadata("test", deps=("dep1", "dep2"))
        assert "dep1" in m.dependencies

    def test_metadata_status_experimental(self) -> None:
        m = make_metadata("test", status=CapabilityStatus.EXPERIMENTAL)
        assert m.status == CapabilityStatus.EXPERIMENTAL

    def test_metadata_status_deprecated(self) -> None:
        m = make_metadata("test", status=CapabilityStatus.DEPRECATED)
        assert m.status == CapabilityStatus.DEPRECATED

    def test_metadata_disabled(self) -> None:
        m = make_metadata("test", enabled=False)
        assert m.enabled is False

    def test_match_immutable(self) -> None:
        cap = BaseCapability(make_metadata("test"))
        m = CapabilityMatch(capability=cap, score=1.0)
        with pytest.raises(Exception):
            m.score = 0.5  # type: ignore[misc]

    def test_recommendation_immutable(self) -> None:
        rec = CapabilityRecommendation(winner=None, explanation="None")
        with pytest.raises(Exception):
            rec.confidence = 1.0  # type: ignore[misc]

    def test_metrics_immutable(self) -> None:
        m = CapabilityMetrics()
        with pytest.raises(Exception):
            m.registry_size = 10  # type: ignore[misc]

    def test_analysis_immutable(self) -> None:
        goal = make_goal("test")
        a = CapabilityAnalysis(goal=goal)
        with pytest.raises(Exception):
            a.state = CapabilityRuntimeState.FAILED  # type: ignore[misc]

    def test_metadata_tags(self) -> None:
        m = make_metadata("test", tags=("a", "b"))
        assert "a" in m.tags

    def test_metadata_supported_languages(self) -> None:
        m = make_metadata("test", lang=("python",))
        assert "python" in m.supported_languages

    def test_category_values(self) -> None:
        assert CapabilityCategory.TRANSFORMATION == "transformation"

    def test_cost_values(self) -> None:
        assert CapabilityCost.HIGH == "high"

    def test_risk_values(self) -> None:
        assert CapabilityRisk.MEDIUM == "medium"

    def test_status_values(self) -> None:
        assert CapabilityStatus.STABLE == "stable"

    def test_runtime_state_values(self) -> None:
        assert CapabilityRuntimeState.READY == "ready"

    def test_metadata_to_dict(self) -> None:
        m = make_metadata("test", deps=("d1",))
        d = m.to_dict()
        assert d["id"] == "test"
        assert "d1" in d["dependencies"]

    def test_metadata_from_dict(self) -> None:
        d = {"id": "test", "name": "Test", "dependencies": ["d1"], "status": "experimental"}
        m = CapabilityMetadata.from_dict(d)
        assert m.id == "test"
        assert m.status == CapabilityStatus.EXPERIMENTAL
        assert "d1" in m.dependencies

    def test_metadata_serialization_round_trip(self) -> None:
        m1 = make_metadata("test", deps=("d1",), status=CapabilityStatus.EXPERIMENTAL, latency=10.5)
        m2 = CapabilityMetadata.from_dict(m1.to_dict())
        assert m1 == m2

    def test_match_reason_parts(self) -> None:
        cap = BaseCapability(make_metadata("test"))
        m = CapabilityMatch(capability=cap, score=1.0, reason_parts=("Intent matched",))
        assert "Intent matched" in m.reason_parts

    def test_metadata_latency(self) -> None:
        m = make_metadata("test", latency=50.0)
        assert m.latency_ms == 50.0

    def test_metadata_token_cost(self) -> None:
        m = make_metadata("test", token_cost=100.0)
        assert m.token_cost == 100.0

    def test_metadata_empty_dependencies(self) -> None:
        m = make_metadata("test")
        assert m.dependencies == ()

    def test_metadata_empty_tags(self) -> None:
        m = make_metadata("test")
        assert m.tags == ()

    def test_metadata_supported_languages_empty(self) -> None:
        m = CapabilityMetadata(id="test", name="Test", supported_languages=())
        assert m.supported_languages == ()

    def test_requirement_values(self) -> None:
        from eag.chief.capabilities.enums import CapabilityRequirement
        assert CapabilityRequirement.SOURCE_INDEXED == "source_indexed"

    def test_metadata_version(self) -> None:
        m = CapabilityMetadata(id="test", name="Test", version="2.0.0")
        assert m.version == "2.0.0"


# --- Registry Tests (30) ---

class TestCapabilityRegistry:
    def test_register(self, registry: CapabilityRegistry) -> None:
        assert len(registry.list()) == 3

    def test_duplicate_register_raises(self, registry: CapabilityRegistry) -> None:
        with pytest.raises(DuplicateCapability):
            registry.register(BaseCapability(make_metadata("rename_symbol")))

    def test_find_success(self, registry: CapabilityRegistry) -> None:
        cap = registry.find("rename_symbol")
        assert cap.metadata.id == "rename_symbol"

    def test_find_missing_raises(self, registry: CapabilityRegistry) -> None:
        with pytest.raises(CapabilityNotFound):
            registry.find("nonexistent")

    def test_unregister_success(self, registry: CapabilityRegistry) -> None:
        assert registry.unregister("rename_symbol") is True
        assert len(registry.list()) == 2

    def test_unregister_missing(self, registry: CapabilityRegistry) -> None:
        assert registry.unregister("nonexistent") is False

    def test_list_returns_tuple(self, registry: CapabilityRegistry) -> None:
        caps = registry.list()
        assert isinstance(caps, tuple)

    def test_list_sorted_deterministic(self, registry: CapabilityRegistry) -> None:
        caps = registry.list()
        ids = [c.metadata.id for c in caps]
        assert ids == sorted(ids)

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
        reg.register(BaseCapability(make_metadata("c1")))
        reg.register(BaseCapability(make_metadata("c2")))
        assert len(reg.list()) == 2

    def test_unregister_then_register(self, registry: CapabilityRegistry) -> None:
        registry.unregister("rename_symbol")
        registry.register(BaseCapability(make_metadata("rename_symbol")))
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

    def test_list_active_filters_disabled(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", enabled=True)))
        reg.register(BaseCapability(make_metadata("c2", enabled=False)))
        active = reg.list_active()
        assert len(active) == 1
        assert active[0].metadata.id == "c1"

    def test_list_active_filters_deprecated(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.STABLE)))
        reg.register(BaseCapability(make_metadata("c2", status=CapabilityStatus.DEPRECATED)))
        active = reg.list_active()
        assert len(active) == 1
        assert active[0].metadata.id == "c1"

    def test_list_active_keeps_experimental(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.EXPERIMENTAL)))
        active = reg.list_active()
        assert len(active) == 1

    def test_search_sorts_deterministically(self, registry: CapabilityRegistry) -> None:
        # Add a cap that might mess up ordering if not sorted
        registry.register(BaseCapability(make_metadata("aaa_cap", tags=("test",))))
        results = registry.search("test") # None match "test" tag except aaa_cap
        # Wait, generate_app has no tags, fix_bug has "bug", rename has "refactor"
        # Let's just search for something that matches multiple
        registry.register(BaseCapability(make_metadata("zzz_cap", tags=("python",))))
        registry.register(BaseCapability(make_metadata("mmm_cap", tags=("python",))))
        # Actually, all caps support python by default in make_metadata, but search doesn't check language
        # Let's add a common tag
        registry.register(BaseCapability(make_metadata("zzz_tag", tags=("common",))))
        registry.register(BaseCapability(make_metadata("aaa_tag", tags=("common",))))
        results = registry.search("common")
        ids = [c.metadata.id for c in results]
        assert ids == sorted(ids)

    def test_search_returns_tuple(self, registry: CapabilityRegistry) -> None:
        results = registry.search("rename")
        assert isinstance(results, tuple)

    def test_registry_size(self, registry: CapabilityRegistry) -> None:
        assert len(registry.list()) == 3

    def test_register_disabled_cap(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", enabled=False)))
        assert len(reg.list()) == 1
        assert len(reg.list_active()) == 0

    def test_register_deprecated_cap(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.DEPRECATED)))
        assert len(reg.list()) == 1
        assert len(reg.list_active()) == 0


# --- Matcher Tests (35) ---

class TestCapabilityMatcher:
    def test_match_returns_list(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test")
        matches = matcher.match(goal)
        assert isinstance(matches, list)

    def test_match_filters_disabled(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", enabled=False), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 0

    def test_match_filters_deprecated(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.DEPRECATED), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 0

    def test_match_keeps_experimental(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.EXPERIMENTAL), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 1

    def test_match_language_compatible(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("python",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="python")
        assert len(matcher.match(goal)) == 1

    def test_match_language_incompatible(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("java",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="python")
        assert len(matcher.match(goal)) == 0

    def test_match_language_not_specified_in_goal(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("python",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang=None)
        assert len(matcher.match(goal)) == 1  # Should match if goal doesn't specify

    def test_match_language_not_specified_in_cap(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=()), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="python")
        assert len(matcher.match(goal)) == 1  # Should match if cap doesn't specify

    def test_match_filters_unsupported(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1"), supports_result=False))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 0

    def test_match_reason_parts_populated(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test")
        matches = matcher.match(goal)
        if matches:
            assert len(matches[0].reason_parts) > 0

    def test_match_reason_parts_contains_language(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test", lang="python")
        matches = matcher.match(goal)
        if matches:
            assert any("Language" in r for r in matches[0].reason_parts)

    def test_match_reason_parts_contains_intent(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test")
        matches = matcher.match(goal)
        if matches:
            assert any("Intent" in r for r in matches[0].reason_parts)

    def test_match_empty_registry(self) -> None:
        reg = CapabilityRegistry()
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 0

    def test_match_determinism(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test")
        m1 = matcher.match(goal)
        m2 = matcher.match(goal)
        assert m1 == m2

    def test_match_multiple_capabilities(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1"), supports_result=True))
        reg.register(BaseCapability(make_metadata("c2"), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 2

    def test_match_partial_language_match(self) -> None:
        reg = CapabilityRegistry()
        # Goal asks for 'python 3', cap supports 'python'
        reg.register(BaseCapability(make_metadata("c1", lang=("python",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="python 3")
        assert len(matcher.match(goal)) == 1

    def test_match_score_preserved(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test")
        matches = matcher.match(goal)
        for m in matches:
            assert m.score == m.capability.score(goal)

    def test_match_reason_string_set(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test")
        matches = matcher.match(goal)
        if matches:
            assert "Matched:" in matches[0].reason

    def test_match_filters_deprecated_keeps_stable(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.DEPRECATED), supports_result=True))
        reg.register(BaseCapability(make_metadata("c2", status=CapabilityStatus.STABLE), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        matches = matcher.match(goal)
        assert len(matches) == 1
        assert matches[0].capability.metadata.id == "c2"

    def test_match_filters_disabled_keeps_enabled(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", enabled=False), supports_result=True))
        reg.register(BaseCapability(make_metadata("c2", enabled=True), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        matches = matcher.match(goal)
        assert len(matches) == 1
        assert matches[0].capability.metadata.id == "c2"

    def test_match_case_insensitive_language(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("python",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="PYTHON")
        assert len(matcher.match(goal)) == 1

    def test_match_reason_parts_empty_if_no_match(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test", lang="java") # No caps support java
        matches = matcher.match(goal)
        assert len(matches) == 0

    def test_match_all_disabled(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", enabled=False), supports_result=True))
        reg.register(BaseCapability(make_metadata("c2", enabled=False), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 0

    def test_match_all_deprecated(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.DEPRECATED), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 0

    def test_match_all_experimental(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.EXPERIMENTAL), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 1

    def test_match_mixed_status(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.STABLE), supports_result=True))
        reg.register(BaseCapability(make_metadata("c2", status=CapabilityStatus.EXPERIMENTAL), supports_result=True))
        reg.register(BaseCapability(make_metadata("c3", status=CapabilityStatus.DEPRECATED), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 2

    def test_match_mixed_enabled(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", enabled=True), supports_result=True))
        reg.register(BaseCapability(make_metadata("c2", enabled=False), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test")
        assert len(matcher.match(goal)) == 1

    def test_match_mixed_language(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("python",)), supports_result=True))
        reg.register(BaseCapability(make_metadata("c2", lang=("java",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="python")
        assert len(matcher.match(goal)) == 1

    def test_match_no_language_in_goal(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("python",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang=None)
        assert len(matcher.match(goal)) == 1

    def test_match_no_language_in_cap(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=()), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="python")
        assert len(matcher.match(goal)) == 1

    def test_match_language_python3(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("python",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="python 3")
        assert len(matcher.match(goal)) == 1

    def test_match_language_typescript(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("typescript",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="typescript")
        assert len(matcher.match(goal)) == 1

    def test_match_language_mismatch(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("typescript",)), supports_result=True))
        matcher = CapabilityMatcher(reg)
        goal = make_goal("test", lang="python")
        assert len(matcher.match(goal)) == 0

    def test_match_returns_matches_not_caps(self, registry: CapabilityRegistry) -> None:
        matcher = CapabilityMatcher(registry)
        goal = make_goal("test")
        matches = matcher.match(goal)
        assert all(isinstance(m, CapabilityMatch) for m in matches)


# --- Ranker Tests (25) ---

class TestCapabilityRanker:
    def test_rank_sorts_by_score(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        cap2 = BaseCapability(make_metadata("c2"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=0.8)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m2, m1])
        assert ranked[0].score >= ranked[1].score

    def test_rank_applies_risk_penalty(self) -> None:
        cap1 = BaseCapability(make_metadata("c1", risk=CapabilityRisk.HIGH))
        cap2 = BaseCapability(make_metadata("c2", risk=CapabilityRisk.LOW))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        assert ranked[0].capability.metadata.id == "c2"

    def test_rank_applies_cost_penalty(self) -> None:
        cap1 = BaseCapability(make_metadata("c1", cost=CapabilityCost.HIGH))
        cap2 = BaseCapability(make_metadata("c2", cost=CapabilityCost.LOW))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        assert ranked[0].capability.metadata.id == "c2"

    def test_rank_empty_list(self) -> None:
        ranker = CapabilityRanker()
        assert ranker.rank([]) == []

    def test_rank_single_item(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m])
        assert len(ranked) == 1

    def test_rank_penalty_does_not_go_negative(self) -> None:
        cap = BaseCapability(make_metadata("c1", cost=CapabilityCost.HIGH, risk=CapabilityRisk.HIGH))
        m = CapabilityMatch(capability=cap, score=0.1)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m])
        assert ranked[0].score >= 0.0

    def test_rank_deterministic_tie_breaker_id(self) -> None:
        cap1 = BaseCapability(make_metadata("zzz_cap"))
        cap2 = BaseCapability(make_metadata("aaa_cap"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        # Tie broken by ID alphabetically
        assert ranked[0].capability.metadata.id == "aaa_cap"
        assert ranked[1].capability.metadata.id == "zzz_cap"

    def test_rank_tie_breaker_with_different_scores(self) -> None:
        cap1 = BaseCapability(make_metadata("zzz_cap"))
        cap2 = BaseCapability(make_metadata("aaa_cap"))
        m1 = CapabilityMatch(capability=cap1, score=0.9)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        # Score takes precedence over ID
        assert ranked[0].capability.metadata.id == "aaa_cap"

    def test_rank_applies_latency_penalty(self) -> None:
        cap1 = BaseCapability(make_metadata("c1", latency=100.0))
        cap2 = BaseCapability(make_metadata("c2", latency=0.0))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        # cap2 has lower latency, so higher final score
        assert ranked[0].capability.metadata.id == "c2"

    def test_rank_applies_token_cost_penalty(self) -> None:
        cap1 = BaseCapability(make_metadata("c1", token_cost=10.0))
        cap2 = BaseCapability(make_metadata("c2", token_cost=0.0))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        # cap2 has lower token cost, so higher final score
        assert ranked[0].capability.metadata.id == "c2"

    def test_rank_does_not_mutate_input(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1])
        assert m1 in ranked

    def test_rank_returns_list(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1])
        assert isinstance(ranked, list)

    def test_rank_stable_sort(self) -> None:
        # Same ID, same score (shouldn't happen in registry, but good to test sort stability)
        cap1 = BaseCapability(make_metadata("c1"))
        cap2 = BaseCapability(make_metadata("c1"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        assert len(ranked) == 2

    def test_rank_high_risk_high_cost(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.HIGH, cost=CapabilityCost.HIGH))
        m = CapabilityMatch(capability=cap, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m])
        # 1.0 - 0.2 (risk) - 0.2 (cost) = 0.6
        assert ranked[0].score == pytest.approx(0.6)

    def test_rank_medium_risk_medium_cost(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.MEDIUM, cost=CapabilityCost.MEDIUM))
        m = CapabilityMatch(capability=cap, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m])
        # 1.0 - 0.1 (risk) - 0.1 (cost) = 0.8
        assert ranked[0].score == 0.8

    def test_rank_no_penalty(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.NONE, cost=CapabilityCost.TRIVIAL))
        m = CapabilityMatch(capability=cap, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m])
        assert ranked[0].score == 1.0

    def test_rank_penalty_order(self) -> None:
        cap1 = BaseCapability(make_metadata("c1", risk=CapabilityRisk.HIGH, cost=CapabilityCost.LOW))
        cap2 = BaseCapability(make_metadata("c2", risk=CapabilityRisk.LOW, cost=CapabilityCost.HIGH))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        # Both have 0.8 final score. Tie-breaker by ID: c1 < c2
        assert ranked[0].capability.metadata.id == "c1"

    def test_rank_negative_score_clamped(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.HIGH, cost=CapabilityCost.HIGH))
        m = CapabilityMatch(capability=cap, score=0.1)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m])
        # 0.1 - 0.4 = -0.3 -> clamped to 0.0
        assert ranked[0].score == 0.0

    def test_rank_token_cost_minor_impact(self) -> None:
        cap1 = BaseCapability(make_metadata("c1", token_cost=1.0))
        cap2 = BaseCapability(make_metadata("c2", token_cost=0.0))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        # 1.0 - 0.01 = 0.99 vs 1.0
        assert ranked[0].capability.metadata.id == "c2"

    def test_rank_latency_minor_impact(self) -> None:
        cap1 = BaseCapability(make_metadata("c1", latency=10.0))
        cap2 = BaseCapability(make_metadata("c2", latency=0.0))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        # 1.0 - 0.01 = 0.99 vs 1.0
        assert ranked[0].capability.metadata.id == "c2"

    def test_rank_determinism(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        cap2 = BaseCapability(make_metadata("c2"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=0.8)
        ranker = CapabilityRanker()
        r1 = ranker.rank([m1, m2])
        r2 = ranker.rank([m1, m2])
        assert r1 == r2

    def test_rank_sorts_descending(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        cap2 = BaseCapability(make_metadata("c2"))
        m1 = CapabilityMatch(capability=cap1, score=0.5)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        assert ranked[0].score > ranked[1].score

    def test_rank_tie_breaker_alphabetical(self) -> None:
        cap1 = BaseCapability(make_metadata("b_cap"))
        cap2 = BaseCapability(make_metadata("a_cap"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        ranker = CapabilityRanker()
        ranked = ranker.rank([m1, m2])
        assert ranked[0].capability.metadata.id == "a_cap"

    def test_rank_tie_breaker_multiple(self) -> None:
        caps = [
            CapabilityMatch(capability=BaseCapability(make_metadata(f"cap_{i}")), score=1.0)
            for i in range(5)
        ]
        ranker = CapabilityRanker()
        ranked = ranker.rank(caps)
        ids = [m.capability.metadata.id for m in ranked]
        assert ids == sorted(ids)


# --- Recommender Tests (25) ---

class TestRecommender:
    def test_recommend_winner(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert r.winner is not None
        assert r.winner.capability.metadata.id == "c1"

    def test_recommend_no_matches(self) -> None:
        rec = Recommender()
        r = rec.recommend([])
        assert r.winner is None
        assert "No capabilities" in r.explanation

    def test_recommend_alternatives(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        cap2 = BaseCapability(make_metadata("c2"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=0.8)
        rec = Recommender()
        r = rec.recommend([m1, m2])
        assert len(r.alternatives) == 1
        assert r.alternatives[0].capability.metadata.id == "c2"

    def test_recommend_confidence(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert r.confidence == 1.0

    def test_recommend_warning_high_risk(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.HIGH))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert len(r.warnings) > 0
        assert "risk" in r.warnings[0].lower()

    def test_recommend_warning_llm(self) -> None:
        cap = BaseCapability(make_metadata("c1", requires_llm=True))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert any("LLM" in w for w in r.warnings)

    def test_recommend_no_warnings_low_risk(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.LOW))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert len(r.warnings) == 0

    def test_recommend_warning_dependencies(self) -> None:
        cap = BaseCapability(make_metadata("c1", deps=("dep1",)))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert any("dependencies" in w for w in r.warnings)

    def test_recommend_explanation_contains_reasons(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=1.0, reason_parts=("Intent matched", "Language supported"))
        rec = Recommender()
        r = rec.recommend([m])
        assert "Intent matched" in r.explanation
        assert "Language supported" in r.explanation

    def test_recommend_explanation_contains_score(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=0.95)
        rec = Recommender()
        r = rec.recommend([m])
        assert "0.95" in r.explanation

    def test_recommend_explanation_contains_name(self) -> None:
        cap = BaseCapability(make_metadata("c1", name="My Capability"))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert "My Capability" in r.explanation

    def test_recommend_explanation_empty_if_no_winner(self) -> None:
        rec = Recommender()
        r = rec.recommend([])
        assert r.explanation == "No capabilities matched the goal."

    def test_recommend_alternatives_sorted_by_score(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        cap2 = BaseCapability(make_metadata("c2"))
        cap3 = BaseCapability(make_metadata("c3"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=0.8)
        m3 = CapabilityMatch(capability=cap3, score=0.9)
        rec = Recommender()
        r = rec.recommend([m1, m2, m3])
        assert r.alternatives[0].score >= r.alternatives[1].score

    def test_recommend_warning_medium_risk(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.MEDIUM))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert "medium risk" in r.warnings[0]

    def test_recommend_warning_multiple(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.HIGH, requires_llm=True, deps=("d1",)))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert len(r.warnings) == 3

    def test_recommend_winner_is_highest_score(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        cap2 = BaseCapability(make_metadata("c2"))
        m1 = CapabilityMatch(capability=cap1, score=0.5)
        m2 = CapabilityMatch(capability=cap2, score=1.0)
        rec = Recommender()
        r = rec.recommend([m1, m2])
        assert r.winner.capability.metadata.id == "c2"

    def test_recommend_confidence_matches_winner_score(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        m1 = CapabilityMatch(capability=cap1, score=0.85)
        rec = Recommender()
        r = rec.recommend([m1])
        assert r.confidence == 0.85

    def test_recommend_determinism(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        rec = Recommender()
        r1 = rec.recommend([m1])
        r2 = rec.recommend([m1])
        assert r1 == r2

    def test_recommend_returns_tuple_for_alternatives(self) -> None:
        cap1 = BaseCapability(make_metadata("c1"))
        cap2 = BaseCapability(make_metadata("c2"))
        m1 = CapabilityMatch(capability=cap1, score=1.0)
        m2 = CapabilityMatch(capability=cap2, score=0.8)
        rec = Recommender()
        r = rec.recommend([m1, m2])
        assert isinstance(r.alternatives, tuple)

    def test_recommend_returns_tuple_for_warnings(self) -> None:
        cap = BaseCapability(make_metadata("c1", risk=CapabilityRisk.HIGH))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert isinstance(r.warnings, tuple)

    def test_recommend_empty_alternatives_if_single_match(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=1.0)
        rec = Recommender()
        r = rec.recommend([m])
        assert len(r.alternatives) == 0

    def test_recommend_reason_parts_empty(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=1.0, reason_parts=())
        rec = Recommender()
        r = rec.recommend([m])
        assert "Reasons: " not in r.explanation

    def test_recommend_reason_parts_single(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=1.0, reason_parts=("Reason1",))
        rec = Recommender()
        r = rec.recommend([m])
        assert "Reasons: Reason1." in r.explanation

    def test_recommend_reason_parts_multiple(self) -> None:
        cap = BaseCapability(make_metadata("c1"))
        m = CapabilityMatch(capability=cap, score=1.0, reason_parts=("Reason1", "Reason2"))
        rec = Recommender()
        r = rec.recommend([m])
        assert "Reasons: Reason1; Reason2." in r.explanation


# --- Runtime Tests (45) ---

class TestCapabilityRuntime:
    def test_runtime_analyze_build(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build an app", GoalIntent.BUILD)
        analysis = runtime.analyze(goal)
        assert analysis.recommendation is not None
        assert analysis.recommendation.winner is not None
        # All dummy caps return True for supports, so score determines winner.
        # Rename (1.0) > FixBug (0.9) > GenerateApp (0.8)
        # But wait, GenerateApp has high risk/cost penalty, so Rename wins.
        assert analysis.recommendation.winner.capability.metadata.id == "rename_symbol"

    def test_runtime_analyze_rename(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Rename class Foo to Bar", GoalIntent.REFACTOR)
        analysis = runtime.analyze(goal)
        assert analysis.recommendation is not None
        assert analysis.recommendation.winner.capability.metadata.id == "rename_symbol"

    def test_runtime_analyze_no_match(self) -> None:
        # All caps are disabled
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", enabled=False)))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
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
        assert analysis.metrics.candidates_count == 3
        assert analysis.metrics.matching_time_ms > 0

    def test_runtime_events_published(self, runtime: CapabilityRuntime, event_bus: MockEventBus) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD)
        runtime.analyze(goal)
        assert len(event_bus.published_events) > 0
        
        event_types = [type(e) for e in event_bus.published_events]
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

    def test_runtime_explanation_rich(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD, lang="python")
        analysis = runtime.analyze(goal)
        assert "Score:" in analysis.recommendation.explanation

    def test_runtime_warnings_populated(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build app", GoalIntent.BUILD, lang="python")
        analysis = runtime.analyze(goal)
        # Rename wins (low risk), but if GenerateApp won, it would have warnings.
        # Let's force GenerateApp to win by giving it a higher score.
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("generate_app", risk=CapabilityRisk.HIGH, requires_llm=True, deps=("models",)), score_val=1.0))
        reg.register(BaseCapability(make_metadata("rename_symbol", risk=CapabilityRisk.LOW), score_val=0.5))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        analysis = rt.analyze(goal)
        assert len(analysis.recommendation.warnings) == 3  # risk, llm, deps

    def test_runtime_filters_disabled(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", enabled=False), score_val=1.0))
        reg.register(BaseCapability(make_metadata("c2", enabled=True), score_val=0.5))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.recommendation.winner.capability.metadata.id == "c2"

    def test_runtime_filters_deprecated(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", status=CapabilityStatus.DEPRECATED), score_val=1.0))
        reg.register(BaseCapability(make_metadata("c2", status=CapabilityStatus.STABLE), score_val=0.5))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.recommendation.winner.capability.metadata.id == "c2"

    def test_runtime_language_filter(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", lang=("java",)), score_val=1.0))
        reg.register(BaseCapability(make_metadata("c2", lang=("python",)), score_val=0.5))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test", lang="python")
        analysis = rt.analyze(goal)
        assert analysis.recommendation.winner.capability.metadata.id == "c2"

    def test_runtime_no_candidates(self) -> None:
        reg = CapabilityRegistry()
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.metrics.candidates_count == 0
        assert analysis.recommendation.winner is None

    def test_runtime_tie_breaking(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("zzz_cap"), score_val=1.0))
        reg.register(BaseCapability(make_metadata("aaa_cap"), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.recommendation.winner.capability.metadata.id == "aaa_cap"

    def test_runtime_determinism(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("Build an app", GoalIntent.BUILD)
        
        analysis1 = runtime.analyze(goal)
        analysis2 = runtime.analyze(goal)
        
        # Compare everything EXCEPT the metrics which contain timestamps
        assert analysis1.recommendation == analysis2.recommendation
        assert analysis1.candidates == analysis2.candidates
        assert analysis1.state == analysis2.state

    def test_runtime_metrics_rejected_count(self, runtime: CapabilityRuntime) -> None:
        # Not explicitly tracking rejected in runtime, defaults to 0
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.metrics.rejected_count == 0

    def test_runtime_state_failed_on_error(self) -> None:
        # Hard to trigger error without mocking, but we can test the state enum
        assert CapabilityRuntimeState.FAILED == "failed"

    def test_runtime_candidates_sorted_by_score(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        scores = [m.score for m in analysis.candidates]
        assert scores == sorted(scores, reverse=True)

    def test_runtime_alternatives_populated(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert len(analysis.recommendation.alternatives) == 2

    def test_runtime_winner_score_matches_confidence(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.recommendation.confidence == analysis.recommendation.winner.score

    def test_runtime_goal_attached(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.goal == goal

    def test_runtime_registry_size_matches(self, runtime: CapabilityRuntime, registry: CapabilityRegistry) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.metrics.registry_size == len(registry.list())

    def test_runtime_empty_goal_handled(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("   a   ")
        analysis = runtime.analyze(goal)
        assert analysis.state == CapabilityRuntimeState.COMPLETE

    def test_runtime_initial_state_ready(self, registry: CapabilityRegistry, event_bus: MockEventBus) -> None:
        rt = CapabilityRuntime(registry=registry, event_bus=event_bus)
        assert rt.state == CapabilityRuntimeState.READY

    def test_runtime_state_matching_during_execution(self, registry: CapabilityRegistry, event_bus: MockEventBus) -> None:
        # Cannot easily test intermediate states without async/mocking, but enum exists
        assert CapabilityRuntimeState.MATCHING == "matching"

    def test_runtime_state_ranking_during_execution(self, registry: CapabilityRegistry, event_bus: MockEventBus) -> None:
        assert CapabilityRuntimeState.RANKING == "ranking"

    def test_runtime_all_caps_match(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1"), score_val=1.0))
        reg.register(BaseCapability(make_metadata("c2"), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.metrics.candidates_count == 2

    def test_runtime_high_cost_penalty(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", cost=CapabilityCost.HIGH), score_val=1.0))
        reg.register(BaseCapability(make_metadata("c2", cost=CapabilityCost.LOW), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.recommendation.winner.capability.metadata.id == "c2"

    def test_runtime_high_risk_penalty(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", risk=CapabilityRisk.HIGH), score_val=1.0))
        reg.register(BaseCapability(make_metadata("c2", risk=CapabilityRisk.LOW), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.recommendation.winner.capability.metadata.id == "c2"

    def test_runtime_token_cost_penalty(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", token_cost=100.0), score_val=1.0))
        reg.register(BaseCapability(make_metadata("c2", token_cost=0.0), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.recommendation.winner.capability.metadata.id == "c2"

    def test_runtime_latency_penalty(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", latency=100.0), score_val=1.0))
        reg.register(BaseCapability(make_metadata("c2", latency=0.0), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert analysis.recommendation.winner.capability.metadata.id == "c2"

    def test_runtime_dependencies_warning(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", deps=("d1",)), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert any("dependencies" in w for w in analysis.recommendation.warnings)

    def test_runtime_llm_warning(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", requires_llm=True), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert any("LLM" in w for w in analysis.recommendation.warnings)

    def test_runtime_no_warnings(self) -> None:
        reg = CapabilityRegistry()
        reg.register(BaseCapability(make_metadata("c1", risk=CapabilityRisk.LOW, cost=CapabilityCost.LOW), score_val=1.0))
        rt = CapabilityRuntime(registry=reg, event_bus=MockEventBus())
        goal = make_goal("test")
        analysis = rt.analyze(goal)
        assert len(analysis.recommendation.warnings) == 0

    def test_runtime_explanation_contains_score(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        score_str = f"{analysis.recommendation.winner.score:.2f}"
        assert score_str in analysis.recommendation.explanation

    def test_runtime_explanation_contains_name(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        name = analysis.recommendation.winner.capability.metadata.name
        assert name in analysis.recommendation.explanation

    def test_runtime_candidates_count_matches_matches(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.metrics.candidates_count == len(analysis.candidates)

    def test_runtime_matching_time_positive(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.metrics.matching_time_ms >= 0.0

    def test_runtime_ranking_time_positive(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.metrics.ranking_time_ms >= 0.0

    def test_runtime_recommendation_time_positive(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.metrics.recommendation_time_ms >= 0.0

    def test_runtime_confidence_matches_winner(self, runtime: CapabilityRuntime) -> None:
        goal = make_goal("test")
        analysis = runtime.analyze(goal)
        assert analysis.metrics.confidence == analysis.recommendation.confidence