from pathlib import Path

from eag.events import EventBus
from eag.index.builder import RepositoryIndexBuilder
from eag.index.errors import IndexBuildError
from eag.index.events import (
    RepositoryIndexCompleted,
    RepositoryIndexFailed,
    RepositoryIndexStarted,
)
from eag.index.models import RepositoryIndex
from eag.source.models import AnalysisResult
from eag.source.runtime import SourceRuntime


class IndexRuntime:
    def __init__(self, source_runtime: SourceRuntime, event_bus: EventBus) -> None:
        self._source_runtime = source_runtime
        self._event_bus = event_bus
        self._current_index: RepositoryIndex | None = None
        self._last_analysis_results: tuple[AnalysisResult, ...] = ()

    def current(self) -> RepositoryIndex | None:
        return self._current_index

    def analysis_results(self) -> tuple[AnalysisResult, ...]:
        """Return immutable per-file actual analysis results from the latest build."""
        return self._last_analysis_results

    def supported_extensions(self) -> tuple[str, ...]:
        """Expose registered source extensions without requiring callers to reach into internals."""
        return tuple(sorted(self._source_runtime._registry.supported_extensions()))

    def build(
        self,
        repository_root: Path,
        repository_name: str,
        *,
        source_files: tuple[Path, ...] | None = None,
    ) -> RepositoryIndex:
        """Build an index, optionally from a pre-screened read-only source-file list."""
        self._event_bus.publish(RepositoryIndexStarted(repository=repository_name))

        try:
            builder = RepositoryIndexBuilder(repository_name)
            candidates = (
                source_files
                if source_files is not None
                else tuple(self._discover_source_files(repository_root))
            )
            results: list[AnalysisResult] = []

            for file_path in candidates:
                # Preserve existing behavior: empty package markers are not indexed.
                if file_path.name == "__init__.py":
                    continue
                result = self._source_runtime.analyze_file(
                    path=file_path,
                    repository_root=repository_root,
                    settings={},
                    cache=None,
                )
                results.append(result)
                builder.add_result(result)

            index = builder.build()
            self._current_index = index
            self._last_analysis_results = tuple(results)
            self._event_bus.publish(
                RepositoryIndexCompleted(repository=repository_name, index=index)
            )
            return index
        except Exception as error:
            self._last_analysis_results = ()
            self._event_bus.publish(RepositoryIndexFailed(repository=repository_name, error=str(error)))
            raise IndexBuildError(f"Indexing failed: {error}") from error

    def _discover_source_files(self, root: Path) -> list[Path]:
        supported_exts = self.supported_extensions()
        files = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in supported_exts:
                if ".venv" in path.parts or "__pycache__" in path.parts or ".git" in path.parts:
                    continue
                files.append(path)
        return files
