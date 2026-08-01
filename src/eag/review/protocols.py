"""Engineering Review protocols for EAG."""

from typing import Protocol, runtime_checkable

from eag.review.models import ReviewIssue


@runtime_checkable
class ReviewAnalyzer(Protocol):
    """The contract for a review analyzer."""

    def analyze(self, context: any) -> tuple[ReviewIssue, ...]: ...
