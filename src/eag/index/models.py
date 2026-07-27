from dataclasses import dataclass, field
from datetime import UTC, datetime

from eag.index.errors import SymbolNotFoundError

# Change line 6
from eag.source.models import Dependency, ModuleIdentity, SemanticRelationship, Symbol, SymbolKind


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryIndexIdentity:
    repository: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryIndexStatistics:
    files: int = 0
    modules: int = 0
    classes: int = 0
    interfaces: int = 0
    protocols: int = 0
    enums: int = 0
    dataclasses: int = 0
    functions: int = 0
    methods: int = 0
    constants: int = 0
    symbols: int = 0
    dependencies: int = 0

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.files, "files")
        _validate_non_negative_int(self.modules, "modules")
        _validate_non_negative_int(self.classes, "classes")
        _validate_non_negative_int(self.interfaces, "interfaces")
        _validate_non_negative_int(self.protocols, "protocols")
        _validate_non_negative_int(self.enums, "enums")
        _validate_non_negative_int(self.dataclasses, "dataclasses")
        _validate_non_negative_int(self.functions, "functions")
        _validate_non_negative_int(self.methods, "methods")
        _validate_non_negative_int(self.constants, "constants")
        _validate_non_negative_int(self.symbols, "symbols")
        _validate_non_negative_int(self.dependencies, "dependencies")


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryIndex:
    identity: RepositoryIndexIdentity
    statistics: RepositoryIndexStatistics
    modules: tuple[ModuleIdentity, ...] = ()
    symbols: tuple[Symbol, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    semantic_relationships: tuple[SemanticRelationship, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RepositoryIndexIdentity):
            raise TypeError("identity must be a RepositoryIndexIdentity")
        if not isinstance(self.statistics, RepositoryIndexStatistics):
            raise TypeError("statistics must be a RepositoryIndexStatistics")
        if not isinstance(self.modules, tuple):
            raise TypeError("modules must be a tuple")
        if not isinstance(self.symbols, tuple):
            raise TypeError("symbols must be a tuple")
        if not isinstance(self.dependencies, tuple):
            raise TypeError("dependencies must be a tuple")
        if not isinstance(self.semantic_relationships, tuple):
            raise TypeError("semantic_relationships must be a tuple")

    # --- Query API ---

    def find_module(self, name: str) -> ModuleIdentity:
        for m in self.modules:
            if m.name == name:
                return m
        raise ModuleNotFoundError(f"Module '{name}' not found")

    def find_symbol(self, qualified_name: str) -> Symbol:
        for s in self.symbols:
            if s.identity.qualified_name == qualified_name:
                return s
        raise SymbolNotFoundError(f"Symbol '{qualified_name}' not found")

    def find_symbols(self, kind: SymbolKind) -> tuple[Symbol, ...]:
        return tuple(s for s in self.symbols if s.identity.kind == kind)

    def find_dependencies(self, source: str) -> tuple[Dependency, ...]:
        return tuple(d for d in self.dependencies if d.source == source)

    def find_dependents(self, target: str) -> tuple[Dependency, ...]:
        return tuple(d for d in self.dependencies if d.target == target)
