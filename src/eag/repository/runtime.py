from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eag.events import EventBus
from eag.repository.errors import RepositoryError
from eag.repository.events import (
    RepositoryProfileGenerated,
    RepositoryScanCompleted,
    RepositoryScanFailed,
    RepositoryScanStarted,
)
from eag.repository.models import RepositoryProfile, RepositorySnapshot
from eag.repository.scanner import RepositoryScanner


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryServices:
    scanner: RepositoryScanner
    event_bus: EventBus
    settings: Any


class RepositoryRuntime:
    def __init__(self, services: RepositoryServices) -> None:
        self._services = services
        self._last_snapshot: RepositorySnapshot | None = None

    def scan(self, root: Path | None = None) -> RepositorySnapshot:
        target_root = root or self._services.settings.kernel.workspace
        try:
            self._services.event_bus.publish(RepositoryScanStarted(repository_root=target_root))
            profile = self._services.scanner.scan(target_root)
            self._services.event_bus.publish(
                RepositoryProfileGenerated(repository_root=target_root, profile=profile)
            )
            snapshot = RepositorySnapshot(profile=profile)
            self._last_snapshot = snapshot
            self._services.event_bus.publish(
                RepositoryScanCompleted(repository_root=target_root, profile=profile)
            )
            return snapshot
        except RepositoryError as e:
            self._services.event_bus.publish(
                RepositoryScanFailed(repository_root=target_root, error=str(e))
            )
            raise
        except Exception as e:
            self._services.event_bus.publish(
                RepositoryScanFailed(repository_root=target_root, error=f"Unexpected error: {e}")
            )
            raise

    def profile(self) -> RepositoryProfile | None:
        return self._last_snapshot.profile if self._last_snapshot else None
