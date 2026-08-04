"""Execution Graph and Artifact Graph implementations for EAG."""

from eag.execution_graph.errors import (
    CycleError,
    DuplicateNodeError,
    MissingNodeError,
)
from eag.execution_graph.models import (
    ArtifactEdge,
    ArtifactNode,
    ExecutionEdge,
    ExecutionNode,
)


class ExecutionGraph:
    """An immutable DAG of engineering execution tasks."""

    def __init__(
        self, nodes: tuple[ExecutionNode, ...] = (), edges: tuple[ExecutionEdge, ...] = ()
    ) -> None:
        self._nodes = nodes
        self._edges = edges

        self._node_map = {n.id: n for n in self._nodes}
        if len(self._node_map) != len(self._nodes):
            raise DuplicateNodeError("Duplicate node IDs detected")

        self._children_map: dict[str, list[str]] = {n.id: [] for n in self._nodes}
        self._parents_map: dict[str, list[str]] = {n.id: [] for n in self._nodes}

        for edge in self._edges:
            if edge.source not in self._node_map:
                raise MissingNodeError(f"Edge source '{edge.source}' not found")
            if edge.target not in self._node_map:
                raise MissingNodeError(f"Edge target '{edge.target}' not found")

            self._children_map[edge.source].append(edge.target)
            self._parents_map[edge.target].append(edge.source)

        self._check_cycles()

    def _check_cycles(self) -> None:
        visited: set[str] = set()
        recursion_stack: set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            recursion_stack.add(node_id)

            for child_id in self._children_map.get(node_id, []):
                if child_id not in visited:
                    if dfs(child_id):
                        return True
                elif child_id in recursion_stack:
                    return True

            recursion_stack.remove(node_id)
            return False

        for node in self._nodes:
            if node.id not in visited:
                if dfs(node.id):
                    raise CycleError("Cycle detected in execution graph")

    @property
    def nodes(self) -> tuple[ExecutionNode, ...]:
        return self._nodes

    @property
    def edges(self) -> tuple[ExecutionEdge, ...]:
        return self._edges

    def add_node(self, node: ExecutionNode) -> "ExecutionGraph":
        return ExecutionGraph(self._nodes + (node,), self._edges)

    def add_edge(self, edge: ExecutionEdge) -> "ExecutionGraph":
        return ExecutionGraph(self._nodes, self._edges + (edge,))

    def roots(self) -> tuple[ExecutionNode, ...]:
        return tuple(n for n in self._nodes if not self._parents_map.get(n.id))

    def leaves(self) -> tuple[ExecutionNode, ...]:
        return tuple(n for n in self._nodes if not self._children_map.get(n.id))

    def ready(self, completed: set[str]) -> tuple[ExecutionNode, ...]:
        """Returns nodes whose all parents are completed, sorted by ID."""
        ready_nodes = []
        for node in self._nodes:
            if node.id in completed:
                continue
            parents = self._parents_map.get(node.id, [])
            if all(p in completed for p in parents):
                ready_nodes.append(node)

        ready_nodes.sort(key=lambda n: n.id)
        return tuple(ready_nodes)

    def is_complete(self, completed: set[str]) -> bool:
        return all(n.id in completed for n in self._nodes)


class ArtifactGraph:
    """An immutable DAG of engineering artifacts."""

    def __init__(
        self, nodes: tuple[ArtifactNode, ...] = (), edges: tuple[ArtifactEdge, ...] = ()
    ) -> None:
        self._nodes = nodes
        self._edges = edges

        self._node_map = {n.id: n for n in self._nodes}
        if len(self._node_map) != len(self._nodes):
            raise DuplicateNodeError("Duplicate artifact IDs detected")

        self._children_map: dict[str, list[str]] = {n.id: [] for n in self._nodes}
        self._parents_map: dict[str, list[str]] = {n.id: [] for n in self._nodes}

        for edge in self._edges:
            if edge.source not in self._node_map:
                raise MissingNodeError(f"Artifact edge source '{edge.source}' not found")
            if edge.target not in self._node_map:
                raise MissingNodeError(f"Artifact edge target '{edge.target}' not found")

            self._children_map[edge.source].append(edge.target)
            self._parents_map[edge.target].append(edge.source)

    @property
    def nodes(self) -> tuple[ArtifactNode, ...]:
        return self._nodes

    @property
    def edges(self) -> tuple[ArtifactEdge, ...]:
        return self._edges

    def add_node(self, node: ArtifactNode) -> "ArtifactGraph":
        return ArtifactGraph(self._nodes + (node,), self._edges)

    def add_edge(self, edge: ArtifactEdge) -> "ArtifactGraph":
        return ArtifactGraph(self._nodes, self._edges + (edge,))
