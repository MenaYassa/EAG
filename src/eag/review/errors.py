"""Engineering Review errors for EAG."""


class ReviewError(Exception):
    """Base error for all review failures."""


class AnalyzerError(ReviewError):
    """Raised when an analyzer fails."""


class ReflectionError(ReviewError):
    """Raised when reflection fails."""


class ReviewValidationError(ReviewError):
    """Raised when review validation fails."""
