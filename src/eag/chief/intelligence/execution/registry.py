"""Execution provider registry for EAG."""

from eag.chief.intelligence.execution.errors import ProviderNotFoundError
from eag.chief.intelligence.execution.protocol import AIProvider


class ProviderRegistry:
    """Discovers and manages available AI execution providers."""

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider: AIProvider) -> None:
        pid = provider.provider_id
        if pid in self._providers:
            raise ValueError(f"Provider '{pid}' is already registered.")
        self._providers[pid] = provider

    def find(self, provider_id: str) -> AIProvider:
        if provider_id not in self._providers:
            raise ProviderNotFoundError(f"Provider '{provider_id}' not found.")
        return self._providers[provider_id]

    def list(self) -> tuple[AIProvider, ...]:
        """Returns all providers, sorted by ID for determinism."""
        return tuple(sorted(self._providers.values(), key=lambda p: p.provider_id))
