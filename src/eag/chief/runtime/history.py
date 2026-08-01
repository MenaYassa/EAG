"""Run history for EAG Chief Runtime."""

from collections.abc import Mapping
from eag.chief.runtime.models import ChiefRun, RunResult


class RunHistory:
    """Stores and retrieves Chief run histories."""

    def __init__(self) -> None:
        self._runs: dict[str, ChiefRun] = {}
        self._results: dict[str, RunResult] = {}

    def record(self, run: ChiefRun) -> None:
        self._runs[run.run_id] = run

    def record_result(self, result: RunResult) -> None:
        self._results[result.run_id] = result

    def get_run(self, run_id: str) -> ChiefRun | None:
        return self._runs.get(run_id)

    def get_result(self, run_id: str) -> RunResult | None:
        return self._results.get(run_id)

    def list_runs(self) -> tuple[ChiefRun, ...]:
        return tuple(self._runs.values())

    def list_results(self) -> tuple[RunResult, ...]:
        return tuple(self._results.values())

    def clear(self) -> None:
        self._runs.clear()
        self._results.clear()