"""G2.4.4 pre-mutation executable-authority freshness boundary.

This module is intentionally separate from G2.4.3 replanning.  It validates only
artifacts that exist after authorization and before mutation; complete iteration
receipt and verification freshness remains exclusively in G2.4.3.
"""

from __future__ import annotations

from dataclasses import dataclass

FRESH_ITERATION_AUTHORITY_CONTRACT_VERSION = "1.0"


class FreshIterationAuthorityError(ValueError):
    """Raised when a candidate pre-mutation authority is stale or malformed."""


@dataclass(frozen=True, slots=True, kw_only=True)
class FreshIterationAuthority:
    """Immutable executable authority allocated before one governed mutation.

    The object deliberately excludes receipt and verification identities because
    those artifacts are produced only after a mutation and its verification.
    """

    execution_id: str
    iteration: int
    context_artifact_id: str
    context_fingerprint: str
    decision_request_id: str
    decision_id: str
    proposal_id: str
    authorization_id: str
    contract_version: str = FRESH_ITERATION_AUTHORITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "execution_id",
            "context_artifact_id",
            "context_fingerprint",
            "decision_request_id",
            "decision_id",
            "proposal_id",
            "authorization_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise FreshIterationAuthorityError(f"{field_name} cannot be empty")
        if not isinstance(self.iteration, int) or isinstance(self.iteration, bool) or self.iteration < 1:
            raise FreshIterationAuthorityError("iteration must be a positive integer")
        if self.contract_version != FRESH_ITERATION_AUTHORITY_CONTRACT_VERSION:
            raise FreshIterationAuthorityError("unsupported fresh iteration authority contract version")


def validate_fresh_authority(
    previous: FreshIterationAuthority,
    candidate: FreshIterationAuthority,
) -> None:
    """Reject stale executable authority before a subsequent iteration mutates.

    This is an additive pre-mutation comparison. It never receives, validates, or
    substitutes the post-mutation receipt/verification identities owned by G2.4.3.
    """
    if not isinstance(previous, FreshIterationAuthority):
        raise TypeError("previous must be a FreshIterationAuthority")
    if not isinstance(candidate, FreshIterationAuthority):
        raise TypeError("candidate must be a FreshIterationAuthority")
    if candidate.execution_id != previous.execution_id:
        raise FreshIterationAuthorityError("candidate authority belongs to another execution")
    if candidate.iteration != previous.iteration + 1:
        raise FreshIterationAuthorityError("candidate authority must be for the next serial iteration")
    for field_name in (
        "context_artifact_id",
        "context_fingerprint",
        "decision_request_id",
        "decision_id",
        "proposal_id",
        "authorization_id",
    ):
        if getattr(candidate, field_name) == getattr(previous, field_name):
            raise FreshIterationAuthorityError(f"fresh authority reuses stale {field_name}")


__all__ = [
    "FRESH_ITERATION_AUTHORITY_CONTRACT_VERSION",
    "FreshIterationAuthority",
    "FreshIterationAuthorityError",
    "validate_fresh_authority",
]
