class ExplorerError(Exception):
    """Base error for explorer operations."""


class ViewNotFoundError(ExplorerError):
    """Raised when a requested view cannot be generated."""


class SymbolNotFoundError(ExplorerError):
    """Raised when a symbol is not found."""


class ModuleNotFoundError(ExplorerError):
    """Raised when a module is not found."""
