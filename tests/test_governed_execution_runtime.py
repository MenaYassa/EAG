"""Deterministic G2.4.4 serial-runtime tests using public authority seams only."""

from __future__ import annotations

import hashlib
from pathlib import Path

from test_support.g2_4_4_runtime_fixture import governed_request, runtime_fixture

from eag.governed_execution import GovernedExecutionState, VerificationSpecification


def test_serial_runtime_recovers_once_with_fresh_authority_and_completes(tmp_path: Path) -> None:
    (tmp_path / "article.py").write_text("first\n", encoding="utf-8")
    runtime, gateway, context_factory, request_factory, verification_factory = runtime_fixture(
        tmp_path,
        contents=("second\n", "third\n"),
        fail_first_only=True,
    )

    result = runtime.execute(governed_request(tmp_path))

    assert result.succeeded is True
    assert result.context.state is GovernedExecutionState.COMPLETED
    assert result.context.iteration == 2
    assert result.context.budget.iterations_used == 2
    assert result.context.budget.mutations_used == 2
    assert result.context.budget.verifications_used == 2
    assert len(result.iteration_artifacts) == 2
    assert result.iteration_artifacts[0].artifact_id != result.iteration_artifacts[1].artifact_id
    assert result.iteration_artifacts[0].context_fingerprint != result.iteration_artifacts[1].context_fingerprint
    assert gateway.calls == 2
    assert context_factory.calls == 2
    assert request_factory.calls == 2
    assert verification_factory.calls == 2
    assert (tmp_path / "article.py").read_text(encoding="utf-8") == "third\n"


def test_serial_runtime_second_verification_failure_is_terminal_without_third_iteration(tmp_path: Path) -> None:
    (tmp_path / "article.py").write_text("first\n", encoding="utf-8")
    runtime, gateway, context_factory, request_factory, verification_factory = runtime_fixture(
        tmp_path,
        contents=("second\n", "third\n"),
        fail_first_only=True,
    )
    verification_factory.fail_first = True
    original_build = verification_factory.build

    def always_fail(proposal):
        specification = original_build(proposal)
        return VerificationSpecification(
            specification_id=specification.specification_id,
            target_path=specification.target_path,
            check=specification.check,
            expected_fingerprint=hashlib.sha256(b"wrong-content").hexdigest(),
        )

    verification_factory.build = always_fail  # type: ignore[method-assign]
    result = runtime.execute(governed_request(tmp_path))

    assert result.succeeded is False
    assert result.context.state is GovernedExecutionState.FAILED
    assert result.context.stop_reason.value == "verification_failed"
    assert result.context.iteration == 2
    assert result.context.budget.iterations_used == 2
    assert gateway.calls == 2
    assert context_factory.calls == 2
    assert request_factory.calls == 2
    assert verification_factory.calls == 2
