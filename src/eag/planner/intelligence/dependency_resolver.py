"""Task Dependency Resolver for EAG.

Builds a validated TaskDependencyGraph from a list of EngineeringTasks.
"""

from collections import defaultdict  # <-- ADDED

from eag.planner.errors import (
    DependencyCycleError,
    DuplicateTaskError,
    UnknownDependencyError,
)
from eag.planner.intelligence.models import (
    TaskDependencyGraph,
    TaskDependencyNode,
    TaskDependencyStatistics,
)
from eag.planner.models import EngineeringTask


class TaskDependencyResolver:
    """Builds a task dependency graph and validates its structure."""

    def build(self, tasks: tuple[EngineeringTask, ...]) -> TaskDependencyGraph:
        """Build a validated TaskDependencyGraph from engineering tasks."""
        self._validate(tasks)
        nodes = self._build_nodes(tasks)
        self._detect_cycles(nodes)
        stats = self._compute_statistics(nodes)
        return TaskDependencyGraph(nodes=nodes, statistics=stats)

    def _validate(self, tasks: tuple[EngineeringTask, ...]) -> None:
        ids = [t.id for t in tasks]
        if len(ids) != len(set(ids)):
            raise DuplicateTaskError("Duplicate task IDs detected.")

        task_map = {t.id: t for t in tasks}
        for t in tasks:
            if t.id in t.dependencies:
                raise UnknownDependencyError(f"Task {t.id} cannot depend on itself.")
            for dep_id in t.dependencies:
                if dep_id not in task_map:
                    raise UnknownDependencyError(f"Task {t.id} depends on unknown task {dep_id}.")

    def _build_nodes(self, tasks: tuple[EngineeringTask, ...]) -> dict[str, TaskDependencyNode]:
        # Fix: Use defaultdict(list) to avoid KeyErrors
        incoming_map: dict[str, list[str]] = defaultdict(list)
        outgoing_map = {t.id: list(t.dependencies) for t in tasks}

        for t in tasks:
            # Ensure every task has an entry in incoming_map even if it has no successors
            if t.id not in incoming_map:
                incoming_map[t.id] = []

            for dep_id in t.dependencies:
                incoming_map[dep_id].append(t.id)

        nodes = {}
        for t in tasks:
            nodes[t.id] = TaskDependencyNode(
                task=t,
                incoming=tuple(sorted(incoming_map[t.id])),
                outgoing=tuple(sorted(outgoing_map[t.id])),
            )
        return nodes

    def _detect_cycles(self, nodes: dict[str, TaskDependencyNode]) -> None:
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in nodes}

        def dfs(node_id: str) -> None:
            color[node_id] = GRAY
            for dep_id in nodes[node_id].outgoing:
                if color[dep_id] == GRAY:
                    raise DependencyCycleError(f"Cycle detected involving {node_id} and {dep_id}")
                if color[dep_id] == WHITE:
                    dfs(dep_id)
            color[node_id] = BLACK

        for node_id in nodes:
            if color[node_id] == WHITE:
                dfs(node_id)

    def _compute_statistics(self, nodes: dict[str, TaskDependencyNode]) -> TaskDependencyStatistics:
        task_count = len(nodes)
        edge_count = sum(len(n.outgoing) for n in nodes.values())
        root_count = sum(1 for n in nodes.values() if not n.outgoing)
        leaf_count = sum(1 for n in nodes.values() if not n.incoming)
        independent_tasks = sum(1 for n in nodes.values() if not n.incoming and not n.outgoing)

        # Compute max depth (longest path)
        depth_cache: dict[str, int] = {}

        def get_depth(node_id: str) -> int:
            if node_id in depth_cache:
                return depth_cache[node_id]
            node = nodes[node_id]
            if not node.outgoing:
                depth_cache[node_id] = 0
            else:
                depth_cache[node_id] = 1 + max(get_depth(pred_id) for pred_id in node.outgoing)
            return depth_cache[node_id]

        max_depth = max((get_depth(nid) for nid in nodes), default=0)

        return TaskDependencyStatistics(
            task_count=task_count,
            edge_count=edge_count,
            root_count=root_count,
            leaf_count=leaf_count,
            maximum_depth=max_depth,
            independent_tasks=independent_tasks,
            cyclic=False,
        )
