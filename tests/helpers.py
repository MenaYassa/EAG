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
