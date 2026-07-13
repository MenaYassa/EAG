from collections.abc import Mapping

from eag.graph.algorithms.models import TraversalResult
from eag.graph.models import EngineeringGraph
from eag.graph.state import RelationshipType


class TraversalEngine:
    def __init__(self, graph: EngineeringGraph):
        self._graph = graph
        self._node_map = {n.id: n for n in graph.nodes}
        self._outgoing = self._build_adjacency("out")
        self._incoming = self._build_adjacency("in")

    def _build_adjacency(self, direction: str) -> Mapping[str, list[str]]:
        adj: dict[str, list[str]] = {n.id: [] for n in self._graph.nodes}
        for edge in self._graph.edges:
            if direction == "out":
                adj[edge.source].append(edge.target)
            else:
                adj[edge.target].append(edge.source)
        return adj

    def _bfs(
        self,
        start: str,
        direction: str,
        relationship_types: set[RelationshipType | str] | None = None,
    ) -> tuple[str, ...]:

        visited = {start}
        queue = [start]
        order = [start]

        adj = self._outgoing if direction == "out" else self._incoming

        # Convert allowed types into matching strings for resilient cache matching
        str_types: set[RelationshipType | str] = set()
        if relationship_types:
            for t in relationship_types:
                if isinstance(t, RelationshipType):
                    str_types.add(t)
                    str_types.add(t.value)
                    str_types.add(str(t))
                else:
                    str_types.add(t)

        while queue:
            node = queue.pop(0)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if relationship_types:
                        match = False
                        for e in self._graph.edges:
                            # Normalize the current edge relationship target string
                            e_rel = (
                                e.relationship.value
                                if isinstance(e.relationship, RelationshipType)
                                else e.relationship
                            )

                            if direction == "out":
                                if (
                                    e.source == node
                                    and e.target == neighbor
                                    and (e.relationship in str_types or e_rel in str_types)
                                ):
                                    match = True
                                    break
                            else:
                                if (
                                    e.target == node
                                    and e.source == neighbor
                                    and (e.relationship in str_types or e_rel in str_types)
                                ):
                                    match = True
                                    break
                        if not match:
                            continue

                    visited.add(neighbor)
                    order.append(neighbor)
                    queue.append(neighbor)

        return tuple(order)

    def bfs(self, start: str) -> TraversalResult:
        node_ids = self._bfs(start, "out")
        return TraversalResult(
            nodes=tuple(self._node_map[n] for n in node_ids if n in self._node_map)
        )

    def dfs(self, start: str) -> TraversalResult:
        visited = set()
        order = []
        stack = [start]
        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                order.append(node)
                for neighbor in reversed(self._outgoing.get(node, [])):
                    if neighbor not in visited:
                        stack.append(neighbor)
        return TraversalResult(nodes=tuple(self._node_map[n] for n in order if n in self._node_map))

    def reachable(self, start: str) -> TraversalResult:
        return self.bfs(start)

    def reverse_reachable(self, start: str) -> TraversalResult:
        node_ids = self._bfs(start, "in")
        return TraversalResult(
            nodes=tuple(self._node_map[n] for n in node_ids if n in self._node_map)
        )
