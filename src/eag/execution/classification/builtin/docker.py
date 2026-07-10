"""Docker command policy rules."""

from eag.execution.classification.models import (
    CommandClassification,
    PolicyOutcome,
)
from eag.execution.classification.rules import (
    ExactCommandRule,
)


def docker_rules() -> tuple[ExactCommandRule, ...]:
    """Return built-in Docker policy rules."""
    return (
        ExactCommandRule(
            rule_name="docker.system.prune",
            executable="docker",
            argument_prefix=("system", "prune"),
            classification=(CommandClassification.DESTRUCTIVE),
            outcome=PolicyOutcome.DENY,
            reason=(
                "Docker system prune may remove images, containers, networks, and build cache."
            ),
        ),
        ExactCommandRule(
            rule_name="docker.volume.prune",
            executable="docker",
            argument_prefix=("volume", "prune"),
            classification=(CommandClassification.DESTRUCTIVE),
            outcome=PolicyOutcome.DENY,
            reason=("Docker volume prune may remove data."),
        ),
        ExactCommandRule(
            rule_name="docker.ps",
            executable="docker",
            argument_prefix=("ps",),
            classification=(CommandClassification.READ_ONLY),
            outcome=PolicyOutcome.ALLOW,
            reason="Listing Docker containers is read-only.",
        ),
        ExactCommandRule(
            rule_name="docker.images",
            executable="docker",
            argument_prefix=("images",),
            classification=(CommandClassification.READ_ONLY),
            outcome=PolicyOutcome.ALLOW,
            reason="Listing Docker images is read-only.",
        ),
        ExactCommandRule(
            rule_name="docker.compose.ps",
            executable="docker",
            argument_prefix=("compose", "ps"),
            classification=(CommandClassification.READ_ONLY),
            outcome=PolicyOutcome.ALLOW,
            reason=("Inspecting Docker Compose services is read-only."),
        ),
        ExactCommandRule(
            rule_name="docker.compose.build",
            executable="docker",
            argument_prefix=("compose", "build"),
            classification=(CommandClassification.BUILD),
            outcome=PolicyOutcome.ALLOW,
            reason=("Docker Compose build is an approved build operation."),
        ),
        ExactCommandRule(
            rule_name="docker.compose.down",
            executable="docker",
            argument_prefix=("compose", "down"),
            classification=(CommandClassification.MUTATING),
            outcome=PolicyOutcome.REQUIRE_APPROVAL,
            reason=("Stopping and removing Compose resources requires approval."),
        ),
    )
