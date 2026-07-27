"""Node.js ecosystem command policy rules."""

from eag.execution.classification.models import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.classification.rules import (
    ExactCommandRule,
)


def node_rules() -> tuple[ExactCommandRule, ...]:
    """Return built-in Node.js ecosystem rules."""
    return (
        ExactCommandRule(
            rule_name="node.npm.test",
            executable="npm",
            argument_prefix=("test",),
            classification=(CommandClassification.VALIDATION),
            outcome=PolicyOutcome.ALLOW,
            reason="Running npm tests is allowed.",
        ),
        ExactCommandRule(
            rule_name="node.npm.build",
            executable="npm",
            argument_prefix=("run", "build"),
            classification=(CommandClassification.BUILD),
            outcome=PolicyOutcome.ALLOW,
            reason="Running npm build is allowed.",
        ),
        ExactCommandRule(
            rule_name="node.pnpm.test",
            executable="pnpm",
            argument_prefix=("test",),
            classification=(CommandClassification.VALIDATION),
            outcome=PolicyOutcome.ALLOW,
            reason="Running pnpm tests is allowed.",
        ),
        ExactCommandRule(
            rule_name="node.pnpm.build",
            executable="pnpm",
            argument_prefix=("run", "build"),
            classification=(CommandClassification.BUILD),
            outcome=PolicyOutcome.ALLOW,
            reason="Running pnpm build is allowed.",
        ),
    )
