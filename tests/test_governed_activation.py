"""Deterministic contracts for G2.4.6.1 controlled governed activation admission."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

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
class _AuditObserver:
    preflight_calls: int = 0
    terminal_record_calls: int = 0

    def preflight(self, workspace_root: Path) -> None:
        del workspace_root
        self.preflight_calls += 1

    def record_terminal_result(self, result: object) -> object:
        del result
        self.terminal_record_calls += 1
        return object()


def _request(tmp_path: Path, **overrides: object) -> GovernedActivationRequest:
    source_root = tmp_path / "source"
    source_root.mkdir(exist_ok=True)
    execution_id = "activation-execution"
    values: dict[str, object] = {
        "confirmation": CallerActivationConfirmation(
            confirmation_id="caller-confirmation",
            execution_id=execution_id,
            affirmed=True,
        ),
        "provider_policy": ProviderExecutionPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
        ),
        "isolation": ExecutionIsolation(
            workspace_root=tmp_path / "workspace",
            audit_root=tmp_path / "audit",
            source_repository_root=source_root,
            execution_id=execution_id,
        ),
        "audit_observer": _AuditObserver(),
    }
    values.update(overrides)
    return GovernedActivationRequest(**values)  # type: ignore[arg-type]


def test_complete_explicit_activation_is_approved_without_operational_effects(tmp_path: Path) -> None:
    request = _request(tmp_path)
    observer = request.audit_observer

    receipt = GovernedActivationAdmission().admit(request)

    assert receipt.decision.disposition is ActivationDisposition.APPROVED_TO_START
    assert receipt.decision.reason is None
    assert receipt.decision.execution_id == "activation-execution"
    assert len(receipt.policy_digest) == 64
    assert isinstance(observer, _AuditObserver)
    assert observer.preflight_calls == 0
    assert observer.terminal_record_calls == 0
    assert not (tmp_path / "workspace").exists()
    assert not (tmp_path / "audit").exists()


@pytest.mark.parametrize(
    ("override", "expected_reason"),
    [
        ("confirmation", ActivationRejectionReason.MISSING_CALLER_CONFIRMATION),
        ("audit_observer", ActivationRejectionReason.MISSING_AUDIT_OBSERVER),
        ("provider_policy", ActivationRejectionReason.MISSING_PROVIDER_POLICY),
    ],
)
def test_missing_required_admission_binding_is_rejected(
    tmp_path: Path,
    override: str,
    expected_reason: ActivationRejectionReason,
) -> None:
    request = _request(tmp_path, **{override: None})

    receipt = GovernedActivationAdmission().admit(request)

    assert receipt.decision.disposition is ActivationDisposition.REJECTED
    assert receipt.decision.reason is expected_reason


def test_invalid_provider_policy_is_rejected_before_observer_or_workspace_effects(tmp_path: Path) -> None:
    observer = _AuditObserver()
    request = _request(
        tmp_path,
        audit_observer=observer,
        provider_policy=ProviderExecutionPolicy(
            max_attempts=2,
            allow_fallback=False,
            timeout_ms=30_000,
        ),
    )

    receipt = GovernedActivationAdmission().admit(request)

    assert receipt.decision.reason is ActivationRejectionReason.INVALID_PROVIDER_POLICY
    assert observer.preflight_calls == 0
    assert observer.terminal_record_calls == 0
    assert not (tmp_path / "workspace").exists()


def test_missing_isolation_root_is_rejected(tmp_path: Path) -> None:
    request = _request(
        tmp_path,
        isolation=ExecutionIsolation(
            workspace_root=None,
            audit_root=tmp_path / "audit",
            source_repository_root=tmp_path / "source",
            execution_id="activation-execution",
        ),
    )

    receipt = GovernedActivationAdmission().admit(request)

    assert receipt.decision.reason is ActivationRejectionReason.MISSING_ISOLATION_ROOT


def test_identical_workspace_and_audit_roots_are_rejected(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    request = _request(
        tmp_path,
        isolation=ExecutionIsolation(
            workspace_root=shared,
            audit_root=shared,
            source_repository_root=tmp_path / "source",
            execution_id="activation-execution",
        ),
    )

    receipt = GovernedActivationAdmission().admit(request)

    assert receipt.decision.reason is ActivationRejectionReason.IDENTICAL_WORKSPACE_AND_AUDIT_ROOT


def test_source_repository_workspace_selection_and_empty_execution_identity_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_selected = _request(
        tmp_path,
        isolation=ExecutionIsolation(
            workspace_root=source,
            audit_root=tmp_path / "audit",
            source_repository_root=source,
            execution_id="activation-execution",
        ),
    )
    empty_identity = _request(
        tmp_path,
        isolation=ExecutionIsolation(
            workspace_root=tmp_path / "workspace",
            audit_root=tmp_path / "audit",
            source_repository_root=source,
            execution_id="",
        ),
    )

    assert (
        GovernedActivationAdmission().admit(source_selected).decision.reason
        is ActivationRejectionReason.SOURCE_WORKSPACE_SELECTED
    )
    assert (
        GovernedActivationAdmission().admit(empty_identity).decision.reason
        is ActivationRejectionReason.EMPTY_EXECUTION_ID
    )


def test_admission_has_no_execution_authority_or_runtime_handle(tmp_path: Path) -> None:
    admission = GovernedActivationAdmission()
    receipt = admission.admit(_request(tmp_path))

    assert receipt.decision.disposition is ActivationDisposition.APPROVED_TO_START
    assert not hasattr(admission, "execute")
    assert not hasattr(admission, "resume")
    assert not hasattr(admission, "mutate")
    assert not hasattr(admission, "verify")
    assert not hasattr(admission, "authorize")
