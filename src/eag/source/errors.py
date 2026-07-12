class SourceError(Exception):
    """Base error for source intelligence operations."""


class UnsupportedLanguageError(SourceError):
    """Raised when the language is not supported."""


class AnalyzerNotFoundError(SourceError):
    """Raised when no analyzer is found for a file."""


class AnalysisFailedError(SourceError):
    """Raised when analysis fails."""
