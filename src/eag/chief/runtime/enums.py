"""Chief Runtime domain vocabulary for EAG."""

from enum import StrEnum


class RunState(StrEnum):
    """Lifecycle state of a Chief run."""

    CREATED = "created"
    RECEIVED = "received"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    READY = "ready"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"

    @property
    def is_terminal(self) -> bool:
        return self in {RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED}

    def can_transition_to(self, target: "RunState") -> bool:
        if self.is_terminal:
            return False
        if self is target:
            return True
        allowed = {
            RunState.CREATED: {RunState.RECEIVED, RunState.CANCELLED},
            RunState.RECEIVED: {RunState.ANALYZING, RunState.PLANNING, RunState.CANCELLED},
            RunState.ANALYZING: {RunState.PLANNING, RunState.FAILED, RunState.CANCELLED},
            RunState.PLANNING: {RunState.READY, RunState.FAILED, RunState.CANCELLED},
            RunState.READY: {RunState.EXECUTING, RunState.CANCELLED},
            RunState.EXECUTING: {
                RunState.VALIDATING,
                RunState.COMPLETED,
                RunState.FAILED,
                RunState.PAUSED,
                RunState.CANCELLED,
                RunState.ROLLING_BACK,
            },  # Added COMPLETED here
            RunState.VALIDATING: {
                RunState.EXECUTING,
                RunState.COMPLETED,
                RunState.FAILED,
                RunState.ROLLING_BACK,
                RunState.CANCELLED,
            },
            RunState.PAUSED: {RunState.EXECUTING, RunState.CANCELLED},
            RunState.ROLLING_BACK: {RunState.FAILED, RunState.COMPLETED},
        }
        return target in allowed.get(self, set())


class RunPhase(StrEnum):
    """The current phase of a run."""

    INITIALIZATION = "initialization"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    COMPLETION = "completion"


class RunOutcome(StrEnum):
    """The final outcome of a run."""

    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class ValidationDecision(StrEnum):
    """Decisions the validator can make after an execution."""

    CONTINUE = "continue"
    RETRY = "retry"
    ROLLBACK = "rollback"
    ABORT = "abort"
    ESCALATE = "escalate"


class StepState(StrEnum):
    """Lifecycle state of a plan step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"
