"""Tests for the task dependency resolver."""

import pytest

from eag.planner.errors import (
    DependencyCycleError,
    DuplicateTaskError,
    UnknownDependencyError,
)
from eag.planner.intelligence.dependency_resolver import TaskDependencyResolver
from eag.planner.models import EngineeringTask


@pytest.fixture
def resolver():
    return TaskDependencyResolver()


class TestDependencyResolverValidation:
    def test_duplicate_ids(self, resolver):
        tasks = (
            EngineeringTask(id="A", title="Task A"),
            EngineeringTask(id="A", title="Task A Dup"),
        )
        with pytest.raises(DuplicateTaskError):
            resolver.build(tasks)

    def test_missing_dependency(self, resolver):
        tasks = (EngineeringTask(id="A", title="Task A", dependencies=("B",)),)
        with pytest.raises(UnknownDependencyError):
            resolver.build(tasks)

    def test_self_dependency(self, resolver):
        tasks = (EngineeringTask(id="A", title="Task A", dependencies=("A",)),)
        with pytest.raises(UnknownDependencyError):
            resolver.build(tasks)


class TestDependencyResolverCycleDetection:
    def test_simple_cycle(self, resolver):
        tasks = (
            EngineeringTask(id="A", title="Task A", dependencies=("B",)),
            EngineeringTask(id="B", title="Task B", dependencies=("A",)),
        )
        with pytest.raises(DependencyCycleError):
            resolver.build(tasks)

    def test_large_cycle(self, resolver):
        # FIXED: Added required title keyword arguments
        tasks = (
            EngineeringTask(id="A", title="Task A", dependencies=("C",)),
            EngineeringTask(id="B", title="Task B", dependencies=("A",)),
            EngineeringTask(id="C", title="Task C", dependencies=("B",)),
        )
        with pytest.raises(DependencyCycleError):
            resolver.build(tasks)


class TestDependencyResolverSorting:
    def test_empty_input(self, resolver):
        graph = resolver.build(())
        assert graph.statistics.task_count == 0
        assert graph.ordered_tasks() == ()

    def test_single_task(self, resolver):
        tasks = (EngineeringTask(id="A", title="Task A"),)
        graph = resolver.build(tasks)
        assert graph.ordered_tasks()[0].id == "A"

    def test_chain(self, resolver):
        # FIXED: Added required title keyword arguments
        tasks = (
            EngineeringTask(id="C", title="Task C", dependencies=("B",)),
            EngineeringTask(id="B", title="Task B", dependencies=("A",)),
            EngineeringTask(id="A", title="Task A"),
        )
        graph = resolver.build(tasks)
        ordered = [t.id for t in graph.ordered_tasks()]
        assert ordered == ["A", "B", "C"]

    def test_diamond(self, resolver):
        # FIXED: Added required title keyword arguments
        tasks = (
            EngineeringTask(id="D", title="Task D", dependencies=("B", "C")),
            EngineeringTask(id="B", title="Task B", dependencies=("A",)),
            EngineeringTask(id="C", title="Task C", dependencies=("A",)),
            EngineeringTask(id="A", title="Task A"),
        )
        graph = resolver.build(tasks)
        ordered = [t.id for t in graph.ordered_tasks()]
        assert ordered == ["A", "B", "C", "D"]

    def test_parallel_determinism(self, resolver):
        # FIXED: Added required title keyword arguments
        tasks = (
            EngineeringTask(id="C", title="Task C"),
            EngineeringTask(id="A", title="Task A"),
            EngineeringTask(id="B", title="Task B"),
        )
        graph = resolver.build(tasks)
        ordered = [t.id for t in graph.ordered_tasks()]
        assert ordered == ["A", "B", "C"]

        # Run again to verify determinism
        graph2 = resolver.build(tasks)
        ordered2 = [t.id for t in graph2.ordered_tasks()]
        assert ordered == ordered2

    def test_large_graph_performance(self, resolver):
        # FIXED: Added required title keyword argument inside the generator expression
        tasks = tuple(
            EngineeringTask(
                id=f"T{i:03d}",
                title=f"Task T{i:03d}",
                dependencies=(f"T{i - 1:03d}",) if i > 0 else (),
            )
            for i in range(100)
        )
        graph = resolver.build(tasks)
        ordered = graph.ordered_tasks()
        assert len(ordered) == 100
        assert ordered[0].id == "T000"
        assert ordered[-1].id == "T099"
