from dataclasses import dataclass
from datetime import UTC, datetime

from eag.events import EventBus
from eag.graph.errors import GraphBuildError
from eag.graph.events import (
    GraphBuildCompleted,
    GraphBuildFailed,
    GraphBuildStarted,
    GraphEdgeCreated,
    GraphNodeCreated,
)
from eag.graph.factory import EdgeFactory, NodeFactory
from eag.graph.models import (
    EngineeringGraph,
    GraphEdge,
    GraphIdentity,
    GraphNode,
    GraphStatistics,
)
from eag.graph.state import GraphState, RelationshipType
from eag.index.models import RepositoryIndex
from eag.source.state import SymbolKind


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphBuilderReport:
    nodes_created: int = 0
    edges_created: int = 0
    duplicates_skipped: int = 0
    elapsed_ms: float = 0.0


class GraphBuilder:
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus
        self._index: RepositoryIndex | None = None
        self.reset()

    def reset(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[tuple[str, str, RelationshipType], GraphEdge] = {}
        self._duplicates = 0

    def add_index(self, index: RepositoryIndex) -> None:
        self._index = index

    def build(self) -> tuple[EngineeringGraph, GraphBuilderReport]:
        if not self._index:
            raise GraphBuildError("No index provided to builder")

        start_time = datetime.now(UTC)
        if self._event_bus:
            self._event_bus.publish(GraphBuildStarted(repository=self._index.identity.repository))

        try:
            self._collect_nodes()
            self._connect_contains()
            self._connect_imports()
            self._validate()
            stats = self._compute_statistics()

            graph = EngineeringGraph(
                identity=GraphIdentity(repository=self._index.identity.repository),
                state=GraphState.READY,
                nodes=tuple(self._nodes.values()),
                edges=tuple(self._edges.values()),
                statistics=stats,
                created_at=datetime.now(UTC),
            )

            elapsed = (datetime.now(UTC) - start_time).total_seconds() * 1000
            report = GraphBuilderReport(
                nodes_created=len(self._nodes),
                edges_created=len(self._edges),
                duplicates_skipped=self._duplicates,
                elapsed_ms=round(elapsed, 2),
            )

            if self._event_bus:
                self._event_bus.publish(GraphBuildCompleted(graph=graph))

            return graph, report

        except Exception as e:
            if self._event_bus:
                self._event_bus.publish(GraphBuildFailed(error=str(e)))
            raise GraphBuildError(f"Graph build failed: {e}") from e

    def _add_node(self, node: GraphNode) -> None:
        if node.id in self._nodes:
            self._duplicates += 1
            return
        self._nodes[node.id] = node
        if self._event_bus:
            self._event_bus.publish(GraphNodeCreated(node=node))

    def _add_edge(self, edge: GraphEdge) -> None:
        key = (edge.source, edge.target, edge.relationship)
        if key in self._edges:
            self._duplicates += 1
            return
        self._edges[key] = edge
        if self._event_bus:
            self._event_bus.publish(GraphEdgeCreated(edge=edge))

    def _collect_nodes(self) -> None:
        if not self._index:
            return

        for mod in self._index.modules:
            self._add_node(NodeFactory.module(mod.name))

        for sym in self._index.symbols:
            if sym.identity.kind == SymbolKind.CLASS:
                self._add_node(NodeFactory.class_(sym.identity.qualified_name, sym.identity.module))
            elif sym.identity.kind == SymbolKind.FUNCTION:
                self._add_node(
                    NodeFactory.function(sym.identity.qualified_name, sym.identity.module)
                )
            elif sym.identity.kind == SymbolKind.METHOD:
                self._add_node(NodeFactory.method(sym.identity.qualified_name, sym.identity.module))

        for dep in self._index.dependencies:
            self._add_node(NodeFactory.dependency(dep.target))

    def _connect_contains(self) -> None:
        if not self._index:
            return

        for sym in self._index.symbols:
            mod_id = f"module:{sym.identity.module}"

            if sym.identity.kind == SymbolKind.CLASS:
                cls_id = f"class:{sym.identity.qualified_name}"
                self._add_edge(EdgeFactory.contains(mod_id, cls_id))

            elif sym.identity.kind == SymbolKind.FUNCTION:
                fn_id = f"function:{sym.identity.qualified_name}"
                self._add_edge(EdgeFactory.contains(mod_id, fn_id))

            elif sym.identity.kind == SymbolKind.METHOD:
                # Method is contained by its parent Class
                # e.g. eag.source.runtime.SourceRuntime.analyze -> eag.source.runtime.SourceRuntime
                parts = sym.identity.qualified_name.rsplit(".", 1)
                if len(parts) == 2:
                    cls_qn = parts[0]
                    cls_id = f"class:{cls_qn}"
                    meth_id = f"method:{sym.identity.qualified_name}"
                    self._add_edge(EdgeFactory.contains(cls_id, meth_id))

    def _connect_imports(self) -> None:
        if not self._index:
            return

        for dep in self._index.dependencies:
            mod_id = f"module:{dep.source}"
            dep_id = f"dependency:{dep.target}"
            self._add_edge(EdgeFactory.imports(mod_id, dep_id))

    def _validate(self) -> None:
        node_ids = set(self._nodes.keys())
        for edge in self._edges.values():
            if edge.source not in node_ids:
                raise GraphBuildError(f"Edge source '{edge.source}' not found in nodes")
            if edge.target not in node_ids:
                raise GraphBuildError(f"Edge target '{edge.target}' not found in nodes")

    def _compute_statistics(self) -> GraphStatistics:
        counts: dict[RelationshipType, int] = {}
        for edge in self._edges.values():
            counts[edge.relationship] = counts.get(edge.relationship, 0) + 1

        return GraphStatistics(
            nodes=len(self._nodes),
            edges=len(self._edges),
            relationship_counts=counts,
        )
