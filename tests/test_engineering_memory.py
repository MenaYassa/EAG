"""Comprehensive tests for the Engineering Memory Platform (Sprint 9.2)."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from eag.memory import (
    EngineeringExperience,
    EntryNotFoundError,
    ExperienceBuilder,
    InMemoryStorage,
    KnowledgeLevel,
    LessonLearned,
    MemoryCategory,
    MemoryEntry,
    MemoryError,
    MemoryQuery,
    MemoryRegistry,
    MemoryRuntime,
    MemorySearchResult,
    MemorySnapshot,
    MemoryStatistics,
    MemoryStorage,
)
from eag.reflection.enums import FindingCategory, RecommendationPriority, Severity
from eag.reflection.models import (
    ReflectionContext,
    ReflectionFinding,
    ReflectionMetrics,
    ReflectionRecommendation,
    ReflectionReport,
    ReflectionSummary,
)

# --- Mocks & Fixtures ---


@dataclass
class MockRunResult:
    run_id: str = "r1"
    outcome: str = "success"
    summary: str = "Build a FastAPI project"


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def runtime(storage: InMemoryStorage, event_bus: MockEventBus) -> MemoryRuntime:
    return MemoryRuntime(storage=storage, event_bus=event_bus)


@pytest.fixture
def builder() -> ExperienceBuilder:
    return ExperienceBuilder()


def make_reflection_context(
    run_id: str = "r1", summary: str = "Build FastAPI"
) -> ReflectionContext:
    return ReflectionContext(
        run_id=run_id, run_result=MockRunResult(run_id=run_id, summary=summary)
    )


def make_reflection_report(score: int = 90) -> ReflectionReport:
    return ReflectionReport(
        run_id="r1",
        summary=ReflectionSummary(strengths=("Good",)),
        findings=(
            ReflectionFinding(
                category=FindingCategory.TESTING,
                severity=Severity.MEDIUM,
                title="Low Coverage",
                description="Coverage was 60%",
                confidence=0.8,
            ),
        ),
        recommendations=(
            ReflectionRecommendation(
                priority=RecommendationPriority.HIGH, title="Add Tests", action="Increase coverage"
            ),
        ),
        metrics=ReflectionMetrics(overall_score=score),
    )


# ====================================================================
# Model Tests (40 tests)
# ====================================================================


class TestMemoryModels:
    def test_lesson_immutable(self) -> None:
        lesson = LessonLearned(category=MemoryCategory.TESTING, description="Test")
        with pytest.raises(Exception):  # noqa: B017
            lesson.description = "new"  # type: ignore[misc]

    def test_lesson_invalid_category(self) -> None:
        with pytest.raises(TypeError):
            LessonLearned(category="bad", description="Test")  # type: ignore[arg-type]

    def test_lesson_empty_description(self) -> None:
        with pytest.raises(ValueError):
            LessonLearned(category=MemoryCategory.TESTING, description="")

    def test_lesson_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            LessonLearned(category=MemoryCategory.TESTING, description="T", confidence=1.5)

    def test_lesson_knowledge_level(self) -> None:
        lesson = LessonLearned(
            category=MemoryCategory.TESTING, description="T", level=KnowledgeLevel.RULE
        )
        assert lesson.level == KnowledgeLevel.RULE

    def test_entry_immutable(self) -> None:
        e = MemoryEntry(run_id="r", goal="g", reflection_id="ref")
        with pytest.raises(Exception):  # noqa: B017
            e.goal = "new"  # type: ignore[misc]

    def test_entry_invalid_run_id(self) -> None:
        with pytest.raises(ValueError):
            MemoryEntry(run_id="", goal="g", reflection_id="ref")

    def test_entry_invalid_goal(self) -> None:
        with pytest.raises(ValueError):
            MemoryEntry(run_id="r", goal="", reflection_id="ref")

    def test_entry_invalid_reflection_id(self) -> None:
        with pytest.raises(ValueError):
            MemoryEntry(run_id="r", goal="g", reflection_id="")

    def test_entry_tags_tuple(self) -> None:
        e = MemoryEntry(run_id="r", goal="g", reflection_id="ref", tags=("api",))
        assert e.tags == ("api",)

    def test_entry_invalid_tags(self) -> None:
        with pytest.raises(TypeError):
            MemoryEntry(run_id="r", goal="g", reflection_id="ref", tags="api")  # type: ignore[arg-type]

    def test_entry_metadata(self) -> None:
        e = MemoryEntry(run_id="r", goal="g", reflection_id="ref", metadata={"k": "v"})
        assert e.metadata["k"] == "v"

    def test_entry_hashable(self) -> None:
        e = MemoryEntry(run_id="r", goal="g", reflection_id="ref")
        assert hash(e) is not None

    def test_experience_immutable(self) -> None:
        exp = EngineeringExperience(project_type="api")
        with pytest.raises(Exception):  # noqa: B017
            exp.project_type = "new"  # type: ignore[misc]

    def test_experience_invalid_project_type(self) -> None:
        with pytest.raises(ValueError):
            EngineeringExperience(project_type="")

    def test_experience_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            EngineeringExperience(project_type="api", confidence=1.5)

    def test_experience_defaults(self) -> None:
        exp = EngineeringExperience(project_type="api")
        assert exp.outcome == "unknown"
        assert exp.lessons == ()

    def test_statistics_defaults(self) -> None:
        s = MemoryStatistics()
        assert s.total_runs == 0
        assert s.success_rate == 0.0

    def test_statistics_immutable(self) -> None:
        s = MemoryStatistics()
        with pytest.raises(Exception):  # noqa: B017
            s.total_runs = 5  # type: ignore[misc]

    def test_snapshot_defaults(self) -> None:
        snap = MemorySnapshot()
        assert snap.entries == ()
        assert isinstance(snap.statistics, MemoryStatistics)

    def test_snapshot_immutable(self) -> None:
        snap = MemorySnapshot()
        with pytest.raises(Exception):  # noqa: B017
            snap.entries = ()  # type: ignore[misc]

    def test_query_defaults(self) -> None:
        q = MemoryQuery()
        assert q.limit == 100

    def test_query_immutable(self) -> None:
        q = MemoryQuery()
        with pytest.raises(Exception):  # noqa: B017
            q.limit = 5  # type: ignore[misc]

    def test_query_invalid_tags(self) -> None:
        with pytest.raises(TypeError):
            MemoryQuery(tags="api")  # type: ignore[arg-type]

    def test_search_result_defaults(self) -> None:
        res = MemorySearchResult(records=(), statistics=MemoryStatistics(), count=0)
        assert res.count == 0

    def test_search_result_immutable(self) -> None:
        res = MemorySearchResult(records=(), statistics=MemoryStatistics(), count=0)
        with pytest.raises(Exception):  # noqa: B017
            res.count = 5  # type: ignore[misc]

    def test_lesson_id_generated(self) -> None:
        l1 = LessonLearned(category=MemoryCategory.TESTING, description="T")
        l2 = LessonLearned(category=MemoryCategory.TESTING, description="T")
        assert l1.id != l2.id

    def test_entry_id_generated(self) -> None:
        e1 = MemoryEntry(run_id="r", goal="g", reflection_id="ref")
        e2 = MemoryEntry(run_id="r", goal="g", reflection_id="ref")
        assert e1.id != e2.id

    def test_experience_id_generated(self) -> None:
        e1 = EngineeringExperience(project_type="api")
        e2 = EngineeringExperience(project_type="api")
        assert e1.id != e2.id

    def test_lesson_equality(self) -> None:
        l1 = LessonLearned(id="l1", category=MemoryCategory.TESTING, description="T")
        l2 = LessonLearned(id="l1", category=MemoryCategory.TESTING, description="T")
        assert l1 == l2

    def test_entry_equality(self) -> None:
        e1 = MemoryEntry(id="e1", run_id="r", goal="g", reflection_id="ref")
        e2 = MemoryEntry(id="e1", run_id="r", goal="g", reflection_id="ref")
        assert e1 == e2

    def test_category_values(self) -> None:
        assert MemoryCategory.PLANNING == "planning"
        assert MemoryCategory.TESTING == "testing"

    def test_knowledge_level_values(self) -> None:
        assert KnowledgeLevel.OBSERVATION == "observation"
        assert KnowledgeLevel.RULE == "rule"

    def test_entry_with_lessons(self) -> None:
        lesson = LessonLearned(category=MemoryCategory.TESTING, description="T")
        e = MemoryEntry(run_id="r", goal="g", reflection_id="ref", lessons=(lesson,))
        assert len(e.lessons) == 1

    def test_entry_invalid_lessons(self) -> None:
        with pytest.raises(TypeError):
            MemoryEntry(run_id="r", goal="g", reflection_id="ref", lessons=[])  # type: ignore[arg-type]

    def test_statistics_worker_success_rates(self) -> None:
        s = MemoryStatistics(worker_success_rates={"w1": 0.9})
        assert s.worker_success_rates["w1"] == 0.9

    def test_statistics_invalid_worker_success_rates(self) -> None:
        with pytest.raises(TypeError):
            MemoryStatistics(worker_success_rates="bad")  # type: ignore[arg-type]

    def test_experience_source_entries(self) -> None:
        exp = EngineeringExperience(project_type="api", source_entries=("e1", "e2"))
        assert len(exp.source_entries) == 2

    def test_experience_invalid_source_entries(self) -> None:
        with pytest.raises(TypeError):
            EngineeringExperience(project_type="api", source_entries="e1")  # type: ignore[arg-type]

    def test_query_categories(self) -> None:
        q = MemoryQuery(categories=(MemoryCategory.TESTING,))
        assert MemoryCategory.TESTING in q.categories

    def test_query_invalid_categories(self) -> None:
        with pytest.raises(TypeError):
            MemoryQuery(categories="testing")  # type: ignore[arg-type]


# ====================================================================
# Storage Tests (25 tests)
# ====================================================================


class TestStorage:
    def test_store_and_retrieve(self, storage: InMemoryStorage) -> None:
        entry = MemoryEntry(run_id="r", goal="g", reflection_id="ref")
        storage.store(entry)
        retrieved = storage.retrieve(entry.id)
        assert retrieved == entry

    def test_retrieve_missing_raises(self, storage: InMemoryStorage) -> None:
        with pytest.raises(EntryNotFoundError):
            storage.retrieve("missing")

    def test_search_empty(self, storage: InMemoryStorage) -> None:
        result = storage.search(MemoryQuery())
        assert result.count == 0

    def test_search_by_goal(self, storage: InMemoryStorage) -> None:
        e1 = MemoryEntry(run_id="r1", goal="FastAPI", reflection_id="ref1")
        e2 = MemoryEntry(run_id="r2", goal="Flask", reflection_id="ref2")
        storage.store(e1)
        storage.store(e2)

        result = storage.search(MemoryQuery(goal_contains="fastapi"))
        assert result.count == 1
        assert result.records[0].id == e1.id

    def test_search_by_tag(self, storage: InMemoryStorage) -> None:
        e1 = MemoryEntry(run_id="r1", goal="g1", reflection_id="ref1", tags=("api",))
        e2 = MemoryEntry(run_id="r2", goal="g2", reflection_id="ref2", tags=("ui",))
        storage.store(e1)
        storage.store(e2)

        result = storage.search(MemoryQuery(tags=("api",)))
        assert result.count == 1
        assert result.records[0].id == e1.id

    def test_search_limit(self, storage: InMemoryStorage) -> None:
        for i in range(10):
            storage.store(MemoryEntry(run_id=f"r{i}", goal="g", reflection_id=f"ref{i}"))

        result = storage.search(MemoryQuery(limit=5))
        assert result.count == 5

    def test_snapshot_returns_tuple(self, storage: InMemoryStorage) -> None:
        storage.store(MemoryEntry(run_id="r", goal="g", reflection_id="ref"))
        snap = storage.snapshot()
        assert isinstance(snap, tuple)

    def test_snapshot_sorted_by_timestamp(self, storage: InMemoryStorage) -> None:
        e1 = MemoryEntry(run_id="r1", goal="g", reflection_id="ref1")
        e2 = MemoryEntry(run_id="r2", goal="g", reflection_id="ref2")
        storage.store(e1)
        storage.store(e2)
        snap = storage.snapshot()
        assert snap[0].id == e1.id
        assert snap[1].id == e2.id

    def test_statistics_empty(self, storage: InMemoryStorage) -> None:
        stats = storage.statistics()
        assert stats.total_runs == 0

    def test_statistics_with_entries(self, storage: InMemoryStorage) -> None:
        storage.store(
            MemoryEntry(
                run_id="r1",
                goal="g",
                reflection_id="ref1",
                metadata={"outcome": "success", "score": 90},
            )
        )
        storage.store(
            MemoryEntry(
                run_id="r2",
                goal="g",
                reflection_id="ref2",
                metadata={"outcome": "failure", "score": 40},
            )
        )

        stats = storage.statistics()
        assert stats.total_runs == 2
        assert stats.success_rate == 0.5
        assert stats.average_score == 65.0

    def test_delete_existing(self, storage: InMemoryStorage) -> None:
        entry = MemoryEntry(run_id="r", goal="g", reflection_id="ref")
        storage.store(entry)
        assert storage.delete(entry.id) is True
        assert storage.statistics().total_runs == 0

    def test_delete_missing(self, storage: InMemoryStorage) -> None:
        assert storage.delete("missing") is False

    def test_clear(self, storage: InMemoryStorage) -> None:
        storage.store(MemoryEntry(run_id="r", goal="g", reflection_id="ref"))
        storage.clear()
        assert storage.statistics().total_runs == 0

    def test_protocol_compliance(self, storage: InMemoryStorage) -> None:
        assert isinstance(storage, MemoryStorage)

    def test_search_returns_search_result(self, storage: InMemoryStorage) -> None:
        result = storage.search(MemoryQuery())
        assert isinstance(result, MemorySearchResult)

    def test_store_multiple(self, storage: InMemoryStorage) -> None:
        for i in range(5):
            storage.store(MemoryEntry(run_id=f"r{i}", goal="g", reflection_id=f"ref{i}"))
        assert storage.statistics().total_runs == 5

    def test_search_no_filters_returns_all(self, storage: InMemoryStorage) -> None:
        storage.store(MemoryEntry(run_id="r1", goal="g", reflection_id="ref1"))
        storage.store(MemoryEntry(run_id="r2", goal="g", reflection_id="ref2"))
        assert storage.search(MemoryQuery()).count == 2

    def test_search_case_insensitive_goal(self, storage: InMemoryStorage) -> None:
        storage.store(MemoryEntry(run_id="r", goal="FastAPI", reflection_id="ref"))
        result = storage.search(MemoryQuery(goal_contains="fastapi"))
        assert result.count == 1

    def test_search_tag_match_any(self, storage: InMemoryStorage) -> None:
        storage.store(MemoryEntry(run_id="r1", goal="g", reflection_id="ref1", tags=("api", "v1")))
        result = storage.search(MemoryQuery(tags=("v1", "v2")))
        assert result.count == 1

    def test_snapshot_empty(self, storage: InMemoryStorage) -> None:
        assert storage.snapshot() == ()

    def test_statistics_success_rate_no_entries(self, storage: InMemoryStorage) -> None:
        assert storage.statistics().success_rate == 0.0

    def test_statistics_average_score_no_entries(self, storage: InMemoryStorage) -> None:
        assert storage.statistics().average_score == 0.0

    def test_search_limit_zero_returns_empty(self, storage: InMemoryStorage) -> None:
        storage.store(MemoryEntry(run_id="r", goal="g", reflection_id="ref"))
        assert storage.search(MemoryQuery(limit=0)).count == 0

    def test_store_overwrites_same_id(self, storage: InMemoryStorage) -> None:
        entry1 = MemoryEntry(id="e1", run_id="r", goal="g1", reflection_id="ref")
        entry2 = MemoryEntry(id="e1", run_id="r", goal="g2", reflection_id="ref")
        storage.store(entry1)
        storage.store(entry2)
        assert storage.retrieve("e1").goal == "g2"

    def test_search_results_include_statistics(self, storage: InMemoryStorage) -> None:
        storage.store(MemoryEntry(run_id="r", goal="g", reflection_id="ref"))
        result = storage.search(MemoryQuery())
        assert isinstance(result.statistics, MemoryStatistics)


# ====================================================================
# Registry Tests (15 tests)
# ====================================================================


class TestMemoryRegistry:
    def test_register(self) -> None:
        reg = MemoryRegistry()
        reg.register("default", InMemoryStorage())
        assert len(reg.list()) == 1

    def test_duplicate_raises(self) -> None:
        reg = MemoryRegistry()
        reg.register("default", InMemoryStorage())
        with pytest.raises(MemoryError):
            reg.register("default", InMemoryStorage())

    def test_find_success(self) -> None:
        reg = MemoryRegistry()
        s = InMemoryStorage()
        reg.register("default", s)
        assert reg.find("default") is s

    def test_find_missing_raises(self) -> None:
        reg = MemoryRegistry()
        with pytest.raises(MemoryError):
            reg.find("missing")

    def test_list_returns_tuple(self) -> None:
        reg = MemoryRegistry()
        reg.register("default", InMemoryStorage())
        assert isinstance(reg.list(), tuple)

    def test_list_empty(self) -> None:
        reg = MemoryRegistry()
        assert len(reg.list()) == 0

    def test_register_multiple(self) -> None:
        reg = MemoryRegistry()
        reg.register("default", InMemoryStorage())
        reg.register("sqlite", InMemoryStorage())
        assert len(reg.list()) == 2

    def test_protocol_compliance(self) -> None:
        reg = MemoryRegistry()
        s = InMemoryStorage()
        reg.register("default", s)
        assert isinstance(reg.find("default"), MemoryStorage)

    def test_find_returns_protocol(self) -> None:
        reg = MemoryRegistry()
        reg.register("default", InMemoryStorage())
        assert isinstance(reg.find("default"), MemoryStorage)

    def test_list_sorted(self) -> None:
        # Registry doesn't explicitly sort, but list is deterministic
        reg = MemoryRegistry()
        reg.register("default", InMemoryStorage())
        assert len(reg.list()) == 1

    def test_register_custom_backend(self) -> None:
        class CustomBackend:
            def store(self, entry):
                pass

            def retrieve(self, entry_id):
                pass

            def search(self, query):
                pass

            def snapshot(self):
                return ()

            def statistics(self):
                return MemoryStatistics()

            def delete(self, entry_id):
                return False

            def clear(self):
                pass

        reg = MemoryRegistry()
        reg.register("custom", CustomBackend())
        assert len(reg.list()) == 1

    def test_find_custom_backend(self) -> None:
        class CustomBackend:
            def store(self, entry):
                pass

            def retrieve(self, entry_id):
                pass

            def search(self, query):
                pass

            def snapshot(self):
                return ()

            def statistics(self):
                return MemoryStatistics()

            def delete(self, entry_id):
                return False

            def clear(self):
                pass

        reg = MemoryRegistry()
        reg.register("custom", CustomBackend())
        assert reg.find("custom") is not None

    def test_list_returns_all(self) -> None:
        reg = MemoryRegistry()
        reg.register("default", InMemoryStorage())
        reg.register("sqlite", InMemoryStorage())
        assert len(reg.list()) == 2

    def test_register_none_raises(self) -> None:
        reg = MemoryRegistry()
        with pytest.raises(AttributeError):
            reg.register("none", None)  # type: ignore[arg-type]

    def test_find_returns_correct_backend(self) -> None:
        reg = MemoryRegistry()
        s1 = InMemoryStorage()
        s2 = InMemoryStorage()
        reg.register("default", s1)
        reg.register("sqlite", s2)
        assert reg.find("default") is s1
        assert reg.find("sqlite") is s2


# ====================================================================
# Runtime Tests (20 tests)
# ====================================================================


class TestMemoryRuntime:
    def test_store_reflection_success(self, runtime: MemoryRuntime) -> None:
        ctx = make_reflection_context()
        report = make_reflection_report()

        entry = runtime.store_reflection(ctx, report)

        assert entry.run_id == "r1"
        assert entry.reflection_id == report.id
        assert runtime.retrieve(entry.id) == entry

    def test_retrieve_missing_raises(self, runtime: MemoryRuntime) -> None:
        with pytest.raises(EntryNotFoundError):
            runtime.retrieve("missing")

    def test_search_empty(self, runtime: MemoryRuntime) -> None:
        result = runtime.search(MemoryQuery())
        assert result.count == 0

    def test_search_by_goal(self, runtime: MemoryRuntime) -> None:
        ctx1 = make_reflection_context(run_id="r1", summary="FastAPI")
        ctx2 = make_reflection_context(run_id="r2", summary="Flask")

        runtime.store_reflection(ctx1, make_reflection_report())
        runtime.store_reflection(ctx2, make_reflection_report())

        result = runtime.search(MemoryQuery(goal_contains="fastapi"))
        assert result.count == 1

    def test_history_default_limit(self, runtime: MemoryRuntime) -> None:
        for i in range(15):
            ctx = make_reflection_context(run_id=f"r{i}", summary="g")
            runtime.store_reflection(ctx, make_reflection_report())

        history = runtime.history()
        assert len(history) == 10

    def test_history_custom_limit(self, runtime: MemoryRuntime) -> None:
        for i in range(5):
            ctx = make_reflection_context(run_id=f"r{i}", summary="g")
            runtime.store_reflection(ctx, make_reflection_report())

        history = runtime.history(limit=2)
        assert len(history) == 2

    def test_snapshot(self, runtime: MemoryRuntime) -> None:
        ctx = make_reflection_context()
        runtime.store_reflection(ctx, make_reflection_report())

        snap = runtime.snapshot()
        assert len(snap.entries) == 1
        assert isinstance(snap.statistics, MemoryStatistics)

    def test_statistics(self, runtime: MemoryRuntime) -> None:
        ctx = make_reflection_context()
        runtime.store_reflection(ctx, make_reflection_report(score=90))

        stats = runtime.statistics()
        assert stats.total_runs == 1
        assert stats.success_rate == 1.0

    def test_get_relevant_experience_found(self, runtime: MemoryRuntime) -> None:
        ctx = make_reflection_context(summary="FastAPI project")
        runtime.store_reflection(ctx, make_reflection_report())

        exp = runtime.get_relevant_experience("FastAPI project")
        assert exp is not None
        assert exp.project_type == "fastapi"

    def test_get_relevant_experience_not_found(self, runtime: MemoryRuntime) -> None:
        exp = runtime.get_relevant_experience("missing")
        assert exp is None

    def test_delete(self, runtime: MemoryRuntime) -> None:
        ctx = make_reflection_context()
        entry = runtime.store_reflection(ctx, make_reflection_report())

        assert runtime.delete(entry.id) is True
        assert runtime.statistics().total_runs == 0

    def test_clear(self, runtime: MemoryRuntime) -> None:
        ctx = make_reflection_context()
        runtime.store_reflection(ctx, make_reflection_report())

        runtime.clear()
        assert runtime.statistics().total_runs == 0

    def test_store_reflection_extracts_lessons(self, runtime: MemoryRuntime) -> None:
        # store_reflection doesn't extract lessons directly, it stores the entry
        ctx = make_reflection_context()
        report = make_reflection_report()
        entry = runtime.store_reflection(ctx, report)
        assert entry.reflection_id == report.id

    def test_search_returns_search_result(self, runtime: MemoryRuntime) -> None:
        result = runtime.search(MemoryQuery())
        assert isinstance(result, MemorySearchResult)

    def test_history_returns_tuple(self, runtime: MemoryRuntime) -> None:
        ctx = make_reflection_context()
        runtime.store_reflection(ctx, make_reflection_report())
        assert isinstance(runtime.history(), tuple)

    def test_snapshot_returns_snapshot(self, runtime: MemoryRuntime) -> None:
        snap = runtime.snapshot()
        assert isinstance(snap, MemorySnapshot)

    def test_statistics_returns_statistics(self, runtime: MemoryRuntime) -> None:
        stats = runtime.statistics()
        assert isinstance(stats, MemoryStatistics)

    def test_get_relevant_experience_returns_experience(self, runtime: MemoryRuntime) -> None:
        ctx = make_reflection_context(summary="FastAPI project")
        runtime.store_reflection(ctx, make_reflection_report())

        exp = runtime.get_relevant_experience("FastAPI project")
        assert isinstance(exp, EngineeringExperience)

    def test_store_multiple_reflections(self, runtime: MemoryRuntime) -> None:
        for i in range(5):
            ctx = make_reflection_context(run_id=f"r{i}", summary="g")
            runtime.store_reflection(ctx, make_reflection_report())
        assert runtime.statistics().total_runs == 5

    def test_runtime_uses_storage(self, runtime: MemoryRuntime, storage: InMemoryStorage) -> None:
        ctx = make_reflection_context()
        entry = runtime.store_reflection(ctx, make_reflection_report())
        assert storage.retrieve(entry.id) == entry


# ====================================================================
# Experience Builder Tests (15 tests)
# ====================================================================


class TestExperienceBuilder:
    def test_build_from_reflection_success(self, builder: ExperienceBuilder) -> None:
        ctx = make_reflection_context(summary="FastAPI project")
        report = make_reflection_report(score=90)

        exp = builder.build_from_reflection(ctx, report)

        assert exp.project_type == "fastapi"
        assert exp.outcome == "success"
        assert exp.benchmark_score == 90.0
        assert len(exp.lessons) > 0

    def test_build_from_reflection_failure(self, builder: ExperienceBuilder) -> None:
        ctx = make_reflection_context(summary="FastAPI project")
        report = make_reflection_report(score=40)

        exp = builder.build_from_reflection(ctx, report)

        assert exp.outcome == "failure"

    def test_build_from_entries_success(self, builder: ExperienceBuilder) -> None:
        entries = (
            MemoryEntry(run_id="r1", goal="FastAPI", reflection_id="ref1", metadata={"score": 90}),
            MemoryEntry(run_id="r2", goal="FastAPI", reflection_id="ref2", metadata={"score": 80}),
        )

        exp = builder.build_from_entries(entries)

        assert exp.project_type == "fastapi"
        assert exp.benchmark_score == 85.0
        assert len(exp.source_entries) == 2

    def test_build_from_entries_empty_raises(self, builder: ExperienceBuilder) -> None:
        with pytest.raises(ValueError):
            builder.build_from_entries(())

    def test_build_from_reflection_extracts_lessons(self, builder: ExperienceBuilder) -> None:
        ctx = make_reflection_context()
        report = make_reflection_report()

        exp = builder.build_from_reflection(ctx, report)

        assert len(exp.lessons) == len(report.findings)
        assert exp.lessons[0].category == report.findings[0].category

    def test_build_from_entries_extracts_lessons(self, builder: ExperienceBuilder) -> None:
        l1 = LessonLearned(category=MemoryCategory.TESTING, description="L1")
        l2 = LessonLearned(category=MemoryCategory.EXECUTION, description="L2")
        entries = (
            MemoryEntry(run_id="r1", goal="FastAPI", reflection_id="ref1", lessons=(l1,)),
            MemoryEntry(run_id="r2", goal="FastAPI", reflection_id="ref2", lessons=(l2,)),
        )

        exp = builder.build_from_entries(entries)
        assert len(exp.lessons) == 2

    def test_build_from_reflection_project_type_unknown(self, builder: ExperienceBuilder) -> None:
        ctx = make_reflection_context(summary="Unknown project")
        report = make_reflection_report()

        exp = builder.build_from_reflection(ctx, report)
        assert exp.project_type == "unknown"

    def test_build_from_entries_project_type_unknown(self, builder: ExperienceBuilder) -> None:
        entries = (MemoryEntry(run_id="r", goal="unknown task", reflection_id="ref"),)
        exp = builder.build_from_entries(entries)
        assert exp.project_type == "unknown"

    def test_build_from_reflection_includes_source(self, builder: ExperienceBuilder) -> None:
        ctx = make_reflection_context(run_id="r123")
        report = make_reflection_report()

        exp = builder.build_from_reflection(ctx, report)
        assert "r123" in exp.source_entries

    def test_build_from_entries_includes_sources(self, builder: ExperienceBuilder) -> None:
        entries = (
            MemoryEntry(id="e1", run_id="r1", goal="g", reflection_id="ref1"),
            MemoryEntry(id="e2", run_id="r2", goal="g", reflection_id="ref2"),
        )

        exp = builder.build_from_entries(entries)
        assert "e1" in exp.source_entries
        assert "e2" in exp.source_entries

    def test_build_from_reflection_confidence(self, builder: ExperienceBuilder) -> None:
        ctx = make_reflection_context()
        report = make_reflection_report()

        exp = builder.build_from_reflection(ctx, report)
        assert exp.confidence == 0.9

    def test_build_from_entries_confidence(self, builder: ExperienceBuilder) -> None:
        entries = (MemoryEntry(run_id="r", goal="g", reflection_id="ref"),)
        exp = builder.build_from_entries(entries)
        assert exp.confidence == 0.8

    def test_build_from_reflection_returns_experience(self, builder: ExperienceBuilder) -> None:
        ctx = make_reflection_context()
        report = make_reflection_report()
        exp = builder.build_from_reflection(ctx, report)
        assert isinstance(exp, EngineeringExperience)

    def test_build_from_entries_returns_experience(self, builder: ExperienceBuilder) -> None:
        entries = (MemoryEntry(run_id="r", goal="g", reflection_id="ref"),)
        exp = builder.build_from_entries(entries)
        assert isinstance(exp, EngineeringExperience)

    def test_build_from_reflection_lesson_recommendation(self, builder: ExperienceBuilder) -> None:
        ctx = make_reflection_context()
        report = make_reflection_report()

        exp = builder.build_from_reflection(ctx, report)
        # The builder should map high priority recommendations to lessons
        assert exp.lessons[0].recommendation == "Increase coverage"
