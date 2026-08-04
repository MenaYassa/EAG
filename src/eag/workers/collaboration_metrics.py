"""Collaboration metrics for EAG."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class CollaborationMetrics:
    """Metrics tracking the effectiveness of the engineering organization."""
    delegations: int = 0
    successful_delegations: int = 0
    review_acceptance_rate: float = 0.0
    average_delegation_score: float = 0.0
    artifacts_produced: int = 0