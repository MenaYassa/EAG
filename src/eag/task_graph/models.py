"""Task Graph domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from eag.task_graph.enums import DependencyType
from eag.workers.enums import TaskPriority


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskNode:
    """Represents one engineering activity in the graph."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    required_capability: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration: float = 1.0
    dependencies: tuple[str, ...] = ()  # For metadata/convenience
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _validate_non_empty_str(self.title, "title"))
        if not isinstance(self.priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        if not isinstance(self.dependencies, tuple):
            raise TypeError("dependencies must be a tuple")
        if self.estimated_duration < 0:  # (or <= 0, depending on your spec)
            raise ValueError("estimated_duration must be non-negative")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskEdge:
    """Represents a dependency between two tasks."""

    source: str
    target: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _validate_non_empty_str(self.source, "source"))
        object.__setattr__(self, "target", _validate_non_empty_str(self.target, "target"))
        if not isinstance(self.dependency_type, DependencyType):
            raise TypeError("dependency_type must be a DependencyType")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))
