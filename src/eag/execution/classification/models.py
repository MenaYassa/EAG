"""Command classification and policy decision models."""

from dataclasses import dataclass
from enum import StrEnum

from eag.execution.models import CommandRequest


class CommandClassification(StrEnum):
    """Describe the operational effect of a command."""

    READ_ONLY = "read_only"
    VALIDATION = "validation"
    BUILD = "build"
    MUTATING = "mutating"
    PRIVILEGED = "privileged"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"


class PolicyOutcome(StrEnum):
    """Describe whether execution may proceed."""

    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class PolicyDecision:
    """Describe the result of command policy evaluation."""

    request: CommandRequest
    classification: CommandClassification
    outcome: PolicyOutcome
    reason: str
    matched_rule: str

    @property
    def allowed(self) -> bool:
        """Return whether execution may proceed immediately."""
        return self.outcome is PolicyOutcome.ALLOW

    @property
    def requires_approval(self) -> bool:
        """Return whether execution requires approval."""
        return self.outcome is PolicyOutcome.REQUIRE_APPROVAL

    @property
    def denied(self) -> bool:
        """Return whether execution is denied."""
        return self.outcome is PolicyOutcome.DENY
