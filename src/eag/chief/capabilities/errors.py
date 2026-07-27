"""Capability domain errors for EAG Chief Engineer."""


class CapabilityError(Exception):
    """Base error for all capability failures."""


class DuplicateCapability(CapabilityError):
    """Raised when registering a capability with an ID that already exists."""


class CapabilityNotFound(CapabilityError):
    """Raised when a specific capability by ID is not found."""


class RequirementMissing(CapabilityError):
    """Raised when a capability's requirements are not met."""


class RankingFailure(CapabilityError):
    """Raised when ranking fails."""
