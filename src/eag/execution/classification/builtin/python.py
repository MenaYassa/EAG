"""Python ecosystem command policy rules."""

from eag.execution.classification.models import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.classification.rules import (
    ExactCommandRule,
    ExecutableRule,
)


def python_rules() -> tuple[
    ExactCommandRule | ExecutableRule,
    ...,
]:
    """Return built-in Python ecosystem rules."""
    return (
        ExecutableRule(
            rule_name="python.pytest",
            executables=frozenset(
                {
                    "pytest",
                }
            ),
            classification=(CommandClassification.VALIDATION),
            outcome=PolicyOutcome.ALLOW,
            reason="Running tests is allowed.",
        ),
        ExecutableRule(
            rule_name="python.ruff",
            executables=frozenset(
                {
                    "ruff",
                }
            ),
            classification=(CommandClassification.VALIDATION),
            outcome=PolicyOutcome.ALLOW,
            reason=("Running Ruff validation is allowed."),
        ),
        ExecutableRule(
            rule_name="python.mypy",
            executables=frozenset(
                {
                    "mypy",
                }
            ),
            classification=(CommandClassification.VALIDATION),
            outcome=PolicyOutcome.ALLOW,
            reason=("Running static type checks is allowed."),
        ),
        ExactCommandRule(
            rule_name="python.uv.pytest",
            executable="uv",
            argument_prefix=("run", "pytest"),
            classification=(CommandClassification.VALIDATION),
            outcome=PolicyOutcome.ALLOW,
            reason=("Running tests through uv is allowed."),
        ),
        ExactCommandRule(
            rule_name="python.uv.ruff",
            executable="uv",
            argument_prefix=("run", "ruff"),
            classification=(CommandClassification.VALIDATION),
            outcome=PolicyOutcome.ALLOW,
            reason=("Running Ruff through uv is allowed."),
        ),
        ExactCommandRule(
            rule_name="python.uv.mypy",
            executable="uv",
            argument_prefix=("run", "mypy"),
            classification=(CommandClassification.VALIDATION),
            outcome=PolicyOutcome.ALLOW,
            reason=("Running mypy through uv is allowed."),
        ),
    )
