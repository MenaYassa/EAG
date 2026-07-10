"""Tests for command classification and execution policy."""

from pathlib import Path

import pytest

from eag.execution import (
    CommandRequest,
    ExecutionPolicy,
)
from eag.execution.classification import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.errors import (
    CommandApprovalRequiredError,
    CommandDeniedError,
)


@pytest.fixture
def policy(tmp_path: Path) -> ExecutionPolicy:
    """Create the production execution policy."""
    return ExecutionPolicy(workspace=tmp_path)


@pytest.mark.parametrize(
    (
        "executable",
        "arguments",
        "classification",
        "outcome",
        "matched_rule",
    ),
    (
        (
            "git",
            ("status",),
            CommandClassification.READ_ONLY,
            PolicyOutcome.ALLOW,
            "git.status",
        ),
        (
            "git",
            ("diff",),
            CommandClassification.READ_ONLY,
            PolicyOutcome.ALLOW,
            "git.diff",
        ),
        (
            "git",
            ("reset", "--hard", "HEAD"),
            CommandClassification.DESTRUCTIVE,
            PolicyOutcome.DENY,
            "git.reset.hard",
        ),
        (
            "git",
            ("add", "."),
            CommandClassification.MUTATING,
            PolicyOutcome.REQUIRE_APPROVAL,
            "git.add",
        ),
        (
            "git",
            ("commit", "-m", "test"),
            CommandClassification.MUTATING,
            PolicyOutcome.REQUIRE_APPROVAL,
            "git.commit",
        ),
        (
            "docker",
            ("ps",),
            CommandClassification.READ_ONLY,
            PolicyOutcome.ALLOW,
            "docker.ps",
        ),
        (
            "docker",
            ("compose", "ps"),
            CommandClassification.READ_ONLY,
            PolicyOutcome.ALLOW,
            "docker.compose.ps",
        ),
        (
            "docker",
            ("compose", "build"),
            CommandClassification.BUILD,
            PolicyOutcome.ALLOW,
            "docker.compose.build",
        ),
        (
            "docker",
            ("compose", "down"),
            CommandClassification.MUTATING,
            PolicyOutcome.REQUIRE_APPROVAL,
            "docker.compose.down",
        ),
        (
            "docker",
            ("system", "prune", "-a"),
            CommandClassification.DESTRUCTIVE,
            PolicyOutcome.DENY,
            "docker.system.prune",
        ),
        (
            "pytest",
            ("-q",),
            CommandClassification.VALIDATION,
            PolicyOutcome.ALLOW,
            "python.pytest",
        ),
        (
            "uv",
            ("run", "pytest"),
            CommandClassification.VALIDATION,
            PolicyOutcome.ALLOW,
            "python.uv.pytest",
        ),
        (
            "ruff",
            ("check", "."),
            CommandClassification.VALIDATION,
            PolicyOutcome.ALLOW,
            "python.ruff",
        ),
        (
            "mypy",
            ("src",),
            CommandClassification.VALIDATION,
            PolicyOutcome.ALLOW,
            "python.mypy",
        ),
        (
            "npm",
            ("test",),
            CommandClassification.VALIDATION,
            PolicyOutcome.ALLOW,
            "node.npm.test",
        ),
        (
            "npm",
            ("run", "build"),
            CommandClassification.BUILD,
            PolicyOutcome.ALLOW,
            "node.npm.build",
        ),
        (
            "sudo",
            ("apt", "update"),
            CommandClassification.PRIVILEGED,
            PolicyOutcome.DENY,
            "system.privileged",
        ),
        (
            "rm",
            ("-rf", "src"),
            CommandClassification.DESTRUCTIVE,
            PolicyOutcome.DENY,
            "system.destructive",
        ),
        (
            "strange-tool",
            ("hello",),
            CommandClassification.UNKNOWN,
            PolicyOutcome.REQUIRE_APPROVAL,
            "default.unknown",
        ),
    ),
)
def test_policy_classification(
    policy: ExecutionPolicy,
    executable: str,
    arguments: tuple[str, ...],
    classification: CommandClassification,
    outcome: PolicyOutcome,
    matched_rule: str,
) -> None:
    """Test built-in command classification decisions."""
    request = CommandRequest(
        executable=executable,
        arguments=arguments,
    )

    decision = policy.evaluate(request)

    assert decision.classification is classification
    assert decision.outcome is outcome
    assert decision.matched_rule == matched_rule


def test_authorize_allows_safe_command(
    policy: ExecutionPolicy,
) -> None:
    """Test immediate authorization for allowed commands."""
    request = CommandRequest(
        executable="git",
        arguments=("status",),
    )

    decision = policy.authorize(request)

    assert decision.outcome is PolicyOutcome.ALLOW


def test_authorize_requires_approval(
    policy: ExecutionPolicy,
) -> None:
    """Test approval requirement enforcement."""
    request = CommandRequest(
        executable="git",
        arguments=("commit", "-m", "test"),
    )

    with pytest.raises(CommandApprovalRequiredError) as exc_info:
        policy.authorize(request)

    assert exc_info.value.decision.matched_rule == "git.commit"


def test_authorize_denies_destructive_command(
    policy: ExecutionPolicy,
) -> None:
    """Test destructive command denial."""
    request = CommandRequest(
        executable="rm",
        arguments=("-rf", "src"),
    )

    with pytest.raises(CommandDeniedError) as exc_info:
        policy.authorize(request)

    assert exc_info.value.decision.matched_rule == "system.destructive"
