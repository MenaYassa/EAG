"""ChangeSet builder states."""

from enum import StrEnum


class ChangeSetBuilderState(StrEnum):
    """States for a ChangeSetBuilder."""

    BUILDING = "building"
    FINALIZED = "finalized"


__all__ = [
    "ChangeSetBuilderState",
]