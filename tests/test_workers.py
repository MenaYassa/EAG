"""Comprehensive tests for the Worker Domain (Sprint 8.1)."""

from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

from eag.workers import (
    ExperienceLevel,
    TaskPriority,
    Worker,
    WorkerAssignment,
    WorkerContext,
    WorkerError,
    WorkerHealth,
    WorkerMetrics,
    WorkerProfile,
    WorkerResult,
    WorkerRole,
    WorkerState,
    WorkerTask,
)
from eag.workers.errors import (
    WorkerAssignmentError,
    WorkerBusyError,
    WorkerCapabilityError,
    WorkerNotFoundError,
    WorkerUnavailableError,
)

# --- Enum Tests (15) ---


class TestEnums:
    def test_worker_role_values(self) -> None:
        assert WorkerRole.BACKEND == "backend"
        assert WorkerRole.AI == "ai"

    def test_worker_state_values(self) -> None:
        assert WorkerState.EXECUTING == "executing"
        assert WorkerState.IDLE == "idle"

    def test_worker_health_values(self) -> None:
        assert WorkerHealth.HEALTHY == "healthy"
        assert WorkerHealth.UNAVAILABLE == "unavailable"

    def test_experience_level_values(self) -> None:
        assert ExperienceLevel.SENIOR == "senior"
        assert ExperienceLevel.JUNIOR == "junior"

    def test_task_priority_values(self) -> None:
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.LOW == "low"

    def test_worker_role_count(self) -> None:
        assert len(list(WorkerRole)) == 10

    def test_worker_state_count(self) -> None:
        assert len(list(WorkerState)) == 9

    def test_worker_health_count(self) -> None:
        assert len(list(WorkerHealth)) == 4

    def test_experience_level_count(self) -> None:
        assert len(list(ExperienceLevel)) == 4

    def test_task_priority_count(self) -> None:
        assert len(list(TaskPriority)) == 4

    def test_enum_immutable(self) -> None:
        with pytest.raises(AttributeError):
            WorkerRole.BACKEND = "new_role"  # type: ignore[misc]

    def test_role_order(self) -> None:
        roles = list(WorkerRole)
        assert roles.index(WorkerRole.GENERAL) < roles.index(WorkerRole.AI)

    def test_state_order(self) -> None:
        states = list(WorkerState)
        assert states.index(WorkerState.IDLE) < states.index(WorkerState.COMPLETED)

    def test_health_order(self) -> None:
        healths = list(WorkerHealth)
        assert healths.index(WorkerHealth.HEALTHY) < healths.index(WorkerHealth.UNAVAILABLE)

    def test_priority_order(self) -> None:
        priorities = list(TaskPriority)
        assert priorities.index(TaskPriority.LOW) < priorities.index(TaskPriority.CRITICAL)


# --- WorkerProfile Tests (15) ---


class TestWorkerProfile:
    def test_profile_immutable(self) -> None:
        p = WorkerProfile(name="Alice")
        with pytest.raises(FrozenInstanceError):
            p.name = "Bob"  # type: ignore[misc]

    def test_profile_invalid_name(self) -> None:
        with pytest.raises(ValueError):
            WorkerProfile(name="")

    def test_profile_defaults(self) -> None:
        p = WorkerProfile(name="Alice")
        assert p.role == WorkerRole.GENERAL
        assert p.experience == ExperienceLevel.MID
        assert p.max_parallel_tasks == 1
        assert p.health == WorkerHealth.HEALTHY

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

    def test_profile_capabilities_tuple(self) -> None:
        p = WorkerProfile(name="A", capabilities=("python",))
        assert p.capabilities == ("python",)

    def test_profile_preferred_capabilities(self) -> None:
        p = WorkerProfile(name="A", preferred_capabilities=("testing",))
        assert p.preferred_capabilities == ("testing",)

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

    def test_profile_supported_languages(self) -> None:
        p = WorkerProfile(name="A", supported_languages=("python", "rust"))
        assert "rust" in p.supported_languages


# --- WorkerTask Tests (15) ---


class TestWorkerTask:
    def test_task_immutable(self) -> None:
        t = WorkerTask(title="Do something")
        with pytest.raises(FrozenInstanceError):
            t.title = "new"  # type: ignore[misc]

    def test_task_invalid_title(self) -> None:
        with pytest.raises(ValueError):
            WorkerTask(title="")

    def test_task_defaults(self) -> None:
        t = WorkerTask(title="Task")
        assert t.priority == TaskPriority.NORMAL
        assert t.dependencies == ()
        assert t.estimated_complexity == 1.0

    def test_task_invalid_priority(self) -> None:
        with pytest.raises(TypeError):
            WorkerTask(title="T", priority="bad")  # type: ignore[arg-type]

    def test_task_dependencies_tuple(self) -> None:
        t = WorkerTask(title="T", dependencies=("t1",))
        assert t.dependencies == ("t1",)

    def test_task_invalid_dependencies(self) -> None:
        with pytest.raises(TypeError):
            WorkerTask(title="T", dependencies=["t1"])  # type: ignore[arg-type]

    def test_task_metadata(self) -> None:
        t = WorkerTask(title="T", metadata={"k": "v"})
        assert t.metadata["k"] == "v"

    def test_task_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            WorkerTask(title="T", metadata="bad")  # type: ignore[arg-type]

    def test_task_estimated_complexity(self) -> None:
        t = WorkerTask(title="T", estimated_complexity=5.5)
        assert t.estimated_complexity == 5.5

    def test_task_invalid_complexity_type(self) -> None:
        with pytest.raises(ValueError):
            WorkerTask(title="T", estimated_complexity="high")  # type: ignore[arg-type]

    def test_task_invalid_complexity_negative(self) -> None:
        with pytest.raises(ValueError):
            WorkerTask(title="T", estimated_complexity=-1.0)

    def test_task_required_capability(self) -> None:
        t = WorkerTask(title="T", required_capability="python")
        assert t.required_capability == "python"

    def test_task_id_generated(self) -> None:
        t1 = WorkerTask(title="T1")
        t2 = WorkerTask(title="T2")
        assert t1.id != t2.id

    def test_task_hashable(self) -> None:
        t = WorkerTask(title="T")
        assert hash(t) is not None

    def test_task_equality(self) -> None:
        t1 = WorkerTask(id="t1", title="T")
        t2 = WorkerTask(id="t1", title="T")
        assert t1 == t2


# --- Assignment Tests (10) ---


class TestAssignments:
    def test_assignment_immutable(self) -> None:
        a = WorkerAssignment(worker_id="w1", task_id="t1")
        with pytest.raises(FrozenInstanceError):
            a.worker_id = "w2"  # type: ignore[misc]

    def test_assignment_invalid_worker_id(self) -> None:
        with pytest.raises(ValueError):
            WorkerAssignment(worker_id="", task_id="t1")

    def test_assignment_invalid_task_id(self) -> None:
        with pytest.raises(ValueError):
            WorkerAssignment(worker_id="w1", task_id="")

    def test_assignment_defaults(self) -> None:
        a = WorkerAssignment(worker_id="w1", task_id="t1")
        assert a.reason == ""
        assert isinstance(a.assigned_at, datetime)

    def test_assignment_metadata(self) -> None:
        a = WorkerAssignment(worker_id="w1", task_id="t1", metadata={"k": "v"})
        assert a.metadata["k"] == "v"

    def test_assignment_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            WorkerAssignment(worker_id="w1", task_id="t1", metadata="bad")  # type: ignore[arg-type]

    def test_assignment_id_generated(self) -> None:
        a1 = WorkerAssignment(worker_id="w1", task_id="t1")
        a2 = WorkerAssignment(worker_id="w1", task_id="t1")
        assert a1.assignment_id != a2.assignment_id

    def test_assignment_hashable(self) -> None:
        a = WorkerAssignment(worker_id="w1", task_id="t1")
        assert hash(a) is not None

    def test_assignment_equality(self) -> None:
        a1 = WorkerAssignment(assignment_id="a1", worker_id="w1", task_id="t1")
        a2 = WorkerAssignment(assignment_id="a1", worker_id="w1", task_id="t1")
        assert a1 == a2

    def test_assignment_timestamp_aware(self) -> None:
        a = WorkerAssignment(worker_id="w1", task_id="t1")
        assert a.assigned_at.tzinfo is not None


# --- Context Tests (10) ---


class TestWorkerContext:
    def test_context_immutable(self) -> None:
        c = WorkerContext(run_id="r1", goal="G", workspace=Path("/tmp"))
        with pytest.raises(FrozenInstanceError):
            c.goal = "new"  # type: ignore[misc]

    def test_context_invalid_run_id(self) -> None:
        with pytest.raises(ValueError):
            WorkerContext(run_id="", goal="G", workspace=Path("/tmp"))

    def test_context_invalid_goal(self) -> None:
        with pytest.raises(ValueError):
            WorkerContext(run_id="r1", goal="", workspace=Path("/tmp"))

    def test_context_invalid_workspace(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r1", goal="G", workspace="/tmp")  # type: ignore[arg-type]

    def test_context_defaults(self) -> None:
        c = WorkerContext(run_id="r1", goal="G", workspace=Path("/tmp"))
        assert c.repository is None
        assert c.trace_id is None
        assert c.metadata == {}

    def test_context_metadata(self) -> None:
        c = WorkerContext(run_id="r1", goal="G", workspace=Path("/tmp"), metadata={"k": "v"})
        assert c.metadata["k"] == "v"

    def test_context_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r1", goal="G", workspace=Path("/tmp"), metadata="bad")  # type: ignore[arg-type]

    def test_context_repository_path(self) -> None:
        c = WorkerContext(run_id="r1", goal="G", workspace=Path("/tmp"), repository=Path("/repo"))
        assert c.repository == Path("/repo")

    def test_context_invalid_repository(self) -> None:
        with pytest.raises(TypeError):
            WorkerContext(run_id="r1", goal="G", workspace=Path("/tmp"), repository="/repo")  # type: ignore[arg-type]

    def test_context_hashable(self) -> None:
        c = WorkerContext(run_id="r1", goal="G", workspace=Path("/tmp"))
        assert hash(c) is not None


# --- Result Tests (15) ---


class TestWorkerResult:
    def test_result_immutable(self) -> None:
        r = WorkerResult(worker_id="w1", task_id="t1", success=True)
        with pytest.raises(FrozenInstanceError):
            r.success = False  # type: ignore[misc]

    def test_result_invalid_worker_id(self) -> None:
        with pytest.raises(ValueError):
            WorkerResult(worker_id="", task_id="t1", success=True)

    def test_result_invalid_task_id(self) -> None:
        with pytest.raises(ValueError):
            WorkerResult(worker_id="w1", task_id="", success=True)

    def test_result_invalid_success(self) -> None:
        with pytest.raises(TypeError):
            WorkerResult(worker_id="w1", task_id="t1", success="yes")  # type: ignore[arg-type]

    def test_result_is_success(self) -> None:
        r = WorkerResult(worker_id="w1", task_id="t1", success=True)
        assert r.is_success is True
        assert r.is_failure is False

    def test_result_is_failure(self) -> None:
        r = WorkerResult(worker_id="w1", task_id="t1", success=False)
        assert r.is_failure is True
        assert r.is_success is False

    def test_result_artifacts(self) -> None:
        r = WorkerResult(worker_id="w1", task_id="t1", success=True, artifacts=("file.py",))
        assert "file.py" in r.artifacts

    def test_result_invalid_artifacts(self) -> None:
        with pytest.raises(TypeError):
            WorkerResult(worker_id="w1", task_id="t1", success=True, artifacts=["file.py"])  # type: ignore[arg-type]

    def test_result_warnings(self) -> None:
        r = WorkerResult(worker_id="w1", task_id="t1", success=True, warnings=("warn1",))
        assert "warn1" in r.warnings

    def test_result_invalid_warnings(self) -> None:
        with pytest.raises(TypeError):
            WorkerResult(worker_id="w1", task_id="t1", success=True, warnings=["warn1"])  # type: ignore[arg-type]

    def test_result_metrics(self) -> None:
        m = WorkerMetrics(tasks_completed=1)
        r = WorkerResult(worker_id="w1", task_id="t1", success=True, metrics=m)
        assert r.metrics.tasks_completed == 1

    def test_result_invalid_metrics(self) -> None:
        with pytest.raises(TypeError):
            WorkerResult(worker_id="w1", task_id="t1", success=True, metrics="bad")  # type: ignore[arg-type]

    def test_result_metadata(self) -> None:
        r = WorkerResult(worker_id="w1", task_id="t1", success=True, metadata={"k": "v"})
        assert r.metadata["k"] == "v"

    def test_result_hashable(self) -> None:
        r = WorkerResult(worker_id="w1", task_id="t1", success=True)
        assert hash(r) is not None

    def test_result_defaults(self) -> None:
        r = WorkerResult(worker_id="w1", task_id="t1", success=True)
        assert r.summary == ""
        assert r.artifacts == ()
        assert r.warnings == ()


# --- Protocol & Metrics Tests (10) ---


class TestProtocolAndMetrics:
    def test_worker_metrics_immutable(self) -> None:
        m = WorkerMetrics()
        with pytest.raises(FrozenInstanceError):
            m.tasks_completed = 5  # type: ignore[misc]

    def test_worker_metrics_negative_value(self) -> None:
        with pytest.raises(ValueError):
            WorkerMetrics(tasks_completed=-1)

    def test_worker_metrics_defaults(self) -> None:
        m = WorkerMetrics()
        assert m.tasks_completed == 0
        assert m.average_duration_ms == 0.0

    def test_worker_protocol_compliance(self) -> None:
        class MockWorker:
            @property
            def profile(self) -> WorkerProfile:
                return WorkerProfile(name="Test")

            def supports(self, task: WorkerTask) -> bool:
                return True

            def estimate(self, task: WorkerTask) -> float:
                return 1.0

            def execute(self, task: WorkerTask, context: WorkerContext) -> WorkerResult:
                return WorkerResult(worker_id="w1", task_id=task.id, success=True)

        w = MockWorker()
        assert isinstance(w, Worker)

    def test_worker_protocol_missing_method(self) -> None:
        class IncompleteWorker:
            @property
            def profile(self) -> WorkerProfile:
                return WorkerProfile(name="Test")

        w = IncompleteWorker()
        assert not isinstance(w, Worker)

    def test_worker_metrics_hashable(self) -> None:
        m = WorkerMetrics()
        assert hash(m) is not None

    def test_worker_metrics_equality(self) -> None:
        m1 = WorkerMetrics(tasks_completed=1)
        m2 = WorkerMetrics(tasks_completed=1)
        assert m1 == m2

    def test_worker_profile_deterministic(self) -> None:
        p1 = WorkerProfile(id="w1", name="A", role=WorkerRole.BACKEND)
        p2 = WorkerProfile(id="w1", name="A", role=WorkerRole.BACKEND)
        assert p1 == p2

    def test_worker_task_deterministic(self) -> None:
        t1 = WorkerTask(id="t1", title="A", priority=TaskPriority.HIGH)
        t2 = WorkerTask(id="t1", title="A", priority=TaskPriority.HIGH)
        assert t1 == t2

    def test_worker_result_deterministic(self) -> None:
        r1 = WorkerResult(worker_id="w1", task_id="t1", success=True)
        r2 = WorkerResult(worker_id="w1", task_id="t1", success=True)
        assert r1 == r2


# --- Error Tests (5) ---


class TestErrors:
    def test_error_hierarchy(self) -> None:
        assert issubclass(WorkerNotFoundError, WorkerError)
        assert issubclass(WorkerBusyError, WorkerError)
        assert issubclass(WorkerUnavailableError, WorkerError)
        assert issubclass(WorkerCapabilityError, WorkerError)
        assert issubclass(WorkerAssignmentError, WorkerError)

    def test_worker_not_found_raises(self) -> None:
        with pytest.raises(WorkerNotFoundError):
            raise WorkerNotFoundError("Not found")

    def test_worker_busy_raises(self) -> None:
        with pytest.raises(WorkerBusyError):
            raise WorkerBusyError("Busy")

    def test_worker_capability_raises(self) -> None:
        with pytest.raises(WorkerCapabilityError):
            raise WorkerCapabilityError("Cannot")

    def test_base_error_raises(self) -> None:
        with pytest.raises(WorkerError):
            raise WorkerError("Failed")
