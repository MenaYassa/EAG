"""ChangeSet domain models and builder."""

from eag.changeset.builder import ChangeSetBuilder
from eag.changeset.errors import (
    ChangeSetError,
    ChangeSetFinalizedError,
    RecorderNotAttachedError,
)
from eag.changeset.events import (
    ChangeRecorded,
    ChangeSetBuilderStarted,
    ChangeSetCompleted,
    ChangeSetFinalized,
    ChangeSetRecordingStarted,
)
from eag.changeset.models import (
    ChangedFile,
    ChangeIdentity,
    ChangeRisk,
    ChangeSet,
    ChangeSummary,
    CommandRecord,
    ExecutionMetrics,
    FileChangeType,
    GitSnapshot,
    TestRecord,
)
from eag.changeset.recorder import ChangeSetRecorder
from eag.changeset.state import ChangeSetBuilderState

__all__ = [
    "ChangeIdentity",
    "ChangeRecorded",
    "ChangeRisk",
    "ChangeSet",
    "ChangeSetBuilder",
    "ChangeSetBuilderStarted",
    "ChangeSetBuilderState",
    "ChangeSetCompleted",
    "ChangeSetError",
    "ChangeSetFinalized",
    "ChangeSetFinalizedError",
    "ChangeSetRecordingStarted",
    "ChangeSetRecorder",
    "ChangeSummary",
    "ChangedFile",
    "CommandRecord",
    "ExecutionMetrics",
    "FileChangeType",
    "GitSnapshot",
    "RecorderNotAttachedError",
    "TestRecord",
]