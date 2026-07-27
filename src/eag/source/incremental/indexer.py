"""Incremental semantic indexer for EAG."""

from dataclasses import dataclass
from pathlib import Path

from eag.source.cache import SemanticCache
from eag.source.models import SourceDocument
from eag.source.runtime import SourceRuntime


@dataclass(frozen=True)
class ChangeSet:
    """Represents changes in the repository."""

    added: tuple[Path, ...] = ()
    modified: tuple[Path, ...] = ()
    deleted: tuple[Path, ...] = ()


@dataclass(frozen=True)
class IndexDelta:
    """The result of an incremental index update."""

    updated_documents: tuple[SourceDocument, ...] = ()
    deleted_paths: tuple[Path, ...] = ()
    cache_hits: int = 0
    cache_misses: int = 0


class IncrementalIndexer:
    """Indexes only changed files using a semantic cache."""

    def __init__(self, runtime: SourceRuntime, cache: SemanticCache | None = None) -> None:
        self._runtime = runtime
        self._cache = cache or SemanticCache()

    def update(self, changeset: ChangeSet, file_contents: dict[Path, str]) -> IndexDelta:
        updated_docs: list[SourceDocument] = []
        deleted_paths: list[Path] = list(changeset.deleted)
        hits = 0
        misses = 0

        for path in changeset.added + changeset.modified:
            content = file_contents.get(path, "")
            checksum = self._runtime.parse(path, content).checksum

            cached_doc = self._cache.get(path, checksum)
            if cached_doc:
                updated_docs.append(cached_doc)
                hits += 1
            else:
                doc = self._runtime.parse(path, content)
                self._cache.set(path, checksum, doc)
                updated_docs.append(doc)
                misses += 1

        for path in deleted_paths:
            self._cache.invalidate(path)

        return IndexDelta(
            updated_documents=tuple(updated_docs),
            deleted_paths=tuple(deleted_paths),
            cache_hits=hits,
            cache_misses=misses,
        )
