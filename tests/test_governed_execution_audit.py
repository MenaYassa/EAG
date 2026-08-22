"""Deterministic contracts for the G2.4.5 read-only governed audit boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_support.g2_4_4_runtime_fixture import governed_request, runtime_fixture

from eag.events import EventBus
from eag.governed_audit import (
    AuditCollisionError,
    AuditIntegrityError,
    AuditPersistenceRequiredError,
    FileGovernedExecutionAuditStore,
    GovernedExecutionAuditQuery,
    GovernedExecutionAuditRecorder,
    InterruptedExecutionRejected,
)
from eag.governed_execution import (
    ExecutionBudget,
    ExecutionEvidenceKind,
    ExecutionEvidenceRef,
    GovernedExecutionContext,
    GovernedExecutionState,
    GovernedExecutionStateMachine,
    GovernedExecutionStopReason,
)


def _context(*, terminal: bool, goal: str = "audit fixture") -> GovernedExecutionContext:
    machine = GovernedExecutionStateMachine(EventBus())
    context = GovernedExecutionContext(
        execution_id="audit-execution",
        run_id="audit-run",
        goal=goal,
        budget=ExecutionBudget(max_iterations=1, max_mutations=1, max_verifications=1),
    )
    context = machine.transition_or_raise(context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    if not terminal:
        return context
    context = machine.transition_or_raise(
        context,
        GovernedExecutionState.PLANNING,
        evidence=(
            ExecutionEvidenceRef(
                kind=ExecutionEvidenceKind.PLAN,
                reference_id="plan-1",
                metadata={"raw_content": "must-not-persist"},
            ),
        ),
    )
    context = machine.transition_or_raise(context, GovernedExecutionState.DECIDING)
    context = machine.transition_or_raise(context, GovernedExecutionState.PROPOSING)
    context = machine.transition_or_raise(context, GovernedExecutionState.AUTHORIZING)
    context = machine.transition_or_raise(context, GovernedExecutionState.MUTATING)
    context = machine.transition_or_raise(context, GovernedExecutionState.VERIFYING)
    return machine.transition_or_raise(
        context,
        GovernedExecutionState.COMPLETED,
        stop_reason=GovernedExecutionStopReason.SUCCESS,
    )


def test_audit_envelope_persists_redacted_immutable_terminal_history(tmp_path: Path) -> None:
    store = FileGovernedExecutionAuditStore(tmp_path / "audit")
    recorder = GovernedExecutionAuditRecorder(store)
    context = _context(terminal=True)

    persisted = recorder.record_context(context)
    reloaded = FileGovernedExecutionAuditStore(tmp_path / "audit").get(context.execution_id)

    assert persisted.is_terminal is True
    assert reloaded == persisted
    assert reloaded is not None
    assert reloaded.history[-1].to_state is GovernedExecutionState.COMPLETED
    assert reloaded.budget == context.budget
    assert len(reloaded.evidence) == len(context.evidence)
    raw = next((tmp_path / "audit").glob("*.json")).read_text(encoding="utf-8")
    assert "must-not-persist" not in raw
    with pytest.raises(AttributeError):
        persisted.execution_id = "mutated"  # type: ignore[misc]


def test_audit_store_rejects_collision_and_retains_original_record(tmp_path: Path) -> None:
    store = FileGovernedExecutionAuditStore(tmp_path / "audit")
    recorder = GovernedExecutionAuditRecorder(store)
    original = recorder.record_context(_context(terminal=True, goal="original"))
    conflicting = __import__("eag.governed_audit", fromlist=["GovernedExecutionAuditEnvelope"])
    alternative = conflicting.GovernedExecutionAuditEnvelope.from_context(
        _context(terminal=True, goal="different")
    )

    with pytest.raises(AuditCollisionError):
        store.append(alternative)

    assert store.get(original.execution_id) == original


def test_tampered_audit_record_fails_closed_on_load(tmp_path: Path) -> None:
    store = FileGovernedExecutionAuditStore(tmp_path / "audit")
    envelope = GovernedExecutionAuditRecorder(store).record_context(_context(terminal=True))
    path = next((tmp_path / "audit").glob("*.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["record_digest"] = "0" * 64
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    with pytest.raises(AuditIntegrityError):
        FileGovernedExecutionAuditStore(tmp_path / "audit").get(envelope.execution_id)


def test_interruption_is_queryable_and_cannot_become_execution_continuation(tmp_path: Path) -> None:
    store = FileGovernedExecutionAuditStore(tmp_path / "audit")
    recorder = GovernedExecutionAuditRecorder(store)
    context = _context(terminal=False)

    persisted = recorder.record_interruption(context)
    query = GovernedExecutionAuditQuery(FileGovernedExecutionAuditStore(tmp_path / "audit"))
    interruption = query.interruption(context.execution_id)

    assert persisted.is_terminal is False
    assert interruption is not None
    assert interruption.envelope == persisted
    with pytest.raises(InterruptedExecutionRejected):
        query.reject_continuation(interruption)
    assert query.get(context.execution_id) == persisted


class _TerminalAuditFailure:
    def preflight(self, workspace_root: Path) -> None:
        del workspace_root

    def record_terminal_result(self, result: object) -> None:
        del result
        raise RuntimeError("deterministic terminal audit write failure")


def test_required_terminal_audit_failure_is_explicit_and_never_retries_execution(tmp_path: Path) -> None:
    (tmp_path / "article.py").write_text("first\n", encoding="utf-8")
    runtime, gateway, context_factory, request_factory, verification_factory = runtime_fixture(
        tmp_path,
        contents=("second\n", "third\n"),
        fail_first_only=True,
        audit_observer=_TerminalAuditFailure(),
    )

    with pytest.raises(AuditPersistenceRequiredError):
        runtime.execute(governed_request(tmp_path))

    assert gateway.calls == 2
    assert context_factory.calls == 2
    assert request_factory.calls == 2
    assert verification_factory.calls == 2
    assert (tmp_path / "article.py").read_text(encoding="utf-8") == "third\n"
