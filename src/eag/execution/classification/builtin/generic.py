"""Generic command policy rules."""

from eag.execution.classification.models import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.classification.rules import (
    ExecutableRule,
)


def generic_rules() -> tuple[ExecutableRule, ...]:
    """Return generic command policy rules."""
    return (
        ExecutableRule(
            rule_name="generic.read_only",
            executables=frozenset(
                {
                    "pwd",
                    "whoami",
                    "hostname",
                    "uname",
                }
            ),
            classification=(CommandClassification.READ_ONLY),
            outcome=PolicyOutcome.ALLOW,
            reason=("Command is recognized as read-only."),
        ),
    )
