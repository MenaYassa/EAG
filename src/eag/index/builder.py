from collections.abc import Iterable
from datetime import UTC, datetime

from eag.index.errors import IndexBuildError
from eag.index.models import (
    RepositoryIndex,
    RepositoryIndexIdentity,
    RepositoryIndexStatistics,
)
from eag.source.models import (
    AnalysisResult,
    Dependency,
    ModuleIdentity,
    SemanticRelationship,
    Symbol,
)
from eag.source.state import SymbolKind


class RepositoryIndexBuilder:
    def __init__(self, repository_name: str) -> None:
        self._repository_name = repository_name
        self._modules: dict[str, ModuleIdentity] = {}
        self._symbols: dict[str, Symbol] = {}
        self._dependencies: list[Dependency] = []
        self._files = 0
        self._semantic_relationships: list[SemanticRelationship] = []

    def add_result(self, result: AnalysisResult) -> None:
        if not isinstance(result, AnalysisResult):
            raise TypeError("result must be an AnalysisResult")

        self._files += 1
        self._modules[result.module.name] = result.module
        self._semantic_relationships.extend(result.semantic_relationships)

        for sym in result.symbols:
            self._symbols[sym.identity.qualified_name] = sym

        for dep in result.dependencies:
            self._dependencies.append(dep)

    @classmethod
    def build_from_results(
        cls, results: Iterable[AnalysisResult], repository_name: str
    ) -> RepositoryIndex:
        builder = cls(repository_name)
        for res in results:
            builder.add_result(res)
        return builder.build()

    def build(self) -> RepositoryIndex:
        try:
            stats = self._calculate_statistics()
            return RepositoryIndex(
                identity=RepositoryIndexIdentity(
                    repository=self._repository_name,
                    created_at=datetime.now(UTC),
                ),
                statistics=stats,
                modules=tuple(self._modules.values()),
                symbols=tuple(self._symbols.values()),
                dependencies=tuple(self._dependencies),
                semantic_relationships=tuple(self._semantic_relationships),
            )
        except Exception as e:
            raise IndexBuildError(f"Failed to build index: {e}") from e

    def _calculate_statistics(self) -> RepositoryIndexStatistics:
        classes = sum(1 for s in self._symbols.values() if s.identity.kind == SymbolKind.CLASS)
        interfaces = sum(
            1 for s in self._symbols.values() if s.identity.kind == SymbolKind.INTERFACE
        )
        protocols = sum(1 for s in self._symbols.values() if "is_protocol" in s.attributes)
        enums = sum(1 for s in self._symbols.values() if "is_enum" in s.attributes)
        dataclasses = sum(1 for s in self._symbols.values() if "is_dataclass" in s.attributes)
        functions = sum(1 for s in self._symbols.values() if s.identity.kind == SymbolKind.FUNCTION)
        methods = sum(1 for s in self._symbols.values() if s.identity.kind == SymbolKind.METHOD)
        constants = sum(1 for s in self._symbols.values() if s.identity.kind == SymbolKind.CONSTANT)

        return RepositoryIndexStatistics(
            files=self._files,
            modules=len(self._modules),
            classes=classes,
            interfaces=interfaces,
            protocols=protocols,
            enums=enums,
            dataclasses=dataclasses,
            functions=functions,
            methods=methods,
            constants=constants,
            symbols=len(self._symbols),
            dependencies=len(self._dependencies),
        )
