"""Redacted context-assembly events with no source, secret, prompt, or host-path payloads."""

from __future__ import annotations

from dataclasses import dataclass

from eag.events import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryContextEvent(Event):
    repository_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryContextAssemblyStarted(RepositoryContextEvent):
    policy_version: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryContextAssemblyCompleted(RepositoryContextEvent):
    snapshot_fingerprint: str
    context_fingerprint: str
    files_selected: int
    symbols_selected: int
    dependencies_selected: int
    excerpts_selected: int
    omitted_items: int
    truncated: bool
    insufficient: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryContextStaleDetected(RepositoryContextEvent):
    expected_snapshot_fingerprint: str
    current_snapshot_fingerprint: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryContextAssemblyFailed(RepositoryContextEvent):
    reason_code: str
