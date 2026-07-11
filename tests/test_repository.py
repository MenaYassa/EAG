from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from eag.events import EventBus
from eag.repository.errors import (
    RepositoryError,
    RepositoryNotFoundError,
    ScanFailedError,
    UnsupportedRepositoryError,
)
from eag.repository.events import (
    RepositoryProfileGenerated,
    RepositoryScanCompleted,
    RepositoryScanFailed,
    RepositoryScanStarted,
)
from eag.repository.ignore import IgnoreEngine, RepositoryIgnoreRules
from eag.repository.models import (
    LanguageSummary,
    ProjectLayout,
    RepositoryFact,
    RepositoryHealth,
    RepositoryIdentity,
    RepositoryKind,
    RepositoryMetadata,
    RepositoryProfile,
    RepositorySnapshot,
    RepositoryStatistics,
)
from eag.repository.runtime import RepositoryRuntime, RepositoryServices
from eag.repository.scanner import RepositoryScanner
from eag.repository.state import RepositoryState


# ==========================================
# 1. Enums & State Tests
# ==========================================
class TestRepositoryEnums:
    def test_state_values(self):
        assert RepositoryState.UNKNOWN == "unknown"
        assert RepositoryState.SCANNING == "scanning"
        assert RepositoryState.READY == "ready"

    def test_health_values(self):
        assert RepositoryHealth.HEALTHY == "healthy"
        assert RepositoryHealth.WARNING == "warning"
        assert RepositoryHealth.ERROR == "error"

    def test_kind_values(self):
        assert RepositoryKind.PYTHON == "python"
        assert RepositoryKind.NODE == "node"

    def test_layout_values(self):
        assert ProjectLayout.SRC_LAYOUT == "src_layout"
        assert ProjectLayout.MONOREPO == "monorepo"


# ==========================================
# 2. Domain Model Validation Tests
# ==========================================
class TestRepositoryIdentity:
    def test_valid(self):
        identity = RepositoryIdentity(
            name="EAG", root=Path("/tmp/eag"), discovered_at=datetime.now(UTC)
        )
        assert identity.name == "EAG"

    def test_strips_whitespace(self):
        identity = RepositoryIdentity(
            name="  EAG  ", root=Path("/tmp/eag"), discovered_at=datetime.now(UTC)
        )
        assert identity.name == "EAG"

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            RepositoryIdentity(name="", root=Path("/tmp"), discovered_at=datetime.now(UTC))

    def test_whitespace_name_rejected(self):
        with pytest.raises(ValueError):
            RepositoryIdentity(name="   ", root=Path("/tmp"), discovered_at=datetime.now(UTC))

    def test_relative_path_rejected(self):
        with pytest.raises(ValueError):
            RepositoryIdentity(name="EAG", root=Path("tmp/eag"), discovered_at=datetime.now(UTC))

    def test_immutable(self):
        identity = RepositoryIdentity(
            name="EAG", root=Path("/tmp"), discovered_at=datetime.now(UTC)
        )
        with pytest.raises(FrozenInstanceError):
            identity.name = "New"

    def test_hashable(self):
        ts = datetime.now(UTC)
        id1 = RepositoryIdentity(name="EAG", root=Path("/tmp"), discovered_at=ts)
        id2 = RepositoryIdentity(name="EAG", root=Path("/tmp"), discovered_at=ts)
        assert hash(id1) == hash(id2)

    def test_equality(self):
        ts = datetime.now(UTC)
        id1 = RepositoryIdentity(name="EAG", root=Path("/tmp"), discovered_at=ts)
        id2 = RepositoryIdentity(name="EAG", root=Path("/tmp"), discovered_at=ts)
        assert id1 == id2


class TestLanguageSummary:
    def test_valid(self):
        ls = LanguageSummary(language="Python", file_count=10, line_count=100, percentage=50.0)
        assert ls.language == "Python"

    def test_negative_files_rejected(self):
        with pytest.raises(ValueError):
            LanguageSummary(language="Python", file_count=-1, line_count=100, percentage=50.0)

    def test_percentage_out_of_bounds(self):
        with pytest.raises(ValueError):
            LanguageSummary(language="Python", file_count=10, line_count=100, percentage=150.0)


class TestRepositoryStatistics:
    def test_defaults_zero(self):
        stats = RepositoryStatistics()
        assert stats.files == 0
        assert stats.python_files == 0

    def test_negative_files_rejected(self):
        with pytest.raises(ValueError):
            RepositoryStatistics(files=-1)

    def test_negative_directories_rejected(self):
        with pytest.raises(ValueError):
            RepositoryStatistics(directories=-5)

    def test_negative_bytes_rejected(self):
        with pytest.raises(ValueError):
            RepositoryStatistics(total_bytes=-1024)

    def test_immutable(self):
        stats = RepositoryStatistics()
        with pytest.raises(FrozenInstanceError):
            stats.files = 10


class TestRepositoryMetadata:
    def test_branch_without_commit_rejected(self):
        with pytest.raises(ValueError):
            RepositoryMetadata(current_branch="main", head_commit=None)

    def test_commit_without_branch_allowed(self):
        meta = RepositoryMetadata(current_branch=None, head_commit="abc123")
        assert meta.head_commit == "abc123"

    def test_defaults_none(self):
        meta = RepositoryMetadata()
        assert meta.git_repository is False
        assert meta.pyproject is None


class TestRepositoryFact:
    def test_valid(self):
        fact = RepositoryFact(kind="vcs", value="Git", confidence=1.0)
        assert fact.kind == "vcs"

    def test_empty_kind_rejected(self):
        with pytest.raises(ValueError):
            RepositoryFact(kind="", value="Git", confidence=1.0)

    def test_confidence_out_of_bounds(self):
        with pytest.raises(ValueError):
            RepositoryFact(kind="vcs", value="Git", confidence=1.5)


class TestRepositoryProfile:
    def setup_method(self):
        self.identity = RepositoryIdentity(
            name="EAG", root=Path("/tmp"), discovered_at=datetime.now(UTC)
        )
        self.stats = RepositoryStatistics()
        self.meta = RepositoryMetadata()

    def test_valid_creation(self):
        profile = RepositoryProfile(
            identity=self.identity,
            statistics=self.stats,
            metadata=self.meta,
            health=RepositoryHealth.HEALTHY,
        )
        assert profile.health == RepositoryHealth.HEALTHY
        assert profile.kind == RepositoryKind.UNKNOWN

    def test_immutable(self):
        profile = RepositoryProfile(
            identity=self.identity,
            statistics=self.stats,
            metadata=self.meta,
            health=RepositoryHealth.HEALTHY,
        )
        with pytest.raises(FrozenInstanceError):
            profile.health = RepositoryHealth.ERROR

    def test_invalid_identity_type(self):
        with pytest.raises(TypeError):
            RepositoryProfile(
                identity="bad",
                statistics=self.stats,
                metadata=self.meta,
                health=RepositoryHealth.HEALTHY,
            )

    def test_invalid_stats_type(self):
        with pytest.raises(TypeError):
            RepositoryProfile(
                identity=self.identity,
                statistics="bad",
                metadata=self.meta,
                health=RepositoryHealth.HEALTHY,
            )


class TestRepositorySnapshot:
    def test_valid_creation(self):
        identity = RepositoryIdentity(
            name="EAG", root=Path("/tmp"), discovered_at=datetime.now(UTC)
        )
        profile = RepositoryProfile(
            identity=identity,
            statistics=RepositoryStatistics(),
            metadata=RepositoryMetadata(),
            health=RepositoryHealth.HEALTHY,
        )
        snapshot = RepositorySnapshot(profile=profile)
        assert snapshot.profile == profile
        assert isinstance(snapshot.timestamp, datetime)

    def test_invalid_profile_type(self):
        with pytest.raises(TypeError):
            RepositorySnapshot(profile="bad")


# ==========================================
# 3. Error Hierarchy Tests
# ==========================================
class TestErrors:
    def test_base_error(self):
        assert issubclass(RepositoryNotFoundError, RepositoryError)
        assert issubclass(ScanFailedError, RepositoryError)

    def test_raise_not_found(self):
        with pytest.raises(RepositoryNotFoundError):
            raise RepositoryNotFoundError("Not found")

    def test_raise_unsupported(self):
        with pytest.raises(UnsupportedRepositoryError):
            raise UnsupportedRepositoryError("Unsupported")


# ==========================================
# 4. Ignore Engine Tests
# ==========================================
class TestIgnoreEngine:
    def setup_method(self):
        self.engine = IgnoreEngine()

    def test_ignore_git_dir(self):
        assert self.engine.should_ignore(Path("/repo/.git")) is True

    def test_ignore_pycache(self):
        assert self.engine.should_ignore(Path("/repo/__pycache__")) is True

    def test_ignore_venv(self):
        assert self.engine.should_ignore(Path("/repo/.venv")) is True

    def test_ignore_pyc_file(self):
        assert self.engine.should_ignore(Path("/repo/main.pyc")) is True

    def test_ignore_pyo_file(self):
        assert self.engine.should_ignore(Path("/repo/main.pyo")) is True

    def test_ignore_egg_info(self):
        assert self.engine.should_ignore(Path("/repo/eag.egg-info")) is True

    def test_ignore_coverage_file(self):
        assert self.engine.should_ignore(Path("/repo/.coverage")) is True

    def test_dont_ignore_src(self):
        assert self.engine.should_ignore(Path("/repo/src")) is False

    def test_dont_ignore_main_py(self):
        assert self.engine.should_ignore(Path("/repo/main.py")) is False

    def test_nested_ignored_dir(self):
        assert self.engine.should_ignore(Path("/repo/src/__pycache__")) is True

    def test_custom_directory_rule_overrides_defaults(self):
        rules = RepositoryIgnoreRules(directories=frozenset({"logs"}))
        engine = IgnoreEngine(rules=rules)
        assert engine.should_ignore(Path("/repo/logs")) is True
        # Defaults are overridden
        assert engine.should_ignore(Path("/repo/.git")) is False

    def test_case_sensitivity(self):
        # Linux is case-sensitive, so this should not be ignored
        assert self.engine.should_ignore(Path("/repo/__PyCache__")) is False


# ==========================================
# 5. Scanner Tests
# ==========================================
class TestRepositoryScanner:
    def test_scanner_not_found(self, tmp_path):
        scanner = RepositoryScanner(IgnoreEngine())
        with pytest.raises(RepositoryNotFoundError):
            scanner.scan(tmp_path / "nonexistent")

    def test_scanner_minimal_repo(self, tmp_path):
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "__init__.py").write_text("")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test(): pass")

        scanner = RepositoryScanner(IgnoreEngine())
        profile = scanner.scan(tmp_path)

        assert profile.identity.name == tmp_path.name
        assert profile.statistics.files >= 4
        assert profile.statistics.packages == 1
        assert profile.statistics.tests == 1
        assert profile.health == RepositoryHealth.HEALTHY
        assert profile.kind == RepositoryKind.PYTHON
        assert profile.layout == ProjectLayout.SRC_LAYOUT

    def test_scanner_ignores_paths(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("")
        (tmp_path / "main.py").write_text("print('hello')")

        scanner = RepositoryScanner(IgnoreEngine())
        profile = scanner.scan(tmp_path)

        assert profile.statistics.files == 1
        assert profile.statistics.directories == 0  # .git is pruned before counting

    def test_scanner_detects_flat_layout(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        scanner = RepositoryScanner(IgnoreEngine())
        profile = scanner.scan(tmp_path)
        assert profile.layout == ProjectLayout.FLAT

    def test_scanner_detects_monorepo_layout(self, tmp_path):
        (tmp_path / "packages").mkdir()
        scanner = RepositoryScanner(IgnoreEngine())
        profile = scanner.scan(tmp_path)
        assert profile.layout == ProjectLayout.MONOREPO

    def test_health_warning_missing_readme(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")
        scanner = RepositoryScanner(IgnoreEngine())
        profile = scanner.scan(tmp_path)
        assert profile.health == RepositoryHealth.WARNING

    def test_health_error_missing_pyproject_and_git(self, tmp_path):
        (tmp_path / "README.md").write_text("")
        scanner = RepositoryScanner(IgnoreEngine())
        profile = scanner.scan(tmp_path)
        assert profile.health == RepositoryHealth.ERROR

    def test_large_tree_performance(self, tmp_path):
        # Generate 300 dirs and 500 files
        for i in range(300):
            d = tmp_path / f"dir_{i}"
            d.mkdir()
            (d / "file.py").write_text("")

        for i in range(200):
            (tmp_path / f"root_file_{i}.py").write_text("")

        scanner = RepositoryScanner(IgnoreEngine())
        import time

        start = time.time()
        profile = scanner.scan(tmp_path)
        end = time.time()

        assert profile.statistics.directories == 300
        assert profile.statistics.files == 500
        assert (end - start) < 1.0  # Should be extremely fast


# ==========================================
# 6. Runtime & Events Tests
# ==========================================
class TestRepositoryRuntime:
    def test_runtime_scan_success(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")

        mock_settings = MagicMock()
        mock_settings.kernel.workspace = tmp_path

        services = RepositoryServices(
            scanner=RepositoryScanner(IgnoreEngine()), event_bus=EventBus(), settings=mock_settings
        )
        runtime = RepositoryRuntime(services)
        snapshot = runtime.scan()

        assert snapshot.profile is not None
        assert runtime.profile() is not None

    def test_runtime_scan_failed_event(self, tmp_path):
        mock_settings = MagicMock()
        mock_settings.kernel.workspace = tmp_path / "does_not_exist"

        services = RepositoryServices(
            scanner=RepositoryScanner(IgnoreEngine()), event_bus=EventBus(), settings=mock_settings
        )
        runtime = RepositoryRuntime(services)

        with pytest.raises(RepositoryNotFoundError):
            runtime.scan()

    def test_runtime_publishes_events(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")

        mock_settings = MagicMock()
        mock_settings.kernel.workspace = tmp_path

        # Use a Mock event bus to verify publish calls directly
        mock_event_bus = MagicMock()
        services = RepositoryServices(
            scanner=RepositoryScanner(IgnoreEngine()),
            event_bus=mock_event_bus,
            settings=mock_settings,
        )
        runtime = RepositoryRuntime(services)

        runtime.scan()

        # 3 events: Started, ProfileGenerated, Completed
        assert mock_event_bus.publish.call_count == 3

        published_events = [call.args[0] for call in mock_event_bus.publish.call_args_list]
        assert isinstance(published_events[0], RepositoryScanStarted)
        assert isinstance(published_events[1], RepositoryProfileGenerated)
        assert isinstance(published_events[2], RepositoryScanCompleted)

    def test_runtime_failed_publishes_failed_event(self, tmp_path):
        mock_settings = MagicMock()
        mock_settings.kernel.workspace = tmp_path / "does_not_exist"

        mock_event_bus = MagicMock()
        services = RepositoryServices(
            scanner=RepositoryScanner(IgnoreEngine()),
            event_bus=mock_event_bus,
            settings=mock_settings,
        )
        runtime = RepositoryRuntime(services)

        with pytest.raises(RepositoryNotFoundError):
            runtime.scan()

        # 2 events: Started, Failed
        assert mock_event_bus.publish.call_count == 2

        published_events = [call.args[0] for call in mock_event_bus.publish.call_args_list]
        assert isinstance(published_events[0], RepositoryScanStarted)
        assert isinstance(published_events[1], RepositoryScanFailed)
