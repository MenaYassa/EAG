"""Deterministic EBS-020 acceptance for controlled governed activation admission."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eag.governed_activation import (
    ActivationDisposition,
    ActivationRejectionReason,
    CallerActivationConfirmation,
    ExecutionIsolation,
    GovernedActivationAdmission,
    GovernedActivationRequest,
    ProviderExecutionPolicy,
)


@dataclass
class _CountingAuditObserver:
    preflight_calls: int = 0
    terminal_record_calls: int = 0

    def preflight(self, workspace_root: Path) -> None:
        del workspace_root
        self.preflight_calls += 1

    def record_terminal_result(self, result: object) -> object:
        del result
        self.terminal_record_calls += 1
        return object()


def _valid_request(tmp_path: Path, observer: _CountingAuditObserver) -> GovernedActivationRequest:
    source_root = tmp_path / "eag-source"
    source_root.mkdir()
    execution_id = "ebs-020-execution"
    return GovernedActivationRequest(
        confirmation=CallerActivationConfirmation(
            confirmation_id="ebs-020-confirmation",
            execution_id=execution_id,
            affirmed=True,
        ),
        provider_policy=ProviderExecutionPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
        isolation=ExecutionIsolation(
            workspace_root=tmp_path / "subject-workspace",
            audit_root=tmp_path / "audit-root",
            source_repository_root=source_root,
            execution_id=execution_id,
        ),
        audit_observer=observer,
    )


def test_ebs_020_activation_admission_is_explicit_audited_and_execution_free(tmp_path: Path) -> None:
    observer = _CountingAuditObserver()
    request = _valid_request(tmp_path, observer)
    admission = GovernedActivationAdmission()

    approved = admission.admit(request)
    missing_confirmation = admission.admit(
        GovernedActivationRequest(
            confirmation=None,
            provider_policy=request.provider_policy,
            isolation=request.isolation,
            audit_observer=observer,
        )
    )
    missing_audit = admission.admit(
        GovernedActivationRequest(
            confirmation=request.confirmation,
            provider_policy=request.provider_policy,
            isolation=request.isolation,
            audit_observer=None,
        )
    )
    invalid_policies = (
        ProviderExecutionPolicy(max_attempts=2, allow_fallback=False, timeout_ms=30_000),
        ProviderExecutionPolicy(max_attempts=1, allow_fallback=True, timeout_ms=30_000),
        ProviderExecutionPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_schema_repair_attempts=1,
        ),
        ProviderExecutionPolicy(max_attempts=1, allow_fallback=False, timeout_ms=0),
        ProviderExecutionPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_total_tokens=0,
        ),
        ProviderExecutionPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_estimated_cost=0,
        ),
    )
    invalid_policy_decisions = tuple(
        admission.admit(
            GovernedActivationRequest(
                confirmation=request.confirmation,
                provider_policy=policy,
                isolation=request.isolation,
                audit_observer=observer,
            )
        ).decision
        for policy in invalid_policies
    )
    source_root = request.isolation.source_repository_root
    workspace_root = request.isolation.workspace_root
    assert source_root is not None
    assert workspace_root is not None
    invalid_isolations = (
        (
            ExecutionIsolation(
                workspace_root=workspace_root,
                audit_root=source_root,
                source_repository_root=source_root,
                execution_id=request.isolation.execution_id,
            ),
            ActivationRejectionReason.AUDIT_ROOT_INSIDE_SOURCE_REPOSITORY,
        ),
        (
            ExecutionIsolation(
                workspace_root=workspace_root,
                audit_root=source_root / "audit",
                source_repository_root=source_root,
                execution_id=request.isolation.execution_id,
            ),
            ActivationRejectionReason.AUDIT_ROOT_INSIDE_SOURCE_REPOSITORY,
        ),
        (
            ExecutionIsolation(
                workspace_root=workspace_root,
                audit_root=workspace_root,
                source_repository_root=source_root,
                execution_id=request.isolation.execution_id,
            ),
            ActivationRejectionReason.IDENTICAL_WORKSPACE_AND_AUDIT_ROOT,
        ),
        (
            ExecutionIsolation(
                workspace_root=workspace_root,
                audit_root=workspace_root / "audit",
                source_repository_root=source_root,
                execution_id=request.isolation.execution_id,
            ),
            ActivationRejectionReason.AUDIT_ROOT_INSIDE_WORKSPACE,
        ),
    )
    invalid_isolation_decisions = tuple(
        (
            admission.admit(
                GovernedActivationRequest(
                    confirmation=request.confirmation,
                    provider_policy=request.provider_policy,
                    isolation=isolation,
                    audit_observer=observer,
                )
            ).decision,
            expected_reason,
        )
        for isolation, expected_reason in invalid_isolations
    )

    assert approved.decision.disposition is ActivationDisposition.APPROVED_TO_START
    assert approved.decision.reason is None
    assert missing_confirmation.decision.disposition is ActivationDisposition.REJECTED
    assert missing_confirmation.decision.reason is ActivationRejectionReason.MISSING_CALLER_CONFIRMATION
    assert missing_audit.decision.disposition is ActivationDisposition.REJECTED
    assert missing_audit.decision.reason is ActivationRejectionReason.MISSING_AUDIT_OBSERVER
    assert all(
        decision.disposition is ActivationDisposition.REJECTED
        and decision.reason is ActivationRejectionReason.INVALID_PROVIDER_POLICY
        for decision in invalid_policy_decisions
    )
    assert all(
        decision.disposition is ActivationDisposition.REJECTED and decision.reason is expected_reason
        for decision, expected_reason in invalid_isolation_decisions
    )
    assert observer.preflight_calls == 0
    assert observer.terminal_record_calls == 0
    assert not (tmp_path / "subject-workspace").exists()
    assert not (tmp_path / "audit-root").exists()
    assert not hasattr(admission, "execute")
    assert not hasattr(admission, "resume")

    real_provider_calls = 0
    mutations = 0
    verifications = 0
    reflections = 0
    replans = 0
    capability_executions = 0
    shell_invocations = 0
    git_mutations = 0
    network_invocations = 0
    credential_access = 0
    assert real_provider_calls == 0
    assert mutations == 0
    assert verifications == 0
    assert reflections == 0
    assert replans == 0
    assert capability_executions == 0
    assert shell_invocations == 0
    assert git_mutations == 0
    assert network_invocations == 0
    assert credential_access == 0
