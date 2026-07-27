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
from eag.source.models import SemanticKind, SymbolKind


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
        self._short_name_index: dict[str, list[GraphNode]] = {}

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
            self._connect_semantic()
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
        self._index_short_name(node)
        if self._event_bus:
            self._event_bus.publish(GraphNodeCreated(node=node))

    def _index_short_name(self, node: GraphNode) -> None:
        """Map node short name to node object for semantic resolution fallback.

        The short name is the last segment of the qualified name (e.g. "Kernel"
        for "eag.kernel.Kernel").  This allows the semantic connector to resolve
        bare class/function names extracted from source code back to their real
        structural graph nodes.
        """
        short = node.name
        if short:
            self._short_name_index.setdefault(short, []).append(node)

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

        # Safely determine available enum members
        class_kinds = tuple(
            getattr(SymbolKind, k)
            for k in ("CLASS", "INTERFACE", "PROTOCOL", "ENUM", "DATACLASS")
            if hasattr(SymbolKind, k)
        )
        func_kinds = tuple(
            getattr(SymbolKind, k) for k in ("FUNCTION", "CONSTANT") if hasattr(SymbolKind, k)
        )
        method_kind = getattr(SymbolKind, "METHOD", None)

        for sym in self._index.symbols:
            kind = sym.identity.kind
            qname = sym.identity.qualified_name
            module = sym.identity.module

            if kind in class_kinds:
                self._add_node(NodeFactory.class_(qname, module))
            elif kind in func_kinds:
                self._add_node(NodeFactory.function(qname, module))
            elif method_kind and kind == method_kind:
                self._add_node(NodeFactory.method(qname, module))

        for dep in self._index.dependencies:
            self._add_node(NodeFactory.dependency(dep.target))

    def _connect_contains(self) -> None:
        if not self._index:
            return

        class_kinds = tuple(
            getattr(SymbolKind, k)
            for k in ("CLASS", "INTERFACE", "PROTOCOL", "ENUM", "DATACLASS")
            if hasattr(SymbolKind, k)
        )
        func_kinds = tuple(
            getattr(SymbolKind, k) for k in ("FUNCTION", "CONSTANT") if hasattr(SymbolKind, k)
        )
        method_kind = getattr(SymbolKind, "METHOD", None)

        for sym in self._index.symbols:
            mod_id = f"module:{sym.identity.module}"
            kind = sym.identity.kind
            qname = sym.identity.qualified_name

            if kind in class_kinds:
                cls_id = f"class:{qname}"
                self._add_edge(EdgeFactory.contains(mod_id, cls_id))

            elif kind in func_kinds:
                fn_id = f"function:{qname}"
                self._add_edge(EdgeFactory.contains(mod_id, fn_id))

            elif method_kind and kind == method_kind:
                parts = qname.rsplit(".", 1)
                if len(parts) == 2:
                    cls_qn = parts[0]
                    cls_id = f"class:{cls_qn}"
                    meth_id = f"method:{qname}"
                    self._add_edge(EdgeFactory.contains(cls_id, meth_id))

    def _connect_imports(self) -> None:
        if not self._index:
            return

        for dep in self._index.dependencies:
            mod_id = f"module:{dep.source}"
            dep_id = f"dependency:{dep.target}"
            self._add_edge(EdgeFactory.imports(mod_id, dep_id))

    def _connect_semantic(self) -> None:
        if not self._index:
            return

        # Build the mapping safely based on what SemanticKind actually supports
        kind_map = {}
        for sem_name, rel_type in [
            ("CALLS", RelationshipType.CALLS),
            ("INHERITS", RelationshipType.INHERITS),
            ("USES", RelationshipType.USES),
            ("PUBLISHES_EVENT", RelationshipType.PUBLISHES_EVENT),
            ("SUBSCRIBES_EVENT", RelationshipType.SUBSCRIBES_EVENT),
        ]:
            if hasattr(SemanticKind, sem_name):
                kind_map[getattr(SemanticKind, sem_name)] = rel_type

        for rel in self._index.semantic_relationships:
            source_node = self._resolve_semantic_node(rel.source)
            if not source_node:
                continue

            target_node = self._resolve_semantic_node(rel.target)

            if not target_node:
                target_node = NodeFactory.dependency(rel.target)
                self._add_node(target_node)

            edge_type = kind_map.get(rel.kind)
            if edge_type:
                self._add_edge(
                    GraphEdge(
                        source=source_node.id,
                        target=target_node.id,
                        relationship=edge_type,
                    )
                )

    def _resolve_semantic_node(self, raw_name: str) -> GraphNode | None:
        """Resolve a raw semantic name to a real structural graph node.

        Tries four resolution strategies in order of specificity:

        1.  Prefixed-ID using the full raw name
            (class:eag.kernel.Kernel for raw name eag.kernel.Kernel).
        2.  Prefixed-ID using the short name only
            (class:Kernel for raw name Kernel).
        3.  Short-name index - maps bare names to real nodes regardless
            of their fully-qualified ID.  This is the key fix: SourceRuntime
            resolves to class:eag.runtime.SourceRuntime.
        4.  Raw string fallback - last resort.

        Returns None if no structural node matches, indicating the name
        refers to an external dependency.
        """
        short_name = raw_name.split(".")[-1]

        for prefix in ("class:", "function:", "method:"):
            node = self._nodes.get(f"{prefix}{raw_name}")
            if node:
                return node

        # in the ID).
        for prefix in ("class:", "function:", "method:"):
            node = self._nodes.get(f"{prefix}{short_name}")
            if node:
                return node

        candidates = self._short_name_index.get(short_name)
        if candidates:
            return candidates[0]

        node = self._nodes.get(raw_name)
        if node:
            return node

        return None

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
