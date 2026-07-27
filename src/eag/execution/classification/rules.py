"""Command classification rule contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from eag.execution.classification.models import (
    CommandClassification,
    PolicyDecision,
    PolicyOutcome,
)
from eag.execution.models import CommandRequest


class CommandRule(ABC):
    """Base contract for command policy rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable rule identifier."""

    @abstractmethod
    def matches(
        self,
        request: CommandRequest,
    ) -> bool:
        """Return whether this rule matches a request."""

    @abstractmethod
    def decide(
        self,
        request: CommandRequest,
    ) -> PolicyDecision:
        """Return the policy decision."""


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class ExactCommandRule(CommandRule):
    """Match an executable and argument prefix."""

    rule_name: str
    executable: str
    argument_prefix: tuple[str, ...]
    classification: CommandClassification
    outcome: PolicyOutcome
    reason: str

    @property
    def name(self) -> str:
        """Return the stable rule identifier."""
        return self.rule_name

    def matches(
        self,
        request: CommandRequest,
    ) -> bool:
        """Return whether executable and prefix match."""
        if request.executable != self.executable:
            return False

        prefix_length = len(self.argument_prefix)

        return request.arguments[:prefix_length] == self.argument_prefix

    def decide(
        self,
        request: CommandRequest,
    ) -> PolicyDecision:
        """Build the rule decision."""
        return PolicyDecision(
            request=request,
            classification=self.classification,
            outcome=self.outcome,
            reason=self.reason,
            matched_rule=self.name,
        )


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class ExecutableRule(CommandRule):
    """Match an executable regardless of arguments."""

    rule_name: str
    executables: frozenset[str]
    classification: CommandClassification
    outcome: PolicyOutcome
    reason: str

    @property
    def name(self) -> str:
        """Return the stable rule identifier."""
        return self.rule_name

    def matches(
        self,
        request: CommandRequest,
    ) -> bool:
        """Return whether executable matches."""
        return request.executable in self.executables

    def decide(
        self,
        request: CommandRequest,
    ) -> PolicyDecision:
        """Build the rule decision."""
        return PolicyDecision(
            request=request,
            classification=self.classification,
            outcome=self.outcome,
            reason=self.reason,
            matched_rule=self.name,
        )
