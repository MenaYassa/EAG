"""Deterministic EBS-018 acceptance for the bounded G2.4.4 serial composition."""

from __future__ import annotations

from test_support.g2_4_4_runtime_fixture import governed_request, runtime_fixture

from eag.governed_execution import ExecutionEvidenceKind, GovernedExecutionState


def _transition_count(result, target: GovernedExecutionState) -> int:
    return sum(record.to_state is target for record in result.context.history)


def _evidence_ids(result, kind: ExecutionEvidenceKind) -> tuple[str, ...]:
    return tuple(
        evidence.reference_id
        for evidence in result.context.evidence
        if evidence.kind is kind
    )


def test_ebs_018_two_iteration_recovery_completes_with_fresh_authority(tmp_path) -> None:
    (tmp_path / "article.py").write_text("first\n", encoding="utf-8")
    runtime, gateway, context_factory, request_factory, verification_factory = runtime_fixture(
        tmp_path,
        contents=("second\n", "third\n"),
        fail_first_only=True,
    )

    result = runtime.execute(governed_request(tmp_path))

    assert result.context.state is GovernedExecutionState.COMPLETED
    assert result.context.iteration == 2
    assert result.context.budget.iterations_used == 2
    assert result.context.budget.mutations_used == 2
    assert result.context.budget.verifications_used == 2
    assert _transition_count(result, GovernedExecutionState.REFLECTING) == 1
    assert _transition_count(result, GovernedExecutionState.REPLANNING) == 1
    assert _transition_count(result, GovernedExecutionState.MUTATING) == 2
    assert _transition_count(result, GovernedExecutionState.VERIFYING) == 2
    assert _transition_count(result, GovernedExecutionState.CONTEXT_ASSEMBLING) == 2
    assert gateway.calls == 2
    assert context_factory.calls == 2
    assert request_factory.calls == 2
    assert verification_factory.calls == 2
    assert len(set(_evidence_ids(result, ExecutionEvidenceKind.DECISION))) == 2
    assert len(set(_evidence_ids(result, ExecutionEvidenceKind.PROPOSAL))) == 2
    assert len(set(_evidence_ids(result, ExecutionEvidenceKind.AUTHORIZATION))) == 2
    assert len(set(_evidence_ids(result, ExecutionEvidenceKind.MUTATION_RECEIPT))) == 2
    assert len(set(_evidence_ids(result, ExecutionEvidenceKind.VERIFICATION))) == 2
    assert len(result.iteration_artifacts) == 2
    assert result.iteration_artifacts[0].artifact_id != result.iteration_artifacts[1].artifact_id
    assert result.iteration_artifacts[0].context_fingerprint != result.iteration_artifacts[1].context_fingerprint
    assert (tmp_path / "article.py").read_text(encoding="utf-8") == "third\n"


def test_ebs_018_second_verification_failure_is_terminal_and_cannot_start_third_iteration(tmp_path) -> None:
    (tmp_path / "article.py").write_text("first\n", encoding="utf-8")
    runtime, gateway, context_factory, request_factory, verification_factory = runtime_fixture(
        tmp_path,
        contents=("second\n", "third\n"),
        fail_first_only=True,
    )
    original_build = verification_factory.build

    def always_fail(proposal):
        specification = original_build(proposal)
        return specification.__class__(
            specification_id=specification.specification_id,
            target_path=specification.target_path,
            check=specification.check,
            expected_fingerprint="0" * 64,
        )

    verification_factory.build = always_fail  # type: ignore[method-assign]
    result = runtime.execute(governed_request(tmp_path))

    assert result.context.state is GovernedExecutionState.FAILED
    assert result.context.stop_reason is not None
    assert result.context.stop_reason.value == "verification_failed"
    assert result.context.iteration == 2
    assert _transition_count(result, GovernedExecutionState.CONTEXT_ASSEMBLING) == 2
    assert _transition_count(result, GovernedExecutionState.MUTATING) == 2
    assert _transition_count(result, GovernedExecutionState.VERIFYING) == 2
    assert gateway.calls == 2
    assert context_factory.calls == 2
    assert request_factory.calls == 2
    assert verification_factory.calls == 2
    assert result.context.state.is_terminal
