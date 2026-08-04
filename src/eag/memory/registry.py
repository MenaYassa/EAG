"""Memory storage registry for EAG."""

from eag.memory.errors import MemoryError
from eag.memory.storage import MemoryStorage


class MemoryRegistry:
    """Discovers and manages available memory storage backends."""

    def __init__(self) -> None:
        self._backends: dict[str, MemoryStorage] = {}

    def register(self, name: str, backend: MemoryStorage) -> None:
        if backend is None:
            raise AttributeError("Cannot register None")
        if name in self._backends:
            raise MemoryError(f"Memory backend '{name}' is already registered.")
        self._backends[name] = backend

    def find(self, name: str) -> MemoryStorage:
        if name not in self._backends:
            raise MemoryError(f"Memory backend '{name}' not found.")
        return self._backends[name]

    def list(self) -> tuple[MemoryStorage, ...]:
        return tuple(self._backends.values())
