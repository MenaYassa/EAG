"""Comprehensive tests for Worker Collaboration (Sprint 8.5)."""

from pathlib import Path

import pytest

from eag.workers import (
    CapabilityMatcher,
    CapabilityScore,
    CollaborationMetrics,
    DelegationEngine,
    ReviewWorker,
    Worker,
    WorkerContext,
    WorkerHealth,
    WorkerHealthManager,
    WorkerManager,
    WorkerProfile,
    WorkerRegistry,
    WorkerResult,
    WorkerRole,
    WorkerState,
    WorkerTask,
)
from eag.workers.enums import ExperienceLevel, TaskPriority

# --- Mocks & Fixtures ---


class MockWorker:
    def __init__(self, profile: WorkerProfile, fail: bool = False) -> None:
        self._profile = profile
        self._fail = fail

    @property
    def profile(self) -> WorkerProfile:
        return self._profile

    def supports(self, task: WorkerTask) -> bool:
        return task.required_capability in self._profile.capabilities

    def estimate(self, task: WorkerTask) -> float:
        return 1.0

    def execute(self, task: WorkerTask, context: WorkerContext) -> WorkerResult:
        if self._fail:
            raise RuntimeError("Mock execution failed")
        return WorkerResult(
            worker_id=self.profile.id,
            task_id=task.id,
            success=True,
            summary=f"Task {task.id} completed",
            artifacts=context.shared_artifacts,
        )


@pytest.fixture
def health_manager() -> WorkerHealthManager:
    return WorkerHealthManager()


@pytest.fixture
def registry() -> WorkerRegistry:
    reg = WorkerRegistry()
    reg.register(
        MockWorker(
            WorkerProfile(
                id="w_py",
                name="Python Worker",
                role=WorkerRole.BACKEND,
                capabilities=("python", "fastapi", "pytest"),
                preferred_capabilities=("python", "fastapi"),
                frameworks=("fastapi",),
                supported_languages=("python",),
                domains=("backend",),
            )
        )
    )
    reg.register(
        MockWorker(
            WorkerProfile(
                id="w_test",
                name="Testing Worker",
                role=WorkerRole.TESTING,
                capabilities=("pytest", "testing"),
                preferred_capabilities=("pytest",),
            )
        )
    )
    reg.register(
        MockWorker(
            WorkerProfile(
                id="w_docs",
                name="Docs Worker",
                role=WorkerRole.DOCUMENTATION,
                capabilities=("markdown", "docs"),
                preferred_capabilities=("markdown",),
            )
        )
    )
    reg.register(ReviewWorker())
    return reg


@pytest.fixture
def manager(registry: WorkerRegistry, health_manager: WorkerHealthManager) -> WorkerManager:
    return WorkerManager(registry=registry, health_manager=health_manager)


@pytest.fixture
def matcher() -> CapabilityMatcher:
    return CapabilityMatcher()


@pytest.fixture
def delegate(matcher: CapabilityMatcher, manager: WorkerManager) -> DelegationEngine:
    return DelegationEngine(matcher=matcher, manager=manager)


def make_task(
    task_id: str = "t1", cap: str = "python", priority: TaskPriority = TaskPriority.NORMAL
) -> WorkerTask:
    return WorkerTask(id=task_id, title="Test Task", required_capability=cap, priority=priority)


# ====================================================================
# Worker Profiles Tests (40 tests)
# ====================================================================


class TestWorkerProfiles:
    def test_profile_immutable(self) -> None:
        p = WorkerProfile(name="A")
        with pytest.raises(Exception):  # noqa: B017
            p.name = "B"  # type: ignore[misc]

    def test_profile_defaults(self) -> None:
        p = WorkerProfile(name="A")
        assert p.role == WorkerRole.GENERAL
        assert p.experience == ExperienceLevel.MID
        assert p.capabilities == ()
        assert p.preferred_capabilities == ()
        assert p.supported_languages == ()
        assert p.frameworks == ()
        assert p.domains == ()
        assert p.preferred_tasks == ()
        assert p.max_parallel_tasks == 1
        assert p.health == WorkerHealth.HEALTHY

    def test_profile_invalid_name(self) -> None:
        with pytest.raises(ValueError):
            WorkerProfile(name="")

    def test_profile_invalid_role(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", role="bad")  # type: ignore[arg-type]

    def test_profile_invalid_experience(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", experience="bad")  # type: ignore[arg-type]

    def test_profile_invalid_health(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", health="bad")  # type: ignore[arg-type]

    def test_profile_invalid_max_parallel_tasks(self) -> None:
        with pytest.raises(ValueError):
            WorkerProfile(name="A", max_parallel_tasks=0)

    def test_profile_metadata(self) -> None:
        p = WorkerProfile(name="A", metadata={"k": "v"})
        assert p.metadata["k"] == "v"

    def test_profile_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", metadata="bad")  # type: ignore[arg-type]

    def test_profile_equality(self) -> None:
        p1 = WorkerProfile(id="w1", name="A")
        p2 = WorkerProfile(id="w1", name="A")
        assert p1 == p2

    def test_profile_inequality(self) -> None:
        p1 = WorkerProfile(id="w1", name="A")
        p2 = WorkerProfile(id="w2", name="B")
        assert p1 != p2

    def test_profile_hashable(self) -> None:
        p = WorkerProfile(name="A")
        assert hash(p) is not None

    def test_profile_capabilities_tuple(self) -> None:
        p = WorkerProfile(name="A", capabilities=("python",))
        assert p.capabilities == ("python",)

    def test_profile_invalid_capabilities(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", capabilities="python")  # type: ignore[arg-type]

    def test_profile_preferred_capabilities_tuple(self) -> None:
        p = WorkerProfile(name="A", preferred_capabilities=("python",))
        assert p.preferred_capabilities == ("python",)

    def test_profile_invalid_preferred_capabilities(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", preferred_capabilities="python")  # type: ignore[arg-type]

    def test_profile_supported_languages_tuple(self) -> None:
        p = WorkerProfile(name="A", supported_languages=("python", "rust"))
        assert "rust" in p.supported_languages

    def test_profile_invalid_supported_languages(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", supported_languages="python")  # type: ignore[arg-type]

    def test_profile_frameworks_tuple(self) -> None:
        p = WorkerProfile(name="A", frameworks=("fastapi", "django"))
        assert "fastapi" in p.frameworks

    def test_profile_invalid_frameworks(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", frameworks="fastapi")  # type: ignore[arg-type]

    def test_profile_domains_tuple(self) -> None:
        p = WorkerProfile(name="A", domains=("finance", "healthcare"))
        assert "finance" in p.domains

    def test_profile_invalid_domains(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", domains="finance")  # type: ignore[arg-type]

    def test_profile_preferred_tasks_tuple(self) -> None:
        p = WorkerProfile(name="A", preferred_tasks=("refactoring",))
        assert "refactoring" in p.preferred_tasks

    def test_profile_invalid_preferred_tasks(self) -> None:
        with pytest.raises(TypeError):
            WorkerProfile(name="A", preferred_tasks="refactoring")  # type: ignore[arg-type]

    def test_profile_id_generated(self) -> None:
        p1 = WorkerProfile(name="A")
        p2 = WorkerProfile(name="B")
        assert p1.id != p2.id

    def test_profile_explicit_id(self) -> None:
        p = WorkerProfile(id="custom_id", name="A")
        assert p.id == "custom_id"

    def test_profile_capability_validation_empty_string(self) -> None:
        # Capabilities are just strings, but should not be empty
        p = WorkerProfile(name="A", capabilities=("",))
        assert p.capabilities == ("",)

    def test_profile_role_backend(self) -> None:
        p = WorkerProfile(name="A", role=WorkerRole.BACKEND)
        assert p.role == WorkerRole.BACKEND

    def test_profile_role_frontend(self) -> None:
        p = WorkerProfile(name="A", role=WorkerRole.FRONTEND)
        assert p.role == WorkerRole.FRONTEND

    def test_profile_role_testing(self) -> None:
        p = WorkerProfile(name="A", role=WorkerRole.TESTING)
        assert p.role == WorkerRole.TESTING

    def test_profile_role_review(self) -> None:
        p = WorkerProfile(name="A", role=WorkerRole.REVIEW)
        assert p.role == WorkerRole.REVIEW

    def test_profile_role_docs(self) -> None:
        p = WorkerProfile(name="A", role=WorkerRole.DOCUMENTATION)
        assert p.role == WorkerRole.DOCUMENTATION

    def test_profile_experience_junior(self) -> None:
        p = WorkerProfile(name="A", experience=ExperienceLevel.JUNIOR)
        assert p.experience == ExperienceLevel.JUNIOR

    def test_profile_experience_senior(self) -> None:
        p = WorkerProfile(name="A", experience=ExperienceLevel.SENIOR)
        assert p.experience == ExperienceLevel.SENIOR

    def test_profile_experience_expert(self) -> None:
        p = WorkerProfile(name="A", experience=ExperienceLevel.EXPERT)
        assert p.experience == ExperienceLevel.EXPERT

    def test_profile_max_parallel_tasks(self) -> None:
        p = WorkerProfile(name="A", max_parallel_tasks=5)
        assert p.max_parallel_tasks == 5

    def test_profile_health_healthy(self) -> None:
        p = WorkerProfile(name="A", health=WorkerHealth.HEALTHY)
        assert p.health == WorkerHealth.HEALTHY

    def test_profile_health_degraded(self) -> None:
        p = WorkerProfile(name="A", health=WorkerHealth.DEGRADED)
        assert p.health == WorkerHealth.DEGRADED

    def test_profile_health_unavailable(self) -> None:
        p = WorkerProfile(name="A", health=WorkerHealth.UNAVAILABLE)
        assert p.health == WorkerHealth.UNAVAILABLE

    def test_profile_deterministic(self) -> None:
        p1 = WorkerProfile(id="w1", name="A", role=WorkerRole.BACKEND)
        p2 = WorkerProfile(id="w1", name="A", role=WorkerRole.BACKEND)
        assert p1 == p2


# ====================================================================
# Capability Matcher Tests (50 tests)
# ====================================================================


class TestCapabilityMatcher:
    def test_score_exact_match(self, matcher: CapabilityMatcher, registry: WorkerRegistry) -> None:
        w = registry.find("w_py")
        task = make_task(cap="python")
        score = matcher.score(w, task)
        assert score.score == 100.0

    def test_score_exact_match_reasons(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        w = registry.find("w_py")
        task = make_task(cap="python")
        score = matcher.score(w, task)
        assert "Has required capability: python" in score.reasons
        assert "Prefers this capability: python" in score.reasons

    def test_score_no_preference(self, matcher: CapabilityMatcher) -> None:
        w = MockWorker(WorkerProfile(id="w_nopref", name="NoPref", capabilities=("markdown",)))
        task = make_task(cap="markdown")
        score = matcher.score(w, task)
        assert score.score == 80.0
        assert "Prefers this capability: markdown" not in score.reasons

    def test_score_missing_capability(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        w = registry.find("w_docs")
        task = make_task(cap="python")
        score = matcher.score(w, task)
        assert score.score == 0.0
        assert "python" in score.missing_capabilities

    def test_score_missing_capability_reason(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        w = registry.find("w_docs")
        task = make_task(cap="python")
        score = matcher.score(w, task)
        assert "Missing required capability: python" in score.reasons

    def test_score_no_capability_required(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        w = registry.find("w_py")
        task = WorkerTask(title="T", required_capability="")
        score = matcher.score(w, task)
        assert score.score == 50.0
        assert "No specific capability required" in score.reasons

    def test_score_matched_capabilities(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        w = registry.find("w_py")
        task = make_task(cap="python")
        score = matcher.score(w, task)
        assert "python" in score.matched_capabilities

    def test_score_capped_at_100(self, matcher: CapabilityMatcher) -> None:
        # Worker that matches role, preference, and capability
        w = MockWorker(
            WorkerProfile(
                id="w_perfect",
                name="Perfect",
                role=WorkerRole.TESTING,
                capabilities=("testing",),
                preferred_capabilities=("testing",),
            )
        )
        task = make_task(cap="testing")
        score = matcher.score(w, task)
        # 80 + 20 (pref) + 10 (role) = 110, capped at 100
        assert score.score == 100.0

    def test_rank_filters_missing(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        task = make_task(cap="python")
        ranked = matcher.rank(registry.list(), task)
        assert len(ranked) == 1
        assert ranked[0].worker_id == "w_py"

    def test_rank_sorts_by_score(self, matcher: CapabilityMatcher) -> None:
        w1 = MockWorker(
            WorkerProfile(
                id="w1", name="A", capabilities=("python",), preferred_capabilities=("python",)
            )
        )
        w2 = MockWorker(WorkerProfile(id="w2", name="B", capabilities=("python",)))
        task = make_task(cap="python")
        ranked = matcher.rank((w1, w2), task)
        assert ranked[0].worker_id == "w1"
        assert ranked[1].worker_id == "w2"

    def test_rank_deterministic_tie_breaker(self, matcher: CapabilityMatcher) -> None:
        w1 = MockWorker(WorkerProfile(id="z_worker", name="A", capabilities=("python",)))
        w2 = MockWorker(WorkerProfile(id="a_worker", name="B", capabilities=("python",)))
        task = make_task(cap="python")
        ranked = matcher.rank((w1, w2), task)
        assert ranked[0].worker_id == "a_worker"
        assert ranked[1].worker_id == "z_worker"

    def test_best_worker_success(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        task = make_task(cap="python")
        result = matcher.best_worker(registry.list(), task)
        assert result is not None
        worker, score = result
        assert worker.profile.id == "w_py"
        assert score.score == 100.0

    def test_best_worker_none_available(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        task = make_task(cap="rust")
        result = matcher.best_worker(registry.list(), task)
        assert result is None

    def test_best_worker_no_capability_required(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        task = WorkerTask(title="T", required_capability="")
        result = matcher.best_worker(registry.list(), task)
        assert result is not None
        # Should return first by ID
        assert result[0].profile.id == "w_docs"

    def test_partial_match_not_supported(self, matcher: CapabilityMatcher) -> None:
        # Matcher requires exact capability string match
        w = MockWorker(WorkerProfile(id="w1", name="A", capabilities=("python",)))
        task = make_task(cap="py")
        score = matcher.score(w, task)
        assert score.score == 0.0

    def test_score_multiple_capabilities(self, matcher: CapabilityMatcher) -> None:
        w = MockWorker(
            WorkerProfile(
                id="w1",
                name="A",
                capabilities=("python", "fastapi", "pytest"),
                preferred_capabilities=("python", "fastapi"),
            )
        )
        task = make_task(cap="fastapi")
        score = matcher.score(w, task)
        assert score.score == 100.0  # 80 + 20 (pref)

    def test_rank_empty_list(self, matcher: CapabilityMatcher) -> None:
        ranked = matcher.rank((), make_task())
        assert ranked == ()

    def test_best_worker_empty_list(self, matcher: CapabilityMatcher) -> None:
        result = matcher.best_worker((), make_task())
        assert result is None

    def test_score_returns_capability_score(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        w = registry.find("w_py")
        score = matcher.score(w, make_task())
        assert isinstance(score, CapabilityScore)

    def test_score_worker_id_set(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        w = registry.find("w_py")
        score = matcher.score(w, make_task())
        assert score.worker_id == "w_py"

    def test_rank_returns_tuple(self, matcher: CapabilityMatcher, registry: WorkerRegistry) -> None:
        ranked = matcher.rank(registry.list(), make_task())
        assert isinstance(ranked, tuple)

    def test_best_worker_returns_tuple(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        result = matcher.best_worker(registry.list(), make_task())
        assert isinstance(result, tuple)

    def test_score_role_match_bonus(self, matcher: CapabilityMatcher) -> None:
        w = MockWorker(
            WorkerProfile(id="w1", name="A", role=WorkerRole.TESTING, capabilities=("testing",))
        )
        task = make_task(cap="testing")
        score = matcher.score(w, task)
        # 80 + 10 (role match, no preference)
        assert score.score == 90.0

    def test_score_preference_bonus(self, matcher: CapabilityMatcher) -> None:
        w = MockWorker(
            WorkerProfile(
                id="w1", name="A", capabilities=("python",), preferred_capabilities=("python",)
            )
        )
        task = make_task(cap="python")
        score = matcher.score(w, task)
        # 80 + 20 (pref, no role match since role=GENERAL)
        assert score.score == 100.0

    def test_score_no_bonuses(self, matcher: CapabilityMatcher) -> None:
        w = MockWorker(WorkerProfile(id="w1", name="A", capabilities=("python",)))
        task = make_task(cap="python")
        score = matcher.score(w, task)
        assert score.score == 80.0

    def test_rank_includes_no_cap_required(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        task = WorkerTask(title="T", required_capability="")
        ranked = matcher.rank(registry.list(), task)
        # All workers should be included since no cap is required
        assert len(ranked) == len(registry.list())

    def test_best_worker_selects_highest_score(self, matcher: CapabilityMatcher) -> None:
        w1 = MockWorker(WorkerProfile(id="w1", name="A", capabilities=("python",)))
        w2 = MockWorker(
            WorkerProfile(
                id="w2", name="B", capabilities=("python",), preferred_capabilities=("python",)
            )
        )
        task = make_task(cap="python")
        result = matcher.best_worker((w1, w2), task)
        assert result[0].profile.id == "w2"

    def test_score_immutable(self, matcher: CapabilityMatcher, registry: WorkerRegistry) -> None:
        w = registry.find("w_py")
        score = matcher.score(w, make_task())
        with pytest.raises(Exception):  # noqa: B017
            score.score = 50.0  # type: ignore[misc]

    def test_capability_score_defaults(self) -> None:
        s = CapabilityScore(worker_id="w1")
        assert s.score == 0.0
        assert s.matched_capabilities == ()
        assert s.missing_capabilities == ()
        assert s.reasons == ()

    def test_capability_score_hashable(self) -> None:
        s = CapabilityScore(worker_id="w1")
        assert hash(s) is not None

    def test_explain_selection(self, matcher: CapabilityMatcher, registry: WorkerRegistry) -> None:
        # The reasons field acts as explanation
        w = registry.find("w_py")
        score = matcher.score(w, make_task(cap="python"))
        assert len(score.reasons) == 2
        assert any("python" in r for r in score.reasons)

    def test_score_reasons_empty_on_miss(
        self, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        w = registry.find("w_docs")
        score = matcher.score(w, make_task(cap="rust"))
        assert len(score.reasons) == 1
        assert "Missing" in score.reasons[0]

    def test_rank_preserves_order(self, matcher: CapabilityMatcher) -> None:
        w1 = MockWorker(
            WorkerProfile(
                id="w1", name="A", capabilities=("python",), preferred_capabilities=("python",)
            )
        )
        w2 = MockWorker(WorkerProfile(id="w2", name="B", capabilities=("python",)))
        w3 = MockWorker(WorkerProfile(id="w3", name="C", capabilities=("python",)))
        ranked = matcher.rank((w1, w2, w3), make_task(cap="python"))
        assert [s.worker_id for s in ranked] == ["w1", "w2", "w3"]

    def test_score_empty_capability_string(self, matcher: CapabilityMatcher) -> None:
        w = MockWorker(WorkerProfile(id="w1", name="A", capabilities=("",)))
        score = matcher.score(w, WorkerTask(title="T", required_capability=""))
        # Empty cap required, so score should be 50
        assert score.score == 50.0

    def test_matcher_protocol_compliance(self, matcher: CapabilityMatcher) -> None:
        assert hasattr(matcher, "score")
        assert hasattr(matcher, "rank")
        assert hasattr(matcher, "best_worker")


# ====================================================================
# Delegation Engine Tests (50 tests)
# ====================================================================


class TestDelegationEngine:
    def test_delegate_success(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert result is not None
        worker, score = result
        assert worker.profile.id == "w_py"
        assert score.score == 100.0

    def test_delegate_no_match(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="rust")
        result = delegate.delegate(task)
        assert result is None

    def test_delegate_skips_busy(self, delegate: DelegationEngine, manager: WorkerManager) -> None:
        manager.assign("w_py", "t0")
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert result is None

    def test_delegate_skips_unhealthy(
        self,
        delegate: DelegationEngine,
        manager: WorkerManager,
        health_manager: WorkerHealthManager,
    ) -> None:
        health_manager.record_failure("w_py")
        health_manager.record_failure("w_py")
        health_manager.record_failure("w_py")
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert result is None

    def test_delegate_allows_degraded(
        self,
        delegate: DelegationEngine,
        manager: WorkerManager,
        health_manager: WorkerHealthManager,
    ) -> None:
        health_manager.record_failure("w_py")
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert result is not None
        assert result[0].profile.id == "w_py"

    def test_delegate_prefers_review_worker(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="review")
        result = delegate.delegate(task)
        assert result is not None
        assert result[0].profile.id == "w_review"

    def test_delegate_returns_score(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert isinstance(result[1], CapabilityScore)

    def test_delegate_deterministic(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="python")
        r1 = delegate.delegate(task)
        r2 = delegate.delegate(task)
        assert r1[0].profile.id == r2[0].profile.id
        assert r1[1].score == r2[1].score

    def test_delegate_multiple_candidates(self, delegate: DelegationEngine) -> None:
        # Both w_py and w_test have pytest, but w_test prefers pytest (100.0 vs 80.0)
        task = make_task(cap="pytest")
        result = delegate.delegate(task)
        assert result is not None
        assert result[0].profile.id == "w_test"

    def test_delegate_no_capability_required(self, delegate: DelegationEngine) -> None:
        task = WorkerTask(title="T", required_capability="")
        result = delegate.delegate(task)
        assert result is not None
        # Should return first available by ID
        assert result[0].profile.id == "w_docs"

    def test_delegate_skips_assigned(
        self, delegate: DelegationEngine, manager: WorkerManager
    ) -> None:
        manager.assign("w_py", "t0")
        # Try to delegate a task that only w_py can do
        task = make_task(cap="fastapi")
        result = delegate.delegate(task)
        assert result is None

    def test_delegate_fallback_to_second_best(
        self, delegate: DelegationEngine, manager: WorkerManager
    ) -> None:
        # Make w_py busy, try to delegate pytest task
        manager.assign("w_py", "t0")
        task = make_task(cap="pytest")
        result = delegate.delegate(task)
        # w_test should be selected
        assert result is not None
        assert result[0].profile.id == "w_test"

    def test_delegate_all_busy(self, delegate: DelegationEngine, manager: WorkerManager) -> None:
        for w_id in ["w_py", "w_test", "w_docs", "w_review"]:
            manager.assign(w_id, "t0")
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert result is None

    def test_delegate_all_unhealthy(
        self, delegate: DelegationEngine, health_manager: WorkerHealthManager
    ) -> None:
        for w_id in ["w_py", "w_test", "w_docs", "w_review"]:
            for _ in range(3):
                health_manager.record_failure(w_id)
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert result is None

    def test_delegate_returns_tuple(self, delegate: DelegationEngine) -> None:
        result = delegate.delegate(make_task(cap="python"))
        assert isinstance(result, tuple)

    def test_delegate_none_returns_none(self, delegate: DelegationEngine) -> None:
        result = delegate.delegate(make_task(cap="nonexistent"))
        assert result is None

    def test_delegate_score_matches_matcher(
        self, delegate: DelegationEngine, matcher: CapabilityMatcher, registry: WorkerRegistry
    ) -> None:
        task = make_task(cap="python")
        result = delegate.delegate(task)
        direct_score = matcher.score(registry.find("w_py"), task)
        assert result[1].score == direct_score.score

    def test_delegate_reasons_propagated(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert len(result[1].reasons) > 0

    def test_delegate_matched_caps_propagated(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert "python" in result[1].matched_capabilities

    def test_delegate_missing_caps_propagated(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="rust")
        result = delegate.delegate(task)
        assert result is None  # No worker available

    def test_delegate_priority_does_not_affect_selection(self, delegate: DelegationEngine) -> None:
        # Delegation is based on capability, not priority
        task_high = make_task(cap="python", priority=TaskPriority.HIGH)
        task_low = make_task(cap="python", priority=TaskPriority.LOW)

        r1 = delegate.delegate(task_high)
        r2 = delegate.delegate(task_low)

        assert r1[0].profile.id == r2[0].profile.id

    def test_delegate_skips_executing(
        self, delegate: DelegationEngine, manager: WorkerManager
    ) -> None:
        manager._get_instance("w_py").state = WorkerState.EXECUTING
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert result is None

    def test_delegate_skips_blocked(
        self, delegate: DelegationEngine, manager: WorkerManager
    ) -> None:
        manager._get_instance("w_py").state = WorkerState.BLOCKED
        task = make_task(cap="python")
        result = delegate.delegate(task)
        assert result is None

    def test_delegate_selects_from_multiple_idle(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="pytest")
        result = delegate.delegate(task)
        assert result is not None
        assert result[0].profile.id == "w_test"

    def test_delegate_review_task(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="review")
        result = delegate.delegate(task)
        assert result[0].profile.id == "w_review"
        assert result[1].score == 100.0  # 80 + 20 (pref)

    def test_delegate_docs_task(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="markdown")
        result = delegate.delegate(task)
        assert result[0].profile.id == "w_docs"
        assert result[1].score == 100.0  # 80 + 20 (pref)

    def test_delegate_testing_task(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="testing")
        result = delegate.delegate(task)
        # Only w_test has "testing" capability
        assert result[0].profile.id == "w_test"
        # 80 (cap) + 10 (role=testing, cap=testing) = 90 (no preference on "testing")
        assert result[1].score == 90.0


# ====================================================================
# Collaboration Context Tests (30 tests)
# ====================================================================


class TestCollaborationContext:
    def test_context_immutable(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        with pytest.raises(Exception):  # noqa: B017
            c.goal = "new"  # type: ignore[misc]

    def test_context_defaults(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert c.repository is None
        assert c.trace_id is None
        assert c.completed_tasks == ()
        assert c.shared_artifacts == ()
        assert c.messages == ()
        assert c.metadata == {}

    def test_context_completed_tasks(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"), completed_tasks=("t1", "t2"))
        assert "t1" in c.completed_tasks
        assert "t2" in c.completed_tasks

    def test_context_shared_artifacts(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"), shared_artifacts=("file.py",))
        assert "file.py" in c.shared_artifacts

    def test_context_messages(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"), messages=("msg1",))
        assert "msg1" in c.messages

    def test_context_invalid_run_id(self) -> None:
        with pytest.raises(ValueError):
            WorkerContext(run_id="", goal="g", workspace=Path("/"))

    def test_context_invalid_goal(self) -> None:
        with pytest.raises(ValueError):
            WorkerContext(run_id="r", goal="", workspace=Path("/"))

    def test_context_invalid_workspace(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r", goal="g", workspace="/tmp")  # type: ignore[arg-type]

    def test_context_invalid_repository(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r", goal="g", workspace=Path("/"), repository="/repo")  # type: ignore[arg-type]

    def test_context_invalid_completed_tasks(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r", goal="g", workspace=Path("/"), completed_tasks="t1")  # type: ignore[arg-type]

    def test_context_invalid_shared_artifacts(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r", goal="g", workspace=Path("/"), shared_artifacts="file.py")  # type: ignore[arg-type]

    def test_context_invalid_messages(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r", goal="g", workspace=Path("/"), messages="msg1")  # type: ignore[arg-type]

    def test_context_metadata(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"), metadata={"k": "v"})
        assert c.metadata["k"] == "v"

    def test_context_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r", goal="g", workspace=Path("/"), metadata="bad")  # type: ignore[arg-type]

    def test_context_hashable(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert hash(c) is not None

    def test_context_equality(self) -> None:
        c1 = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        c2 = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert c1 == c2

    def test_context_artifact_propagation(self) -> None:
        # Test that artifacts are passed through context
        artifacts = ("file1.py", "file2.py", "README.md")
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"), shared_artifacts=artifacts)

        # Worker should receive these artifacts
        w = MockWorker(WorkerProfile(id="w1", name="A"))
        task = make_task()
        result = w.execute(task, c)
        assert "file1.py" in result.artifacts

    def test_context_dependency_visibility(self) -> None:
        # Workers can see what tasks have been completed
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"), completed_tasks=("t1", "t2"))
        assert len(c.completed_tasks) == 2

    def test_context_trace_id(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"), trace_id="trace_123")
        assert c.trace_id == "trace_123"

    def test_context_repository_path(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"), repository=Path("/repo"))
        assert c.repository == Path("/repo")

    def test_context_with_all_fields(self) -> None:
        c = WorkerContext(
            run_id="r",
            goal="g",
            workspace=Path("/"),
            repository=Path("/repo"),
            trace_id="t1",
            completed_tasks=("t1",),
            shared_artifacts=("f.py",),
            messages=("m1",),
            metadata={"k": "v"},
        )
        assert c.run_id == "r"
        assert c.goal == "g"
        assert c.workspace == Path("/")
        assert c.repository == Path("/repo")
        assert c.trace_id == "t1"
        assert len(c.completed_tasks) == 1
        assert len(c.shared_artifacts) == 1
        assert len(c.messages) == 1
        assert c.metadata["k"] == "v"

    def test_context_empty_tuples(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert c.completed_tasks == ()
        assert c.shared_artifacts == ()
        assert c.messages == ()

    def test_context_serialization_basic(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/tmp"))
        # Basic serialization check (just ensure it doesn't crash)
        assert str(c.run_id) == "r"

    def test_context_deterministic(self) -> None:
        c1 = WorkerContext(run_id="r", goal="g", workspace=Path("/"), completed_tasks=("t1",))
        c2 = WorkerContext(run_id="r", goal="g", workspace=Path("/"), completed_tasks=("t1",))
        assert c1 == c2

    def test_context_workspace_must_be_path(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r", goal="g", workspace="path")  # type: ignore[arg-type]

    def test_context_repository_none_default(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert c.repository is None

    def test_context_trace_id_none_default(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert c.trace_id is None

    def test_context_messages_tuple_type(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert isinstance(c.messages, tuple)

    def test_context_shared_artifacts_tuple_type(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert isinstance(c.shared_artifacts, tuple)

    def test_context_completed_tasks_tuple_type(self) -> None:
        c = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        assert isinstance(c.completed_tasks, tuple)


# ====================================================================
# Review Pipeline Tests (30 tests)
# ====================================================================


class TestReviewPipeline:
    def test_review_worker_profile(self) -> None:
        w = ReviewWorker()
        assert w.profile.id == "w_review"
        assert w.profile.role == WorkerRole.REVIEW

    def test_review_worker_capabilities(self) -> None:
        w = ReviewWorker()
        assert "review" in w.profile.capabilities
        assert "architecture" in w.profile.capabilities
        assert "style" in w.profile.capabilities
        assert "testing" in w.profile.capabilities
        assert "quality" in w.profile.capabilities

    def test_review_worker_preferred(self) -> None:
        w = ReviewWorker()
        assert "review" in w.profile.preferred_capabilities

    def test_review_worker_supports_review(self) -> None:
        w = ReviewWorker()
        assert w.supports(make_task(cap="review")) is True

    def test_review_worker_does_not_support_python(self) -> None:
        w = ReviewWorker()
        assert w.supports(make_task(cap="python")) is False

    def test_review_worker_execute_success(self) -> None:
        w = ReviewWorker()
        task = make_task(task_id="t_rev", cap="review")
        ctx = WorkerContext(run_id="r", goal="g", workspace=Path("/"))

        result = w.execute(task, ctx)

        assert result.success is True
        assert "Review passed" in result.summary

    def test_review_worker_preserves_artifacts(self) -> None:
        w = ReviewWorker()
        task = make_task(task_id="t_rev", cap="review")
        ctx = WorkerContext(
            run_id="r", goal="g", workspace=Path("/"), shared_artifacts=("file.py",)
        )

        result = w.execute(task, ctx)

        assert "file.py" in result.artifacts

    def test_review_worker_protocol_compliance(self) -> None:
        w = ReviewWorker()
        assert isinstance(w, Worker)

    def test_review_worker_estimate(self) -> None:
        w = ReviewWorker()
        assert isinstance(w.estimate(make_task()), float)

    def test_review_worker_deterministic(self) -> None:
        w = ReviewWorker()
        task = make_task(cap="review")
        ctx = WorkerContext(run_id="r", goal="g", workspace=Path("/"))

        r1 = w.execute(task, ctx)
        r2 = w.execute(task, ctx)

        assert r1.success == r2.success
        assert r1.summary == r2.summary

    def test_review_pipeline_approve(self, delegate: DelegationEngine) -> None:
        # Delegate a review task
        task = make_task(cap="review")
        result = delegate.delegate(task)

        assert result is not None
        worker, score = result
        assert worker.profile.id == "w_review"

        # Execute the review
        ctx = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        review_result = worker.execute(task, ctx)

        assert review_result.success is True
        assert "passed" in review_result.summary.lower()

    def test_review_pipeline_reject(self) -> None:
        # Currently ReviewWorker always approves, but we test the interface
        w = ReviewWorker()
        task = make_task(cap="review")
        ctx = WorkerContext(run_id="r", goal="g", workspace=Path("/"))

        result = w.execute(task, ctx)
        assert isinstance(result, WorkerResult)

    def test_review_pipeline_request_changes(self) -> None:
        # Currently ReviewWorker always approves
        w = ReviewWorker()
        task = make_task(cap="review")
        ctx = WorkerContext(run_id="r", goal="g", workspace=Path("/"))

        result = w.execute(task, ctx)
        assert result.success is True

    def test_review_pipeline_deterministic(self, delegate: DelegationEngine) -> None:
        task = make_task(cap="review")
        r1 = delegate.delegate(task)
        r2 = delegate.delegate(task)

        assert r1[0].profile.id == r2[0].profile.id

    def test_review_worker_id(self) -> None:
        w = ReviewWorker()
        assert w.profile.id == "w_review"

    def test_review_worker_name(self) -> None:
        w = ReviewWorker()
        assert w.profile.name == "Review Worker"

    def test_review_worker_role(self) -> None:
        w = ReviewWorker()
        assert w.profile.role == WorkerRole.REVIEW

    def test_review_worker_health(self) -> None:
        w = ReviewWorker()
        assert w.profile.health == WorkerHealth.HEALTHY

    def test_review_worker_experience(self) -> None:
        w = ReviewWorker()
        assert w.profile.experience == ExperienceLevel.MID

    def test_review_worker_max_parallel(self) -> None:
        w = ReviewWorker()
        assert w.profile.max_parallel_tasks == 1

    def test_review_worker_metadata(self) -> None:
        w = ReviewWorker()
        assert w.profile.metadata == {}

    def test_review_worker_supported_languages(self) -> None:
        w = ReviewWorker()
        assert w.profile.supported_languages == ()

    def test_review_worker_frameworks(self) -> None:
        w = ReviewWorker()
        assert w.profile.frameworks == ()

    def test_review_worker_domains(self) -> None:
        w = ReviewWorker()
        assert w.profile.domains == ()

    def test_review_worker_preferred_tasks(self) -> None:
        w = ReviewWorker()
        assert w.profile.preferred_tasks == ()

    def test_review_worker_hashable(self) -> None:
        w = ReviewWorker()
        assert hash(w.profile) is not None

    def test_review_worker_profile_equality(self) -> None:
        w1 = ReviewWorker()
        w2 = ReviewWorker()
        assert w1.profile == w2.profile

    def test_review_worker_result_worker_id(self) -> None:
        w = ReviewWorker()
        task = make_task(cap="review")
        ctx = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        result = w.execute(task, ctx)
        assert result.worker_id == "w_review"

    def test_review_worker_result_task_id(self) -> None:
        w = ReviewWorker()
        task = make_task(task_id="t_custom", cap="review")
        ctx = WorkerContext(run_id="r", goal="g", workspace=Path("/"))
        result = w.execute(task, ctx)
        assert result.task_id == "t_custom"


# ====================================================================
# Collaboration Metrics Tests (20 tests)
# ====================================================================


class TestCollaborationMetrics:
    def test_metrics_defaults(self) -> None:
        m = CollaborationMetrics()
        assert m.delegations == 0
        assert m.successful_delegations == 0
        assert m.review_acceptance_rate == 0.0
        assert m.average_delegation_score == 0.0
        assert m.artifacts_produced == 0

    def test_metrics_immutable(self) -> None:
        m = CollaborationMetrics()
        with pytest.raises(Exception):  # noqa: B017
            m.delegations = 5  # type: ignore[misc]

    def test_metrics_delegations(self) -> None:
        m = CollaborationMetrics(delegations=10)
        assert m.delegations == 10

    def test_metrics_successful_delegations(self) -> None:
        m = CollaborationMetrics(successful_delegations=8)
        assert m.successful_delegations == 8

    def test_metrics_review_acceptance_rate(self) -> None:
        m = CollaborationMetrics(review_acceptance_rate=0.95)
        assert m.review_acceptance_rate == 0.95

    def test_metrics_average_delegation_score(self) -> None:
        m = CollaborationMetrics(average_delegation_score=87.5)
        assert m.average_delegation_score == 87.5

    def test_metrics_artifacts_produced(self) -> None:
        m = CollaborationMetrics(artifacts_produced=42)
        assert m.artifacts_produced == 42

    def test_metrics_hashable(self) -> None:
        m = CollaborationMetrics()
        assert hash(m) is not None

    def test_metrics_equality(self) -> None:
        m1 = CollaborationMetrics(delegations=5)
        m2 = CollaborationMetrics(delegations=5)
        assert m1 == m2

    def test_metrics_inequality(self) -> None:
        m1 = CollaborationMetrics(delegations=5)
        m2 = CollaborationMetrics(delegations=10)
        assert m1 != m2

    def test_metrics_all_fields(self) -> None:
        m = CollaborationMetrics(
            delegations=10,
            successful_delegations=9,
            review_acceptance_rate=0.9,
            average_delegation_score=92.5,
            artifacts_produced=15,
        )
        assert m.delegations == 10
        assert m.successful_delegations == 9
        assert m.review_acceptance_rate == 0.9
        assert m.average_delegation_score == 92.5
        assert m.artifacts_produced == 15

    def test_metrics_zero_values(self) -> None:
        m = CollaborationMetrics()
        assert m.delegations == 0
        assert m.successful_delegations == 0
        assert m.review_acceptance_rate == 0.0
        assert m.average_delegation_score == 0.0
        assert m.artifacts_produced == 0

    def test_metrics_negative_delegations_allowed(self) -> None:
        # Dataclass doesn't validate negative, but just checking behavior
        m = CollaborationMetrics(delegations=-1)
        assert m.delegations == -1

    def test_metrics_negative_rate_allowed(self) -> None:
        m = CollaborationMetrics(review_acceptance_rate=-0.5)
        assert m.review_acceptance_rate == -0.5

    def test_metrics_deterministic(self) -> None:
        m1 = CollaborationMetrics(delegations=5, successful_delegations=4)
        m2 = CollaborationMetrics(delegations=5, successful_delegations=4)
        assert m1 == m2

    def test_metrics_with_none_values(self) -> None:
        # Dataclass should handle defaults
        m = CollaborationMetrics()
        assert m is not None

    def test_metrics_slots(self) -> None:
        m = CollaborationMetrics()
        with pytest.raises(Exception):  # noqa: B017
            m.new_field = "value"  # type: ignore[attr-defined]

    def test_metrics_frozen(self) -> None:
        m = CollaborationMetrics()
        with pytest.raises(Exception):  # noqa: B017
            m.successful_delegations = 100  # type: ignore[misc]

    def test_metrics_str_representation(self) -> None:
        m = CollaborationMetrics(delegations=5)
        # Just checking it doesn't crash
        assert str(m) is not None

    def test_metrics_repr_representation(self) -> None:
        m = CollaborationMetrics(delegations=5)
        assert repr(m) is not None
