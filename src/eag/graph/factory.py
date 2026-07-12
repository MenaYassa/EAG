from eag.graph.models import GraphEdge, GraphNode
from eag.graph.state import GraphNodeKind, RelationshipType


class NodeFactory:
    """Factory for creating graph nodes with deterministic IDs."""

    @staticmethod
    def module(name: str) -> GraphNode:
        return GraphNode(
            id=f"module:{name}",
            kind=GraphNodeKind.MODULE,
            name=name.split(".")[-1],
            qualified_name=name,
        )

    @staticmethod
    def class_(qualified_name: str, module: str) -> GraphNode:
        return GraphNode(
            id=f"class:{qualified_name}",
            kind=GraphNodeKind.CLASS,
            name=qualified_name.split(".")[-1],
            qualified_name=qualified_name,
            metadata={"module": module},
        )

    @staticmethod
    def function(qualified_name: str, module: str) -> GraphNode:
        return GraphNode(
            id=f"function:{qualified_name}",
            kind=GraphNodeKind.FUNCTION,
            name=qualified_name.split(".")[-1],
            qualified_name=qualified_name,
            metadata={"module": module},
        )

    @staticmethod
    def method(qualified_name: str, module: str) -> GraphNode:
        return GraphNode(
            id=f"method:{qualified_name}",
            kind=GraphNodeKind.METHOD,
            name=qualified_name.split(".")[-1],
            qualified_name=qualified_name,
            metadata={"module": module},
        )

    @staticmethod
    def dependency(target: str) -> GraphNode:
        return GraphNode(
            id=f"dependency:{target}",
            kind=GraphNodeKind.DEPENDENCY,
            name=target.split(".")[-1],
            qualified_name=target,
        )


class EdgeFactory:
    """Factory for creating graph edges."""

    @staticmethod
    def contains(source: str, target: str) -> GraphEdge:
        return GraphEdge(
            source=source,
            target=target,
            relationship=RelationshipType.CONTAINS,
        )

    @staticmethod
    def imports(source: str, target: str) -> GraphEdge:
        return GraphEdge(
            source=source,
            target=target,
            relationship=RelationshipType.IMPORTS,
        )
