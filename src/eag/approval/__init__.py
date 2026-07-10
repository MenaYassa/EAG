"""EAG approval subsystem."""

from eag.approval.errors import (
    ApprovalAlreadyExistsError,
    ApprovalCommandMismatchError,
    ApprovalError,
    ApprovalExpiredError,
    ApprovalInvalidTransitionError,
    ApprovalNotFoundError,
)
from eag.approval.events import (
    ApprovalApproved,
    ApprovalConsumed,
    ApprovalExpired,
    ApprovalRejected,
    ApprovalRequested,
)
from eag.approval.manager import ApprovalManager
from eag.approval.models import (
    ApprovalRequest,
    ApprovalStatus,
    new_approval_request,
)
from eag.approval.store import (
    ApprovalStore,
    InMemoryApprovalStore,
)

__all__ = [
    "ApprovalAlreadyExistsError",
    "ApprovalCommandMismatchError",
    "ApprovalError",
    "ApprovalExpiredError",
    "ApprovalInvalidTransitionError",
    "ApprovalManager",
    "ApprovalNotFoundError",
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalStore",
    "InMemoryApprovalStore",
    "new_approval_request",
    "ApprovalApproved",
    "ApprovalConsumed",
    "ApprovalExpired",
    "ApprovalRejected",
    "ApprovalRequested",
]
