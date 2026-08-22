"""Library-only, execution-free admission contracts for controlled governed activation."""

from eag.governed_activation.admission import (
    GovernedActivationAdmission,
    admit_governed_activation,
)
from eag.governed_activation.models import (
    ActivationDisposition,
    ActivationRejectionReason,
    CallerActivationConfirmation,
    ExecutionIsolation,
    GovernedActivationDecision,
    GovernedActivationError,
    GovernedActivationReceipt,
    GovernedActivationRequest,
    ProviderExecutionPolicy,
)

__all__ = [
    "ActivationDisposition",
    "ActivationRejectionReason",
    "CallerActivationConfirmation",
    "ExecutionIsolation",
    "GovernedActivationAdmission",
    "GovernedActivationDecision",
    "GovernedActivationError",
    "GovernedActivationReceipt",
    "GovernedActivationRequest",
    "ProviderExecutionPolicy",
    "admit_governed_activation",
]
