"""Reflection domain errors for EAG."""


class ReflectionError(Exception):
    """Base error for all reflection failures."""


class ReflectionValidationError(ReflectionError):
    """Raised when reflection validation fails."""


class EngineNotFoundError(ReflectionError):
    """Raised when a specific reflection engine is not found."""
