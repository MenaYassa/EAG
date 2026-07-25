"""Benchmark runner for EAG."""

import time
from dataclasses import dataclass
from pathlib import Path

from eag.source.python import RenameTransformation, TransformationContext
from eag.source.runtime import SourceRuntime


@dataclass
class BenchmarkResult:
    size: int
    parse_time_ms: float
    transform_time_ms: float
    total_time_ms: float


class BenchmarkRunner:
    """Measures performance and scalability of the source platform."""

    def __init__(self, runtime: SourceRuntime) -> None:
        self._runtime = runtime

    def run_suite(self, sizes: list[int] | None = None) -> list[BenchmarkResult]:
        if sizes is None:
            sizes = [10, 100, 1000]
        results: list[BenchmarkResult] = []
        for size in sizes:
            results.append(self._run_benchmark(size))
        return results

    def _run_benchmark(self, num_files: int) -> BenchmarkResult:
        # Generate synthetic files
        files: dict[Path, str] = {}
        for i in range(num_files):
            path = Path(f"module_{i}.py")
            content = f"def func_{i}():\n    pass\n\nfunc_{i}()\n"
            files[path] = content

        # Benchmark Parse
        start_parse = time.monotonic()
        docs = []
        for path, content in files.items():
            docs.append(self._runtime.parse(path, content))
        parse_time = (time.monotonic() - start_parse) * 1000

        # Benchmark Transform
        start_transform = time.monotonic()
        for doc in docs:
            ctx = TransformationContext(document=doc, content=files[doc.path])
            transform = RenameTransformation(f"func_{doc.path.stem.split('_')[1]}", "renamed_func")
            transform.apply(ctx)
        transform_time = (time.monotonic() - start_transform) * 1000

        return BenchmarkResult(
            size=num_files,
            parse_time_ms=parse_time,
            transform_time_ms=transform_time,
            total_time_ms=parse_time + transform_time,
        )
