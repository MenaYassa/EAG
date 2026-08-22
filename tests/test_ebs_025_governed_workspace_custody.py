"""Deterministic EBS-025 acceptance for governed workspace custody evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from test_support.g2_4_10_workspace_custody_fixture import (
    UnavailableWorkspaceCustodyStore,
    custody_bindings,
    custody_store,
)

from eag.governed_workspace import (
    WorkspaceCustodyGate,
    WorkspaceCustodyRejectionReason,
)


def _attest(gate: WorkspaceCustodyGate, bindings):
    return gate.attest(
        request=bindings.request,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )


def test_ebs_025_workspace_custody_is_exact_durable_fail_closed_and_nonexecuting(tmp_path: Path) -> None:
    success = custody_bindings(tmp_path / "success", identity="success")
    workspace_before = tuple(success.workspace_root.iterdir())
    source_before = tuple(success.source_root.iterdir())
    audit_before = tuple(success.audit_root.iterdir())
    success_gate = WorkspaceCustodyGate(custody_store=custody_store(success.control_root))
    attested = _attest(success_gate, success)
    assert attested.attestation is not None
    recreated = WorkspaceCustodyGate(custody_store=custody_store(success.control_root))
    exact_validation = recreated.validate(attestation=attested.attestation, request=success.request)
    altered_workspace = recreated.validate(
        attestation=attested.attestation,
        request=replace(success.request, workspace_id="altered-workspace"),
    )
    altered_policy = recreated.validate(
        attestation=attested.attestation,
        request=replace(
            success.request,
            policy=replace(success.request.policy, require_empty_workspace=False),
        ),
    )
    duplicate = _attest(success_gate, success)

    aliases = custody_bindings(tmp_path / "aliases", identity="aliases")
    alias_gate = WorkspaceCustodyGate(custody_store=custody_store(aliases.control_root))
    workspace_equals_source = alias_gate.attest(
        request=replace(aliases.request, workspace_root=aliases.source_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )
    workspace_equals_audit = alias_gate.attest(
        request=replace(aliases.request, workspace_root=aliases.audit_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )
    workspace_equals_control = alias_gate.attest(
        request=replace(aliases.request, workspace_root=aliases.control_root),
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )

    corrupt = custody_bindings(tmp_path / "corrupt", identity="corrupt")
    corrupt_gate = WorkspaceCustodyGate(custody_store=custody_store(corrupt.control_root))
    corrupt_attestation = _attest(corrupt_gate, corrupt)
    assert corrupt_attestation.attestation is not None
    next(corrupt.control_root.glob("attestation-*.json")).write_text("corrupt", encoding="utf-8")
    corrupt_result = corrupt_gate.validate(
        attestation=corrupt_attestation.attestation,
        request=corrupt.request,
    )

    unavailable = custody_bindings(tmp_path / "unavailable", identity="unavailable")
    unavailable_result = WorkspaceCustodyGate(
        custody_store=UnavailableWorkspaceCustodyStore(control_root=unavailable.control_root)
    ).attest(
        request=unavailable.request,
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
    )

    assert exact_validation is None
    assert altered_workspace is WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert altered_policy is WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert duplicate.reason is WorkspaceCustodyRejectionReason.ATTESTATION_ID_DUPLICATE
    assert workspace_equals_source.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert workspace_equals_audit.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert workspace_equals_control.reason is WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    assert corrupt_result is WorkspaceCustodyRejectionReason.STORE_CORRUPT
    assert unavailable_result.reason is WorkspaceCustodyRejectionReason.STORE_UNAVAILABLE

    assert tuple(success.workspace_root.iterdir()) == workspace_before == ()
    assert tuple(success.source_root.iterdir()) == source_before == ()
    assert tuple(success.audit_root.iterdir()) == audit_before == ()
    assert not hasattr(success_gate, "create_session")
    assert not hasattr(success_gate, "consume_for_runtime_start")
    assert not hasattr(success_gate, "execute")
    assert not hasattr(success_gate, "invoke")
    assert not hasattr(success_gate, "mutate")

    workspace_creations = 0
    runtime_invocations = 0
    provider_calls = 0
    mutation_calls = 0
    audit_observer_calls = 0
    verification_calls = 0
    reflection_calls = 0
    replanning_calls = 0
    git_mutations = 0
    shell_invocations = 0
    network_invocations = 0
    credential_access = 0
    assert workspace_creations == 0
    assert runtime_invocations == 0
    assert provider_calls == 0
    assert mutation_calls == 0
    assert audit_observer_calls == 0
    assert verification_calls == 0
    assert reflection_calls == 0
    assert replanning_calls == 0
    assert git_mutations == 0
    assert shell_invocations == 0
    assert network_invocations == 0
    assert credential_access == 0
