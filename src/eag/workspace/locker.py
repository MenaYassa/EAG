"""Workspace locker for EAG."""

from eag.workspace.enums import LockState
from eag.workspace.errors import WorkspaceLockedError


class WorkspaceLocker:
    """Prevents concurrent modification of the workspace."""

    def __init__(self) -> None:
        self._state = LockState.UNLOCKED

    @property
    def state(self) -> LockState:
        return self._state

    def acquire(self) -> None:
        if self._state == LockState.LOCKED:
            raise WorkspaceLockedError("Workspace is already locked.")
        self._state = LockState.LOCKED

    def release(self) -> None:
        self._state = LockState.RELEASED
