"""Capability domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from eag.capability.enums import (
    CapabilityKind,
    CapabilityOutcome,
    CapabilityState,
    CapabilityStatus,
)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityMetadata:
    """The 'business card' for a capability."""
    id: str
    name: str
    kind: CapabilityKind = CapabilityKind.UNKNOWN
    description: str = ""
    version: str = "1.0.0"
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityRequest:
    """A request to execute a capability."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capability_id: str
    goal_text: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _validate_mapping(self.parameters, "parameters"))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityContext:
    """Context provided to a capability during execution."""
    workspace_path: Path
    repository_path: Path | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityResult:
    """The immutable result of a capability execution."""
    request_id: str
    capability_id: str
    outcome: CapabilityOutcome
    state: CapabilityState
    output: str = ""
    artifacts: tuple[str, ...] = ()
    error: str | None = None
    duration_ms: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))

    @property
    def success(self) -> bool:
        return self.outcome == CapabilityOutcome.SUCCESS


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityEstimate:
    """Estimate of cost and duration for a capability."""
    capability_id: str
    estimated_duration_ms: float = 0.0
    estimated_cost: float = 0.0
    confidence: float = 1.0


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityHealth:
    """Health status of a capability."""
    capability_id: str
    status: CapabilityStatus = CapabilityStatus.READY
    message: str = ""


@runtime_checkable
class Capability(Protocol):
    """The contract for an engineering capability."""
    @property
    def metadata(self) -> CapabilityMetadata: ...
    
    def supports(self, request: CapabilityRequest) -> bool: ...
    
    def estimate(self, request: CapabilityRequest) -> CapabilityEstimate: ...
    
    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> CapabilityResult: ...
    
    def health(self) -> CapabilityHealth: ...