class SourceError(Exception):
    """Base error for all source intelligence failures."""


class UnsupportedLanguageError(SourceError):
    """Raised when the language is not supported."""


class AnalyzerNotFoundError(SourceError):
    """Raised when no analyzer is found for a file."""


class AnalysisFailedError(SourceError):
    """Raised when analysis fails."""


class SourceParseError(SourceError):
    """Raised when a source file cannot be parsed."""


class SourceValidationError(SourceError):
    """Raised when source validation fails."""
