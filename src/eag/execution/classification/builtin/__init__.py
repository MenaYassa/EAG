"""Built-in command classification rules."""

from eag.execution.classification.builtin.docker import (
    docker_rules,
)
from eag.execution.classification.builtin.generic import (
    generic_rules,
)
from eag.execution.classification.builtin.git import (
    git_rules,
)
from eag.execution.classification.builtin.node import (
    node_rules,
)
from eag.execution.classification.builtin.python import (
    python_rules,
)
from eag.execution.classification.builtin.system import (
    system_rules,
)
from eag.execution.classification.rules import (
    CommandRule,
)


def builtin_rules() -> tuple[CommandRule, ...]:
    """Return built-in rules in evaluation order."""
    return (
        *system_rules(),
        *git_rules(),
        *docker_rules(),
        *python_rules(),
        *node_rules(),
        *generic_rules(),
    )


__all__ = [
    "builtin_rules",
]
