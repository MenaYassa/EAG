"""Session metrics calculation."""

from __future__ import annotations

from datetime import timedelta

from eag.changeset.models import ChangeSet
from eag.session.failures import FailureTracker
from eag.session.models import SessionMetrics


class SessionMetricsCalculator:
    """Calculates session metrics dynamically."""

    @staticmethod
    def calculate(
        changesets: tuple[ChangeSet, ...],
        failures: FailureTracker,
        duration: timedelta,
        warning_count: int = 0,
    ) -> SessionMetrics:
        command_count = sum(len(cs.commands) for cs in changesets)
        file_count = sum(len(cs.files) for cs in changesets)
        test_count = sum(len(cs.tests) for cs in changesets)
        artifact_count = sum(len(cs.artifacts) for cs in changesets)

        failure_count = failures.count()
        recoverable_failures = sum(1 for f in failures.failures if f.recoverable)
        unrecoverable_failures = failure_count - recoverable_failures
        error_count = unrecoverable_failures

        penalty = (2 * warning_count) + (5 * recoverable_failures) + (10 * unrecoverable_failures)
        health_score = max(0, min(100, 100 - penalty))

        return SessionMetrics(
            changeset_count=len(changesets),
            command_count=command_count,
            file_count=file_count,
            test_count=test_count,
            artifact_count=artifact_count,
            failure_count=failure_count,
            recoverable_failures=recoverable_failures,
            unrecoverable_failures=unrecoverable_failures,
            warning_count=warning_count,
            error_count=error_count,
            duration=duration,
            health_score=health_score,
        )


__all__ = [
    "SessionMetrics",
    "SessionMetricsCalculator",
]
