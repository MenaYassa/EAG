"""Provider discovery service for EAG."""

from datetime import UTC, datetime

from eag.chief.intelligence.execution.models import DiscoveryReport


class DiscoveryService:
    """Manages model discovery and caching for providers."""

    def __init__(self) -> None:
        self._cache: dict[str, DiscoveryReport] = {}

    def discover(self, provider) -> DiscoveryReport:
        pid = provider.provider_id
        try:
            report = provider.discover()
            self._cache[pid] = report
            return report
        except Exception as e:
            return DiscoveryReport(
                provider_id=pid, status="failed", error=str(e), timestamp=datetime.now(UTC)
            )

    def get_cached(self, provider_id: str) -> DiscoveryReport | None:
        return self._cache.get(provider_id)

    def clear_cache(self) -> None:
        self._cache.clear()
