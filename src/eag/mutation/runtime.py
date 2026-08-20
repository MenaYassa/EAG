"""Deterministic G2.3.1 governed mutation orchestration with no LLM or shell boundary."""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

from eag.events import EventBus
from eag.mutation.authorization import MutationAuthorizer
from eag.mutation.errors import (
    MutationAuthorizationError,
    MutationPolicyError,
    MutationViolation,
    MutationViolationCode,
)
from eag.mutation.events import (
    MutationAuthorized,
    MutationCompleted,
    MutationFailed,
    MutationProposed,
    MutationRejected,
    MutationStarted,
)
from eag.mutation.models import (
    ChangeProposal,
    MutationAuthorization,
    MutationAuthorizationState,
    MutationOperation,
    MutationReceipt,
    MutationResult,
    ValidatedChangeProposal,
    _sha256_text,
)
from eag.mutation.policy import MutationPolicyValidator


class GovernedMutationRuntime:
    """The only G2.3.1 mutation path: proposal → policy → authorization → receipt."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        policy: MutationPolicyValidator,
        authorizer: MutationAuthorizer,
        event_bus: EventBus,
    ) -> None:
        self._workspace_root = workspace_root.resolve(strict=True)
        self._policy = policy
        self._authorizer = authorizer
        self._event_bus = event_bus
        self._lock = threading.RLock()

    def validate(self, proposal: ChangeProposal) -> ValidatedChangeProposal:
        """Publish proposal lifecycle telemetry and validate without writing a file."""
        self._event_bus.publish(
            MutationProposed(
                proposal_id=proposal.proposal_id,
                run_id=proposal.run_id,
                target_path=proposal.target_path,
                operation=proposal.operation,
                proposal_digest=proposal.digest,
            )
        )
        return self._policy.validate(proposal, self._workspace_root)

    def authorize(self, validated: ValidatedChangeProposal) -> MutationAuthorization:
        """Issue, but do not consume, a proposal-bound authorization."""
        authorization = self._authorizer.authorize(validated)
        proposal = validated.proposal
        self._event_bus.publish(
            MutationAuthorized(
                proposal_id=proposal.proposal_id,
                run_id=proposal.run_id,
                authorization_id=authorization.authorization_id,
                proposal_digest=proposal.digest,
            )
        )
        return authorization

    def execute(self, proposal: ChangeProposal) -> MutationReceipt:
        """Run the complete deterministic path and return a terminal redacted receipt."""
        try:
            validated = self.validate(proposal)
        except MutationPolicyError as error:
            return self._rejected_receipt(proposal, error.violation)
        authorization = self.authorize(validated)
        return self.mutate(validated, authorization)

    def mutate(
        self,
        validated: ValidatedChangeProposal,
        authorization: MutationAuthorization,
    ) -> MutationReceipt:
        """Consume authorization, revalidate state, atomically mutate one file, and verify it."""
        proposal = validated.proposal
        with self._lock:
            try:
                current = self._policy.validate(proposal, self._workspace_root)
                consumed = self._authorizer.consume(authorization, current)
            except MutationPolicyError as error:
                self._publish_rejected(proposal, error.violation)
                return self._rejected_receipt(proposal, error.violation, authorization)
            except MutationAuthorizationError as error:
                self._publish_rejected(proposal, error.violation)
                return self._rejected_receipt(proposal, error.violation, authorization)

            target = self._target_path(proposal)
            before = target.read_bytes() if current.target_exists else b""
            pre_fingerprint = current.target_fingerprint
            self._event_bus.publish(
                MutationStarted(
                    proposal_id=proposal.proposal_id,
                    run_id=proposal.run_id,
                    authorization_id=consumed.authorization_id,
                    target_path=proposal.target_path,
                    operation=proposal.operation,
                )
            )
            try:
                self._atomic_write(target, proposal.content)
                after = target.read_bytes()
                post_fingerprint = _sha256_text(after.decode("utf-8"))
                verification_passed = self._verify_postcondition(proposal, post_fingerprint)
                if not verification_passed:
                    rollback_performed = self._conditional_restore(
                        target=target,
                        proposal=proposal,
                        before=before,
                        observed_post_fingerprint=post_fingerprint,
                    )
                    receipt = MutationReceipt(
                        proposal_id=proposal.proposal_id,
                        run_id=proposal.run_id,
                        authorization_id=consumed.authorization_id,
                        target_path=proposal.target_path,
                        operation=proposal.operation,
                        result=MutationResult.FAILED,
                        pre_fingerprint=pre_fingerprint,
                        post_fingerprint=post_fingerprint,
                        bytes_before=len(before),
                        bytes_after=len(after),
                        bytes_changed=abs(len(after) - len(before)),
                        authorization_state=consumed.state,
                        policy_version=self._policy.policy_version,
                        failure_code=MutationViolationCode.POSTCONDITION_MISMATCH.value,
                        failure_reason="postcondition fingerprint did not match",
                        verification_passed=False,
                        rollback_performed=rollback_performed,
                    )
                    self._publish_failed(proposal, receipt, MutationViolationCode.POSTCONDITION_MISMATCH)
                    return receipt
                receipt = MutationReceipt(
                    proposal_id=proposal.proposal_id,
                    run_id=proposal.run_id,
                    authorization_id=consumed.authorization_id,
                    target_path=proposal.target_path,
                    operation=proposal.operation,
                    result=MutationResult.COMPLETED,
                    pre_fingerprint=pre_fingerprint,
                    post_fingerprint=post_fingerprint,
                    bytes_before=len(before),
                    bytes_after=len(after),
                    bytes_changed=abs(len(after) - len(before)),
                    authorization_state=consumed.state,
                    policy_version=self._policy.policy_version,
                    verification_passed=True,
                )
                self._event_bus.publish(
                    MutationCompleted(
                        proposal_id=proposal.proposal_id,
                        run_id=proposal.run_id,
                        receipt_id=receipt.mutation_id,
                        target_path=proposal.target_path,
                        operation=proposal.operation,
                        result=receipt.result,
                    )
                )
                return receipt
            except OSError:
                receipt = MutationReceipt(
                    proposal_id=proposal.proposal_id,
                    run_id=proposal.run_id,
                    authorization_id=consumed.authorization_id,
                    target_path=proposal.target_path,
                    operation=proposal.operation,
                    result=MutationResult.FAILED,
                    pre_fingerprint=pre_fingerprint,
                    post_fingerprint=None,
                    bytes_before=len(before),
                    bytes_after=0,
                    bytes_changed=0,
                    authorization_state=consumed.state,
                    policy_version=self._policy.policy_version,
                    failure_code=MutationViolationCode.WRITE_FAILED.value,
                    failure_reason="bounded atomic workspace write failed",
                    verification_passed=False,
                )
                self._publish_failed(proposal, receipt, MutationViolationCode.WRITE_FAILED)
                return receipt

    def _target_path(self, proposal: ChangeProposal) -> Path:
        return self._workspace_root.joinpath(*proposal.target_path.split("/"))

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        encoded = content.encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(prefix=".eag-mutation-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _verify_postcondition(proposal: ChangeProposal, fingerprint: str) -> bool:
        expected = proposal.expected_postcondition.expected_fingerprint
        return proposal.expected_postcondition.expect_exists and (expected is None or expected == fingerprint) and fingerprint == proposal.content_fingerprint

    def _conditional_restore(
        self,
        *,
        target: Path,
        proposal: ChangeProposal,
        before: bytes,
        observed_post_fingerprint: str,
    ) -> bool:
        """Compensate only while target still exactly equals this mutation's post-state."""
        try:
            current = target.read_text(encoding="utf-8")
        except OSError:
            return False
        if _sha256_text(current) != observed_post_fingerprint:
            return False
        try:
            if proposal.operation is MutationOperation.CREATE_FILE:
                target.unlink()
            else:
                self._atomic_write(target, before.decode("utf-8"))
            return True
        except OSError:
            return False

    def _rejected_receipt(
        self,
        proposal: ChangeProposal,
        violation: MutationViolation,
        authorization: MutationAuthorization | None = None,
    ) -> MutationReceipt:
        receipt = MutationReceipt(
            proposal_id=proposal.proposal_id,
            run_id=proposal.run_id,
            authorization_id=authorization.authorization_id if authorization else None,
            target_path=proposal.target_path,
            operation=proposal.operation,
            result=MutationResult.REJECTED,
            pre_fingerprint=None,
            post_fingerprint=None,
            bytes_before=0,
            bytes_after=0,
            bytes_changed=0,
            authorization_state=authorization.state if authorization else MutationAuthorizationState.REJECTED,
            policy_version=violation.policy_version,
            failure_code=violation.code.value,
            failure_reason=violation.message,
            verification_passed=False,
        )
        self._event_bus.publish(
            MutationRejected(
                proposal_id=proposal.proposal_id,
                run_id=proposal.run_id,
                code=violation.code,
                stage=violation.stage,
                target_path=violation.target_path,
            )
        )
        return receipt

    def _publish_rejected(self, proposal: ChangeProposal, violation: MutationViolation) -> None:
        self._event_bus.publish(
            MutationRejected(
                proposal_id=proposal.proposal_id,
                run_id=proposal.run_id,
                code=violation.code,
                stage=violation.stage,
                target_path=violation.target_path,
            )
        )

    def _publish_failed(
        self,
        proposal: ChangeProposal,
        receipt: MutationReceipt,
        code: MutationViolationCode,
    ) -> None:
        self._event_bus.publish(
            MutationFailed(
                proposal_id=proposal.proposal_id,
                run_id=proposal.run_id,
                receipt_id=receipt.mutation_id,
                code=code,
                stage="mutation_execution",
            )
        )
