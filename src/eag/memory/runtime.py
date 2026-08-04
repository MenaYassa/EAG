"""Memory runtime for EAG."""

from eag.events import EventBus
from eag.memory.errors import MemoryError
from eag.memory.experience import ExperienceBuilder
from eag.memory.models import (
    EngineeringExperience,
    MemoryEntry,
    MemoryQuery,
    MemorySearchResult,
    MemorySnapshot,
    MemoryStatistics,
)
from eag.memory.storage import MemoryStorage
from eag.reflection.models import ReflectionContext, ReflectionReport


class MemoryRuntime:
    """Orchestrates engineering memory operations."""

    def __init__(self, storage: MemoryStorage, event_bus: EventBus) -> None:
        self._storage = storage
        self._event_bus = event_bus
        self._experience_builder = ExperienceBuilder()

    def store_reflection(self, context: ReflectionContext, report: ReflectionReport) -> MemoryEntry:
        """Automatically stores a reflection as a memory entry."""
        entry = MemoryEntry(
            run_id=context.run_id,
            goal=context.run_result.summary if hasattr(context.run_result, 'summary') else "Unknown Goal",
            reflection_id=report.id,
            summary=report.summary.strengths[0] if report.summary.strengths else "No summary",
            tags=(report.metrics.execution_score > 50 and "success" or "failure",),
            metadata={
                "score": report.metrics.overall_score,
                "outcome": "success" if report.metrics.overall_score > 50 else "failure"
            }
        )
        self._storage.store(entry)
        return entry

    def retrieve(self, entry_id: str) -> MemoryEntry:
        return self._storage.retrieve(entry_id)

    def search(self, query: MemoryQuery) -> MemorySearchResult:
        return self._storage.search(query)

    def history(self, limit: int = 10) -> tuple[MemoryEntry, ...]:
        query = MemoryQuery(limit=limit)
        return self.search(query).records

    def snapshot(self) -> MemorySnapshot:
        entries = self._storage.snapshot()
        stats = self._storage.statistics()
        return MemorySnapshot(entries=entries, statistics=stats)

    def statistics(self) -> MemoryStatistics:
        return self._storage.statistics()

    def get_relevant_experience(self, goal: str) -> EngineeringExperience | None:
        """Retrieves the most relevant past experience for a given goal."""
        query = MemoryQuery(goal_contains=goal.split()[0], limit=5)
        result = self.search(query)
        
        if not result.records:
            return None
            
        return self._experience_builder.build_from_entries(result.records)

    def delete(self, entry_id: str) -> bool:
        return self._storage.delete(entry_id)

    def clear(self) -> None:
        self._storage.clear()