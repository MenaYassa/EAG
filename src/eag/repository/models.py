from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from eag.repository.state import (
    ProjectLayout,
    RepositoryHealth,
    RepositoryKind,
)


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_absolute_path(value: Path, field_name: str) -> Path:
    if not isinstance(value, Path):
        raise TypeError(f"{field_name} must be a Path object")
    if not value.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path")
    return value


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryIdentity:
    name: str
    root: Path
    discovered_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_non_empty_str(self.name, "name"))
        object.__setattr__(self, "root", _validate_absolute_path(self.root, "root"))
        if not isinstance(self.discovered_at, datetime):
            raise TypeError("discovered_at must be a datetime object")


@dataclass(frozen=True, slots=True, kw_only=True)
class LanguageSummary:
    language: str
    file_count: int
    line_count: int
    percentage: float

    def __post_init__(self) -> None:
        _validate_non_empty_str(self.language, "language")
        _validate_non_negative_int(self.file_count, "file_count")
        _validate_non_negative_int(self.line_count, "line_count")
        if not (0.0 <= self.percentage <= 100.0):
            raise ValueError("percentage must be between 0.0 and 100.0")


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryStatistics:
    files: int = 0
    directories: int = 0
    packages: int = 0
    tests: int = 0
    documentation: int = 0
    total_bytes: int = 0
    python_files: int = 0
    markdown_files: int = 0
    config_files: int = 0
    languages: list[LanguageSummary] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.files, "files")
        _validate_non_negative_int(self.directories, "directories")
        _validate_non_negative_int(self.packages, "packages")
        _validate_non_negative_int(self.tests, "tests")
        _validate_non_negative_int(self.documentation, "documentation")
        _validate_non_negative_int(self.total_bytes, "total_bytes")
        _validate_non_negative_int(self.python_files, "python_files")
        _validate_non_negative_int(self.markdown_files, "markdown_files")
        _validate_non_negative_int(self.config_files, "config_files")


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryMetadata:
    git_repository: bool = False
    default_branch: str | None = None
    current_branch: str | None = None
    head_commit: str | None = None
    license: Path | None = None
    readme: Path | None = None
    pyproject: Path | None = None
    docker: Path | None = None
    ci: Path | None = None
    package_manager: str | None = None

    def __post_init__(self) -> None:
        # Branch cannot exist without commit, but commit can exist without branch
        if self.current_branch is not None and self.head_commit is None:
            raise ValueError("head_commit cannot be None if current_branch is set")


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryCapabilities:
    git: bool = False
    docker: bool = False
    tests: bool = False
    ci: bool = False
    package_manager: bool = False
    virtual_env: bool = False
    type_checking: bool = False
    formatting: bool = False
    linting: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryFact:
    kind: str
    value: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        _validate_non_empty_str(self.kind, "kind")
        _validate_non_empty_str(self.value, "value")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryProfile:
    identity: RepositoryIdentity
    statistics: RepositoryStatistics
    metadata: RepositoryMetadata
    health: RepositoryHealth
    kind: RepositoryKind = RepositoryKind.UNKNOWN
    layout: ProjectLayout = ProjectLayout.UNKNOWN
    capabilities: RepositoryCapabilities = field(default_factory=RepositoryCapabilities)
    facts: list[RepositoryFact] = field(default_factory=list)
    fingerprint: str | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RepositoryIdentity):
            raise TypeError("identity must be a RepositoryIdentity")
        if not isinstance(self.statistics, RepositoryStatistics):
            raise TypeError("statistics must be a RepositoryStatistics")
        if not isinstance(self.metadata, RepositoryMetadata):
            raise TypeError("metadata must be a RepositoryMetadata")
        if not isinstance(self.health, RepositoryHealth):
            raise TypeError("health must be a RepositoryHealth")


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositorySnapshot:
    profile: RepositoryProfile
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.profile, RepositoryProfile):
            raise TypeError("profile must be a RepositoryProfile")
