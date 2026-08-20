"""One-time deterministic authorization for validated mutation proposals."""

from __future__ import annotations

from dataclasses import replace

from eag.mutation.errors import (
    MutationAuthorizationError,
    MutationViolation,
    MutationViolationCode,
)
from eag.mutation.models import (
    MutationAuthorization,
    MutationAuthorizationState,
    ValidatedChangeProposal,
)


class MutationAuthorizer:
    """Issues and consumes authorization bound exactly to a validated proposal state."""

    def __init__(self, *, policy_version: str) -> None:
        self._policy_version = policy_version

    def authorize(self, validated: ValidatedChangeProposal) -> MutationAuthorization:
        """Issue an authorization for a currently validated single-file proposal."""
        proposal = validated.proposal
        return MutationAuthorization(
            proposal_id=proposal.proposal_id,
            proposal_digest=proposal.digest,
            target_path=proposal.target_path,
            operation=proposal.operation,
            workspace_fingerprint=validated.workspace_fingerprint,
            repository_snapshot_fingerprint=proposal.repository_snapshot_fingerprint,
            policy_version=self._policy_version,
            authorization_metadata={"contract_version": proposal.contract_version},
        )

    def consume(
        self,
        authorization: MutationAuthorization,
        validated: ValidatedChangeProposal,
    ) -> MutationAuthorization:
        """Consume a matching authorization exactly once before any write is attempted."""
        proposal = validated.proposal
        if authorization.state is not MutationAuthorizationState.AUTHORIZED:
            self._reject(
                MutationViolationCode.AUTHORIZATION_REUSED,
                "authorization is not available for one-time consumption",
                proposal.target_path,
            )
        if (
            authorization.proposal_id != proposal.proposal_id
            or authorization.proposal_digest != proposal.digest
            or authorization.target_path != proposal.target_path
            or authorization.operation is not proposal.operation
            or authorization.workspace_fingerprint != validated.workspace_fingerprint
            or authorization.repository_snapshot_fingerprint != proposal.repository_snapshot_fingerprint
            or authorization.policy_version != self._policy_version
        ):
            self._reject(
                MutationViolationCode.AUTHORIZATION_MISMATCH,
                "authorization does not match the validated proposal state",
                proposal.target_path,
            )
        return replace(authorization, state=MutationAuthorizationState.CONSUMED)

    def reject(self, authorization: MutationAuthorization) -> MutationAuthorization:
        """Return an immutable rejected authorization record without executing a mutation."""
        return replace(authorization, state=MutationAuthorizationState.REJECTED)

    def _reject(self, code: MutationViolationCode, message: str, target_path: str) -> None:
        raise MutationAuthorizationError(
            MutationViolation(
                code=code,
                stage="mutation_authorization",
                message=message,
                target_path=target_path,
                policy_version=self._policy_version,
            )
        )
