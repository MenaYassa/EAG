"""Reflection runtime for EAG."""

from eag.events import EventBus
from eag.reflection.errors import ReflectionError
from eag.reflection.events import ReflectionCompleted, ReflectionFailed, ReflectionStarted
from eag.reflection.models import ReflectionContext, ReflectionReport
from eag.reflection.protocol import ReflectionEngine


class ReflectionRuntime:
    """Orchestrates the reflection process."""

    def __init__(self, engine: ReflectionEngine, event_bus: EventBus) -> None:
        self._engine = engine
        self._event_bus = event_bus

    def reflect(self, context: ReflectionContext) -> ReflectionReport:
        """Runs the reflection engine and produces a report."""
        self._event_bus.publish(ReflectionStarted(run_id=context.run_id))

        try:
            report = self._engine.reflect(context)
            self._event_bus.publish(ReflectionCompleted(run_id=context.run_id, report_id=report.id))
            return report
        except Exception as e:
            self._event_bus.publish(ReflectionFailed(run_id=context.run_id, error=str(e)))
            raise ReflectionError(f"Reflection failed: {e}") from e
