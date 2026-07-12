from dataclasses import dataclass

from eag.events import Event
from eag.graph.models import EngineeringGraph, GraphEdge, GraphNode


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
