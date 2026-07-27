"""System-level command policy rules."""

from eag.execution.classification.models import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.classification.rules import (
    ExecutableRule,
)


def system_rules() -> tuple[ExecutableRule, ...]:
    """Return built-in system command rules."""
    return (
        ExecutableRule(
            rule_name="system.privileged",
            executables=frozenset(
                {
                    "sudo",
                    "su",
                    "doas",
                }
            ),
            classification=(CommandClassification.PRIVILEGED),
            outcome=PolicyOutcome.DENY,
            reason=("Privilege escalation commands are not permitted."),
        ),
        ExecutableRule(
            rule_name="system.destructive",
            executables=frozenset(
                {
                    "rm",
                    "shred",
                    "mkfs",
                    "fdisk",
                    "parted",
                    "shutdown",
                    "reboot",
                    "poweroff",
                    "halt",
                }
            ),
            classification=(CommandClassification.DESTRUCTIVE),
            outcome=PolicyOutcome.DENY,
            reason=("Potentially destructive system commands are denied."),
        ),
    )
