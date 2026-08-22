"""Read-only lookup services for durable governed execution audit envelopes."""

from __future__ import annotations

from eag.governed_audit.models import (
    AuditDisposition,
    GovernedExecutionAuditEnvelope,
    GovernedExecutionInterruptionRecord,
    reject_interrupted_continuation,
)
from eag.governed_audit.store import GovernedExecutionAuditStore


class GovernedExecutionAuditQuery:
    """Read-only retrieval facade; it cannot resume, retry, or execute a record."""

    def __init__(self, store: GovernedExecutionAuditStore) -> None:
        self._store = store

    def get(self, execution_id: str) -> GovernedExecutionAuditEnvelope | None:
        return self._store.get(execution_id)

    def list(self) -> tuple[GovernedExecutionAuditEnvelope, ...]:
        return self._store.list()

    def find_by_evidence(self, reference_id: str) -> tuple[GovernedExecutionAuditEnvelope, ...]:
        return self._store.find_by_evidence(reference_id)

    def interruption(self, execution_id: str) -> GovernedExecutionInterruptionRecord | None:
        envelope = self.get(execution_id)
        if envelope is None or envelope.disposition is not AuditDisposition.INTERRUPTED:
            return None
        return GovernedExecutionInterruptionRecord(envelope=envelope)

    def reject_continuation(self, record: GovernedExecutionInterruptionRecord) -> None:
        """Demonstrate that inspected interruptions cannot become execution inputs."""
        reject_interrupted_continuation(record)


__all__ = ["GovernedExecutionAuditQuery"]
