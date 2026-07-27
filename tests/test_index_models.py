from dataclasses import FrozenInstanceError
from pathlib import PurePosixPath

import pytest

from eag.index.models import (
    RepositoryIndex,
    RepositoryIndexIdentity,
    RepositoryIndexStatistics,
)
from eag.source.models import (
    SourceLocation,
    Symbol,
    SymbolIdentity,
)
from eag.source.state import SymbolKind


class TestIndexModels:
    def test_statistics_validation(self):
        with pytest.raises(ValueError):
            RepositoryIndexStatistics(modules=-1)

    def test_index_immutable(self):
        ident = RepositoryIndexIdentity(repository="test")
        stats = RepositoryIndexStatistics()
        idx = RepositoryIndex(identity=ident, statistics=stats)
        with pytest.raises(FrozenInstanceError):
            idx.statistics = RepositoryIndexStatistics(modules=10)

    def test_find_symbol(self):
        ident = RepositoryIndexIdentity(repository="test")
        stats = RepositoryIndexStatistics()
        sym = Symbol(
            identity=SymbolIdentity(
                qualified_name="eag.main.run", module="eag.main", kind=SymbolKind.FUNCTION
            ),
            location=SourceLocation(
                path=PurePosixPath("main.py"), line=1, column=0, end_line=1, end_column=10
            ),
        )
        idx = RepositoryIndex(identity=ident, statistics=stats, symbols=(sym,))

        found = idx.find_symbol("eag.main.run")
        assert found == sym

    def test_find_symbol_not_found(self):
        from eag.index.errors import SymbolNotFoundError

        ident = RepositoryIndexIdentity(repository="test")
        stats = RepositoryIndexStatistics()
        idx = RepositoryIndex(identity=ident, statistics=stats)

        with pytest.raises(SymbolNotFoundError):
            idx.find_symbol("nonexistent")

    def test_find_symbols_by_kind(self):
        ident = RepositoryIndexIdentity(repository="test")
        stats = RepositoryIndexStatistics()

        sym1 = Symbol(
            identity=SymbolIdentity(
                qualified_name="eag.main.Foo", module="eag.main", kind=SymbolKind.CLASS
            ),
            location=SourceLocation(
                path=PurePosixPath("main.py"), line=1, column=0, end_line=1, end_column=10
            ),
        )
        sym2 = Symbol(
            identity=SymbolIdentity(
                qualified_name="eag.main.run", module="eag.main", kind=SymbolKind.FUNCTION
            ),
            location=SourceLocation(
                path=PurePosixPath("main.py"), line=5, column=0, end_line=5, end_column=10
            ),
        )
        idx = RepositoryIndex(identity=ident, statistics=stats, symbols=(sym1, sym2))

        classes = idx.find_symbols(SymbolKind.CLASS)
        assert len(classes) == 1
        assert classes[0] == sym1
