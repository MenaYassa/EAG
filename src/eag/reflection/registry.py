"""Reflection engine registry for EAG."""

from eag.reflection.errors import EngineNotFoundError
from eag.reflection.protocol import ReflectionEngine


class ReflectionRegistry:
    """Discovers and manages available reflection engines."""

    def __init__(self) -> None:
        self._engines: dict[str, ReflectionEngine] = {}

    def register(self, name: str, engine: ReflectionEngine) -> None:
        if name in self._engines:
            raise ValueError(f"Reflection engine '{name}' is already registered.")
        self._engines[name] = engine

    def find(self, name: str) -> ReflectionEngine:
        if name not in self._engines:
            raise EngineNotFoundError(f"Reflection engine '{name}' not found.")
        return self._engines[name]

    def list(self) -> tuple[ReflectionEngine, ...]:
        return tuple(self._engines.values())
