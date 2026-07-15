"""Tests for the task dependency graph models."""

import pytest

from eag.planner.intelligence.dependency_resolver import TaskDependencyResolver
from eag.planner.models import EngineeringTask


def build_graph(tasks):
    return TaskDependencyResolver().build(tasks)


@pytest.fixture
def simple_tasks():
    return (
        EngineeringTask(id="A", title="Task A"),
        EngineeringTask(id="B", title="Task B", dependencies=("A",)),
        EngineeringTask(id="C", title="Task C", dependencies=("B",)),
    )


class TestTaskDependencyGraphModels:
    def test_statistics_calculation(self, simple_tasks):
        graph = build_graph(simple_tasks)
        stats = graph.statistics
        assert stats.task_count == 3
        assert stats.edge_count == 2
        assert stats.root_count == 1
        assert stats.leaf_count == 1
        assert stats.maximum_depth == 2
        assert stats.independent_tasks == 0

    def test_ordered_tasks_chain(self, simple_tasks):
        graph = build_graph(simple_tasks)
        ordered = graph.ordered_tasks()
        assert [t.id for t in ordered] == ["A", "B", "C"]

    def test_roots(self, simple_tasks):
        graph = build_graph(simple_tasks)
        roots = graph.roots()
        assert len(roots) == 1
        assert roots[0].id == "A"

    def test_leaves(self, simple_tasks):
        graph = build_graph(simple_tasks)
        leaves = graph.leaves()
        assert len(leaves) == 1
        assert leaves[0].id == "C"
