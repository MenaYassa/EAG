"""Provider registry for EAG Chief Engineer."""

from eag.chief.intelligence.enums import ProviderStatus
from eag.chief.intelligence.errors import ProviderNotFoundError
from eag.chief.intelligence.models import ProviderProfile


class ProviderRegistry:
    """Discovers and manages available AI providers."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderProfile] = {}

    def register(self, provider: ProviderProfile) -> None:
        if provider.id in self._providers:
            raise ValueError(f"Provider '{provider.id}' is already registered.")
        self._providers[provider.id] = provider

    def find(self, provider_id: str) -> ProviderProfile:
        if provider_id not in self._providers:
            raise ProviderNotFoundError(f"Provider '{provider_id}' not found.")
        return self._providers[provider_id]

    def list(self) -> tuple[ProviderProfile, ...]:
        return tuple(sorted(self._providers.values(), key=lambda p: p.id))

    def available(self) -> tuple[ProviderProfile, ...]:
        """Returns only online providers, sorted by ID for determinism."""
        return tuple(p for p in self.list() if p.status == ProviderStatus.ONLINE)
