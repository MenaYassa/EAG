"""Deterministic EBS-019 acceptance for the G2.4.5 durable governed audit boundary."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_support.g2_4_4_runtime_fixture import governed_request, runtime_fixture

from eag.events import EventBus
from eag.governed_audit import (
    AuditCollisionError,
    AuditEvidenceReference,
    AuditIntegrityError,
    AuditPersistenceRequiredError,
    AuditTransitionRecord,
    FileGovernedExecutionAuditStore,
    GovernedExecutionAuditEnvelope,
    GovernedExecutionAuditQuery,
    GovernedExecutionAuditRecorder,
    InterruptedExecutionRejected,
)
from eag.governed_execution import (
    ExecutionBudget,
    ExecutionEvidenceKind,
    GovernedExecutionContext,
    GovernedExecutionState,
    GovernedExecutionStateMachine,
)


class _PreflightFailure:
    def preflight(self, workspace_root: Path) -> None:
        del workspace_root
        raise RuntimeError("deterministic audit store unavailable")

    def record_terminal_result(self, result: object):
        raise AssertionError(f"unexpected terminal result recording: {result!r}")


def _expected_audit_history(context: GovernedExecutionContext) -> tuple[AuditTransitionRecord, ...]:
    """Project the authoritative ledger into its intentional redacted audit representation."""
    return tuple(
        AuditTransitionRecord(
            sequence=record.sequence,
            iteration=record.iteration,
            from_state=record.from_state,
            to_state=record.to_state,
            occurred_at=record.occurred_at,
            reason=record.reason,
            evidence=tuple(
                AuditEvidenceReference(
                    kind=evidence.kind,
                    reference_id=evidence.reference_id,
                    digest=evidence.digest,
                )
                for evidence in record.evidence
            ),
        )
        for record in context.history
    )


def _audit_ids_by_iteration(
    loaded,
    kind: ExecutionEvidenceKind,
) -> tuple[str, str]:
    values = tuple(
        evidence.reference_id
        for iteration in (1, 2)
        for record in loaded.history
        if record.iteration == iteration
        for evidence in record.evidence
        if evidence.kind is kind
    )
    assert len(values) == 2
    return values


def _audit_runtime(subject_workspace: Path, audit_root: Path):
    recorder = GovernedExecutionAuditRecorder(FileGovernedExecutionAuditStore(audit_root))
    runtime, gateway, context_factory, request_factory, verification_factory = runtime_fixture(
        subject_workspace,
        contents=("second\n", "third\n"),
        fail_first_only=True,
        audit_observer=recorder,
    )
    return runtime, gateway, context_factory, request_factory, verification_factory


def test_ebs_019_durable_terminal_audit_reloads_and_queries_without_raw_content(tmp_path: Path) -> None:
    subject_workspace = tmp_path / "subject"
    audit_root = tmp_path / "audit"
    subject_workspace.mkdir()
    (subject_workspace / "article.py").write_text("first\n", encoding="utf-8")
    runtime, gateway, context_factory, request_factory, verification_factory = _audit_runtime(
        subject_workspace,
        audit_root,
    )

    request_ids: list[str] = []
    original_build = request_factory.build

    def capture_request_identity(*args, **kwargs):
        decision_request = original_build(*args, **kwargs)
        request_ids.append(decision_request.request_id)
        return decision_request

    request_factory.build = capture_request_identity  # type: ignore[method-assign]
    result = runtime.execute(governed_request(subject_workspace))
    fresh_query = GovernedExecutionAuditQuery(FileGovernedExecutionAuditStore(audit_root))
    loaded = fresh_query.get(result.context.execution_id)

    assert result.context.state is GovernedExecutionState.COMPLETED
    assert result.context.iteration == 2
    assert result.context.budget.iterations_used == 2
    assert result.context.budget.mutations_used == 2
    assert result.context.budget.verifications_used == 2
    assert gateway.calls == 2
    assert context_factory.calls == 2
    assert request_factory.calls == 2
    assert verification_factory.calls == 2
    assert loaded is not None
    assert loaded.is_terminal is True
    expected_history = _expected_audit_history(result.context)
    assert loaded.history == expected_history, "AUDIT_HISTORY_EXACT_MATCH=FAIL"
    assert len(loaded.history) == len(result.context.history)
    for observed, authoritative in zip(loaded.history, result.context.history, strict=True):
        assert observed.sequence == authoritative.sequence
        assert observed.iteration == authoritative.iteration
        assert observed.from_state is authoritative.from_state
        assert observed.to_state is authoritative.to_state
        assert observed.occurred_at == authoritative.occurred_at
        assert observed.reason is authoritative.reason
        assert observed.evidence == tuple(
            AuditEvidenceReference(
                kind=evidence.kind,
                reference_id=evidence.reference_id,
                digest=evidence.digest,
            )
            for evidence in authoritative.evidence
        )
    assert loaded.evidence == tuple(
        evidence for record in expected_history for evidence in record.evidence
    )
    assert loaded.iteration == result.context.iteration
    assert loaded.budget == result.context.budget
    assert len(loaded.evidence) == len(result.context.evidence)

    assert len(result.iteration_artifacts) == 2
    assert result.iteration_artifacts[0].artifact_id != result.iteration_artifacts[1].artifact_id
    assert result.iteration_artifacts[0].context_fingerprint != result.iteration_artifacts[1].context_fingerprint
    assert len(request_ids) == 2
    assert request_ids[0] != request_ids[1]
    plan_ids = _audit_ids_by_iteration(loaded, ExecutionEvidenceKind.PLAN)
    assert plan_ids == tuple(item.artifact_id for item in result.iteration_artifacts)
    for kind in (
        ExecutionEvidenceKind.DECISION,
        ExecutionEvidenceKind.PROPOSAL,
        ExecutionEvidenceKind.AUTHORIZATION,
        ExecutionEvidenceKind.MUTATION_RECEIPT,
        ExecutionEvidenceKind.VERIFICATION,
    ):
        first_identity, second_identity = _audit_ids_by_iteration(loaded, kind)
        assert first_identity != second_identity
    receipt_reference = next(
        item.reference_id
        for item in loaded.evidence
        if item.kind is ExecutionEvidenceKind.MUTATION_RECEIPT
    )
    verification_reference = next(
        item.reference_id
        for item in loaded.evidence
        if item.kind is ExecutionEvidenceKind.VERIFICATION
    )
    assert fresh_query.find_by_evidence(receipt_reference) == (loaded,)
    assert fresh_query.find_by_evidence(verification_reference) == (loaded,)
    raw_record = next(audit_root.glob("*.json")).read_text(encoding="utf-8")
    assert "first\\n" not in raw_record
    assert "second\\n" not in raw_record
    assert "third\\n" not in raw_record
    assert "Controlled fixture mutation" not in raw_record
    assert (subject_workspace / "article.py").read_text(encoding="utf-8") == "third\n"


def test_ebs_019_tamper_and_collision_fail_closed_without_changing_original(tmp_path: Path) -> None:
    subject_workspace = tmp_path / "subject"
    audit_root = tmp_path / "audit"
    subject_workspace.mkdir()
    (subject_workspace / "article.py").write_text("first\n", encoding="utf-8")
    runtime, *_ = _audit_runtime(subject_workspace, audit_root)
    result = runtime.execute(governed_request(subject_workspace))
    store = FileGovernedExecutionAuditStore(audit_root)
    original = store.get(result.context.execution_id)
    assert original is not None

    alternative = GovernedExecutionAuditEnvelope.from_context(
        replace(result.context, run_id="different-audit-run")
    )
    with pytest.raises(AuditCollisionError):
        store.append(alternative)
    assert store.get(result.context.execution_id) == original

    record_path = next(audit_root.glob("*.json"))
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["history"][0]["sequence"] = 99
    record_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(AuditIntegrityError):
        FileGovernedExecutionAuditStore(audit_root).get(result.context.execution_id)
    assert runtime is not None


def test_ebs_019_audit_preflight_failure_prevents_execution_before_provider_or_mutation(tmp_path: Path) -> None:
    (tmp_path / "article.py").write_text("first\n", encoding="utf-8")
    runtime, gateway, context_factory, request_factory, verification_factory = runtime_fixture(
        tmp_path,
        contents=("second\n", "third\n"),
        fail_first_only=True,
        audit_observer=_PreflightFailure(),
    )

    with pytest.raises(AuditPersistenceRequiredError):
        runtime.execute(governed_request(tmp_path))

    assert gateway.calls == 0
    assert context_factory.calls == 0
    assert request_factory.calls == 0
    assert verification_factory.calls == 0
    assert (tmp_path / "article.py").read_text(encoding="utf-8") == "first\n"


def test_ebs_019_interruption_is_read_only_and_repeated_terminal_queries_are_idempotent(tmp_path: Path) -> None:
    audit_root = tmp_path / "audit"
    store = FileGovernedExecutionAuditStore(audit_root)
    recorder = GovernedExecutionAuditRecorder(store)
    machine = GovernedExecutionStateMachine(EventBus())
    context = GovernedExecutionContext(
        execution_id="interrupted-execution",
        run_id="interrupted-run",
        goal="Observe but do not resume.",
        budget=ExecutionBudget(max_iterations=1, max_mutations=1, max_verifications=1),
    )
    context = machine.transition_or_raise(context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    interrupted = recorder.record_interruption(context)
    query = GovernedExecutionAuditQuery(FileGovernedExecutionAuditStore(audit_root))

    inspected = query.interruption(interrupted.execution_id)
    assert inspected is not None
    with pytest.raises(InterruptedExecutionRejected):
        query.reject_continuation(inspected)
    assert query.get(interrupted.execution_id) == interrupted

    terminal_context = machine.transition_or_raise(context, GovernedExecutionState.PLANNING)
    terminal_context = machine.transition_or_raise(terminal_context, GovernedExecutionState.DECIDING)
    terminal_context = machine.transition_or_raise(terminal_context, GovernedExecutionState.PROPOSING)
    terminal_context = machine.transition_or_raise(terminal_context, GovernedExecutionState.AUTHORIZING)
    terminal_context = machine.transition_or_raise(terminal_context, GovernedExecutionState.MUTATING)
    terminal_context = machine.transition_or_raise(terminal_context, GovernedExecutionState.VERIFYING)
    terminal_context = machine.transition_or_raise(
        terminal_context,
        GovernedExecutionState.FAILED,
        stop_reason=__import__("eag.governed_execution", fromlist=["GovernedExecutionStopReason"])
        .GovernedExecutionStopReason.VERIFICATION_FAILED,
    )
    terminal = recorder.record_context(replace(terminal_context, execution_id="terminal-query"))
    terminal_path = next(path for path in audit_root.glob("*.json") if path.read_text(encoding="utf-8").find("terminal-query") >= 0)
    before = terminal_path.read_bytes()
    assert query.get(terminal.execution_id) == terminal
    assert query.get(terminal.execution_id) == terminal
    assert terminal_path.read_bytes() == before
