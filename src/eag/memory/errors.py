"""Engineering Memory errors for EAG."""


class MemoryError(Exception):
    """Base error for all memory failures."""


class EntryNotFoundError(MemoryError):
    """Raised when a memory entry is not found."""


class PersistenceError(MemoryError):
    """Raised when persistence operations fail."""