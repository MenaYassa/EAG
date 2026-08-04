"""Memory storage engines for EAG."""

from typing import Protocol, runtime_checkable

from eag.memory.errors import EntryNotFoundError
from eag.memory.models import MemoryEntry, MemoryQuery, MemorySearchResult, MemoryStatistics


@runtime_checkable
class MemoryStorage(Protocol):
    """The contract for a memory storage backend."""
    def store(self, entry: MemoryEntry) -> None: ...
    def retrieve(self, entry_id: str) -> MemoryEntry: ...
    def search(self, query: MemoryQuery) -> MemorySearchResult: ...
    def snapshot(self) -> tuple[MemoryEntry, ...]: ...
    def statistics(self) -> MemoryStatistics: ...
    def delete(self, entry_id: str) -> bool: ...
    def clear(self) -> None: ...


class InMemoryStorage:
    """A simple in-memory storage backend."""

    def __init__(self) -> None:
        self._entries: dict[str, MemoryEntry] = {}

    def store(self, entry: MemoryEntry) -> None:
        self._entries[entry.id] = entry

    def retrieve(self, entry_id: str) -> MemoryEntry:
        if entry_id not in self._entries:
            raise EntryNotFoundError(f"Memory entry '{entry_id}' not found.")
        return self._entries[entry_id]

    def search(self, query: MemoryQuery) -> MemorySearchResult:
        # If limit is exactly 0, return an empty result immediately
        if query.limit == 0:
            return MemorySearchResult(records=(), statistics=self.statistics(), count=0)
            
        results = list(self._entries.values())
        
        if query.goal_contains:
            results = [e for e in results if query.goal_contains.lower() in e.goal.lower()]
            
        if query.tags:
            results = [e for e in results if any(tag in e.tags for tag in query.tags)]
            
        # Sort by timestamp descending for determinism
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply the limit if it is greater than 0
        if query.limit is not None and query.limit > 0:
            results = results[:query.limit]
            
        stats = self.statistics()
        return MemorySearchResult(records=tuple(results), statistics=stats, count=len(results))
    def snapshot(self) -> tuple[MemoryEntry, ...]:
        return tuple(sorted(self._entries.values(), key=lambda e: e.timestamp))

    def statistics(self) -> MemoryStatistics:
        # Basic stats calculation
        total = len(self._entries)
        successes = sum(1 for e in self._entries.values() if e.metadata.get("outcome") == "success")
        scores = [e.metadata.get("score", 0) for e in self._entries.values()]
        
        return MemoryStatistics(
            total_runs=total,
            success_rate=(successes / total) if total > 0 else 0.0,
            average_score=(sum(scores) / total) if total > 0 else 0.0
        )

    def delete(self, entry_id: str) -> bool:
        return self._entries.pop(entry_id, None) is not None

    def clear(self) -> None:
        self._entries.clear()