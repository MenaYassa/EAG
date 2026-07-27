"""Command classification subsystem."""

from eag.execution.classification.builtin import (
    builtin_rules,
)
from eag.execution.classification.classifier import (
    CommandClassifier,
)
from eag.execution.classification.models import (
    CommandClassification,
    PolicyDecision,
    PolicyOutcome,
)
from eag.execution.classification.rules import (
    CommandRule,
    ExactCommandRule,
    ExecutableRule,
)

__all__ = [
    "CommandClassification",
    "CommandClassifier",
    "CommandRule",
    "ExactCommandRule",
    "ExecutableRule",
    "PolicyDecision",
    "PolicyOutcome",
    "builtin_rules",
]
