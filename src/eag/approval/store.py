"""Approval storage contracts and implementations."""

from abc import ABC, abstractmethod

from eag.approval.errors import (
    ApprovalAlreadyExistsError,
    ApprovalNotFoundError,
)
from eag.approval.models import (
    ApprovalRequest,
    ApprovalStatus,
)


class ApprovalStore(ABC):
    """Storage contract for approval requests."""

    @abstractmethod
    def add(
        self,
        request: ApprovalRequest,
    ) -> None:
        """Persist a new approval request."""

    @abstractmethod
    def get(
        self,
        approval_id: str,
    ) -> ApprovalRequest:
        """Return an approval request by ID."""

    @abstractmethod
    def save(
        self,
        request: ApprovalRequest,
    ) -> None:
        """Persist changes to an existing request."""

    @abstractmethod
    def list(
        self,
        *,
        status: ApprovalStatus | None = None,
    ) -> tuple[ApprovalRequest, ...]:
        """Return approval requests, optionally filtered."""


class InMemoryApprovalStore(ApprovalStore):
    """Store approval requests in process memory."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def add(
        self,
        request: ApprovalRequest,
    ) -> None:
        """Persist a new approval request."""
        if request.id in self._requests:
            raise ApprovalAlreadyExistsError(f"Approval request already exists: '{request.id}'")

        self._requests[request.id] = request

    def get(
        self,
        approval_id: str,
    ) -> ApprovalRequest:
        """Return an approval request by ID."""
        try:
            return self._requests[approval_id]
        except KeyError as exc:
            raise ApprovalNotFoundError(f"Approval request not found: '{approval_id}'") from exc

    def save(
        self,
        request: ApprovalRequest,
    ) -> None:
        """Persist changes to an existing request."""
        if request.id not in self._requests:
            raise ApprovalNotFoundError(f"Approval request not found: '{request.id}'")

        self._requests[request.id] = request

    def list(
        self,
        *,
        status: ApprovalStatus | None = None,
    ) -> tuple[ApprovalRequest, ...]:
        """Return approval requests, optionally filtered."""
        requests = tuple(self._requests.values())

        if status is None:
            return requests

        return tuple(request for request in requests if request.status is status)
