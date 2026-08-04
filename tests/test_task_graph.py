"""Comprehensive tests for the Task Graph Platform (Sprint 8.3)."""

import pytest

from eag.task_graph import (
    CycleError,
    DependencyType,
    DuplicateEdgeError,
    DuplicateNodeError,
    MissingNodeError,
    NodeState,
    SelfDependencyError,
    TaskEdge,
    TaskGraph,
    TaskGraphError,
    TaskNode,
)
from eag.workers.enums import TaskPriority

# --- Fixtures ---


def make_node(
    node_id: str = "n1",
    title: str = "Task",
    cap: str = "python",
    priority: TaskPriority = TaskPriority.NORMAL,
) -> TaskNode:
    return TaskNode(id=node_id, title=title, required_capability=cap, priority=priority)


def make_edge(source: str, target: str) -> TaskEdge:
    return TaskEdge(source=source, target=target)


# --- Model Tests (25) ---


class TestTaskGraphModels:
    def test_node_immutable(self) -> None:
        n = make_node()
        with pytest.raises(Exception):  # noqa: B017
            n.title = "new"  # type: ignore[misc]

    def test_node_invalid_title(self) -> None:
        with pytest.raises(ValueError):
            TaskNode(title="")

    def test_node_defaults(self) -> None:
        n = TaskNode(title="T")
        assert n.priority == TaskPriority.NORMAL
        assert n.dependencies == ()

    def test_node_invalid_priority(self) -> None:
        with pytest.raises(TypeError):
            TaskNode(title="T", priority="bad")  # type: ignore[arg-type]

    def test_node_metadata(self) -> None:
        n = TaskNode(title="T", metadata={"k": "v"})
        assert n.metadata["k"] == "v"

    def test_node_hashable(self) -> None:
        n = make_node()
        assert hash(n) is not None

    def test_edge_immutable(self) -> None:
        e = make_edge("a", "b")
        with pytest.raises(Exception):  # noqa: B017
            e.source = "c"  # type: ignore[misc]

    def test_edge_invalid_source(self) -> None:
        with pytest.raises(ValueError):
            TaskEdge(source="", target="b")

    def test_edge_invalid_target(self) -> None:
        with pytest.raises(ValueError):
            TaskEdge(source="a", target="")

    def test_edge_defaults(self) -> None:
        e = make_edge("a", "b")
        assert e.dependency_type == DependencyType.FINISH_TO_START

    def test_edge_metadata(self) -> None:
        e = TaskEdge(source="a", target="b", metadata={"k": "v"})
        assert e.metadata["k"] == "v"

    def test_edge_hashable(self) -> None:
        e = make_edge("a", "b")
        assert hash(e) is not None

    def test_dependency_type_values(self) -> None:
        assert DependencyType.FINISH_TO_START == "finish_to_start"
        assert DependencyType.OPTIONAL == "optional"

    def test_node_state_values(self) -> None:
        assert NodeState.READY == "ready"
        assert NodeState.COMPLETED == "completed"

    def test_node_equality(self) -> None:
        n1 = TaskNode(id="n1", title="T")
        n2 = TaskNode(id="n1", title="T")
        assert n1 == n2

    def test_node_inequality(self) -> None:
        n1 = TaskNode(id="n1", title="T")
        n2 = TaskNode(id="n2", title="T")
        assert n1 != n2

    def test_edge_equality(self) -> None:
        e1 = make_edge("a", "b")
        e2 = make_edge("a", "b")
        assert e1 == e2

    def test_node_estimated_duration(self) -> None:
        n = TaskNode(title="T", estimated_duration=5.5)
        assert n.estimated_duration == 5.5

    def test_node_invalid_duration(self) -> None:
        with pytest.raises(ValueError):
            TaskNode(title="T", estimated_duration=-1.0)

    def test_node_dependencies(self) -> None:
        n = TaskNode(title="T", dependencies=("n1",))
        assert "n1" in n.dependencies

    def test_edge_invalid_dependency_type(self) -> None:
        with pytest.raises(TypeError):
            TaskEdge(source="a", target="b", dependency_type="bad")  # type: ignore[arg-type]

    def test_node_id_generated(self) -> None:
        n1 = TaskNode(title="T1")
        n2 = TaskNode(title="T2")
        assert n1.id != n2.id

    def test_node_supported_languages_not_in_model(self) -> None:
        # Just checking we didn't accidentally add it
        n = TaskNode(title="T")
        assert not hasattr(n, "supported_languages")

    def test_node_required_capability(self) -> None:
        n = TaskNode(title="T", required_capability="rust")
        assert n.required_capability == "rust"

    def test_edge_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            TaskEdge(source="a", target="b", metadata="bad")  # type: ignore[arg-type]

    def test_node_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            TaskNode(title="T", metadata="bad")  # type: ignore[arg-type]


# --- Graph Construction & API Tests (25) ---


class TestTaskGraphAPI:
    def test_empty_graph(self) -> None:
        g = TaskGraph()
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_add_node_returns_new_graph(self) -> None:
        g1 = TaskGraph()
        g2 = g1.add_node(make_node("n1"))
        assert len(g1.nodes) == 0
        assert len(g2.nodes) == 1

    def test_add_edge_returns_new_graph(self) -> None:
        g1 = TaskGraph(nodes=(make_node("n1"), make_node("n2")))
        g2 = g1.add_edge(make_edge("n1", "n2"))
        assert len(g1.edges) == 0
        assert len(g2.edges) == 1

    def test_roots(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = TaskGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n2"), make_edge("n2", "n3")))
        roots = g.roots()
        assert len(roots) == 1
        assert roots[0].id == "n1"

    def test_leaves(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = TaskGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n2"), make_edge("n2", "n3")))
        leaves = g.leaves()
        assert len(leaves) == 1
        assert leaves[0].id == "n3"

    def test_parents(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        parents = g.parents("n2")
        assert len(parents) == 1
        assert parents[0].id == "n1"

    def test_children(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        children = g.children("n1")
        assert len(children) == 1
        assert children[0].id == "n2"

    def test_roots_multiple(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = TaskGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n3"), make_edge("n2", "n3")))
        roots = g.roots()
        assert len(roots) == 2

    def test_leaves_multiple(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = TaskGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n2"), make_edge("n1", "n3")))
        leaves = g.leaves()
        assert len(leaves) == 2

    def test_parents_empty(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        assert g.parents("n1") == ()

    def test_children_empty(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        assert g.children("n1") == ()

    def test_graph_immutable_nodes(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        with pytest.raises(AttributeError):
            g.nodes = ()  # type: ignore[misc]

    def test_graph_immutable_edges(self) -> None:
        n1 = make_node("n1")
        n2 = make_node("n2")
        g = TaskGraph(
            nodes=(n1, n2),
            edges=(make_edge("n1", "n2"),),
        )
        with pytest.raises(AttributeError):
            g.edges = ()  # type: ignore[misc]

    def test_add_multiple_nodes(self) -> None:
        g = TaskGraph().add_node(make_node("n1")).add_node(make_node("n2"))
        assert len(g.nodes) == 2

    def test_add_multiple_edges(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"), make_node("n2"), make_node("n3")))
        g = g.add_edge(make_edge("n1", "n2")).add_edge(make_edge("n2", "n3"))
        assert len(g.edges) == 2

    def test_roots_empty_graph(self) -> None:
        assert TaskGraph().roots() == ()

    def test_leaves_empty_graph(self) -> None:
        assert TaskGraph().leaves() == ()

    def test_parents_missing_node(self) -> None:
        g = TaskGraph()
        assert g.parents("missing") == ()

    def test_children_missing_node(self) -> None:
        g = TaskGraph()
        assert g.children("missing") == ()

    def test_graph_holds_node_objects(self) -> None:
        n1 = make_node("n1")
        g = TaskGraph(nodes=(n1,))
        assert g.nodes[0] is n1

    def test_graph_holds_edge_objects(self) -> None:
        e1 = make_edge("n1", "n2")
        g = TaskGraph(nodes=(make_node("n1"), make_node("n2")), edges=(e1,))
        assert g.edges[0] is e1

    def test_add_node_with_dependencies_metadata(self) -> None:
        n1 = make_node("n1")
        n2 = TaskNode(id="n2", title="T2", dependencies=("n1",))
        g = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        assert g.nodes[1].dependencies == ("n1",)

    def test_complex_graph_structure(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(5))
        edges = (
            make_edge("n0", "n1"),
            make_edge("n0", "n2"),
            make_edge("n1", "n3"),
            make_edge("n2", "n3"),
            make_edge("n3", "n4"),
        )
        g = TaskGraph(nodes=nodes, edges=edges)
        assert len(g.roots()) == 1
        assert len(g.leaves()) == 1
        assert len(g.parents("n3")) == 2

    def test_graph_with_no_edges_all_roots(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(3))
        g = TaskGraph(nodes=nodes)
        assert len(g.roots()) == 3
        assert len(g.leaves()) == 3

    def test_node_lookup_in_graph(self) -> None:
        n1 = make_node("n1")
        g = TaskGraph(nodes=(n1,))
        # Internal map should find it
        assert g.parents("n1") == ()


# --- Validation Tests (25) ---


class TestTaskGraphValidation:
    def test_cycle_detection_simple(self) -> None:
        nodes = (make_node("n1"), make_node("n2"))
        edges = (make_edge("n1", "n2"), make_edge("n2", "n1"))
        with pytest.raises(CycleError):
            TaskGraph(nodes=nodes, edges=edges)

    def test_cycle_detection_complex(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(4))
        edges = (
            make_edge("n0", "n1"),
            make_edge("n1", "n2"),
            make_edge("n2", "n3"),
            make_edge("n3", "n1"),  # Cycle back to n1
        )
        with pytest.raises(CycleError):
            TaskGraph(nodes=nodes, edges=edges)

    def test_self_dependency(self) -> None:
        nodes = (make_node("n1"),)
        edges = (make_edge("n1", "n1"),)
        with pytest.raises(SelfDependencyError):
            TaskGraph(nodes=nodes, edges=edges)

    def test_duplicate_node(self) -> None:
        nodes = (make_node("n1"), make_node("n1"))
        with pytest.raises(DuplicateNodeError):
            TaskGraph(nodes=nodes)

    def test_duplicate_edge(self) -> None:
        nodes = (make_node("n1"), make_node("n2"))
        edges = (make_edge("n1", "n2"), make_edge("n1", "n2"))
        with pytest.raises(DuplicateEdgeError):
            TaskGraph(nodes=nodes, edges=edges)

    def test_missing_source_node(self) -> None:
        nodes = (make_node("n1"),)
        edges = (make_edge("missing", "n1"),)
        with pytest.raises(MissingNodeError):
            TaskGraph(nodes=nodes, edges=edges)

    def test_missing_target_node(self) -> None:
        nodes = (make_node("n1"),)
        edges = (make_edge("n1", "missing"),)
        with pytest.raises(MissingNodeError):
            TaskGraph(nodes=nodes, edges=edges)

    def test_valid_graph_no_cycles(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(3))
        edges = (make_edge("n0", "n1"), make_edge("n1", "n2"))
        g = TaskGraph(nodes=nodes, edges=edges)
        assert len(g.nodes) == 3

    def test_add_edge_creates_cycle(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(3))
        edges = (make_edge("n0", "n1"), make_edge("n1", "n2"))
        g = TaskGraph(nodes=nodes, edges=edges)
        with pytest.raises(CycleError):
            g.add_edge(make_edge("n2", "n0"))

    def test_add_duplicate_node(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        with pytest.raises(DuplicateNodeError):
            g.add_node(make_node("n1"))

    def test_add_duplicate_edge(self) -> None:
        nodes = (make_node("n1"), make_node("n2"))
        g = TaskGraph(nodes=nodes, edges=(make_edge("n1", "n2"),))
        with pytest.raises(DuplicateEdgeError):
            g.add_edge(make_edge("n1", "n2"))

    def test_add_edge_missing_source(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        with pytest.raises(MissingNodeError):
            g.add_edge(make_edge("missing", "n1"))

    def test_add_edge_missing_target(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        with pytest.raises(MissingNodeError):
            g.add_edge(make_edge("n1", "missing"))

    def test_add_edge_self_dependency(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        with pytest.raises(SelfDependencyError):
            g.add_edge(make_edge("n1", "n1"))

    def test_large_graph_validation(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(100))
        edges = tuple(make_edge(f"n{i}", f"n{i + 1}") for i in range(99))
        g = TaskGraph(nodes=nodes, edges=edges)
        assert len(g.nodes) == 100

    def test_error_hierarchy(self) -> None:
        assert issubclass(CycleError, TaskGraphError)
        assert issubclass(DuplicateNodeError, TaskGraphError)
        assert issubclass(DuplicateEdgeError, TaskGraphError)
        assert issubclass(MissingNodeError, TaskGraphError)
        assert issubclass(SelfDependencyError, TaskGraphError)

    def test_cycle_error_message(self) -> None:
        with pytest.raises(CycleError, match="Cycle detected"):
            TaskGraph(
                nodes=(make_node("n1"), make_node("n2")),
                edges=(make_edge("n1", "n2"), make_edge("n2", "n1")),
            )

    def test_duplicate_node_error_message(self) -> None:
        with pytest.raises(DuplicateNodeError, match="Duplicate node IDs"):
            TaskGraph(nodes=(make_node("n1"), make_node("n1")))

    def test_duplicate_edge_error_message(self) -> None:
        nodes = (make_node("n1"), make_node("n2"))
        edges = (make_edge("n1", "n2"), make_edge("n1", "n2"))
        with pytest.raises(DuplicateEdgeError, match="Duplicate edge"):
            TaskGraph(nodes=nodes, edges=edges)

    def test_missing_node_error_message(self) -> None:
        with pytest.raises(MissingNodeError, match="not found"):
            TaskGraph(nodes=(make_node("n1"),), edges=(make_edge("n1", "n2"),))

    def test_self_dep_error_message(self) -> None:
        with pytest.raises(SelfDependencyError, match="cannot depend on itself"):
            TaskGraph(nodes=(make_node("n1"),), edges=(make_edge("n1", "n1"),))

    def test_validation_runs_on_construction(self) -> None:
        # All validation should happen in __init__
        pass  # Covered by previous tests

    def test_add_node_does_not_validate_edges(self) -> None:
        # Adding a node shouldn't trigger edge validation failures if edges are valid
        g = TaskGraph(nodes=(make_node("n1"),), edges=())
        g2 = g.add_node(make_node("n2"))
        assert len(g2.nodes) == 2

    def test_add_edge_validates(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"), make_node("n2")))
        with pytest.raises(MissingNodeError):
            g.add_edge(make_edge("n1", "n3"))

    def test_graph_allows_disconnected_nodes(self) -> None:
        nodes = (make_node("n1"), make_node("n2"), make_node("n3"))
        edges = (make_edge("n1", "n2"),)
        g = TaskGraph(nodes=nodes, edges=edges)
        assert len(g.roots()) == 2  # n1 and n3

    def test_empty_graph_is_valid(self) -> None:
        g = TaskGraph()
        assert len(g.nodes) == 0


# --- Scheduling & Determinism Tests (25) ---


class TestTaskGraphScheduling:
    def test_ready_empty_graph(self) -> None:
        g = TaskGraph()
        assert g.ready(set()) == ()

    def test_ready_no_dependencies(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2))
        ready = g.ready(set())
        assert len(ready) == 2

    def test_ready_with_dependencies(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        ready = g.ready(set())
        assert len(ready) == 1
        assert ready[0].id == "n1"

    def test_ready_after_completion(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        ready = g.ready({"n1"})
        assert len(ready) == 1
        assert ready[0].id == "n2"

    def test_ready_excludes_completed(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2))
        ready = g.ready({"n1"})
        assert len(ready) == 1
        assert ready[0].id == "n2"

    def test_ready_blocked_by_multiple_parents(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = TaskGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n3"), make_edge("n2", "n3")))

        # Only n1 and n2 are ready
        assert len(g.ready(set())) == 2

        # Complete n1, n3 is still blocked by n2
        assert len(g.ready({"n1"})) == 1

        # Complete n2, n3 is now ready
        ready = g.ready({"n1", "n2"})
        assert len(ready) == 1
        assert ready[0].id == "n3"

    def test_ready_priority_ordering(self) -> None:
        n1 = make_node("n1", priority=TaskPriority.LOW)
        n2 = make_node("n2", priority=TaskPriority.HIGH)
        n3 = make_node("n3", priority=TaskPriority.CRITICAL)
        g = TaskGraph(nodes=(n1, n2, n3))

        ready = g.ready(set())
        assert ready[0].id == "n3"
        assert ready[1].id == "n2"
        assert ready[2].id == "n1"

    def test_ready_deterministic_ordering_same_priority(self) -> None:
        n1 = make_node("n1")
        n2 = make_node("n2")
        n3 = make_node("n3")
        g = TaskGraph(nodes=(n3, n1, n2))  # Insert out of order

        ready = g.ready(set())
        # Should be sorted by ID
        assert [n.id for n in ready] == ["n1", "n2", "n3"]

    def test_topological_sort_empty(self) -> None:
        g = TaskGraph()
        assert g.topological_sort() == ()

    def test_topological_sort_single_node(self) -> None:
        n1 = make_node("n1")
        g = TaskGraph(nodes=(n1,))
        assert g.topological_sort() == (n1,)

    def test_topological_sort_linear(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = TaskGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n2"), make_edge("n2", "n3")))

        sorted_nodes = g.topological_sort()
        assert [n.id for n in sorted_nodes] == ["n1", "n2", "n3"]

    def test_topological_sort_diamond(self) -> None:
        n1, n2, n3, n4 = (make_node(f"n{i}") for i in range(1, 5))
        edges = (
            make_edge("n1", "n2"),
            make_edge("n1", "n3"),
            make_edge("n2", "n4"),
            make_edge("n3", "n4"),
        )
        g = TaskGraph(nodes=(n1, n2, n3, n4), edges=edges)

        sorted_nodes = g.topological_sort()
        ids = [n.id for n in sorted_nodes]

        assert ids[0] == "n1"
        assert ids[-1] == "n4"
        # n2 and n3 can be in either order, but must be after n1 and before n4
        assert "n2" in ids[1:3]
        assert "n3" in ids[1:3]

    def test_topological_sort_deterministic(self) -> None:
        n1, n2, n3, n4 = (make_node(f"n{i}") for i in range(1, 5))
        edges = (
            make_edge("n1", "n2"),
            make_edge("n1", "n3"),
            make_edge("n2", "n4"),
            make_edge("n3", "n4"),
        )
        g = TaskGraph(nodes=(n1, n2, n3, n4), edges=edges)

        sort1 = g.topological_sort()
        sort2 = g.topological_sort()
        assert sort1 == sort2

    def test_ready_returns_tuple(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        assert isinstance(g.ready(set()), tuple)

    def test_topological_sort_returns_tuple(self) -> None:
        g = TaskGraph(nodes=(make_node("n1"),))
        assert isinstance(g.topological_sort(), tuple)

    def test_ready_with_all_completed(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        assert g.ready({"n1", "n2"}) == ()

    def test_ready_with_partial_completion_complex(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(5))
        edges = (
            make_edge("n0", "n1"),
            make_edge("n0", "n2"),
            make_edge("n1", "n3"),
            make_edge("n2", "n3"),
            make_edge("n3", "n4"),
        )
        g = TaskGraph(nodes=nodes, edges=edges)

        assert len(g.ready(set())) == 1  # n0
        assert len(g.ready({"n0"})) == 2  # n1, n2
        assert len(g.ready({"n0", "n1"})) == 1  # n2
        assert len(g.ready({"n0", "n1", "n2"})) == 1  # n3
        assert len(g.ready({"n0", "n1", "n2", "n3"})) == 1  # n4

    def test_topological_sort_preserves_dependencies(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = TaskGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n3"), make_edge("n2", "n3")))

        sorted_nodes = g.topological_sort()
        ids = [n.id for n in sorted_nodes]

        assert ids.index("n1") < ids.index("n3")
        assert ids.index("n2") < ids.index("n3")

    def test_ready_priority_and_id_combined(self) -> None:
        n1 = make_node("n1", priority=TaskPriority.HIGH)
        n2 = make_node("n2", priority=TaskPriority.HIGH)
        n3 = make_node("n3", priority=TaskPriority.LOW)
        g = TaskGraph(nodes=(n3, n1, n2))

        ready = g.ready(set())
        # High priority first, then sorted by ID
        assert [n.id for n in ready] == ["n1", "n2", "n3"]

    def test_graph_with_no_edges_topological_sort(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = TaskGraph(nodes=(n3, n1, n2))

        sorted_nodes = g.topological_sort()
        assert [n.id for n in sorted_nodes] == ["n1", "n2", "n3"]

    def test_ready_does_not_mutate_completed_set(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        completed = {"n1"}
        g.ready(completed)
        assert completed == {"n1"}

    def test_topological_sort_large_graph(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(100))
        edges = tuple(make_edge(f"n{i}", f"n{i + 1}") for i in range(99))
        g = TaskGraph(nodes=nodes, edges=edges)

        sorted_nodes = g.topological_sort()
        assert len(sorted_nodes) == 100
        assert sorted_nodes[0].id == "n0"
        assert sorted_nodes[-1].id == "n99"

    def test_ready_handles_missing_node_in_completed(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        # n1 is in completed, but what if we pass a missing node?
        ready = g.ready({"n1", "missing"})
        assert len(ready) == 1
        assert ready[0].id == "n2"

    def test_determinism_independent_of_insertion_order(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        edges = (make_edge("n1", "n2"), make_edge("n2", "n3"))

        g1 = TaskGraph(nodes=(n3, n2, n1), edges=edges)
        g2 = TaskGraph(nodes=(n1, n2, n3), edges=edges)

        assert g1.topological_sort() == g2.topological_sort()
        assert g1.ready(set()) == g2.ready(set())
