"""Edit Transactions for EAG."""

from enum import StrEnum

from eag.source.python.transformations.edits import Edit
from eag.source.python.transformations.errors import TransactionError


class TransactionState(StrEnum):
    READY = "ready"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


class EditTransaction:
    """Manages atomic edit operations."""

    def __init__(self):
        self._state = TransactionState.READY
        self._edits: list[Edit] = []

    @property
    def state(self) -> TransactionState:
        return self._state

    def begin(self) -> None:
        if self._state == TransactionState.ACTIVE:
            raise TransactionError("Transaction already active")
        self._state = TransactionState.ACTIVE

    def add_edit(self, edit: Edit) -> None:
        if self._state != TransactionState.ACTIVE:
            raise TransactionError("Transaction not active")
        self._edits.append(edit)

    def commit(self) -> list[Edit]:
        if self._state != TransactionState.ACTIVE:
            raise TransactionError("Transaction not active")
        self._state = TransactionState.COMMITTED
        return self._edits

    def rollback(self) -> None:
        if self._state != TransactionState.ACTIVE:
            raise TransactionError("Transaction not active")
        self._state = TransactionState.ROLLED_BACK
        self._edits.clear()
