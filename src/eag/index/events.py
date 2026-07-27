from dataclasses import dataclass

from eag.events import Event
from eag.index.models import RepositoryIndex


@dataclass(frozen=True, kw_only=True)
class IndexEvent(Event):
    repository: str


@dataclass(frozen=True, kw_only=True)
class RepositoryIndexStarted(IndexEvent):
    pass


@dataclass(frozen=True, kw_only=True)
class RepositoryIndexCompleted(IndexEvent):
    index: RepositoryIndex


@dataclass(frozen=True, kw_only=True)
class RepositoryIndexFailed(IndexEvent):
    error: str
