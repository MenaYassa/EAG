"""Session failure tracking runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import uuid4

from eag.session.models import FailureRecord


class FailureCategory(StrEnum):
    EXECUTION = "execution"
    APPROVAL = "approval"
    FILESYSTEM = "filesystem"
    GIT = "git"
    NETWORK = "network"
    MODEL = "model"
    PLANNER = "planner"
    PLUGIN = "plugin"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


class FailureSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FailureTracker:
    """Mutable runtime container for failures."""

    def __init__(self) -> None:
        self._failures: list[FailureRecord] = []

    def record(
        self,
        *,
        component: str,
        message: str,
        recoverable: bool,
        category: FailureCategory = FailureCategory.UNKNOWN,
        severity: FailureSeverity = FailureSeverity.ERROR,
        exception_type: str | None = None,
        **details: str,
    ) -> FailureRecord:
        record = FailureRecord(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            component=component,
            category=category.value,
            severity=severity.value,
            message=message,
            recoverable=recoverable,
            exception_type=exception_type,
            details=MappingProxyType(details),
        )
        self._failures.append(record)
        return record

    @property
    def failures(self) -> tuple[FailureRecord, ...]:
        return tuple(self._failures)

    def count(self) -> int:
        return len(self._failures)

    def has_failures(self) -> bool:
        return bool(self._failures)

    def has_recoverable(self) -> bool:
        return any(f.recoverable for f in self._failures)

    def has_unrecoverable(self) -> bool:
        return any(not f.recoverable for f in self._failures)

    def last(self) -> FailureRecord | None:
        return self._failures[-1] if self._failures else None

    def clear(self) -> None:
        self._failures.clear()


__all__ = [
    "FailureCategory",
    "FailureRecord",
    "FailureSeverity",
    "FailureTracker",
]
