from dataclasses import dataclass

from eag.graph.models import GraphNode


@dataclass(frozen=True, slots=True, kw_only=True)
class TraversalResult:
    nodes: tuple[GraphNode, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class DependencyReport:
    node: GraphNode
    dependencies: tuple[GraphNode, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ImpactReport:
    changed_node: GraphNode
    direct: tuple[GraphNode, ...]
    indirect: tuple[GraphNode, ...]
    depth: int
    total: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PathReport:
    start: GraphNode
    end: GraphNode
    path: tuple[GraphNode, ...]
    distance: int


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricsReport:
    nodes: int
    edges: int
    most_referenced: GraphNode | None
    most_connected: GraphNode | None
