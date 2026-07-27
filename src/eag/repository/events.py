from dataclasses import dataclass
from pathlib import Path

from eag.events import Event
from eag.repository.models import RepositoryProfile


@dataclass(frozen=True, kw_only=True)
class RepositoryEvent(Event):
    repository_root: Path


@dataclass(frozen=True, kw_only=True)
class RepositoryScanStarted(RepositoryEvent):
    pass


@dataclass(frozen=True, kw_only=True)
class RepositoryScanCompleted(RepositoryEvent):
    profile: RepositoryProfile


@dataclass(frozen=True, kw_only=True)
class RepositoryProfileGenerated(RepositoryEvent):
    profile: RepositoryProfile


@dataclass(frozen=True, kw_only=True)
class RepositoryScanFailed(RepositoryEvent):
    error: str
