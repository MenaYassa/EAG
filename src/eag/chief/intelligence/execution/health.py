"""Provider health manager for EAG."""

from datetime import UTC, datetime

from eag.chief.intelligence.execution.enums import ProviderHealthStatus
from eag.chief.intelligence.execution.models import ProviderHealth


class HealthManager:
    """Tracks and manages provider health metrics."""

    def __init__(self) -> None:
        self._health: dict[str, ProviderHealth] = {}

    def record_success(self, provider_id: str, latency_ms: float) -> None:
        h = self._health.get(provider_id, ProviderHealth(provider_id=provider_id))
        self._health[provider_id] = ProviderHealth(
            provider_id=provider_id,
            status=self._compute_status(h.consecutive_failures, True),
            latency_ms=latency_ms,
            success_count=h.success_count + 1,
            failure_count=h.failure_count,
            consecutive_failures=0,
            last_success=datetime.now(UTC),
            last_failure=h.last_failure,
        )

    def record_failure(self, provider_id: str) -> None:
        h = self._health.get(provider_id, ProviderHealth(provider_id=provider_id))
        consec = h.consecutive_failures + 1
        self._health[provider_id] = ProviderHealth(
            provider_id=provider_id,
            status=self._compute_status(consec, False),
            latency_ms=h.latency_ms,
            success_count=h.success_count,
            failure_count=h.failure_count + 1,
            consecutive_failures=consec,
            last_success=h.last_success,
            last_failure=datetime.now(UTC),
        )

    def health(self, provider_id: str) -> ProviderHealth:
        return self._health.get(provider_id, ProviderHealth(provider_id=provider_id))

    def summary(self) -> dict[str, ProviderHealth]:
        return dict(self._health)

    def _compute_status(self, consecutive_failures: int, is_success: bool) -> ProviderHealthStatus:
        if is_success:
            return ProviderHealthStatus.HEALTHY
        if consecutive_failures >= 5:
            return ProviderHealthStatus.UNHEALTHY
        if consecutive_failures >= 2:
            return ProviderHealthStatus.DEGRADED
        return ProviderHealthStatus.HEALTHY
