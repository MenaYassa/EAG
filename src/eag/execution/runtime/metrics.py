"""Runtime metrics collector for EAG."""

from eag.execution.models import ExecutionMetrics


class MetricsRuntime:
    """Collects live execution metrics."""

    def __init__(self) -> None:
        self._total = 0
        self._completed = 0
        self._failed = 0
        self._elapsed = 0.0

    def set_total(self, total: int) -> None:
        self._total = total

    def record_success(self, duration: float) -> None:
        self._completed += 1
        self._elapsed += duration

    def record_failure(self, duration: float) -> None:
        self._failed += 1
        self._elapsed += duration

    def get_metrics(self) -> ExecutionMetrics:
        return ExecutionMetrics(
            steps_total=self._total,
            steps_completed=self._completed,
            steps_failed=self._failed,
            execution_time=self._elapsed,
        )
