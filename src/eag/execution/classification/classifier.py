"""Command policy classifier."""

from collections.abc import Iterable

from eag.execution.classification.models import (
    CommandClassification,
    PolicyDecision,
    PolicyOutcome,
)
from eag.execution.classification.rules import (
    CommandRule,
)
from eag.execution.models import CommandRequest


class CommandClassifier:
    """Evaluate command requests against ordered rules."""

    def __init__(
        self,
        *,
        rules: Iterable[CommandRule] = (),
    ) -> None:
        self._rules = tuple(rules)

    @property
    def rules(self) -> tuple[CommandRule, ...]:
        """Return classifier rules in evaluation order."""
        return self._rules

    def classify(
        self,
        request: CommandRequest,
    ) -> PolicyDecision:
        """Return the first matching policy decision."""
        for rule in self._rules:
            if rule.matches(request):
                return rule.decide(request)

        return PolicyDecision(
            request=request,
            classification=(CommandClassification.UNKNOWN),
            outcome=PolicyOutcome.REQUIRE_APPROVAL,
            reason=("No command policy rule matched the request."),
            matched_rule="default.unknown",
        )
