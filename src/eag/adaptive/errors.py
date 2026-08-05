"""Adaptive Planning errors for EAG."""


class AdaptivePlanningError(Exception):
    """Base error for adaptive planning failures."""


class AnalysisError(AdaptivePlanningError):
    """Raised when experience analysis fails."""


class StrategyNotFoundError(AdaptivePlanningError):
    """Raised when a planning strategy is not found."""
