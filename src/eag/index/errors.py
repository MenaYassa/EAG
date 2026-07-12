class IndexError(Exception):
    """Base error for repository index operations."""


class SymbolNotFoundError(IndexError):
    """Raised when a symbol is not found in the index."""


class ModuleNotFoundError(IndexError):
    """Raised when a module is not found in the index."""


class IndexBuildError(IndexError):
    """Raised when building the index fails."""
