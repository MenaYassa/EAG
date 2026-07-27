"""Approval storage contracts and implementations."""

from abc import ABC, abstractmethod
from threading import RLock

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

    @abstractmethod
    def transition(
        self,
        approval_id: str,
        *,
        expected: ApprovalStatus,
        replacement: ApprovalRequest,
    ) -> bool:
        """Atomically replace a request when its status matches."""


class InMemoryApprovalStore(ApprovalStore):
    """Store approval requests in process memory."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._lock = RLock()

    def add(
        self,
        request: ApprovalRequest,
    ) -> None:
        """Persist a new approval request."""
        with self._lock:
            if request.id in self._requests:
                raise ApprovalAlreadyExistsError(f"Approval request already exists: '{request.id}'")

            self._requests[request.id] = request

    def get(
        self,
        approval_id: str,
    ) -> ApprovalRequest:
        """Return an approval request by ID."""
        with self._lock:
            try:
                return self._requests[approval_id]
            except KeyError as exc:
                raise ApprovalNotFoundError(f"Approval request not found: '{approval_id}'") from exc

    def save(
        self,
        request: ApprovalRequest,
    ) -> None:
        """Persist changes to an existing request."""
        with self._lock:
            if request.id not in self._requests:
                raise ApprovalNotFoundError(f"Approval request not found: '{request.id}'")

            self._requests[request.id] = request

    def list(
        self,
        *,
        status: ApprovalStatus | None = None,
    ) -> tuple[ApprovalRequest, ...]:
        """Return approval requests, optionally filtered."""
        with self._lock:
            requests = tuple(self._requests.values())

        if status is None:
            return requests

        return tuple(request for request in requests if request.status is status)

    def transition(
        self,
        approval_id: str,
        *,
        expected: ApprovalStatus,
        replacement: ApprovalRequest,
    ) -> bool:
        """Atomically replace a request when its status matches."""
        with self._lock:
            try:
                current = self._requests[approval_id]
            except KeyError as exc:
                raise ApprovalNotFoundError(f"Approval request not found: '{approval_id}'") from exc

            if replacement.id != approval_id:
                raise ValueError("Replacement approval ID must match transition target")

            if current.status is not expected:
                return False

            self._requests[approval_id] = replacement
            return True
