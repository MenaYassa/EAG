"""Reflection domain events for EAG."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionEvent:
    run_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionStarted(ReflectionEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionCompleted(ReflectionEvent):
    report_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionFailed(ReflectionEvent):
    error: str
