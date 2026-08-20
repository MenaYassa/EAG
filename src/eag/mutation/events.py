"""Redacted lifecycle events for deterministic governed mutation."""

from __future__ import annotations

from dataclasses import dataclass

from eag.events import Event
from eag.mutation.errors import MutationViolationCode
from eag.mutation.models import MutationOperation, MutationResult


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationEvent(Event):
    """Base event for G2.3.1 mutation lifecycle telemetry."""

    proposal_id: str
    run_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationProposed(MutationEvent):
    target_path: str
    operation: MutationOperation
    proposal_digest: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationAuthorized(MutationEvent):
    authorization_id: str
    proposal_digest: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationStarted(MutationEvent):
    authorization_id: str
    target_path: str
    operation: MutationOperation


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationRejected(MutationEvent):
    code: MutationViolationCode
    stage: str
    target_path: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationCompleted(MutationEvent):
    receipt_id: str
    target_path: str
    operation: MutationOperation
    result: MutationResult


@dataclass(frozen=True, slots=True, kw_only=True)
class MutationFailed(MutationEvent):
    receipt_id: str
    code: MutationViolationCode
    stage: str
