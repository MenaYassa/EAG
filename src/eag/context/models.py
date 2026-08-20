"""Immutable, read-only repository-context contracts for G2.2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Any

from eag.graph.runtime import GraphSnapshot
from eag.index.models import RepositoryIndex
from eag.repository.models import RepositoryProfile
from eag.source.models import AnalysisResult

CONTEXT_CONTRACT_VERSION = "1.0"
CONTEXT_POLICY_VERSION = "1.0"


def _freeze_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _relative_path(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a relative repository path")
    return path.as_posix()


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositorySnapshotFingerprint:
    """Stable fingerprint for deterministic repository evidence, never scanner time state."""

    value: str
    version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _non_empty(self.value, "value"))
        object.__setattr__(self, "version", _non_empty(self.version, "version"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextFingerprint:
    """Stable fingerprint for the selected and redacted provider projection."""

    value: str
    version: str = CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _non_empty(self.value, "value"))
        object.__setattr__(self, "version", _non_empty(self.version, "version"))


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryStateEvidence:
    """Read-only VCS state projected without host paths or raw file content."""

    available: bool
    branch: str | None = None
    head: str | None = None
    is_detached: bool = False
    changed_paths: tuple[str, ...] = ()
    state_fingerprint: str = "none"

    def __post_init__(self) -> None:
        if self.branch is not None:
            object.__setattr__(self, "branch", _non_empty(self.branch, "branch"))
        if self.head is not None:
            object.__setattr__(self, "head", _non_empty(self.head, "head"))
        object.__setattr__(
            self,
            "changed_paths",
            tuple(_relative_path(path, "changed_paths") for path in self.changed_paths),
        )
        object.__setattr__(
            self,
            "state_fingerprint",
            _non_empty(self.state_fingerprint, "state_fingerprint"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextBudget:
    """Configurable, deterministic maximums for a provider-facing context projection."""

    max_profile_characters: int = 1_500
    max_files: int = 16
    max_symbols: int = 50
    max_dependencies: int = 60
    max_excerpts: int = 12
    max_excerpt_lines: int = 80
    max_excerpt_characters: int = 6_000
    max_total_characters: int = 24_000
    max_file_bytes: int = 512_000
    max_graph_depth: int = 2
    policy_version: str = CONTEXT_POLICY_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "max_profile_characters",
            "max_files",
            "max_symbols",
            "max_dependencies",
            "max_excerpts",
            "max_excerpt_lines",
            "max_excerpt_characters",
            "max_total_characters",
            "max_file_bytes",
            "max_graph_depth",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative")
        object.__setattr__(self, "policy_version", _non_empty(self.policy_version, "policy_version"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextProvenanceRecord:
    """An attributable deterministic source or derivation for selected context evidence."""

    provenance_id: str
    kind: str
    subject: str
    source_fingerprint: str
    selection_reason: str
    location_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    derivation: str = ""
    resolution_confidence: str = "exact"
    sensitivity_action: str = "included"
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        for field_name in (
            "provenance_id",
            "kind",
            "subject",
            "source_fingerprint",
            "selection_reason",
            "resolution_confidence",
            "sensitivity_action",
        ):
            object.__setattr__(self, field_name, _non_empty(getattr(self, field_name), field_name))
        if self.location_path is not None:
            object.__setattr__(
                self,
                "location_path",
                _relative_path(self.location_path, "location_path"),
            )
        if self.line_start is not None and self.line_start < 1:
            raise ValueError("line_start must be positive")
        if self.line_end is not None and self.line_end < 1:
            raise ValueError("line_end must be positive")
        if self.line_start is not None and self.line_end is not None and self.line_end < self.line_start:
            raise ValueError("line_end cannot precede line_start")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceArtifactRecord:
    """A safe internal link to a single actual SourceRuntime analysis result."""

    repository_path: str
    fingerprint: str
    language: str
    byte_size: int
    analysis: AnalysisResult
    sensitivity_action: str = "included"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "repository_path",
            _relative_path(self.repository_path, "repository_path"),
        )
        object.__setattr__(self, "fingerprint", _non_empty(self.fingerprint, "fingerprint"))
        object.__setattr__(self, "language", _non_empty(self.language, "language"))
        if self.byte_size < 0:
            raise ValueError("byte_size cannot be negative")
        object.__setattr__(
            self,
            "sensitivity_action",
            _non_empty(self.sensitivity_action, "sensitivity_action"),
        )
        if not isinstance(self.analysis, AnalysisResult):
            raise TypeError("analysis must be an AnalysisResult")


@dataclass(frozen=True, slots=True, kw_only=True)
class FileReference:
    repository_path: str
    fingerprint: str
    role: str
    selection_reason: str
    score: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "repository_path",
            _relative_path(self.repository_path, "repository_path"),
        )
        for field_name in ("fingerprint", "role", "selection_reason"):
            object.__setattr__(self, field_name, _non_empty(getattr(self, field_name), field_name))


@dataclass(frozen=True, slots=True, kw_only=True)
class SymbolReference:
    qualified_name: str
    kind: str
    module: str
    repository_path: str
    line_start: int
    line_end: int
    selection_reason: str
    score: int

    def __post_init__(self) -> None:
        for field_name in ("qualified_name", "kind", "module", "selection_reason"):
            object.__setattr__(self, field_name, _non_empty(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "repository_path",
            _relative_path(self.repository_path, "repository_path"),
        )
        if self.line_start < 1 or self.line_end < self.line_start:
            raise ValueError("symbol line range is invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class DependencyReference:
    source: str
    target: str
    kind: str
    resolved: bool
    selection_reason: str
    score: int

    def __post_init__(self) -> None:
        for field_name in ("source", "target", "kind", "selection_reason"):
            object.__setattr__(self, field_name, _non_empty(getattr(self, field_name), field_name))


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceExcerpt:
    repository_path: str
    line_start: int
    line_end: int
    content: str
    fingerprint: str
    provenance_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "repository_path",
            _relative_path(self.repository_path, "repository_path"),
        )
        if self.line_start < 1 or self.line_end < self.line_start:
            raise ValueError("excerpt line range is invalid")
        object.__setattr__(self, "fingerprint", _non_empty(self.fingerprint, "fingerprint"))
        object.__setattr__(self, "provenance_id", _non_empty(self.provenance_id, "provenance_id"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextTruncationReport:
    """Configured limits and redacted accounting for selected/omitted context material."""

    configured_limits: Mapping[str, int]
    actual_usage: Mapping[str, int]
    omitted_counts: Mapping[str, int]
    omission_reasons: Mapping[str, int]
    truncated: bool
    insufficient: bool

    def __post_init__(self) -> None:
        for field_name in (
            "configured_limits",
            "actual_usage",
            "omitted_counts",
            "omission_reasons",
        ):
            value = _freeze_mapping(getattr(self, field_name), field_name)
            if any(not isinstance(item, int) or item < 0 for item in value.values()):
                raise ValueError(f"{field_name} values must be non-negative integers")
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryContextSnapshot:
    """Full read-only evidence snapshot used before a provider-facing projection."""

    repository_profile: RepositoryProfile
    repository_state: RepositoryStateEvidence
    index: RepositoryIndex
    graph: GraphSnapshot | None
    source_artifacts: tuple[SourceArtifactRecord, ...]
    snapshot_fingerprint: RepositorySnapshotFingerprint
    assembled_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    policy_version: str = CONTEXT_POLICY_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.repository_profile, RepositoryProfile):
            raise TypeError("repository_profile must be a RepositoryProfile")
        if not isinstance(self.repository_state, RepositoryStateEvidence):
            raise TypeError("repository_state must be a RepositoryStateEvidence")
        if not isinstance(self.index, RepositoryIndex):
            raise TypeError("index must be a RepositoryIndex")
        if not isinstance(self.snapshot_fingerprint, RepositorySnapshotFingerprint):
            raise TypeError("snapshot_fingerprint must be a RepositorySnapshotFingerprint")
        if not all(isinstance(item, SourceArtifactRecord) for item in self.source_artifacts):
            raise TypeError("source_artifacts must contain SourceArtifactRecord values")
        object.__setattr__(self, "policy_version", _non_empty(self.policy_version, "policy_version"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectedRepositoryContext:
    """Redacted, bounded provider-facing projection with deterministic evidence links."""

    repository_summary: str
    source_findings: tuple[str, ...]
    files: tuple[FileReference, ...]
    symbols: tuple[SymbolReference, ...]
    dependencies: tuple[DependencyReference, ...]
    excerpts: tuple[SourceExcerpt, ...]
    provenance: tuple[ContextProvenanceRecord, ...]
    truncation: ContextTruncationReport
    context_fingerprint: ContextFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.truncation, ContextTruncationReport):
            raise TypeError("truncation must be a ContextTruncationReport")
        if not isinstance(self.context_fingerprint, ContextFingerprint):
            raise TypeError("context_fingerprint must be a ContextFingerprint")
        if not all(isinstance(item, ContextProvenanceRecord) for item in self.provenance):
            raise TypeError("provenance must contain ContextProvenanceRecord values")


class ContextAssemblyError(RuntimeError):
    """Raised when safe, sufficient repository context cannot be assembled."""


class StaleContextError(ContextAssemblyError):
    """Raised when a selected context no longer matches current repository evidence."""
