"""Execution Graph domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.execution_graph.enums import NodeState


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionNode:
    """Represents a task in the execution graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    title: str = ""
    state: NodeState = NodeState.PENDING
    dependencies: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not self.task_id or not self.task_id.strip():
            raise ValueError("task_id cannot be empty")
        object.__setattr__(self, "task_id", self.task_id.strip())
        
        if not isinstance(self.dependencies, tuple):
            raise TypeError("dependencies must be a tuple")
            
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))

@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionEdge:
    """Represents a dependency between two execution nodes."""
    source: str
    target: str

    def __post_init__(self) -> None:
        if self.source == self.target:
            raise ValueError("Source and target cannot be the same")


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactNode:
    """Represents an artifact produced by a worker."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str
    creator_worker_id: str
    version: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not self.path or str(self.path).strip() == "." or str(self.path).strip() == "":
            raise ValueError("path cannot be empty")
            
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))

@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactEdge:
    """Represents a dependency between two artifacts."""
    source: str  # Artifact ID
    target: str  # Artifact ID


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerMessage:
    """A message exchanged between workers."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: str
    msg_type: str
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))