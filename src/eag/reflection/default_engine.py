"""Default deterministic reflection engine for EAG."""

from eag.reflection.enums import FindingCategory, RecommendationPriority, Severity
from eag.reflection.models import (
    ReflectionContext,
    ReflectionFinding,
    ReflectionMetrics,
    ReflectionRecommendation,
    ReflectionReport,
    ReflectionSummary,
)


class DefaultReflectionEngine:
    """A rule-based reflection engine that analyzes run results."""

    _SEVERITY_ORDER = {
        Severity.CRITICAL: 4,
        Severity.HIGH: 3,
        Severity.MEDIUM: 2,
        Severity.LOW: 1,
        Severity.INFO: 0,
    }

    _PRIORITY_ORDER = {
        RecommendationPriority.URGENT: 4,
        RecommendationPriority.HIGH: 3,
        RecommendationPriority.NORMAL: 2,
        RecommendationPriority.LOW: 1,
    }

    def reflect(self, context: ReflectionContext) -> ReflectionReport:
        findings: list[ReflectionFinding] = []
        recommendations: list[ReflectionRecommendation] = []
        strengths: list[str] = []
        weaknesses: list[str] = []

        run_result = context.run_result
        review_report = context.review_report
        benchmark_result = context.benchmark_result

        # Analyze Execution
        if hasattr(run_result, "outcome") and run_result.outcome == "failure":
            findings.append(
                ReflectionFinding(
                    category=FindingCategory.EXECUTION,
                    severity=Severity.CRITICAL,
                    title="Execution Failed",
                    description="The engineering execution failed to complete successfully.",
                    evidence=run_result.summary,
                    confidence=1.0,
                )
            )
            weaknesses.append("Execution failed")

        # Analyze Review
        if review_report:
            if hasattr(review_report, "decision") and review_report.decision != "approved":
                findings.append(
                    ReflectionFinding(
                        category=FindingCategory.REVIEW,
                        severity=Severity.HIGH,
                        title="Review Rejected",
                        description=f"Review decision was {review_report.decision}.",
                        evidence=review_report.summary,
                        confidence=0.9,
                    )
                )
                weaknesses.append("Quality review rejected the work")

                recommendations.append(
                    ReflectionRecommendation(
                        priority=RecommendationPriority.HIGH,
                        title="Address Review Issues",
                        description="Fix the issues identified in the review report.",
                        action="Re-execute failed tasks with fixes.",
                        confidence=0.9,
                    )
                )
            else:
                strengths.append("Quality review approved the work")

        # Analyze Benchmark
        if benchmark_result:
            if hasattr(benchmark_result, "success") and not benchmark_result.success:
                findings.append(
                    ReflectionFinding(
                        category=FindingCategory.BENCHMARK,
                        severity=Severity.HIGH,
                        title="Benchmark Failed",
                        description="The engineering task failed to pass the benchmark.",
                        confidence=1.0,
                    )
                )
                weaknesses.append("Benchmark failed")
            elif hasattr(benchmark_result, "metadata"):
                score = benchmark_result.metadata.get("score", 100)
                if score < 80:
                    findings.append(
                        ReflectionFinding(
                            category=FindingCategory.TESTING,
                            severity=Severity.MEDIUM,
                            title="Low Test Coverage",
                            description=f"Benchmark score was only {score}.",
                            confidence=0.8,
                        )
                    )
                    weaknesses.append("Low benchmark score")

                    recommendations.append(
                        ReflectionRecommendation(
                            priority=RecommendationPriority.NORMAL,
                            title="Increase Test Coverage",
                            description="Add more unit tests to cover edge cases.",
                            action="Schedule Testing Worker for additional tests.",
                            confidence=0.8,
                        )
                    )

        # If no findings, it was a perfect run
        if not findings:
            strengths.append("No issues detected")
            findings.append(
                ReflectionFinding(
                    category=FindingCategory.EXECUTION,
                    severity=Severity.INFO,
                    title="Successful Execution",
                    description="The engineering task completed without detectable issues.",
                    confidence=1.0,
                )
            )

        # Deterministic Sorting
        findings.sort(
            key=lambda f: (-self._SEVERITY_ORDER.get(f.severity, 0), -f.confidence, f.title)
        )
        recommendations.sort(
            key=lambda r: (-self._PRIORITY_ORDER.get(r.priority, 0), -r.confidence, r.title)
        )

        summary = ReflectionSummary(
            strengths=tuple(strengths),
            weaknesses=tuple(weaknesses),
            risks=tuple(),
            opportunities=tuple(),
        )

        # Simple deterministic metrics
        exec_score = 100 if run_result.outcome == "success" else 0
        review_score = 100
        if review_report and hasattr(review_report, "overall_score"):
            review_score = review_report.overall_score

        metrics = ReflectionMetrics(
            execution_score=exec_score,
            review_score=review_score,
            overall_score=(exec_score + review_score) // 2,
        )

        return ReflectionReport(
            run_id=context.run_id,
            summary=summary,
            findings=tuple(findings),
            recommendations=tuple(recommendations),
            metrics=metrics,
        )
