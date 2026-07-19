"""VCS transaction manager for EAG."""

from eag.vcs.enums import TransactionState
from eag.vcs.errors import TransactionError


class TransactionManager:
    """Manages atomic VCS operations."""

    def __init__(self) -> None:
        self._state = TransactionState.READY

    @property
    def state(self) -> TransactionState:
        return self._state

    def begin(self) -> None:
        if self._state == TransactionState.ACTIVE:
            raise TransactionError("Transaction already active.")
        self._state = TransactionState.ACTIVE

    def commit(self) -> None:
        if self._state != TransactionState.ACTIVE:
            raise TransactionError("No active transaction to commit.")
        self._state = TransactionState.COMMITTED

    def rollback(self) -> None:
        if self._state != TransactionState.ACTIVE:
            raise TransactionError("No active transaction to rollback.")
        self._state = TransactionState.ROLLED_BACK

    def reset(self) -> None:
        self._state = TransactionState.READY
