from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from eag.graph.state import GraphNodeKind, GraphState, RelationshipType


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphNode:
    id: str
    kind: GraphNodeKind
    name: str
    qualified_name: str
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_non_empty_str(self.id, "id"))
        if not isinstance(self.kind, GraphNodeKind):
            raise TypeError("kind must be a GraphNodeKind")
        object.__setattr__(self, "name", _validate_non_empty_str(self.name, "name"))
        object.__setattr__(
            self, "qualified_name", _validate_non_empty_str(self.qualified_name, "qualified_name")
        )
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a Mapping")
        # Freeze the mapping
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphEdge:
    source: str
    target: str
    relationship: RelationshipType
    weight: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _validate_non_empty_str(self.source, "source"))
        object.__setattr__(self, "target", _validate_non_empty_str(self.target, "target"))
        if not isinstance(self.relationship, RelationshipType):
            raise TypeError("relationship must be a RelationshipType")
        if isinstance(self.weight, bool) or not isinstance(self.weight, (int, float)):
            raise TypeError("weight must be a number")
        if self.weight < 0:
            raise ValueError("weight must be non-negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphStatistics:
    nodes: int = 0
    edges: int = 0
    relationship_counts: Mapping[RelationshipType, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.nodes, "nodes")
        _validate_non_negative_int(self.edges, "edges")
        if not isinstance(self.relationship_counts, Mapping):
            raise TypeError("relationship_counts must be a Mapping")

        validated_counts: dict[RelationshipType, int] = {}
        for k, v in self.relationship_counts.items():
            if not isinstance(k, RelationshipType):
                raise TypeError("relationship_counts keys must be RelationshipType")
            validated_counts[k] = _validate_non_negative_int(v, "relationship_count_value")

        object.__setattr__(self, "relationship_counts", MappingProxyType(validated_counts))


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphIdentity:
    repository: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "repository", _validate_non_empty_str(self.repository, "repository")
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringGraph:
    identity: GraphIdentity
    state: GraphState
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    statistics: GraphStatistics = field(default_factory=GraphStatistics)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.identity, GraphIdentity):
            raise TypeError("identity must be a GraphIdentity")
        if not isinstance(self.state, GraphState):
            raise TypeError("state must be a GraphState")
        if not isinstance(self.nodes, tuple):
            raise TypeError("nodes must be a tuple")
        if not isinstance(self.edges, tuple):
            raise TypeError("edges must be a tuple")
        if not isinstance(self.statistics, GraphStatistics):
            raise TypeError("statistics must be a GraphStatistics")
