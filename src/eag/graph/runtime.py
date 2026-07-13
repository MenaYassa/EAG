from dataclasses import dataclass
from datetime import datetime

from eag.events import EventBus
from eag.graph.algorithms.dependency import DependencyAnalyzer
from eag.graph.algorithms.impact import ImpactAnalyzer
from eag.graph.algorithms.metrics import MetricsAnalyzer
from eag.graph.algorithms.models import (
    DependencyReport,
    ImpactReport,
    MetricsReport,
    PathReport,
)
from eag.graph.algorithms.path import PathFinder
from eag.graph.builder import GraphBuilder
from eag.graph.errors import GraphNotLoadedError, GraphQueryError
from eag.graph.events import GraphBuilt, GraphLoaded, GraphQueryExecuted
from eag.graph.models import EngineeringGraph, GraphNode, GraphStatistics
from eag.index.models import RepositoryIndex


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphSnapshot:
    graph: EngineeringGraph
    generated_at: datetime
    repository: str
    version: str = "1.0"


class GraphRuntime:
    def __init__(self, builder: GraphBuilder, event_bus: EventBus) -> None:
        self._builder = builder
        self._event_bus = event_bus
        self._snapshot: GraphSnapshot | None = None

    @property
    def _current_snapshot(self) -> GraphSnapshot:
        """Helper property to narrow types and ensure the graph is loaded."""
        if self._snapshot is None:
            raise GraphNotLoadedError("No graph loaded. Call build() or load() first.")
        return self._snapshot

    def build(self, index: RepositoryIndex) -> GraphSnapshot:
        self._builder.reset()
        self._builder.add_index(index)
        graph, _ = self._builder.build()

        snapshot = GraphSnapshot(
            graph=graph,
            generated_at=graph.created_at,
            repository=graph.identity.repository,
        )
        self._snapshot = snapshot
        self._event_bus.publish(GraphBuilt(snapshot=snapshot))
        return snapshot

    def load(self, graph: EngineeringGraph) -> GraphSnapshot:
        snapshot = GraphSnapshot(
            graph=graph,
            generated_at=graph.created_at,
            repository=graph.identity.repository,
        )
        self._snapshot = snapshot
        self._event_bus.publish(GraphLoaded(snapshot=snapshot))
        return snapshot

    def graph(self) -> EngineeringGraph:
        return self._current_snapshot.graph

    def statistics(self) -> GraphStatistics:
        return self._current_snapshot.graph.statistics

    def find_node(self, name: str) -> GraphNode:
        """Finds a node by its ID, name, or qualified name."""
        snapshot = self._current_snapshot
        self._event_bus.publish(GraphQueryExecuted(query=f"find_node:{name}"))

        for n in snapshot.graph.nodes:
            if n.id == name or n.name == name or n.qualified_name == name:
                return n
        raise GraphQueryError(f"Node '{name}' not found.")

    def node(self, node_id: str) -> GraphNode:
        return self.find_node(node_id)

    def neighbors(self, node_id: str) -> tuple[GraphNode, ...]:
        snapshot = self._current_snapshot
        self._event_bus.publish(GraphQueryExecuted(query=f"neighbors:{node_id}"))

        neighbor_ids: set[str] = set()
        for edge in snapshot.graph.edges:
            if edge.source == node_id:
                neighbor_ids.add(edge.target)
            elif edge.target == node_id:
                neighbor_ids.add(edge.source)

        return tuple(self.find_node(n_id) for n_id in neighbor_ids)

    def dependencies(self, node_id: str) -> tuple[GraphNode, ...]:
        snapshot = self._current_snapshot
        analyzer = DependencyAnalyzer(snapshot.graph)
        report = analyzer.direct_dependencies(node_id)
        return report.dependencies

    def dependents(self, node_id: str) -> tuple[GraphNode, ...]:
        snapshot = self._current_snapshot
        analyzer = DependencyAnalyzer(snapshot.graph)
        report = analyzer.direct_dependents(node_id)
        return report.dependencies

    def transitive_dependencies(self, node_id: str) -> DependencyReport:
        snapshot = self._current_snapshot
        analyzer = DependencyAnalyzer(snapshot.graph)
        return analyzer.transitive_dependencies(node_id)

    def transitive_dependents(self, node_id: str) -> DependencyReport:
        snapshot = self._current_snapshot
        analyzer = DependencyAnalyzer(snapshot.graph)
        return analyzer.transitive_dependents(node_id)

    def impact(self, node_id: str) -> ImpactReport:
        snapshot = self._current_snapshot
        analyzer = ImpactAnalyzer(snapshot.graph)
        return analyzer.impact(node_id)

    def path(self, start_id: str, end_id: str) -> PathReport:
        snapshot = self._current_snapshot
        analyzer = PathFinder(snapshot.graph)
        return analyzer.path(start_id, end_id)

    def metrics(self) -> MetricsReport:
        snapshot = self._current_snapshot
        analyzer = MetricsAnalyzer(snapshot.graph)
        return analyzer.run()
