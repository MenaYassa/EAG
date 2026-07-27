from eag.graph.algorithms.models import PathReport
from eag.graph.algorithms.traversal import TraversalEngine
from eag.graph.models import EngineeringGraph


class PathFinder:
    def __init__(self, graph: EngineeringGraph):
        self._graph = graph
        self._engine = TraversalEngine(graph)
        self._node_map = {n.id: n for n in graph.nodes}

    def path(self, start_id: str, end_id: str) -> PathReport:
        if start_id not in self._node_map or end_id not in self._node_map:
            return PathReport(
                start=self._node_map.get(
                    start_id, self._node_map[start_id]
                ),  # Will raise if missing, which is fine
                end=self._node_map[end_id],
                path=(),
                distance=-1,
            )

        visited = {start_id}
        queue = [(start_id, [start_id])]

        while queue:
            node, path = queue.pop(0)
            if node == end_id:
                return PathReport(
                    start=self._node_map[start_id],
                    end=self._node_map[end_id],
                    path=tuple(self._node_map[n] for n in path),
                    distance=len(path) - 1,
                )

            for neighbor in self._engine._outgoing.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return PathReport(
            start=self._node_map[start_id], end=self._node_map[end_id], path=(), distance=-1
        )
