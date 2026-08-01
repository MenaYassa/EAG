"""Review runtime for EAG."""

import time

from eag.events import EventBus
from eag.review.enums import ReviewDecision, Severity
from eag.review.events import (
    IssueDetected,
    ReflectionCompleted,
    ReflectionStarted,
    ReviewCompleted,
    ReviewStarted,
)
from eag.review.models import (
    ReviewContext,
    ReviewFinding,
    ReviewIssue,
    ReviewMetrics,
    ReviewReport,
)
from eag.review.reflection import ReflectionEngine
from eag.review.registry import AnalyzerRegistry


class ReviewRuntime:
    """Orchestrates the engineering review pipeline."""

    def __init__(
        self,
        registry: AnalyzerRegistry,
        event_bus: EventBus,
        reflection_engine: ReflectionEngine | None = None,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus
        self._reflection = reflection_engine or ReflectionEngine()

    def review(self, context: ReviewContext) -> ReviewReport:
        """Executes the review pipeline and produces a report."""
        review_id = str(__import__("uuid").uuid4())
        self._event_bus.publish(ReviewStarted(review_id=review_id))

        start_time = time.monotonic()

        all_issues: list[ReviewIssue] = []
        for analyzer in self._registry.list():
            issues = analyzer.analyze(context)
            for issue in issues:
                all_issues.append(issue)
                self._event_bus.publish(
                    IssueDetected(
                        review_id=review_id, issue_id=issue.id, severity=issue.severity.value
                    )
                )

        # Aggregate into a single finding for now
        finding = ReviewFinding(
            title="Workspace Review",
            issues=tuple(all_issues),
            score=100,  # Calculated below
        )

        # Calculate Score
        score = 100
        critical_count = 0
        error_count = 0
        warning_count = 0

        for issue in all_issues:
            if issue.severity == Severity.CRITICAL:
                score -= 25
                critical_count += 1
            elif issue.severity == Severity.ERROR:
                score -= 10
                error_count += 1
            elif issue.severity == Severity.WARNING:
                score -= 5
                warning_count += 1

        score = max(0, score)

        # Determine Decision
        if critical_count > 0 or score < 50:
            decision = ReviewDecision.REJECTED
        elif error_count > 0 or score < 70:
            decision = ReviewDecision.CHANGES_REQUESTED
        elif warning_count > 0 or score < 90:
            decision = ReviewDecision.APPROVED_WITH_WARNINGS
        else:
            decision = ReviewDecision.APPROVED

        finding = ReviewFinding(title=finding.title, issues=finding.issues, score=score)

        # Generate Report
        report = ReviewReport(
            review_id=review_id,
            decision=decision,
            overall_score=score,
            findings=(finding,),
            metrics=ReviewMetrics(
                issues_found=len(all_issues),
                warnings=warning_count,
                errors=error_count,
                critical=critical_count,
                review_time_ms=(time.monotonic() - start_time) * 1000,
            ),
        )

        # Reflection
        self._event_bus.publish(ReflectionStarted(review_id=review_id))
        reflection = self._reflection.reflect(report)
        self._event_bus.publish(
            ReflectionCompleted(review_id=review_id, confidence=reflection.confidence)
        )

        final_report = ReviewReport(
            review_id=report.review_id,
            decision=report.decision,
            overall_score=report.overall_score,
            findings=report.findings,
            reflection=reflection,
            metrics=report.metrics,
            duration_ms=(time.monotonic() - start_time) * 1000,
            summary=f"Review completed with decision {decision.value}.",
        )

        self._event_bus.publish(
            ReviewCompleted(review_id=review_id, decision=decision.value, score=score)
        )

        return final_report
