from eag.graph.algorithms.models import DependencyReport
from eag.graph.algorithms.traversal import TraversalEngine
from eag.graph.models import EngineeringGraph
from eag.graph.state import RelationshipType


class DependencyAnalyzer:
    def __init__(self, graph: EngineeringGraph):
        self._graph = graph
        self._engine = TraversalEngine(graph)
        self._node_map = {n.id: n for n in graph.nodes}

        # Support both Enum instances and serialized strings
        raw_types = {
            RelationshipType.IMPORTS,
            RelationshipType.DEPENDS_ON,
            RelationshipType.USES,
            RelationshipType.CALLS,
            RelationshipType.INHERITS,
            RelationshipType.PUBLISHES_EVENT,  # Add if paths use events
            RelationshipType.SUBSCRIBES_EVENT,  # Add if paths use events
        }
        self._dep_types: set[RelationshipType | str] = set()
        for t in raw_types:
            self._dep_types.add(t)
            self._dep_types.add(t.value)  # e.g., "calls" or "CALLS"
            self._dep_types.add(str(t))  # e.g., "RelationshipType.CALLS"

    def direct_dependencies(self, node_id: str) -> DependencyReport:
        deps = {
            edge.target
            for edge in self._graph.edges
            if edge.source == node_id and edge.relationship in self._dep_types
        }
        return DependencyReport(
            node=self._node_map[node_id],
            dependencies=tuple(self._node_map[d] for d in deps if d in self._node_map),
        )

    def transitive_dependencies(self, node_id: str) -> DependencyReport:
        node_ids = self._engine._bfs(node_id, "out", self._dep_types)
        deps = tuple(self._node_map[n] for n in node_ids if n != node_id and n in self._node_map)
        return DependencyReport(node=self._node_map[node_id], dependencies=deps)

    def direct_dependents(self, node_id: str) -> DependencyReport:
        deps = {
            edge.source
            for edge in self._graph.edges
            if edge.target == node_id and edge.relationship in self._dep_types
        }
        return DependencyReport(
            node=self._node_map[node_id],
            dependencies=tuple(self._node_map[d] for d in deps if d in self._node_map),
        )

    def transitive_dependents(self, node_id: str) -> DependencyReport:
        node_ids = self._engine._bfs(node_id, "in", self._dep_types)
        deps = tuple(self._node_map[n] for n in node_ids if n != node_id and n in self._node_map)
        return DependencyReport(node=self._node_map[node_id], dependencies=deps)


class ImpactAnalyzer:
    def __init__(self, graph: EngineeringGraph):
        self._graph = graph
        self._dep_analyzer = DependencyAnalyzer(graph)
        self._node_map = {n.id: n for n in graph.nodes}
        self._dep_types = {
            RelationshipType.IMPORTS,
            RelationshipType.DEPENDS_ON,
            RelationshipType.USES,
            RelationshipType.CALLS,
            RelationshipType.INHERITS,
            RelationshipType.PUBLISHES_EVENT,
            RelationshipType.SUBSCRIBES_EVENT,
        }
