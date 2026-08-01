"""Reflection engine for EAG."""

from eag.review.enums import ReviewDecision, Severity
from eag.review.models import Reflection, ReviewReport


class ReflectionEngine:
    """Generates engineering reflections based on review reports."""

    def reflect(self, report: ReviewReport) -> Reflection:
        critical_issues = [i for f in report.findings for i in f.issues if i.severity == Severity.CRITICAL]
        errors = [i for f in report.findings for i in f.issues if i.severity == Severity.ERROR]
        warnings = [i for f in report.findings for i in f.issues if i.severity == Severity.WARNING]

        if critical_issues:
            root_cause = "Critical failures detected during execution or analysis."
            reasoning = "The implementation contains critical flaws that prevent it from functioning."
            actions = ("Fix critical errors", "Re-run execution", "Re-review")
            confidence = 0.99
        elif report.decision == ReviewDecision.CHANGES_REQUESTED:
            root_cause = "Quality thresholds not met due to errors or missing tests."
            reasoning = f"Found {len(errors)} errors and {len(warnings)} warnings."
            actions = ("Address errors", "Generate missing assets", "Re-run benchmark")
            confidence = 0.95
        elif report.decision == ReviewDecision.APPROVED_WITH_WARNINGS:
            root_cause = "Minor maintainability or documentation issues detected."
            reasoning = f"Found {len(warnings)} warnings. Implementation is functionally correct."
            actions = ("Address warnings when time permits",)
            confidence = 0.90
        else:
            root_cause = "No significant issues detected."
            reasoning = "The implementation meets all engineering quality bars."
            actions = ("Proceed to next task",)
            confidence = 1.0

        return Reflection(
            root_cause=root_cause,
            reasoning=reasoning,
            confidence=confidence,
            recommended_actions=actions
        )