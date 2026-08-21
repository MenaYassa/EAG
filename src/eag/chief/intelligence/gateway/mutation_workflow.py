"""Public composition seam for one governed decision-derived mutation attempt."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from eag.chief.intelligence.gateway.models import (
    EngineeringDecisionRequest,
    EngineeringDecisionResult,
)
from eag.chief.intelligence.gateway.mutation_translation import (
    DecisionToChangeProposalTranslator,
    MutationTranslationError,
    TranslationViolation,
    TrustedWorkspaceState,
)
from eag.chief.intelligence.gateway.protocol import GovernedLLMGateway
from eag.mutation import ChangeProposal, GovernedMutationRuntime, MutationReceipt, MutationResult


class GovernedMutationFailureStage(StrEnum):
    """Sanitized terminal stages for one governed decision-to-mutation workflow."""

    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_FAILURE = "provider_failure"
    SCHEMA_FAILURE = "schema_failure"
    DECISION_REJECTED = "decision_rejected"
    TRANSLATION_FAILURE = "translation_failure"
    POLICY_REJECTED = "policy_rejected"
    AUTHORIZATION_REJECTED = "authorization_rejected"
    MUTATION_FAILED = "mutation_failed"
    VERIFICATION_FAILED = "verification_failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedDecisionMutationResult:
    """Redacted outcome of one composed gateway-to-mutation attempt."""

    gateway_result: EngineeringDecisionResult
    proposal: ChangeProposal | None = None
    receipt: MutationReceipt | None = None
    failure_stage: GovernedMutationFailureStage | None = None
    translation_violation: TranslationViolation | None = None

    @property
    def success(self) -> bool:
        return self.receipt is not None and self.receipt.result is MutationResult.COMPLETED


class GovernedDecisionMutationWorkflow:
    """Compose an advisory gateway result with the existing G2.3.1 mutation boundary.

    This is a public, narrow seam for one explicit operation. The workflow owns no direct file
    write and does not create a generic CapabilityRequest. Mutation authority stays exclusively
    inside the injected GovernedMutationRuntime after translation and policy/authorization gates.
    """

    def __init__(
        self,
        *,
        gateway: GovernedLLMGateway,
        translator: DecisionToChangeProposalTranslator,
        mutation_runtime: GovernedMutationRuntime,
    ) -> None:
        self._gateway = gateway
        self._translator = translator
        self._mutation_runtime = mutation_runtime

    def execute(
        self,
        request: EngineeringDecisionRequest,
        *,
        run_id: str,
        trusted_state: TrustedWorkspaceState,
    ) -> GovernedDecisionMutationResult:
        """Run one governed decision attempt through translation and existing mutation gates."""
        gateway_result = self._gateway.decide(request)
        if not gateway_result.success:
            return GovernedDecisionMutationResult(
                gateway_result=gateway_result,
                failure_stage=_gateway_failure_stage(gateway_result),
            )
        try:
            proposal = self._translator.translate(
                gateway_result,
                request,
                run_id=run_id,
                trusted_state=trusted_state,
            )
        except MutationTranslationError as error:
            return GovernedDecisionMutationResult(
                gateway_result=gateway_result,
                failure_stage=GovernedMutationFailureStage.TRANSLATION_FAILURE,
                translation_violation=error.violation,
            )
        receipt = self._mutation_runtime.execute(proposal)
        return GovernedDecisionMutationResult(
            gateway_result=gateway_result,
            proposal=proposal,
            receipt=receipt,
            failure_stage=_receipt_failure_stage(receipt),
        )


def _gateway_failure_stage(result: EngineeringDecisionResult) -> GovernedMutationFailureStage:
    error_kind = result.error.kind.value if result.error is not None else ""
    if error_kind == "provider_timeout":
        return GovernedMutationFailureStage.PROVIDER_TIMEOUT
    if error_kind in {"schema_invalid", "response_empty_or_malformed"}:
        return GovernedMutationFailureStage.SCHEMA_FAILURE
    if error_kind == "policy_rejected":
        return GovernedMutationFailureStage.DECISION_REJECTED
    return GovernedMutationFailureStage.PROVIDER_FAILURE


def _receipt_failure_stage(receipt: MutationReceipt) -> GovernedMutationFailureStage | None:
    if receipt.result is MutationResult.COMPLETED:
        return None
    if receipt.failure_code in {"authorization_rejected", "authorization_mismatch", "authorization_reused"}:
        return GovernedMutationFailureStage.AUTHORIZATION_REJECTED
    if receipt.failure_code == "postcondition_mismatch":
        return GovernedMutationFailureStage.VERIFICATION_FAILED
    if receipt.result is MutationResult.REJECTED:
        return GovernedMutationFailureStage.POLICY_REJECTED
    return GovernedMutationFailureStage.MUTATION_FAILED
