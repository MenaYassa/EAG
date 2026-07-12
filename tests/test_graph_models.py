from dataclasses import FrozenInstanceError
from datetime import datetime
from types import MappingProxyType

import pytest

from eag.graph.errors import GraphBuildError, GraphError, GraphQueryError, GraphValidationError
from eag.graph.models import (
    EngineeringGraph,
    GraphEdge,
    GraphIdentity,
    GraphNode,
    GraphStatistics,
)
from eag.graph.state import GraphNodeKind, GraphState, RelationshipType


class TestEnums:
    def test_node_kind_values(self):
        assert GraphNodeKind.MODULE == "module"
        assert GraphNodeKind.CLASS == "class"
        assert GraphNodeKind.DEPENDENCY == "dependency"

    def test_relationship_type_values(self):
        assert RelationshipType.CONTAINS == "contains"
        assert RelationshipType.IMPLEMENTS == "implements"
        assert RelationshipType.DEPENDS_ON == "depends_on"

    def test_graph_state_values(self):
        assert GraphState.READY == "ready"
        assert GraphState.BUILDING == "building"


class TestErrors:
    def test_hierarchy(self):
        assert issubclass(GraphValidationError, GraphError)
        assert issubclass(GraphBuildError, GraphError)
        assert issubclass(GraphQueryError, GraphError)


class TestGraphNode:
    def test_valid_creation(self):
        node = GraphNode(
            id="class:eag.main.Kernel",
            kind=GraphNodeKind.CLASS,
            name="Kernel",
            qualified_name="eag.main.Kernel",
        )
        assert node.id == "class:eag.main.Kernel"
        assert node.kind == GraphNodeKind.CLASS
        assert isinstance(node.metadata, MappingProxyType)

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            GraphNode(id="", kind=GraphNodeKind.CLASS, name="Kernel", qualified_name="eag.Kernel")

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            GraphNode(id="id", kind=GraphNodeKind.CLASS, name="", qualified_name="eag.Kernel")

    def test_empty_qualified_name_rejected(self):
        with pytest.raises(ValueError):
            GraphNode(id="id", kind=GraphNodeKind.CLASS, name="Kernel", qualified_name="")

    def test_invalid_kind_rejected(self):
        with pytest.raises(TypeError):
            GraphNode(id="id", kind="class", name="Kernel", qualified_name="eag.Kernel")  # type: ignore[arg-type]

    def test_metadata_immutable(self):
        node = GraphNode(id="id", kind=GraphNodeKind.CLASS, name="K", qualified_name="q")
        with pytest.raises(TypeError):
            node.metadata["key"] = "val"  # type: ignore[index]

    def test_immutable(self):
        node = GraphNode(id="id", kind=GraphNodeKind.CLASS, name="K", qualified_name="q")
        with pytest.raises(FrozenInstanceError):
            node.name = "New"

    def test_hashable(self):
        node1 = GraphNode(id="id", kind=GraphNodeKind.CLASS, name="K", qualified_name="q")
        node2 = GraphNode(id="id", kind=GraphNodeKind.CLASS, name="K", qualified_name="q")
        assert hash(node1) == hash(node2)

    def test_equality(self):
        node1 = GraphNode(id="id", kind=GraphNodeKind.CLASS, name="K", qualified_name="q")
        node2 = GraphNode(id="id", kind=GraphNodeKind.CLASS, name="K", qualified_name="q")
        assert node1 == node2


class TestGraphEdge:
    def test_valid_creation(self):
        edge = GraphEdge(
            source="class:eag.Kernel",
            target="class:eag.Runtime",
            relationship=RelationshipType.USES,
        )
        assert edge.weight == 1.0
        assert edge.relationship == RelationshipType.USES

    def test_empty_source_rejected(self):
        with pytest.raises(ValueError):
            GraphEdge(source="", target="t", relationship=RelationshipType.CONTAINS)

    def test_empty_target_rejected(self):
        with pytest.raises(ValueError):
            GraphEdge(source="s", target="", relationship=RelationshipType.CONTAINS)

    def test_negative_weight_rejected(self):
        with pytest.raises(ValueError):
            GraphEdge(source="s", target="t", relationship=RelationshipType.CONTAINS, weight=-1.0)

    def test_invalid_relationship_rejected(self):
        with pytest.raises(TypeError):
            GraphEdge(source="s", target="t", relationship="uses")  # type: ignore[arg-type]

    def test_immutable(self):
        edge = GraphEdge(source="s", target="t", relationship=RelationshipType.CONTAINS)
        with pytest.raises(FrozenInstanceError):
            edge.weight = 5.0

    def test_hashable(self):
        e1 = GraphEdge(source="s", target="t", relationship=RelationshipType.CONTAINS)
        e2 = GraphEdge(source="s", target="t", relationship=RelationshipType.CONTAINS)
        assert hash(e1) == hash(e2)


class TestGraphStatistics:
    def test_defaults(self):
        stats = GraphStatistics()
        assert stats.nodes == 0
        assert stats.edges == 0
        assert len(stats.relationship_counts) == 0

    def test_valid_counts(self):
        counts = {RelationshipType.CONTAINS: 10, RelationshipType.USES: 5}
        stats = GraphStatistics(nodes=11, edges=15, relationship_counts=counts)
        assert stats.nodes == 11
        assert stats.relationship_counts[RelationshipType.CONTAINS] == 10

    def test_negative_nodes_rejected(self):
        with pytest.raises(ValueError):
            GraphStatistics(nodes=-1)

    def test_invalid_counts_mapping_type(self):
        with pytest.raises(TypeError):
            GraphStatistics(relationship_counts=[])  # type: ignore[arg-type]

    def test_invalid_counts_key_type(self):
        with pytest.raises(TypeError):
            GraphStatistics(relationship_counts={"contains": 10})  # type: ignore[dict-item]

    def test_counts_immutable(self):
        counts = {RelationshipType.CONTAINS: 10}
        stats = GraphStatistics(relationship_counts=counts)
        with pytest.raises(TypeError):
            stats.relationship_counts[RelationshipType.USES] = 5  # type: ignore[index]

    def test_immutable(self):
        stats = GraphStatistics()
        with pytest.raises(FrozenInstanceError):
            stats.nodes = 10


class TestEngineeringGraph:
    def test_valid_empty_graph(self):
        ident = GraphIdentity(repository="test")
        graph = EngineeringGraph(identity=ident, state=GraphState.READY)
        assert graph.nodes == ()
        assert graph.edges == ()
        assert graph.statistics.nodes == 0
        assert isinstance(graph.created_at, datetime)

    def test_invalid_identity_type(self):
        with pytest.raises(TypeError):
            EngineeringGraph(identity="repo", state=GraphState.READY)  # type: ignore[arg-type]

    def test_invalid_state_type(self):
        with pytest.raises(TypeError):
            EngineeringGraph(identity=GraphIdentity(repository="r"), state="ready")  # type: ignore[arg-type]

    def test_invalid_nodes_type(self):
        ident = GraphIdentity(repository="test")
        with pytest.raises(TypeError):
            EngineeringGraph(identity=ident, state=GraphState.READY, nodes=[])  # type: ignore[arg-type]

    def test_immutable(self):
        ident = GraphIdentity(repository="test")
        graph = EngineeringGraph(identity=ident, state=GraphState.READY)
        with pytest.raises(FrozenInstanceError):
            graph.state = GraphState.FAILED
