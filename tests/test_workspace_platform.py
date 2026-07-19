"""Comprehensive tests for the Workspace Platform (Sprint 6.3)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from eag.events import EventBus
from eag.workspace.diff import DiffEngine
from eag.workspace.enums import (
    DiffType,
    LockState,
    WorkspaceMode,
    WorkspaceState,
)
from eag.workspace.errors import (
    PathTraversalError,
    WorkspaceLockedError,
    WorkspaceValidationError,
)
from eag.workspace.events import (
    FileRead,
    FileWritten,
    WorkspaceOpened,
)
from eag.workspace.filesystem import LocalFilesystem
from eag.workspace.locker import WorkspaceLocker
from eag.workspace.manifest import ManifestBuilder
from eag.workspace.models import (
    DiffEntry,
    FileEntry,
    Manifest,
    Snapshot,
    Workspace,
)
from eag.workspace.resolver import PathResolver
from eag.workspace.runtime import WorkspaceRuntime
from eag.workspace.snapshot import SnapshotEngine
from eag.workspace.validator import WorkspaceValidator


@pytest.fixture
def temp_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def filesystem() -> LocalFilesystem:
    return LocalFilesystem()


@pytest.fixture
def resolver(temp_root: Path) -> PathResolver:
    return PathResolver(temp_root)


@pytest.fixture
def validator() -> WorkspaceValidator:
    return WorkspaceValidator()


@pytest.fixture
def locker() -> WorkspaceLocker:
    return WorkspaceLocker()


@pytest.fixture
def manifest_builder(filesystem: LocalFilesystem) -> ManifestBuilder:
    return ManifestBuilder(filesystem)


@pytest.fixture
def snapshot_engine(
    filesystem: LocalFilesystem, manifest_builder: ManifestBuilder
) -> SnapshotEngine:
    return SnapshotEngine(filesystem, manifest_builder)


@pytest.fixture
def diff_engine() -> DiffEngine:
    return DiffEngine()


@pytest.fixture
def runtime(temp_root: Path, event_bus: EventBus) -> WorkspaceRuntime:
    rt = WorkspaceRuntime(root=temp_root, mode=WorkspaceMode.LIVE, event_bus=event_bus)
    rt.open()
    return rt


class TestWorkspaceEnums:
    def test_workspace_mode_values(self) -> None:
        assert WorkspaceMode.LIVE == "live"
        assert WorkspaceMode.DRY_RUN == "dry_run"
        assert WorkspaceMode.READ_ONLY == "read_only"

    def test_workspace_state_values(self) -> None:
        assert WorkspaceState.READY == "ready"
        assert WorkspaceState.LOCKED == "locked"

    def test_lock_state_values(self) -> None:
        assert LockState.UNLOCKED == "unlocked"
        assert LockState.LOCKED == "locked"

    def test_diff_type_values(self) -> None:
        assert DiffType.ADDED == "added"
        assert DiffType.MODIFIED == "modified"


class TestWorkspaceModels:
    def test_workspace_is_immutable(self, temp_root: Path) -> None:
        ws = Workspace(root=temp_root)
        with pytest.raises(AttributeError):
            ws.root = Path("/other")  # type: ignore[misc]

    def test_workspace_validation_requires_path(self) -> None:
        with pytest.raises(TypeError):
            Workspace(root="/not/a/path")  # type: ignore[arg-type]

    def test_file_entry_creation(self) -> None:
        entry = FileEntry(path="test.py", size=100, hash="abc", modified_at=datetime.now(UTC))
        assert entry.path == "test.py"

    def test_manifest_is_immutable(self, temp_root: Path) -> None:
        manifest = Manifest(root=temp_root)
        with pytest.raises(AttributeError):
            manifest.files = ()  # type: ignore[misc]

    def test_snapshot_is_immutable(self, temp_root: Path) -> None:
        manifest = Manifest(root=temp_root)
        snap = Snapshot(manifest=manifest)
        with pytest.raises(AttributeError):
            snap.timestamp = datetime.now()  # type: ignore[misc]

    def test_diff_entry_creation(self) -> None:
        entry = DiffEntry(path="test.py", type=DiffType.MODIFIED)
        assert entry.type == DiffType.MODIFIED


class TestPathResolver:
    def test_resolve_safe_relative_path(self, resolver: PathResolver, temp_root: Path) -> None:
        resolved = resolver.resolve("test.txt")
        assert resolved == temp_root / "test.txt"

    def test_resolve_safe_absolute_path_inside(
        self, resolver: PathResolver, temp_root: Path
    ) -> None:
        abs_path = temp_root / "src" / "app.py"
        resolved = resolver.resolve(abs_path)
        assert resolved == abs_path

    def test_block_path_traversal(self, resolver: PathResolver) -> None:
        with pytest.raises(PathTraversalError):
            resolver.resolve("../../etc/passwd")

    def test_block_absolute_path_outside(self, resolver: PathResolver) -> None:
        with pytest.raises(PathTraversalError):
            resolver.resolve("/etc/passwd")


class TestWorkspaceValidator:
    def test_validate_missing_root(self, validator: WorkspaceValidator) -> None:
        with pytest.raises(WorkspaceValidationError, match="does not exist"):
            validator.validate(Path("/nonexistent/path"), WorkspaceMode.LIVE)

    def test_validate_not_a_directory(self, validator: WorkspaceValidator, temp_root: Path) -> None:
        file_path = temp_root / "file.txt"
        file_path.write_text("test")
        with pytest.raises(WorkspaceValidationError, match="not a directory"):
            validator.validate(file_path, WorkspaceMode.LIVE)

    def test_validate_read_only_mode_skips_write_check(
        self, validator: WorkspaceValidator, temp_root: Path
    ) -> None:
        # Should not raise even if we don't explicitly mock write permissions
        validator.validate(temp_root, WorkspaceMode.READ_ONLY)


class TestWorkspaceLocker:
    def test_initial_state_is_unlocked(self, locker: WorkspaceLocker) -> None:
        assert locker.state == LockState.UNLOCKED

    def test_acquire_lock(self, locker: WorkspaceLocker) -> None:
        locker.acquire()
        assert locker.state == LockState.LOCKED

    def test_double_acquire_raises(self, locker: WorkspaceLocker) -> None:
        locker.acquire()
        with pytest.raises(WorkspaceLockedError):
            locker.acquire()

    def test_release_lock(self, locker: WorkspaceLocker) -> None:
        locker.acquire()
        locker.release()
        assert locker.state == LockState.RELEASED


class TestLocalFilesystem:
    def test_read_write(self, filesystem: LocalFilesystem, temp_root: Path) -> None:
        file_path = temp_root / "test.txt"
        filesystem.write(file_path, "Hello EAG")
        assert filesystem.read(file_path) == "Hello EAG"

    def test_copy(self, filesystem: LocalFilesystem, temp_root: Path) -> None:
        src = temp_root / "src.txt"
        dest = temp_root / "dest.txt"
        filesystem.write(src, "Copy me")
        filesystem.copy(src, dest)
        assert filesystem.read(dest) == "Copy me"

    def test_move(self, filesystem: LocalFilesystem, temp_root: Path) -> None:
        src = temp_root / "src.txt"
        dest = temp_root / "dest.txt"
        filesystem.write(src, "Move me")
        filesystem.move(src, dest)
        assert not filesystem.exists(src)
        assert filesystem.read(dest) == "Move me"

    def test_delete(self, filesystem: LocalFilesystem, temp_root: Path) -> None:
        file_path = temp_root / "test.txt"
        filesystem.write(file_path, "Delete me")
        filesystem.delete(file_path)
        assert not filesystem.exists(file_path)

    def test_mkdir(self, filesystem: LocalFilesystem, temp_root: Path) -> None:
        dir_path = temp_root / "new_dir"
        filesystem.mkdir(dir_path)
        assert filesystem.exists(dir_path)

    def test_list_files(self, filesystem: LocalFilesystem, temp_root: Path) -> None:
        filesystem.write(temp_root / "a.txt", "a")
        filesystem.write(temp_root / "b.txt", "b")
        files = filesystem.list_files(temp_root)
        assert len(files) == 2

    def test_hash_file(self, filesystem: LocalFilesystem, temp_root: Path) -> None:
        file_path = temp_root / "test.txt"
        filesystem.write(file_path, "Hash me")
        h = filesystem.hash_file(file_path)
        assert isinstance(h, str) and len(h) == 64  # SHA256 hex length


class TestManifestBuilder:
    def test_build_manifest_ignores_git(
        self, filesystem: LocalFilesystem, manifest_builder: ManifestBuilder, temp_root: Path
    ) -> None:
        (temp_root / ".git").mkdir()
        (temp_root / ".git" / "config").write_text("git stuff")
        (temp_root / "app.py").write_text("print('hello')")

        manifest = manifest_builder.build(temp_root)
        assert len(manifest.files) == 1
        assert manifest.files[0].path == "app.py"

    def test_build_manifest_captures_directories(
        self, filesystem: LocalFilesystem, manifest_builder: ManifestBuilder, temp_root: Path
    ) -> None:
        (temp_root / "src").mkdir()
        (temp_root / "src" / "app.py").write_text("print('hello')")

        manifest = manifest_builder.build(temp_root)
        assert "src" in manifest.directories
        assert len(manifest.files) == 1


class TestSnapshotEngine:
    def test_create_snapshot(self, snapshot_engine: SnapshotEngine, temp_root: Path) -> None:
        (temp_root / "app.py").write_text("print('hello')")
        snap = snapshot_engine.create(temp_root)

        assert isinstance(snap, Snapshot)
        assert len(snap.manifest.files) == 1
        assert snap.manifest.files[0].path == "app.py"

    def test_snapshot_consistency(self, snapshot_engine: SnapshotEngine, temp_root: Path) -> None:
        (temp_root / "app.py").write_text("print('hello')")
        snap1 = snapshot_engine.create(temp_root)
        snap2 = snapshot_engine.create(temp_root)

        assert snap1.manifest.files[0].hash == snap2.manifest.files[0].hash


class TestDiffEngine:
    def test_diff_added_file(self, diff_engine: DiffEngine, temp_root: Path) -> None:
        old = Manifest(root=temp_root, files=())
        new = Manifest(
            root=temp_root,
            files=(FileEntry(path="new.py", size=10, hash="a", modified_at=datetime.now(UTC)),),
        )

        diffs = diff_engine.diff(old, new)
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.ADDED

    def test_diff_removed_file(self, diff_engine: DiffEngine, temp_root: Path) -> None:
        old = Manifest(
            root=temp_root,
            files=(FileEntry(path="old.py", size=10, hash="a", modified_at=datetime.now(UTC)),),
        )
        new = Manifest(root=temp_root, files=())

        diffs = diff_engine.diff(old, new)
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.REMOVED

    def test_diff_modified_file(self, diff_engine: DiffEngine, temp_root: Path) -> None:
        old = Manifest(
            root=temp_root,
            files=(FileEntry(path="mod.py", size=10, hash="a", modified_at=datetime.now(UTC)),),
        )
        new = Manifest(
            root=temp_root,
            files=(FileEntry(path="mod.py", size=20, hash="b", modified_at=datetime.now(UTC)),),
        )

        diffs = diff_engine.diff(old, new)
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.MODIFIED

    def test_diff_unchanged_file(self, diff_engine: DiffEngine, temp_root: Path) -> None:
        entry = FileEntry(path="same.py", size=10, hash="a", modified_at=datetime.now(UTC))
        old = Manifest(root=temp_root, files=(entry,))
        new = Manifest(root=temp_root, files=(entry,))

        diffs = diff_engine.diff(old, new)
        assert len(diffs) == 0


class TestWorkspaceRuntimeIntegration:
    def test_open_sets_ready_state(self, runtime: WorkspaceRuntime) -> None:
        assert runtime.health().state == WorkspaceState.READY

    def test_write_and_read(self, runtime: WorkspaceRuntime) -> None:
        runtime.write("test.txt", "Hello Platform")
        content = runtime.read("test.txt")
        assert content == "Hello Platform"
        assert runtime.health().state == WorkspaceState.MODIFIED

    def test_write_blocked_when_locked(self, runtime: WorkspaceRuntime) -> None:
        runtime._manager._locker.acquire()
        with pytest.raises(WorkspaceLockedError):
            runtime.write("test.txt", "test")
        runtime._manager._locker.release()

    def test_close_sets_closed_state(self, runtime: WorkspaceRuntime) -> None:
        runtime.close()
        assert runtime.health().state == WorkspaceState.CLOSED

    def test_events_published_on_open(self, temp_root: Path, event_bus: EventBus) -> None:
        from unittest.mock import MagicMock

        # Replace the real publish method with a mock to record calls
        event_bus.publish = MagicMock()

        rt = WorkspaceRuntime(root=temp_root, mode=WorkspaceMode.LIVE, event_bus=event_bus)
        rt.open()

        # Verify that WorkspaceOpened was passed into publish()
        assert any(
            isinstance(call.args[0], WorkspaceOpened)
            for call in event_bus.publish.call_args_list
            if call.args
        )

    def test_events_published_on_write(
        self, runtime: WorkspaceRuntime, event_bus: EventBus
    ) -> None:
        from unittest.mock import MagicMock

        event_bus.publish = MagicMock()

        runtime.write("test.txt", "data")

        # Verify that FileWritten was passed into publish()
        assert any(
            isinstance(call.args[0], FileWritten)
            for call in event_bus.publish.call_args_list
            if call.args
        )

    def test_events_published_on_read(self, runtime: WorkspaceRuntime, event_bus: EventBus) -> None:
        from unittest.mock import MagicMock

        event_bus.publish = MagicMock()

        runtime.write("test.txt", "data")
        runtime.read("test.txt")

        # Verify that FileRead was passed into publish()
        assert any(
            isinstance(call.args[0], FileRead)
            for call in event_bus.publish.call_args_list
            if call.args
        )

    def test_explain_returns_string(self, runtime: WorkspaceRuntime) -> None:
        explanation = runtime.explain()
        assert isinstance(explanation, str)
        assert "Workspace Root:" in explanation
