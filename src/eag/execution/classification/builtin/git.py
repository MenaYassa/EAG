"""Git command policy rules."""

from eag.execution.classification.models import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.classification.rules import (
    ExactCommandRule,
)


def git_rules() -> tuple[ExactCommandRule, ...]:
    """Return built-in Git policy rules."""
    return (
        ExactCommandRule(
            rule_name="git.reset.hard",
            executable="git",
            argument_prefix=("reset", "--hard"),
            classification=(CommandClassification.DESTRUCTIVE),
            outcome=PolicyOutcome.DENY,
            reason=("Hard reset may discard uncommitted working-tree changes."),
        ),
        ExactCommandRule(
            rule_name="git.clean.force",
            executable="git",
            argument_prefix=("clean", "-f"),
            classification=(CommandClassification.DESTRUCTIVE),
            outcome=PolicyOutcome.DENY,
            reason=("Forced Git clean may delete untracked files."),
        ),
        ExactCommandRule(
            rule_name="git.status",
            executable="git",
            argument_prefix=("status",),
            classification=(CommandClassification.READ_ONLY),
            outcome=PolicyOutcome.ALLOW,
            reason="Git status is read-only.",
        ),
        ExactCommandRule(
            rule_name="git.diff",
            executable="git",
            argument_prefix=("diff",),
            classification=(CommandClassification.READ_ONLY),
            outcome=PolicyOutcome.ALLOW,
            reason="Git diff is read-only.",
        ),
        ExactCommandRule(
            rule_name="git.log",
            executable="git",
            argument_prefix=("log",),
            classification=(CommandClassification.READ_ONLY),
            outcome=PolicyOutcome.ALLOW,
            reason="Git log is read-only.",
        ),
        ExactCommandRule(
            rule_name="git.branch.list",
            executable="git",
            argument_prefix=("branch", "--list"),
            classification=(CommandClassification.READ_ONLY),
            outcome=PolicyOutcome.ALLOW,
            reason="Listing Git branches is read-only.",
        ),
        ExactCommandRule(
            rule_name="git.add",
            executable="git",
            argument_prefix=("add",),
            classification=(CommandClassification.MUTATING),
            outcome=PolicyOutcome.REQUIRE_APPROVAL,
            reason=("Staging changes mutates the Git index."),
        ),
        ExactCommandRule(
            rule_name="git.commit",
            executable="git",
            argument_prefix=("commit",),
            classification=(CommandClassification.MUTATING),
            outcome=PolicyOutcome.REQUIRE_APPROVAL,
            reason=("Creating commits requires explicit approval."),
        ),
        ExactCommandRule(
            rule_name="git.checkout",
            executable="git",
            argument_prefix=("checkout",),
            classification=(CommandClassification.MUTATING),
            outcome=PolicyOutcome.REQUIRE_APPROVAL,
            reason=("Git checkout may modify the working tree."),
        ),
        ExactCommandRule(
            rule_name="git.switch",
            executable="git",
            argument_prefix=("switch",),
            classification=(CommandClassification.MUTATING),
            outcome=PolicyOutcome.REQUIRE_APPROVAL,
            reason=("Switching branches may modify the working tree."),
        ),
    )
