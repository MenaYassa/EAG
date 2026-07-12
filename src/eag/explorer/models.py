from dataclasses import dataclass

# --- Requests ---


@dataclass(frozen=True, slots=True, kw_only=True)
class ExplorerRequest:
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class FindSymbolRequest(ExplorerRequest):
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleRequest(ExplorerRequest):
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DependencyRequest(ExplorerRequest):
    source: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchRequest(ExplorerRequest):
    query: str


@dataclass(frozen=True, slots=True, kw_only=True)
class OverviewRequest(ExplorerRequest):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class StatisticsRequest(ExplorerRequest):
    pass


# --- Views ---


@dataclass(frozen=True, slots=True, kw_only=True)
class View:
    """Base class for all explorer views."""

    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class OverviewView(View):
    repository: str
    health: str
    modules: int
    symbols: int
    dependencies: int
    capabilities: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class StatisticsView(View):
    modules: int
    classes: int
    functions: int
    methods: int
    symbols: int
    dependencies: int
    avg_symbols_per_module: float
    largest_module: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SymbolView(View):
    name: str
    kind: str
    module: str
    file: str
    visibility: str
    methods: list[str]
    dependencies: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleView(View):
    name: str
    file: str
    symbols: list[str]
    dependencies: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class DependencyView(View):
    source: str
    dependencies: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchView(View):
    query: str
    results: list[str]
