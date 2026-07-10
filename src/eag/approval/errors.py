"""Approval subsystem errors."""


class ApprovalError(Exception):
    """Base error for approval operations."""


class ApprovalNotFoundError(ApprovalError):
    """Raised when an approval request does not exist."""


class ApprovalAlreadyExistsError(ApprovalError):
    """Raised when an approval ID already exists."""


class ApprovalInvalidTransitionError(ApprovalError):
    """Raised when an approval lifecycle transition is invalid."""


class ApprovalExpiredError(ApprovalError):
    """Raised when an approval request has expired."""


class ApprovalCommandMismatchError(ApprovalError):
    """Raised when execution does not match the approved command."""
