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
from eag.source.runtime import SourceRuntime


class IndexRuntime:
    def __init__(self, source_runtime: SourceRuntime, event_bus: EventBus) -> None:
        self._source_runtime = source_runtime
        self._event_bus = event_bus
        self._current_index: RepositoryIndex | None = None

    def current(self) -> RepositoryIndex | None:
        return self._current_index

    def build(self, repository_root: Path, repository_name: str) -> RepositoryIndex:
        self._event_bus.publish(RepositoryIndexStarted(repository=repository_name))

        try:
            builder = RepositoryIndexBuilder(repository_name)

            # 1. Discover all source files
            source_files = self._discover_source_files(repository_root)

            # 2. Analyze each file and feed the builder
            for file_path in source_files:
                # Skip __init__.py for now if it's empty, or handle gracefully
                if file_path.name == "__init__.py":
                    continue

                result = self._source_runtime.analyze_file(
                    path=file_path,
                    repository_root=repository_root,
                    settings={},  # Pass actual settings if needed by analyzers
                    cache=None,
                )
                builder.add_result(result)

            index = builder.build()
            self._current_index = index
            self._event_bus.publish(
                RepositoryIndexCompleted(repository=repository_name, index=index)
            )
            return index

        except Exception as e:
            self._event_bus.publish(RepositoryIndexFailed(repository=repository_name, error=str(e)))
            raise IndexBuildError(f"Indexing failed: {e}") from e

    def _discover_source_files(self, root: Path) -> list[Path]:
        # Simple discovery for now, respects source analyzers
        supported_exts = self._source_runtime._registry.supported_extensions()
        files = []
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in supported_exts:
                # Basic ignore logic
                if ".venv" in p.parts or "__pycache__" in p.parts or ".git" in p.parts:
                    continue
                files.append(p)
        return files
