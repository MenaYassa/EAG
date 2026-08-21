"""Deterministic G2.4.2 coverage for the trusted verification boundary."""

from __future__ import annotations

import hashlib
import re
from dataclasses import FrozenInstanceError, dataclass
from enum import StrEnum
from pathlib import Path

import pytest

from eag.governed_execution import (
    DeterministicVerifier,
    ExecutionBudget,
    GovernedExecutionContext,
    ObjectiveCompletionPolicy,
    ObjectiveFailureCode,
    ObjectiveStatus,
    VerificationCheck,
    VerificationFailureCode,
    VerificationRequest,
    VerificationRequestError,
    VerificationSpecification,
    VerificationStatus,
)


class _ReceiptResult(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class _ReceiptFixture:
    """Frozen stand-in exposing exactly the G2.3.1 receipt evidence the verifier reads."""

    mutation_id: str
    run_id: str
    target_path: str
    result: _ReceiptResult
    verification_passed: bool


def _receipt(
    *,
    result: _ReceiptResult = _ReceiptResult.COMPLETED,
    postcondition_passed: bool = True,
    target_path: str = "article.txt",
    run_id: str = "verification-run",
) -> _ReceiptFixture:
    return _ReceiptFixture(
        mutation_id="mutation-1",
        run_id=run_id,
        target_path=target_path,
        result=result,
        verification_passed=postcondition_passed if result is _ReceiptResult.COMPLETED else False,
    )


def _request(
    receipt: _ReceiptFixture,
    specification: VerificationSpecification,
    *,
    context: GovernedExecutionContext | None = None,
) -> VerificationRequest:
    return VerificationRequest(
        run_id=receipt.run_id,
        receipt=receipt,
        specification=specification,
        execution_context=context,
    )


def test_successful_mutation_and_trusted_exact_content_verification_establish_objective_success(
    tmp_path: Path,
) -> None:
    (tmp_path / "article.txt").write_text("published\n", encoding="utf-8")
    receipt = _receipt()
    specification = VerificationSpecification(
        target_path="article.txt",
        check=VerificationCheck.EXACT_CONTENT,
        expected_content="published\n",
    )

    result = DeterministicVerifier(workspace_root=tmp_path).verify(_request(receipt, specification))
    objective = ObjectiveCompletionPolicy.assess(receipt, result)

    assert receipt.result is _ReceiptResult.COMPLETED
    assert receipt.verification_passed is True
    assert result.status is VerificationStatus.PASSED
    assert result.failure_code is None
    assert objective.status is ObjectiveStatus.SATISFIED


def test_successful_mutation_and_failed_verification_remain_distinct(tmp_path: Path) -> None:
    (tmp_path / "article.txt").write_text("draft\n", encoding="utf-8")
    receipt = _receipt()
    specification = VerificationSpecification(
        target_path="article.txt",
        check=VerificationCheck.EXACT_CONTENT,
        expected_content="published\n",
    )

    result = DeterministicVerifier(workspace_root=tmp_path).verify(_request(receipt, specification))
    objective = ObjectiveCompletionPolicy.assess(receipt, result)

    assert receipt.result is _ReceiptResult.COMPLETED
    assert receipt.verification_passed is True
    assert result.status is VerificationStatus.FAILED
    assert result.failure_code is VerificationFailureCode.ASSERTION_FAILED
    assert objective.status is ObjectiveStatus.NOT_SATISFIED
    assert objective.failure_code is ObjectiveFailureCode.VERIFICATION_NOT_PASSED


def test_mutation_failure_is_not_a_verification_failure(tmp_path: Path) -> None:
    (tmp_path / "article.txt").write_text("published\n", encoding="utf-8")
    receipt = _receipt(result=_ReceiptResult.FAILED, postcondition_passed=False)
    specification = VerificationSpecification(
        target_path="article.txt",
        check=VerificationCheck.FILE_EXISTS,
    )

    result = DeterministicVerifier(workspace_root=tmp_path).verify(_request(receipt, specification))
    objective = ObjectiveCompletionPolicy.assess(receipt, result)

    assert result.status is VerificationStatus.NOT_RUN
    assert result.failure_code is VerificationFailureCode.MUTATION_NOT_SUCCESSFUL
    assert objective.status is ObjectiveStatus.NOT_SATISFIED
    assert objective.failure_code is ObjectiveFailureCode.MUTATION_NOT_SUCCESSFUL


def test_objective_success_cannot_be_assessed_from_a_different_receipt(tmp_path: Path) -> None:
    (tmp_path / "article.txt").write_text("published\n", encoding="utf-8")
    receipt = _receipt()
    specification = VerificationSpecification(target_path="article.txt", check=VerificationCheck.FILE_EXISTS)
    result = DeterministicVerifier(workspace_root=tmp_path).verify(_request(receipt, specification))
    different_receipt = _ReceiptFixture(
        mutation_id="different-mutation",
        run_id=receipt.run_id,
        target_path="different.txt",
        result=_ReceiptResult.COMPLETED,
        verification_passed=True,
    )

    with pytest.raises(VerificationRequestError, match="receipt_id"):
        ObjectiveCompletionPolicy.assess(different_receipt, result)


def test_llm_claim_text_cannot_be_supplied_as_verification_authority(tmp_path: Path) -> None:
    (tmp_path / "article.txt").write_text("draft\n", encoding="utf-8")
    receipt = _receipt()
    specification = VerificationSpecification(target_path="article.txt", check=VerificationCheck.FILE_EXISTS)

    with pytest.raises(TypeError):
        VerificationRequest(
            run_id=receipt.run_id,
            receipt=receipt,
            specification=specification,
            llm_claim="verification passed",  # type: ignore[call-arg]
        )


def test_malformed_and_unsupported_specifications_are_rejected() -> None:
    with pytest.raises(VerificationRequestError, match="confined relative"):
        VerificationSpecification(target_path="../secret.txt", check=VerificationCheck.FILE_EXISTS)
    with pytest.raises(VerificationRequestError, match="requires expected_content"):
        VerificationSpecification(target_path="article.txt", check=VerificationCheck.EXACT_CONTENT)
    with pytest.raises(VerificationRequestError, match="unsupported verification check"):
        VerificationSpecification(target_path="article.txt", check="shell" )  # type: ignore[arg-type]


def test_verification_request_binds_receipt_target_and_run() -> None:
    receipt = _receipt()
    with pytest.raises(VerificationRequestError, match="target_path"):
        _request(
            receipt,
            VerificationSpecification(target_path="other.txt", check=VerificationCheck.FILE_EXISTS),
        )
    with pytest.raises(VerificationRequestError, match="run_id"):
        VerificationRequest(
            run_id="other-run",
            receipt=receipt,
            specification=VerificationSpecification(
                target_path="article.txt",
                check=VerificationCheck.FILE_EXISTS,
            ),
        )


def test_verification_scope_is_one_confined_bounded_regular_file(tmp_path: Path) -> None:
    (tmp_path / "article.txt").write_bytes(b"x" * 11)
    receipt = _receipt()
    specification = VerificationSpecification(
        target_path="article.txt",
        check=VerificationCheck.EXPECTED_FINGERPRINT,
        expected_fingerprint=hashlib.sha256(b"x" * 11).hexdigest(),
        max_bytes=10,
    )

    result = DeterministicVerifier(workspace_root=tmp_path).verify(_request(receipt, specification))

    assert result.status is VerificationStatus.FAILED
    assert result.failure_code is VerificationFailureCode.TARGET_TOO_LARGE
    assert result.evidence is None


def test_verification_rejects_symlink_escape_without_reading_outside_workspace(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-verification.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (tmp_path / "article.txt").symlink_to(outside)
    receipt = _receipt()
    specification = VerificationSpecification(target_path="article.txt", check=VerificationCheck.FILE_EXISTS)

    result = DeterministicVerifier(workspace_root=tmp_path).verify(_request(receipt, specification))

    assert result.status is VerificationStatus.FAILED
    assert result.failure_code is VerificationFailureCode.TARGET_SYMLINK
    assert outside.read_text(encoding="utf-8") == "outside\n"


def test_verification_is_read_only_and_evidence_is_redacted(tmp_path: Path) -> None:
    target = tmp_path / "article.txt"
    target.write_text("published\n", encoding="utf-8")
    before = target.read_bytes()
    receipt = _receipt()
    specification = VerificationSpecification(target_path="article.txt", check=VerificationCheck.FILE_EXISTS)

    result = DeterministicVerifier(workspace_root=tmp_path).verify(_request(receipt, specification))

    assert target.read_bytes() == before
    assert result.evidence is not None
    assert result.evidence.observed_fingerprint == hashlib.sha256(before).hexdigest()
    assert not hasattr(result.evidence, "content")
    assert result.evidence_ref.kind.value == "verification"
    with pytest.raises(FrozenInstanceError):
        result.status = VerificationStatus.FAILED  # type: ignore[misc]


def test_ledger_reference_is_reconstructable_without_state_transition(tmp_path: Path) -> None:
    (tmp_path / "article.txt").write_text("published\n", encoding="utf-8")
    receipt = _receipt()
    context = GovernedExecutionContext(
        run_id=receipt.run_id,
        goal="Verify a completed mutation.",
        budget=ExecutionBudget(max_iterations=1, max_mutations=1, max_verifications=1),
    )
    specification = VerificationSpecification(target_path="article.txt", check=VerificationCheck.FILE_EXISTS)

    result = DeterministicVerifier(workspace_root=tmp_path).verify(
        _request(receipt, specification, context=context)
    )

    assert context.history == ()
    assert result.evidence_ref.reference_id == result.verification_id
    assert result.evidence_ref.metadata["status"] == VerificationStatus.PASSED.value


def test_verifier_source_has_no_operational_execution_dependencies() -> None:
    source = (
        Path(__file__).parents[1] / "src" / "eag" / "governed_execution" / "verification.py"
    ).read_text(encoding="utf-8")

    forbidden_imports = (
        r"(?:from|import)\\s+subprocess",
        r"(?:from|import)\\s+requests",
        r"(?:from|import)\\s+httpx",
        r"(?:from|import)\\s+socket",
        r"from\\s+eag\\.(?:capability|chief\\.intelligence\\.gateway|workspace)",
        r"from\\s+eag\\.mutation\\s+import\\s+.*GovernedMutationRuntime",
    )
    for pattern in forbidden_imports:
        assert re.search(pattern, source) is None
    assert "os.system(" not in source
