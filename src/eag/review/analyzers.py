"""Built-in review analyzers for EAG."""

from eag.review.enums import IssueCategory, Severity
from eag.review.models import ReviewContext, ReviewIssue


class CorrectnessAnalyzer:
    """Checks if the execution succeeded without runtime errors."""

    def analyze(self, context: ReviewContext) -> tuple[ReviewIssue, ...]:
        issues: list[ReviewIssue] = []
        if not context.execution_success:
            issues.append(
                ReviewIssue(
                    category=IssueCategory.CORRECTNESS,
                    severity=Severity.CRITICAL,
                    title="Execution Failed",
                    description="The engineering execution step reported a failure.",
                    recommendation="Check execution logs and fix the runtime error.",
                )
            )
        return tuple(issues)


class TestingAnalyzer:
    """Checks if tests exist and pass (simulated via metadata)."""

    def analyze(self, context: ReviewContext) -> tuple[ReviewIssue, ...]:
        issues: list[ReviewIssue] = []
        tests_pass = context.metadata.get("tests_pass", False)
        tests_exist = context.metadata.get("tests_exist", False)

        if not tests_exist:
            issues.append(
                ReviewIssue(
                    category=IssueCategory.TESTING,
                    severity=Severity.ERROR,
                    title="Missing Tests",
                    description="No test files were found in the workspace.",
                    recommendation="Generate unit tests for the implemented features.",
                )
            )
        elif not tests_pass:
            issues.append(
                ReviewIssue(
                    category=IssueCategory.TESTING,
                    severity=Severity.ERROR,
                    title="Failing Tests",
                    description="One or more tests failed during execution.",
                    recommendation="Debug the failing tests and update the implementation.",
                )
            )
        return tuple(issues)


class DocumentationAnalyzer:
    """Checks for basic documentation."""

    def analyze(self, context: ReviewContext) -> tuple[ReviewIssue, ...]:
        issues: list[ReviewIssue] = []
        readme_exists = context.metadata.get("readme_exists", False)

        if not readme_exists:
            issues.append(
                ReviewIssue(
                    category=IssueCategory.DOCUMENTATION,
                    severity=Severity.WARNING,
                    title="Missing README",
                    description="The project is missing a README.md file.",
                    recommendation="Generate a README.md with usage instructions.",
                )
            )
        return tuple(issues)
