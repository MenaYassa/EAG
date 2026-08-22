"""Observer-only conversion of authoritative governed contexts into audit envelopes."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from eag.governed_audit.models import (
    AuditDisposition,
    GovernedAuditError,
    GovernedExecutionAuditEnvelope,
)
from eag.governed_audit.store import FileGovernedExecutionAuditStore, GovernedExecutionAuditStore
from eag.governed_execution import GovernedExecutionContext


class AuditPersistenceRequiredError(GovernedAuditError):
    """Raised when required audit observation cannot be prepared or persisted."""


class GovernedExecutionAuditObserver(Protocol):
    """Optional runtime observer with no authority to alter execution lifecycle."""

    def preflight(self, workspace_root: Path) -> None: ...

    def record_terminal_result(self, result: object) -> GovernedExecutionAuditEnvelope: ...


class GovernedExecutionAuditRecorder:
    """Validate, redact, and persist already-authoritative execution observations."""

    def __init__(self, store: GovernedExecutionAuditStore) -> None:
        self._store = store

    def preflight(self, workspace_root: Path) -> None:
        """Reject unsafe audit-root placement before observable execution starts."""
        if not isinstance(workspace_root, Path):
            raise TypeError("workspace_root must be a Path")
        if isinstance(self._store, FileGovernedExecutionAuditStore):
            subject_root = workspace_root.resolve()
            if self._store.audit_root == subject_root or self._store.audit_root.is_relative_to(subject_root):
                raise AuditPersistenceRequiredError(
                    "audit root must be separate from the governed subject workspace"
                )

    def record_context(self, context: GovernedExecutionContext) -> GovernedExecutionAuditEnvelope:
        """Persist a terminal or interruption observation without changing the context."""
        if not isinstance(context, GovernedExecutionContext):
            raise TypeError("context must be a GovernedExecutionContext")
        return self._store.append(GovernedExecutionAuditEnvelope.from_context(context))

    def record_terminal_result(self, result: object) -> GovernedExecutionAuditEnvelope:
        """Persist one terminal result after validating its authoritative context relation."""
        context = getattr(result, "context", None)
        if not isinstance(context, GovernedExecutionContext):
            raise AuditPersistenceRequiredError("audit result must expose a GovernedExecutionContext")
        if not context.state.is_terminal:
            raise AuditPersistenceRequiredError("only terminal governed results can be recorded as terminal")
        succeeded = getattr(result, "succeeded", None)
        if not isinstance(succeeded, bool):
            raise AuditPersistenceRequiredError("audit result must expose a boolean succeeded property")
        if succeeded != (context.state.value == "completed"):
            raise AuditPersistenceRequiredError("terminal result success is inconsistent with context state")
        return self.record_context(context)

    def record_interruption(
        self,
        context: GovernedExecutionContext,
    ) -> GovernedExecutionAuditEnvelope:
        """Persist an observed nonterminal context as read-only interruption evidence."""
        if not isinstance(context, GovernedExecutionContext):
            raise TypeError("context must be a GovernedExecutionContext")
        if context.state.is_terminal:
            raise AuditPersistenceRequiredError("terminal contexts cannot be recorded as interruptions")
        envelope = GovernedExecutionAuditEnvelope.from_context(
            context,
            disposition=AuditDisposition.INTERRUPTED,
        )
        return self._store.append(envelope)


__all__ = [
    "AuditPersistenceRequiredError",
    "GovernedExecutionAuditObserver",
    "GovernedExecutionAuditRecorder",
]
