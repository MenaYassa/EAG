"""Deterministic contracts for the G2.4.7.1 controlled runtime invocation boundary."""

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


def test_valid_session_dispatches_the_exact_runtime_request_once(tmp_path: Path) -> None:
    fixture = invocation_fixture(tmp_path, identity="success")
    invoker = ControlledRuntimeInvoker(session_gate=fixture.gate)

    result = invoker.invoke(fixture.invocation_request)
    replay = invoker.invoke(fixture.invocation_request)

    assert result.disposition is InvocationDisposition.RUNTIME_INVOKED
    assert result.runtime_result is fixture.runtime.result
    assert fixture.runtime.calls == 1
    assert fixture.runtime.received_requests == (fixture.runtime_request,)
    assert replay.disposition is InvocationDisposition.SESSION_REFUSED
    assert replay.session_refusal_reason == "session_consumed"
    assert fixture.runtime.calls == 1
    assert not hasattr(invoker, "execute")
    assert not hasattr(invoker, "mutate")
    assert not hasattr(invoker, "verify")
    assert not hasattr(invoker, "resume")


def test_missing_session_changed_binding_and_unavailable_runtime_refuse_before_dispatch(tmp_path: Path) -> None:
    missing = invocation_fixture(tmp_path / "missing", identity="missing")
    changed = invocation_fixture(tmp_path / "changed", identity="changed")
    unavailable = invocation_fixture(tmp_path / "unavailable", identity="unavailable")

    missing_result = ControlledRuntimeInvoker(session_gate=missing.gate).invoke(
        replace(missing.invocation_request, session=None)
    )
    changed_result = ControlledRuntimeInvoker(session_gate=changed.gate).invoke(
        replace(
            changed.invocation_request,
            runtime_binding=RuntimeExecutorBinding(
                runtime_id="other-runtime",
                executor=changed.runtime,
            ),
        )
    )
    unavailable_result = ControlledRuntimeInvoker(session_gate=unavailable.gate).invoke(
        replace(
            unavailable.invocation_request,
            runtime_availability=RuntimeAvailability(
                runtime_id=unavailable.runtime_availability.runtime_id,
                available=False,
            ),
        )
    )

    assert missing_result.refusal_reason is InvocationRejectionReason.MISSING_SESSION
    assert changed_result.refusal_reason is InvocationRejectionReason.RUNTIME_BINDING_MISMATCH
    assert unavailable_result.session_refusal_reason == "runtime_unavailable"
    assert missing.runtime.calls == 0
    assert changed.runtime.calls == 0
    assert unavailable.runtime.calls == 0


def test_runtime_failure_consumes_the_permit_without_retry_or_replacement_session(tmp_path: Path) -> None:
    fixture = invocation_fixture(tmp_path, identity="failure")
    fixture.runtime.fail_with = RuntimeError("deterministic runtime failure")
    invoker = ControlledRuntimeInvoker(session_gate=fixture.gate)

    failure = invoker.invoke(fixture.invocation_request)
    replay = invoker.invoke(fixture.invocation_request)

    assert failure.disposition is InvocationDisposition.RUNTIME_FAILED_AFTER_CONSUMPTION
    assert failure.failure_type == "RuntimeError"
    assert replay.session_refusal_reason == "session_consumed"
    assert fixture.runtime.calls == 1
