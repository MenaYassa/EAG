from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from eag.source.diagnostics import AnalysisDiagnostic
from eag.source.metrics import AnalysisMetrics
from eag.source.state import DependencyKind, SemanticKind, SymbolKind, Visibility


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
class SourceLocation:
    path: PurePosixPath
    line: int
    column: int
    end_line: int
    end_column: int

    def __post_init__(self) -> None:
        if not isinstance(self.path, PurePosixPath):
            raise TypeError("path must be a PurePosixPath")
        if self.line < 1:
            raise ValueError("line must be >= 1")
        _validate_non_negative_int(self.column, "column")
        _validate_non_negative_int(self.end_line, "end_line")
        if self.end_line < self.line:
            raise ValueError("end_line cannot be less than line")
        _validate_non_negative_int(self.end_column, "end_column")


@dataclass(frozen=True, slots=True, kw_only=True)
class Documentation:
    summary: str = ""
    body: str = ""
    raw: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.summary, str):
            raise TypeError("summary must be a string")
        if not isinstance(self.body, str):
            raise TypeError("body must be a string")
        if not isinstance(self.raw, str):
            raise TypeError("raw must be a string")


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceFileIdentity:
    absolute_path: Path
    repository_path: PurePosixPath
    language: str
    fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "absolute_path",
            _validate_absolute_path(self.absolute_path, "absolute_path"),
        )
        if (
            not isinstance(self.repository_path, PurePosixPath)
            or not str(self.repository_path).strip()
        ):
            raise ValueError("repository_path cannot be empty")
        object.__setattr__(self, "language", _validate_non_empty_str(self.language, "language"))
        object.__setattr__(
            self,
            "fingerprint",
            _validate_non_empty_str(self.fingerprint, "fingerprint"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleIdentity:
    name: str
    path: PurePosixPath

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_non_empty_str(self.name, "name"))
        if not isinstance(self.path, PurePosixPath) or not str(self.path).strip():
            raise ValueError("path cannot be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class SymbolIdentity:
    qualified_name: str
    module: str
    kind: SymbolKind

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "qualified_name",
            _validate_non_empty_str(self.qualified_name, "qualified_name"),
        )
        object.__setattr__(self, "module", _validate_non_empty_str(self.module, "module"))
        if not isinstance(self.kind, SymbolKind):
            raise TypeError("kind must be a SymbolKind")


@dataclass(frozen=True, slots=True, kw_only=True)
class Symbol:
    identity: SymbolIdentity
    location: SourceLocation
    visibility: Visibility = Visibility.PUBLIC
    documentation: Documentation = field(default_factory=Documentation)
    attributes: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.identity, SymbolIdentity):
            raise TypeError("identity must be a SymbolIdentity")
        if not isinstance(self.location, SourceLocation):
            raise TypeError("location must be a SourceLocation")
        if not isinstance(self.visibility, Visibility):
            raise TypeError("visibility must be a Visibility")
        if not isinstance(self.documentation, Documentation):
            raise TypeError("documentation must be a Documentation")
        if not isinstance(self.attributes, frozenset):
            raise TypeError("attributes must be a frozenset")


@dataclass(frozen=True, slots=True, kw_only=True)
class Dependency:
    source: str
    target: str
    kind: DependencyKind
    resolved: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _validate_non_empty_str(self.source, "source"))
        object.__setattr__(self, "target", _validate_non_empty_str(self.target, "target"))
        if not isinstance(self.kind, DependencyKind):
            raise TypeError("kind must be a DependencyKind")
        if not isinstance(self.resolved, bool):
            raise TypeError("resolved must be a bool")


@dataclass(frozen=True, slots=True, kw_only=True)
class SemanticRelationship:
    source: str
    target: str
    kind: "SemanticKind"

    def __post_init__(self) -> None:
        _validate_non_empty_str(self.source, "source")
        _validate_non_empty_str(self.target, "target")
        if not isinstance(self.kind, SemanticKind):
            raise TypeError("kind must be a SemanticKind")


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisResult:
    identity: SourceFileIdentity
    module: ModuleIdentity
    symbols: tuple[Symbol, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    diagnostics: tuple[AnalysisDiagnostic, ...] = ()
    metrics: AnalysisMetrics = field(default_factory=AnalysisMetrics)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    semantic_relationships: tuple[SemanticRelationship, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, SourceFileIdentity):
            raise TypeError("identity must be a SourceFileIdentity")
        if not isinstance(self.module, ModuleIdentity):
            raise TypeError("module must be a ModuleIdentity")
        if not isinstance(self.symbols, tuple):
            raise TypeError("symbols must be a tuple")
        if not isinstance(self.dependencies, tuple):
            raise TypeError("dependencies must be a tuple")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be a tuple")
        if not isinstance(self.metrics, AnalysisMetrics):
            raise TypeError("metrics must be an AnalysisMetrics")
        if not isinstance(self.semantic_relationships, tuple):
            raise TypeError("semantic_relationships must be a tuple")
