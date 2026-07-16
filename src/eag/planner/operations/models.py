"""Engineering operation domain models for EAG."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from eag.planner.operations.enums import (
    OperationCategory,
    OperationComplexity,
    OperationSafety,
)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringOperationDefinition:
    """Metadata describing an engineering operation."""
    id: str
    name: str
    description: str = ""
    category: OperationCategory
    complexity: OperationComplexity = OperationComplexity.LOW
    safety: OperationSafety = OperationSafety.SAFE
    estimated_minutes: float = 1.0
    parallelizable: bool = False
    rollback_supported: bool = True
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")
        if not isinstance(self.category, OperationCategory):
            raise TypeError("category must be an OperationCategory")
        if not isinstance(self.complexity, OperationComplexity):
            raise TypeError("complexity must be an OperationComplexity")
        if not isinstance(self.safety, OperationSafety):
            raise TypeError("safety must be an OperationSafety")
        if not isinstance(self.estimated_minutes, (int, float)) or self.estimated_minutes < 0:
            raise ValueError("estimated_minutes must be non-negative")
        if not isinstance(self.parallelizable, bool):
            raise TypeError("parallelizable must be a bool")
        if not isinstance(self.rollback_supported, bool):
            raise TypeError("rollback_supported must be a bool")
        if not isinstance(self.tags, tuple):
            raise TypeError("tags must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationExecutionContext:
    """Context provided to an operation during execution (future)."""
    workspace: str = ""
    repository: Any = None
    planning_goal: Any = None
    engineering_goal: Any = None
    configuration: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "configuration", _validate_mapping(self.configuration, "configuration"))


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationExecutionResult:
    """Result returned by an operation after execution (future)."""
    success: bool
    generated_tasks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metrics: Mapping[str, Any] = field(default_factory=dict, hash=False)
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise TypeError("success must be a bool")
        if not isinstance(self.generated_tasks, tuple):
            raise TypeError("generated_tasks must be a tuple")
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple")
        object.__setattr__(self, "metrics", _validate_mapping(self.metrics, "metrics"))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))