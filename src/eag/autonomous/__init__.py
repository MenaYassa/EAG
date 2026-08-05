"""Autonomous Engineering Loop Platform for EAG."""

from eag.autonomous.approval import ApprovalRuntime
from eag.autonomous.completion import CompletionEngine
from eag.autonomous.enums import (
    ApprovalState,
    CompletionAction,
    LoopOutcome,
    LoopState,
    RecoveryActionType,
    RecoveryPolicy,
)
from eag.autonomous.models import (
    ApprovalRequest,
    LoopContext,
    LoopDecision,
    LoopIteration,
    LoopMetrics,
    LoopResult,
    RecoveryAction,
)
from eag.autonomous.recovery import RecoveryEngine
from eag.autonomous.runtime import AutonomousLoopRuntime

__all__ = [
    # Enums
    "ApprovalState",
    "CompletionAction",
    "LoopOutcome",
    "LoopState",
    "RecoveryActionType",
    "RecoveryPolicy",
    # Models
    "ApprovalRequest",
    "LoopContext",
    "LoopDecision",
    "LoopIteration",
    "LoopMetrics",
    "LoopResult",
    "RecoveryAction",
    # Components
    "ApprovalRuntime",
    "AutonomousLoopRuntime",
    "CompletionEngine",
    "RecoveryEngine",
]
