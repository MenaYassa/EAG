from datetime import UTC, datetime

from eag.index.errors import IndexBuildError
from eag.index.models import (
    RepositoryIndex,
    RepositoryIndexIdentity,
    RepositoryIndexStatistics,
)
from eag.source.models import AnalysisResult, Dependency, ModuleIdentity, Symbol
from eag.source.state import SymbolKind


class RepositoryIndexBuilder:
    def __init__(self, repository_name: str) -> None:
        self._repository_name = repository_name
        self._modules: dict[str, ModuleIdentity] = {}
        self._symbols: dict[str, Symbol] = {}
        self._dependencies: list[Dependency] = []

    def add_result(self, result: AnalysisResult) -> None:
        if not isinstance(result, AnalysisResult):
            raise TypeError("result must be an AnalysisResult")

        self._modules[result.module.name] = result.module

        for sym in result.symbols:
            self._symbols[sym.identity.qualified_name] = sym

        for dep in result.dependencies:
            self._dependencies.append(dep)

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
            )
        except Exception as e:
            raise IndexBuildError(f"Failed to build index: {e}") from e

    def _calculate_statistics(self) -> RepositoryIndexStatistics:
        classes = sum(1 for s in self._symbols.values() if s.identity.kind == SymbolKind.CLASS)
        functions = sum(1 for s in self._symbols.values() if s.identity.kind == SymbolKind.FUNCTION)
        methods = sum(1 for s in self._symbols.values() if s.identity.kind == SymbolKind.METHOD)

        return RepositoryIndexStatistics(
            modules=len(self._modules),
            classes=classes,
            functions=functions,
            methods=methods,
            symbols=len(self._symbols),
            dependencies=len(self._dependencies),
        )
