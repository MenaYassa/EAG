from eag.explorer.errors import ModuleNotFoundError, SymbolNotFoundError
from eag.explorer.models import (
    DependencyRequest,
    DependencyView,
    FindSymbolRequest,
    ModuleRequest,
    ModuleView,
    OverviewRequest,
    OverviewView,
    SearchRequest,
    SearchView,
    StatisticsRequest,
    StatisticsView,
    SymbolView,
)
from eag.index.models import RepositoryIndex
from eag.source.models import SymbolKind


class ExplorerRuntime:
    def __init__(self, index: RepositoryIndex, repository_name: str = "unknown") -> None:
        self._index = index
        self._repo_name = repository_name

    def overview(self, request: OverviewRequest) -> OverviewView:
        return OverviewView(
            repository=self._repo_name,
            health="HEALTHY",
            modules=self._index.statistics.modules,
            symbols=self._index.statistics.symbols,
            dependencies=self._index.statistics.dependencies,
            capabilities=[
                "Repository Intelligence",
                "Source Intelligence",
                "Engineering Index",
            ],
        )

    def statistics(self, request: StatisticsRequest) -> StatisticsView:
        stats = self._index.statistics
        avg = stats.symbols / stats.modules if stats.modules > 0 else 0.0
        return StatisticsView(
            files=stats.files,
            modules=stats.modules,
            classes=stats.classes,
            interfaces=stats.interfaces,
            protocols=stats.protocols,
            enums=stats.enums,
            dataclasses=stats.dataclasses,
            functions=stats.functions,
            methods=stats.methods,
            constants=stats.constants,
            symbols=stats.symbols,
            dependencies=stats.dependencies,
            avg_symbols_per_module=round(avg, 2),
            largest_module="N/A",
        )

    def find_symbol(self, request: FindSymbolRequest) -> SymbolView:
        sym = None

        # Try exact match first
        for s in self._index.symbols:
            if s.identity.qualified_name == request.name:
                sym = s
                break

        # Try matching by short name
        if not sym:
            for s in self._index.symbols:
                if s.identity.qualified_name.endswith(f".{request.name}"):
                    sym = s
                    break

        if not sym:
            raise SymbolNotFoundError(f"Symbol '{request.name}' not found")

        # Extract methods if it's a class
        methods = [
            s.identity.qualified_name.split(".")[-1] + "()"
            for s in self._index.symbols
            if s.identity.kind == SymbolKind.METHOD
            and s.identity.qualified_name.startswith(f"{sym.identity.qualified_name}.")
        ]

        # Extract dependencies (imports in the same file)
        deps = list(set(d.target for d in self._index.dependencies if d.source == "module"))

        return SymbolView(
            name=sym.identity.qualified_name.split(".")[-1],
            kind=sym.identity.kind.value,
            module=sym.identity.module,
            file=str(sym.location.path),
            visibility=sym.visibility.value,
            methods=methods,
            dependencies=deps,
        )

    def module(self, request: ModuleRequest) -> ModuleView:
        try:
            mod = self._index.find_module(request.name)
        except Exception:
            raise ModuleNotFoundError(f"Module '{request.name}' not found") from None

        syms = [
            s.identity.qualified_name for s in self._index.symbols if s.identity.module == mod.name
        ]
        deps = [d.target for d in self._index.dependencies]

        return ModuleView(name=mod.name, file=str(mod.path), symbols=syms, dependencies=deps)

    def dependencies(self, request: DependencyRequest) -> DependencyView:
        deps = [d.target for d in self._index.dependencies]
        return DependencyView(source=request.source, dependencies=deps)

    def search(self, request: SearchRequest) -> SearchView:
        query = request.query.lower()
        results = [
            s.identity.qualified_name
            for s in self._index.symbols
            if query in s.identity.qualified_name.lower()
        ]
        return SearchView(query=request.query, results=results)
