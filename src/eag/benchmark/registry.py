"""Benchmark registry for EAG."""

from eag.benchmark.errors import RegistryError
from eag.benchmark.models import Benchmark


class BenchmarkRegistry:
    """Discovers and manages available benchmarks."""

    def __init__(self) -> None:
        self._benchmarks: dict[str, Benchmark] = {}

    def register(self, benchmark: Benchmark) -> None:
        if benchmark.id in self._benchmarks:
            raise RegistryError(f"Benchmark '{benchmark.id}' is already registered.")
        self._benchmarks[benchmark.id] = benchmark

    def find(self, benchmark_id: str) -> Benchmark:
        if benchmark_id not in self._benchmarks:
            raise RegistryError(f"Benchmark '{benchmark_id}' not found.")
        return self._benchmarks[benchmark_id]

    def list(self) -> tuple[Benchmark, ...]:
        return tuple(sorted(self._benchmarks.values(), key=lambda b: b.id))

    def list_by_category(self, category: str) -> tuple[Benchmark, ...]:
        return tuple(b for b in self.list() if b.category.value == category)
