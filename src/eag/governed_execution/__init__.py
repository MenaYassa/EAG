"""G2.4.1 deterministic governed execution state-machine foundation."""

from eag.governed_execution.enums import (
    ExecutionEvidenceKind,
    GovernedExecutionState,
    GovernedExecutionStopReason,
)
from eag.governed_execution.errors import IllegalTransitionError
from eag.governed_execution.events import (
    GovernedExecutionEvent,
    GovernedExecutionStarted,
    GovernedExecutionStopped,
    GovernedExecutionTransitioned,
)
from eag.governed_execution.models import (
    ExecutionBudget,
    ExecutionEvidenceRef,
    ExecutionTransitionRecord,
    GovernedExecutionContext,
    TransitionResult,
)
from eag.governed_execution.state_machine import (
    LEGAL_TRANSITIONS,
    GovernedExecutionStateMachine,
)
from eag.governed_execution.verification import (
    VERIFICATION_CONTRACT_VERSION,
    DeterministicVerifier,
    ObjectiveAssessment,
    ObjectiveCompletionPolicy,
    ObjectiveFailureCode,
    ObjectiveStatus,
    VerificationCheck,
    VerificationEvidence,
    VerificationFailureCode,
    VerificationRequest,
    VerificationRequestError,
    VerificationResult,
    VerificationSpecification,
    VerificationStatus,
)

__all__ = [
    "ExecutionBudget",
    "ExecutionEvidenceKind",
    "ExecutionEvidenceRef",
    "ExecutionTransitionRecord",
    "GovernedExecutionContext",
    "GovernedExecutionEvent",
    "GovernedExecutionStarted",
    "GovernedExecutionState",
    "GovernedExecutionStateMachine",
    "GovernedExecutionStopReason",
    "GovernedExecutionStopped",
    "GovernedExecutionTransitioned",
    "IllegalTransitionError",
    "LEGAL_TRANSITIONS",
    "TransitionResult",
    "VERIFICATION_CONTRACT_VERSION",
    "VerificationCheck",
    "VerificationEvidence",
    "VerificationFailureCode",
    "VerificationRequest",
    "VerificationRequestError",
    "VerificationResult",
    "VerificationSpecification",
    "VerificationStatus",
    "DeterministicVerifier",
    "ObjectiveAssessment",
    "ObjectiveCompletionPolicy",
    "ObjectiveFailureCode",
    "ObjectiveStatus",
]
