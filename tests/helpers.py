"""Shared test helpers for EAG tests."""

from pathlib import Path

from eag.execution import ExecutionPolicy
from eag.execution.classification import (
    CommandClassification,
    CommandClassifier,
    ExecutableRule,
    PolicyOutcome,
)


def allowing_policy(
    workspace: Path,
    *executables: str,
) -> ExecutionPolicy:
    """Create a test policy allowing selected executables."""
    classifier = CommandClassifier(
        rules=(
            ExecutableRule(
                rule_name="test.allowed",
                executables=frozenset(executables),
                classification=CommandClassification.VALIDATION,
                outcome=PolicyOutcome.ALLOW,
                reason="Allowed for testing.",
            ),
        )
    )

    return ExecutionPolicy(
        workspace=workspace,
        classifier=classifier,
    )


def permissive_python_policy(
    workspace: Path,
) -> ExecutionPolicy:
    """Create a policy allowing Python for executor tests."""
    return allowing_policy(
        workspace,
        "python",
        "python3",
    )


# Add to helpers.py


def approval_required_python_policy(workspace: Path) -> ExecutionPolicy:
    """Create a policy where Python commands require approval."""
    classifier = CommandClassifier(
        rules=(
            ExecutableRule(
                rule_name="test.python.requires_approval",
                executables=frozenset({"python", "python3"}),
                classification=CommandClassification.MUTATING,
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                reason="Python execution requires explicit approval for tests.",
            ),
        )
    )
    return ExecutionPolicy(
        workspace=workspace,
        classifier=classifier,
    )
