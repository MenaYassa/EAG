from eag.graph.algorithms.dependency import DependencyAnalyzer
from eag.graph.algorithms.models import ImpactReport
from eag.graph.models import EngineeringGraph
from eag.graph.state import RelationshipType


class ImpactAnalyzer:
    def __init__(self, graph: EngineeringGraph):
        self._graph = graph
        self._dep_analyzer = DependencyAnalyzer(graph)
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
            self._dep_types.add(t.value)
            self._dep_types.add(str(t))

    def impact(self, node_id: str) -> ImpactReport:
        affected_ids = set(self._dep_analyzer._engine._bfs(node_id, "in", self._dep_types))
        affected_ids.discard(node_id)

        direct_ids = {
            edge.source
            for edge in self._graph.edges
            if edge.target == node_id and edge.relationship in self._dep_types
        }

        indirect_ids = affected_ids - direct_ids

        # Calculate depth
        depth = 0
        current_level = {node_id}
        visited = {node_id}

        while current_level:
            next_level = set()
            for node in current_level:
                for edge in self._graph.edges:
                    if (
                        edge.target == node
                        and edge.relationship in self._dep_types
                        and edge.source not in visited
                    ):
                        next_level.add(edge.source)
                        visited.add(edge.source)
            if next_level:
                depth += 1
                current_level = next_level
            else:
                break

        return ImpactReport(
            changed_node=self._node_map[node_id],
            direct=tuple(self._node_map[n] for n in direct_ids if n in self._node_map),
            indirect=tuple(self._node_map[n] for n in indirect_ids if n in self._node_map),
            depth=depth,
            total=len(affected_ids),
        )
