"""Unified engineering source models for EAG."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

from eag.source.metrics import AnalysisMetrics

# ─── 1. ENUMS ─────────────────────────────────────────────────────────────────


class Language(StrEnum):
    UNKNOWN = "unknown"
    PYTHON = "python"


class SymbolKind(StrEnum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"


class Visibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"


SymbolVisibility = Visibility


class DiagnosticSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class DependencyKind(StrEnum):
    IMPORT = "import"
    CALL = "call"
    INHERITANCE = "inheritance"


class SemanticKind(StrEnum):
    IMPLEMENTS = "implements"
    OVERRIDES = "overrides"


# ─── 2. VALIDATION HELPERS ────────────────────────────────────────────────────


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


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _coerce_enum(value: Any, enum_cls: type, field_name: str) -> Any:
    try:
        return enum_cls(value)
    except ValueError as err:
        raise TypeError(f"{field_name} must be a {enum_cls.__name__} Enum") from err


# ─── 3. LIGHTWEIGHT AST MODELS (For Parse/Validate) ───────────────────────────


@dataclass(frozen=True, slots=True, kw_only=True)
class Location:
    """A location within a source file."""

    line: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class SymbolReference:
    """A reference to a symbol."""

    source: str
    target: str
    line: int
    column: int = 0
    end_line: int = 0
    end_col: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringSymbol:
    """A semantic engineering symbol (class, function, variable, etc.)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    qualified_name: str = ""
    kind: SymbolKind
    visibility: SymbolVisibility = SymbolVisibility.PUBLIC
    location: Location = field(default_factory=lambda: Location(line=0))
    parent: str | None = None
    is_async: bool = False
    is_generator: bool = False
    decorators: tuple[str, ...] = ()
    references: tuple[SymbolReference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")

        q_name = self.qualified_name if self.qualified_name else self.name
        object.__setattr__(self, "qualified_name", q_name)

        if not isinstance(self.qualified_name, str) or not self.qualified_name.strip():
            raise ValueError("qualified_name cannot be empty")

        # Create a deterministic ID if one wasn't explicitly provided
        if not self.id:
            # Hash the qualified name to create a stable, deterministic 12-character ID
            det_id = hashlib.sha1(self.qualified_name.encode("utf-8")).hexdigest()[:12]
            object.__setattr__(self, "id", det_id)

        object.__setattr__(self, "kind", _coerce_enum(self.kind, SymbolKind, "kind"))
        object.__setattr__(
            self, "visibility", _coerce_enum(self.visibility, Visibility, "visibility")
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportModel:
    """A structured representation of an import statement."""

    module: str
    name: str | None = None
    alias: str | None = None
    relative: bool = False
    used: bool = False
    location: Location = field(default_factory=lambda: Location(line=0))

    def __post_init__(self) -> None:
        if not self.relative:
            object.__setattr__(self, "module", _validate_non_empty_str(self.module, "module"))


@dataclass(frozen=True, slots=True, kw_only=True)
class Diagnostic:
    """A diagnostic message from source analysis."""

    severity: DiagnosticSeverity
    message: str
    location: Location
    rule: str = ""
    provider: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "severity", _coerce_enum(self.severity, DiagnosticSeverity, "severity")
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceDocument:
    """The canonical representation of a source file."""

    path: Path
    language: Language
    checksum: str
    symbols: tuple[EngineeringSymbol, ...] = ()
    references: tuple[SymbolReference, ...] = ()
    imports: tuple[ImportModel, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise TypeError("path must be a Path")
        object.__setattr__(self, "language", _coerce_enum(self.language, Language, "language"))
        if not isinstance(self.checksum, str) or not self.checksum.strip():
            raise ValueError("checksum cannot be empty")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceMetrics:
    """Metrics collected during source analysis."""

    files_parsed: int = 0
    symbols_extracted: int = 0
    imports_extracted: int = 0
    parse_failures: int = 0
    parse_time_ms: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceHealth:
    """Health status of the source runtime."""

    state: str = "READY"
    providers_loaded: int = 1
    last_parse_status: str = "OK"
    summary: str = "Source platform is healthy."


# ─── 4. HEAVYWEIGHT SEMANTIC GRAPH MODELS (For Full Analysis) ─────────────────


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceLocation:
    path: PurePosixPath
    line: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.path, PurePosixPath):
            raise TypeError("path must be a PurePosixPath")
        if self.line < 1:
            raise ValueError("line must be >= 1")

        end_line_val = self.line if self.end_line == 0 else self.end_line
        object.__setattr__(self, "end_line", end_line_val)

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
    language: Language = Language.UNKNOWN
    fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "absolute_path", _validate_absolute_path(self.absolute_path, "absolute_path")
        )
        if (
            not isinstance(self.repository_path, PurePosixPath)
            or not str(self.repository_path).strip()
        ):
            raise ValueError("repository_path cannot be empty")

        lang = self.language
        if isinstance(lang, str) and not lang.strip():
            raise ValueError("language cannot be empty or whitespace")

        object.__setattr__(self, "language", _coerce_enum(lang, Language, "language"))
        object.__setattr__(
            self, "fingerprint", _validate_non_empty_str(self.fingerprint, "fingerprint")
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
            self, "qualified_name", _validate_non_empty_str(self.qualified_name, "qualified_name")
        )
        object.__setattr__(self, "module", _validate_non_empty_str(self.module, "module"))
        object.__setattr__(self, "kind", _coerce_enum(self.kind, SymbolKind, "kind"))


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisDiagnostic:
    severity: DiagnosticSeverity
    message: str
    location: SourceLocation
    rule: str = ""
    provider: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "severity", _coerce_enum(self.severity, DiagnosticSeverity, "severity")
        )
        object.__setattr__(self, "message", _validate_non_empty_str(self.message, "message"))


@dataclass(frozen=True, slots=True, kw_only=True)
class Symbol:
    identity: SymbolIdentity
    location: SourceLocation
    visibility: Visibility = Visibility.PUBLIC
    documentation: Documentation = field(default_factory=Documentation)
    attributes: frozenset[str] = field(default_factory=frozenset)
    references: tuple[SymbolReference, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.identity, SymbolIdentity):
            raise TypeError("identity must be a SymbolIdentity")
        if not isinstance(self.location, SourceLocation):
            raise TypeError("location must be a SourceLocation")
        if not isinstance(self.attributes, frozenset):
            raise TypeError("attributes must be a frozenset")
        object.__setattr__(
            self, "visibility", _coerce_enum(self.visibility, Visibility, "visibility")
        )
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class Dependency:
    source: str
    target: str
    kind: DependencyKind
    resolved: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _validate_non_empty_str(self.source, "source"))
        object.__setattr__(self, "target", _validate_non_empty_str(self.target, "target"))
        object.__setattr__(self, "kind", _coerce_enum(self.kind, DependencyKind, "kind"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SemanticRelationship:
    source: str
    target: str
    kind: SemanticKind

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _validate_non_empty_str(self.source, "source"))
        object.__setattr__(self, "target", _validate_non_empty_str(self.target, "target"))
        object.__setattr__(self, "kind", _coerce_enum(self.kind, SemanticKind, "kind"))


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisResult:
    identity: SourceFileIdentity
    module: ModuleIdentity
    symbols: tuple[Symbol, ...] = ()
    imports: tuple[ImportModel, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    semantic_relationships: tuple[SemanticRelationship, ...] = ()
    diagnostics: tuple[AnalysisDiagnostic, ...] = ()
    metrics: AnalysisMetrics = field(default_factory=AnalysisMetrics)
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

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
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationMetrics:
    total_attempts: int = 0
    succeeded: int = 0
    failed: int = 0
    validation_failures: int = 0
    total_duration_ms: float = 0.0
