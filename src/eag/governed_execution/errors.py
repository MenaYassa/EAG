"""Typed errors for the pure G2.4.1 execution state-machine contract."""

from __future__ import annotations

from dataclasses import dataclass

from eag.governed_execution.enums import GovernedExecutionState


@dataclass(frozen=True, slots=True)
class IllegalTransitionError(ValueError):
    """Raised only by the strict transition API for a disallowed state change."""

    from_state: GovernedExecutionState
    to_state: GovernedExecutionState
    code: str = "illegal_transition"

    def __str__(self) -> str:
        return f"{self.code}: {self.from_state.value} -> {self.to_state.value}"


__all__ = ["IllegalTransitionError"]
