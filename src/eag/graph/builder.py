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
from eag.source.state import SemanticKind, SymbolKind


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

    # ============================================================================
    # FIX: Added _short_name_index — maps bare names ("SourceRuntime") to their
    # real structural GraphNode objects so semantic edges connect to the correct
    # nodes instead of creating floating dependency nodes.
    # ============================================================================
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

    # ============================================================================
    # FIX: Added _index_short_name(node) call so every structural node is
    # registered in the short-name index at insertion time.
    # ============================================================================
    def _add_node(self, node: GraphNode) -> None:
        if node.id in self._nodes:
            self._duplicates += 1
            return
        self._nodes[node.id] = node
        self._index_short_name(node)
        if self._event_bus:
            self._event_bus.publish(GraphNodeCreated(node=node))

    # ============================================================================
    # FIX: New method — builds a reverse lookup from bare short names to real
    # structural node objects.  NodeFactory already sets node.name to the last
    # segment of the qualified_name, so this captures exactly the bare class /
    # function / method names that the semantic extractor emits.
    # ============================================================================
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

        for sym in self._index.symbols:
            kind = sym.identity.kind
            qname = sym.identity.qualified_name
            module = sym.identity.module

            if kind in (
                SymbolKind.CLASS,
                SymbolKind.INTERFACE,
                SymbolKind.PROTOCOL,
                SymbolKind.ENUM,
                SymbolKind.DATACLASS,
            ):
                self._add_node(NodeFactory.class_(qname, module))
            elif kind in (SymbolKind.FUNCTION, SymbolKind.CONSTANT):
                self._add_node(NodeFactory.function(qname, module))
            elif kind == SymbolKind.METHOD:
                self._add_node(NodeFactory.method(qname, module))

        for dep in self._index.dependencies:
            self._add_node(NodeFactory.dependency(dep.target))

    def _connect_contains(self) -> None:
        if not self._index:
            return

        for sym in self._index.symbols:
            mod_id = f"module:{sym.identity.module}"
            kind = sym.identity.kind
            qname = sym.identity.qualified_name

            if kind in (
                SymbolKind.CLASS,
                SymbolKind.INTERFACE,
                SymbolKind.PROTOCOL,
                SymbolKind.ENUM,
                SymbolKind.DATACLASS,
            ):
                cls_id = f"class:{qname}"
                self._add_edge(EdgeFactory.contains(mod_id, cls_id))

            elif kind in (SymbolKind.FUNCTION, SymbolKind.CONSTANT):
                fn_id = f"function:{qname}"
                self._add_edge(EdgeFactory.contains(mod_id, fn_id))

            elif kind == SymbolKind.METHOD:
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

    # ============================================================================
    # FIX: Replaced the old six-lookup cascade with calls to the new
    # _resolve_semantic_node() helper.  The old code could not match bare names
    # like "SourceRuntime" to real nodes with IDs like
    # "class:eag.runtime.SourceRuntime", causing it to create floating
    # dependency nodes and break all traversal paths.
    # ============================================================================
    def _connect_semantic(self) -> None:
        """Wire semantic relationship edges to real structural graph nodes.

        The semantic extractor produces relationship sources and targets as raw
        string names pulled from the AST.  Sources are typically fully-qualified
        (e.g. eag.kernel.Kernel) while targets are frequently bare class or
        function names (e.g. SourceRuntime).

        The previous implementation tried a fixed sequence of self._nodes
        dict lookups using prefixed keys, but a bare name like SourceRuntime
        never matches keys like class:SourceRuntime because the real node
        ID is class:eag.runtime.SourceRuntime.  When all lookups failed the
        code fell through to creating a floating dependency:SourceRuntime
        node, leaving the real structural node completely isolated.

        The fix introduces a multi-strategy resolver (_resolve_semantic_node)
        that consults a short-name index built during node collection.  This
        allows SourceRuntime to match class:eag.runtime.SourceRuntime
        without the semantic extractor needing import-resolution capabilities.
        """
        if not self._index:
            return

        kind_map = {
            SemanticKind.CALLS: RelationshipType.CALLS,
            SemanticKind.INHERITS: RelationshipType.INHERITS,
            SemanticKind.USES: RelationshipType.USES,
            SemanticKind.PUBLISHES_EVENT: RelationshipType.PUBLISHES_EVENT,
            SemanticKind.SUBSCRIBES_EVENT: RelationshipType.SUBSCRIBES_EVENT,
        }

        for rel in self._index.semantic_relationships:
            source_node = self._resolve_semantic_node(rel.source)
            if not source_node:
                continue

            target_node = self._resolve_semantic_node(rel.target)

            # External fallback: if target is genuinely outside this codebase,
            # create a dependency node so the edge is still preserved.
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

    # ============================================================================
    # FIX: New method — multi-strategy semantic name resolver.  This is the core
    # of the fix.  It resolves a raw AST-extracted name to a real structural
    # graph node through four cascading strategies.
    # ============================================================================
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

        # Strategy 1: Direct prefixed-ID lookup using the full raw name.
        # Works when the semantic source is a fully-qualified name that
        # exactly matches a structural node's qualified name.
        for prefix in ("class:", "function:", "method:"):
            node = self._nodes.get(f"{prefix}{raw_name}")
            if node:
                return node

        # Strategy 2: Prefixed-ID lookup using the short name only.
        # Works when a node's qualified_name happens to be the bare name
        # (e.g. top-level functions/constants with no module-component prefix
        # in the ID).
        for prefix in ("class:", "function:", "method:"):
            node = self._nodes.get(f"{prefix}{short_name}")
            if node:
                return node

        # Strategy 3: Short-name index fallback.
        # This is the critical fix: when the semantic extractor produced a bare
        # target like "SourceRuntime" and the real node ID is the fully-qualified
        # "class:eag.runtime.SourceRuntime", the short-name index maps
        # "SourceRuntime" -> that node object directly.
        candidates = self._short_name_index.get(short_name)
        if candidates:
            return candidates[0]

        # Strategy 4: Raw string fallback (should rarely trigger, but kept
        # for safety).
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
