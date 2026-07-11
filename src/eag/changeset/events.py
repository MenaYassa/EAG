"""ChangeSet builder events."""

from dataclasses import dataclass
from typing import Any

from eag.changeset.models import ChangeSet
from eag.events import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSetBuilderStarted(Event):
    """Published when a ChangeSetBuilder is initialized."""

    identity_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeRecorded(Event):
    """Published when a change is recorded in the builder."""

    changeset_id: str
    kind: str
    payload: Any


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSetFinalized(Event):
    """Published when a ChangeSetBuilder is finalized."""

    changeset_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSetRecordingStarted(Event):
    """Published when a recorder starts listening."""

    identity_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSetCompleted(Event):
    """Published after finalization."""

    changeset: ChangeSet


__all__ = [
    "ChangeRecorded",
    "ChangeSetBuilderStarted",
    "ChangeSetCompleted",
    "ChangeSetFinalized",
    "ChangeSetRecordingStarted",
]