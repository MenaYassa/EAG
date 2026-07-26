"""Capability domain vocabulary for EAG Chief Engineer."""

from enum import StrEnum


class CapabilityCategory(StrEnum):
    """The category of a capability."""

    TRANSFORMATION = "transformation"
    GENERATION = "generation"
    ANALYSIS = "analysis"
    REVIEW = "review"
    MIGRATION = "migration"
    UNKNOWN = "unknown"


class CapabilityCost(StrEnum):
    """The estimated computational/resource cost of a capability."""

    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CapabilityRisk(StrEnum):
    """The estimated risk level of a capability."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CapabilityRequirement(StrEnum):
    """Platform requirements for a capability to execute."""

    WORKSPACE_READY = "workspace_ready"
    REPOSITORY_READY = "repository_ready"
    SOURCE_INDEXED = "source_indexed"
    TRANSFORMATION_PLATFORM = "transformation_platform"
    PLANNER = "planner"


class CapabilityRuntimeState(StrEnum):
    """Lifecycle state of the capability runtime."""

    UNINITIALIZED = "uninitialized"
    READY = "ready"
    MATCHING = "matching"
    RANKING = "ranking"
    COMPLETE = "complete"
    FAILED = "failed"
