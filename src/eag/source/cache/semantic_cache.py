"""Semantic cache for EAG source documents."""

from pathlib import Path

from eag.source.models import SourceDocument


class SemanticCache:
    """Caches parsed source documents by path and checksum."""

    def __init__(self) -> None:
        self._cache: dict[Path, tuple[str, SourceDocument]] = {}

    def get(self, path: Path, checksum: str) -> SourceDocument | None:
        entry = self._cache.get(path)
        if entry and entry[0] == checksum:
            return entry[1]
        return None

    def set(self, path: Path, checksum: str, document: SourceDocument) -> None:
        self._cache[path] = (checksum, document)

    def invalidate(self, path: Path) -> None:
        self._cache.pop(path, None)

    def clear(self) -> None:
        self._cache.clear()
