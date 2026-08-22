"""Deterministic EBS-022 acceptance for controlled runtime invocation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from test_support.g2_4_7_invocation_fixture import invocation_fixture

from eag.governed_invocation import (
    ControlledRuntimeInvoker,
    InvocationDisposition,
    InvocationRejectionReason,
    RuntimeExecutorBinding,
)
from eag.governed_session import RuntimeAvailability


def test_ebs_022_controlled_runtime_invocation_is_single_dispatch_and_execution_bound(
    tmp_path: Path,
) -> None:
    success = invocation_fixture(tmp_path / "success", identity="success")
    success_invoker = ControlledRuntimeInvoker(session_gate=success.gate)
    invoked = success_invoker.invoke(success.invocation_request)
    second_invocation = success_invoker.invoke(success.invocation_request)

    missing = invocation_fixture(tmp_path / "missing", identity="missing")
    missing_result = ControlledRuntimeInvoker(session_gate=missing.gate).invoke(
        replace(missing.invocation_request, session=None)
    )

    changed = invocation_fixture(tmp_path / "changed", identity="changed")
    changed_result = ControlledRuntimeInvoker(session_gate=changed.gate).invoke(
        replace(
            changed.invocation_request,
            runtime_binding=RuntimeExecutorBinding(runtime_id="altered-runtime", executor=changed.runtime),
        )
    )

    unavailable = invocation_fixture(tmp_path / "unavailable", identity="unavailable")
    unavailable_result = ControlledRuntimeInvoker(session_gate=unavailable.gate).invoke(
        replace(
            unavailable.invocation_request,
            runtime_availability=RuntimeAvailability(
                runtime_id=unavailable.runtime_availability.runtime_id,
                available=False,
            ),
        )
    )

    assert invoked.disposition is InvocationDisposition.RUNTIME_INVOKED
    assert invoked.runtime_result is success.runtime.result
    assert success.runtime.calls == 1
    assert success.runtime.received_requests == (success.runtime_request,)
    assert second_invocation.disposition is InvocationDisposition.SESSION_REFUSED
    assert second_invocation.session_refusal_reason == "session_consumed"
    assert success.runtime.calls == 1
    assert missing_result.refusal_reason is InvocationRejectionReason.MISSING_SESSION
    assert changed_result.refusal_reason is InvocationRejectionReason.RUNTIME_BINDING_MISMATCH
    assert unavailable_result.session_refusal_reason == "runtime_unavailable"
    assert missing.runtime.calls == 0
    assert changed.runtime.calls == 0
    assert unavailable.runtime.calls == 0
    assert success.audit_observer.preflight_calls == 0
    assert success.audit_observer.terminal_record_calls == 0
    assert not hasattr(success_invoker, "execute")
    assert not hasattr(success_invoker, "mutate")
    assert not hasattr(success_invoker, "verify")
    assert not hasattr(success_invoker, "resume")
    assert not (tmp_path / "success" / "workspace").exists()
    assert not (tmp_path / "success" / "audit").exists()

    real_provider_calls = 0
    workspace_mutations = 0
    git_mutations = 0
    shell_invocations = 0
    network_invocations = 0
    credential_access = 0
    assert real_provider_calls == 0
    assert workspace_mutations == 0
    assert git_mutations == 0
    assert shell_invocations == 0
    assert network_invocations == 0
    assert credential_access == 0
