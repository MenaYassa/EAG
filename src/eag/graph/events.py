from dataclasses import dataclass
from typing import TYPE_CHECKING

from eag.events import Event
from eag.graph.models import EngineeringGraph, GraphEdge, GraphNode

if TYPE_CHECKING:
    from eag.graph.runtime import GraphSnapshot


@dataclass(frozen=True, kw_only=True)
class GraphEvent(Event):
    pass


@dataclass(frozen=True, kw_only=True)
class GraphBuildStarted(GraphEvent):
    repository: str


@dataclass(frozen=True, kw_only=True)
class GraphNodeCreated(GraphEvent):
    node: GraphNode


@dataclass(frozen=True, kw_only=True)
class GraphEdgeCreated(GraphEvent):
    edge: GraphEdge


@dataclass(frozen=True, kw_only=True)
class GraphBuildCompleted(GraphEvent):
    graph: EngineeringGraph


@dataclass(frozen=True, kw_only=True)
class GraphBuildFailed(GraphEvent):
    error: str


@dataclass(frozen=True, kw_only=True)
class GraphBuilt(GraphEvent):
    snapshot: "GraphSnapshot"


@dataclass(frozen=True, kw_only=True)
class GraphLoaded(GraphEvent):
    snapshot: "GraphSnapshot"


@dataclass(frozen=True, kw_only=True)
class GraphQueryExecuted(GraphEvent):
    query: str
