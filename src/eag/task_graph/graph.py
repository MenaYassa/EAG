"""Task Graph implementation for EAG."""

from collections.abc import Mapping
from eag.task_graph.enums import DependencyType
from eag.task_graph.errors import (
    CycleError,
    DuplicateEdgeError,
    DuplicateNodeError,
    MissingNodeError,
    SelfDependencyError,
)
from eag.task_graph.models import TaskEdge, TaskNode


class TaskGraph:
    """An immutable, validated Directed Acyclic Graph (DAG) of engineering tasks."""

    def __init__(
        self,
        nodes: tuple[TaskNode, ...] = (),
        edges: tuple[TaskEdge, ...] = ()
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        
        self._node_map = {n.id: n for n in self._nodes}
        self._children_map: dict[str, list[str]] = {n.id: [] for n in self._nodes}
        self._parents_map: dict[str, list[str]] = {n.id: [] for n in self._nodes}
        
        # Validation
        if len(self._node_map) != len(self._nodes):
            raise DuplicateNodeError("Duplicate node IDs detected")
            
        for edge in self._edges:
            if edge.source not in self._node_map:
                raise MissingNodeError(f"Edge source '{edge.source}' not found in nodes")
            if edge.target not in self._node_map:
                raise MissingNodeError(f"Edge target '{edge.target}' not found in nodes")
            if edge.source == edge.target:
                raise SelfDependencyError(f"Node '{edge.source}' cannot depend on itself")
            
            # Check duplicate edges
            if any(e.source == edge.source and e.target == edge.target for e in self._edges if e is not edge):
                raise DuplicateEdgeError(f"Duplicate edge from '{edge.source}' to '{edge.target}'")
                
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
                    raise CycleError("Cycle detected in task graph")

    @property
    def nodes(self) -> tuple[TaskNode, ...]:
        return self._nodes
        
    @property
    def edges(self) -> tuple[TaskEdge, ...]:
        return self._edges

    def add_node(self, node: TaskNode) -> "TaskGraph":
        """Returns a new graph with the node added."""
        return TaskGraph(self._nodes + (node,), self._edges)
        
    def add_edge(self, edge: TaskEdge) -> "TaskGraph":
        """Returns a new graph with the edge added."""
        return TaskGraph(self._nodes, self._edges + (edge,))

    def parents(self, node_id: str) -> tuple[TaskNode, ...]:
        """Returns the parent nodes of a given node."""
        return tuple(self._node_map[p_id] for p_id in self._parents_map.get(node_id, []))
        
    def children(self, node_id: str) -> tuple[TaskNode, ...]:
        """Returns the child nodes of a given node."""
        return tuple(self._node_map[c_id] for c_id in self._children_map.get(node_id, []))
        
    def roots(self) -> tuple[TaskNode, ...]:
        """Returns nodes with no parents."""
        return tuple(n for n in self._nodes if not self._parents_map.get(n.id))
        
    def leaves(self) -> tuple[TaskNode, ...]:
        """Returns nodes with no children."""
        return tuple(n for n in self._nodes if not self._children_map.get(n.id))
        
    def ready(self, completed: set[str]) -> tuple[TaskNode, ...]:
        """Returns nodes whose all parents are completed, sorted by priority and ID."""
        ready_nodes = []
        for node in self._nodes:
            if node.id in completed:
                continue
            parents = self._parents_map.get(node.id, [])
            if all(p in completed for p in parents):
                ready_nodes.append(node)
                
        # Sort by priority (descending) and then ID for determinism
        priority_order = {
            "critical": 0,
            "high": 1,
            "normal": 2,
            "low": 3
        }
        ready_nodes.sort(key=lambda n: (priority_order.get(n.priority.value, 2), n.id))
        return tuple(ready_nodes)
        
    def topological_sort(self) -> tuple[TaskNode, ...]:
        """Returns nodes in topological order (deterministic)."""
        visited: set[str] = set()
        stack: list[TaskNode] = []
        
        def dfs(node_id: str) -> None:
            visited.add(node_id)
            # Sort children in reverse order so reversing stack yields ascending child order
            for child_id in sorted(self._children_map.get(node_id, []), reverse=True):
                if child_id not in visited:
                    dfs(child_id)
            stack.append(self._node_map[node_id])
            
        # Process starting nodes in reverse sorted order so that reversed(stack) yields ['n1', 'n2', 'n3']
        start_nodes = sorted([n.id for n in self._nodes], reverse=True)
        for node_id in start_nodes:
            if node_id not in visited:
                dfs(node_id)
                
        return tuple(reversed(stack))