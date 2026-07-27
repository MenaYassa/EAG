from pathlib import Path, PurePosixPath

import pytest

from eag.events import EventBus
from eag.graph.builder import GraphBuilder
from eag.graph.errors import GraphNotLoadedError, GraphQueryError
from eag.graph.events import GraphBuilt, GraphQueryExecuted
from eag.graph.runtime import GraphRuntime, GraphSnapshot
from eag.graph.state import GraphNodeKind
from eag.index.builder import RepositoryIndexBuilder
from eag.source.models import (
    AnalysisResult,
    Dependency,
    ModuleIdentity,
    SourceFileIdentity,
    SourceLocation,
    Symbol,
    SymbolIdentity,
)
from eag.source.state import DependencyKind, SymbolKind


@pytest.fixture
def mock_index():
    builder = RepositoryIndexBuilder("test-repo")

    ident = SourceFileIdentity(
        absolute_path=Path("/repo/main.py"),
        repository_path=PurePosixPath("main.py"),
        language="python",
        fingerprint="abc",
    )
    module = ModuleIdentity(name="eag.main", path=PurePosixPath("main.py"))

    sym1 = Symbol(
        identity=SymbolIdentity(
            qualified_name="eag.main.Kernel", module="eag.main", kind=SymbolKind.CLASS
        ),
        location=SourceLocation(
            path=PurePosixPath("main.py"), line=1, column=0, end_line=1, end_column=10
        ),
    )
    sym2 = Symbol(
        identity=SymbolIdentity(
            qualified_name="eag.main.Kernel.run", module="eag.main", kind=SymbolKind.METHOD
        ),
        location=SourceLocation(
            path=PurePosixPath("main.py"), line=2, column=4, end_line=2, end_column=10
        ),
    )

    # eag.main imports eag.events (simulated)
    dep1 = Dependency(source="eag.main", target="eag.events", kind=DependencyKind.IMPORT)

    result = AnalysisResult(
        identity=ident, module=module, symbols=(sym1, sym2), dependencies=(dep1,)
    )
    builder.add_result(result)
    return builder.build()


@pytest.fixture
def runtime(mock_index):
    event_bus = EventBus()
    builder = GraphBuilder(event_bus)
    runtime = GraphRuntime(builder, event_bus)
    runtime.build(mock_index)
    return runtime


class TestGraphRuntime:
    def test_not_loaded_error(self):
        rt = GraphRuntime(GraphBuilder(), EventBus())
        with pytest.raises(GraphNotLoadedError):
            rt.graph()

    def test_build(self, mock_index):
        rt = GraphRuntime(GraphBuilder(), EventBus())
        snapshot = rt.build(mock_index)

        assert isinstance(snapshot, GraphSnapshot)
        assert snapshot.repository == "test-repo"
        assert rt.graph() is not None
        assert rt.statistics().nodes > 0

    def test_node_query(self, runtime):
        node = runtime.node("module:eag.main")
        assert node.kind == GraphNodeKind.MODULE
        assert node.name == "main"  # <-- Change "eag.main" to "main"

    def test_node_not_found(self, runtime):
        with pytest.raises(GraphQueryError):
            runtime.node("module:nonexistent")

    def test_neighbors(self, runtime):
        # Module neighbors should be the class it contains and the dependency it imports
        neighbors = runtime.neighbors("module:eag.main")
        neighbor_ids = {n.id for n in neighbors}

        assert "class:eag.main.Kernel" in neighbor_ids
        assert "dependency:eag.events" in neighbor_ids

    def test_dependencies(self, runtime):
        deps = runtime.dependencies("module:eag.main")
        assert len(deps) == 1
        assert deps[0].id == "dependency:eag.events"

    def test_dependents(self, runtime):
        dependents = runtime.dependents("dependency:eag.events")
        assert len(dependents) == 1
        assert dependents[0].id == "module:eag.main"

    def test_events_published(self, mock_index):
        event_bus = EventBus()
        builder = GraphBuilder(event_bus)
        rt = GraphRuntime(builder, event_bus)

        events = []
        # Subscribe to both event types
        event_bus.subscribe(GraphBuilt, lambda e: events.append(e))
        event_bus.subscribe(GraphQueryExecuted, lambda e: events.append(e))

        rt.build(mock_index)
        rt.node("module:eag.main")

        # Should have GraphBuilt + GraphQueryExecuted
        event_names = [e.__class__.__name__ for e in events]
        assert "GraphBuilt" in event_names
        assert "GraphQueryExecuted" in event_names
