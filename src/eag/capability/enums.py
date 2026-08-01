"""Capability domain vocabulary for EAG."""

from enum import StrEnum


class CapabilityKind(StrEnum):
    """The kind of engineering capability."""

    DISCOVERY = "discovery"
    WORKSPACE = "workspace"
    REPOSITORY = "repository"
    SOURCE = "source"
    TRANSFORMATION = "transformation"
    REVIEW = "review"
    BENCHMARK = "benchmark"
    COMPOSITE = "composite"
    UNKNOWN = "unknown"


class CapabilityStatus(StrEnum):
    """Health status of a capability."""

    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class CapabilityOutcome(StrEnum):
    """The outcome of a capability execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class CapabilityState(StrEnum):
    """Lifecycle state of a capability execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
