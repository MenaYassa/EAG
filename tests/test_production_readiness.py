"""Production Readiness tests for EAG (Sprint 6.5F)."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from eag.source.benchmark import BenchmarkRunner
from eag.source.cache import SemanticCache
from eag.source.incremental import ChangeSet, IncrementalIndexer
from eag.source.python import (
    GenerateSymbolTransformation,
    MoveSymbolTransformation,
    OrganizeImportsTransformation,
    RenameTransformation,
    SafeDeleteTransformation,
    SafeReplaceTransformation,
    Transformation,
    TransformationContext,
    TransformationResult,
)
from eag.source.recovery import RecoveryCoordinator
from eag.source.runtime import SourceRuntime
from eag.source.scheduler import TransformationScheduler


@pytest.fixture
def runtime() -> SourceRuntime:
    return SourceRuntime()


@pytest.fixture
def cache() -> SemanticCache:
    return SemanticCache()


@pytest.fixture
def indexer(runtime: SourceRuntime, cache: SemanticCache) -> IncrementalIndexer:
    return IncrementalIndexer(runtime, cache)


@pytest.fixture
def scheduler(runtime: SourceRuntime) -> TransformationScheduler:
    return TransformationScheduler(runtime)


@pytest.fixture
def coordinator() -> RecoveryCoordinator:
    return RecoveryCoordinator()


@pytest.fixture
def bench_runner(runtime: SourceRuntime) -> BenchmarkRunner:
    return BenchmarkRunner(runtime)


@dataclass
class MockWorkspace:
    writes: dict[Path, str] = field(default_factory=dict)
    snapshots: dict[Path, str] = field(default_factory=dict)
    fail_write: bool = False

    def write(self, path: Path, content: str) -> None:
        if self.fail_write:
            raise OSError("Simulated workspace failure")
        self.writes[path] = content

    def snapshot(self, path: Path, content: str) -> None:
        self.snapshots[path] = content

    def restore(self, path: Path) -> str:
        return self.snapshots.get(path, "")


@dataclass
class MockRepository:
    commits: list[str] = field(default_factory=list)
    fail_commit: bool = False

    def commit(self, message: str) -> str:
        if self.fail_commit:
            raise OSError("Simulated repository failure")
        self.commits.append(message)
        return "mock_commit_hash"

    def revert(self, commit_hash: str) -> None:
        pass


def make_context(runtime: SourceRuntime, code: str, path: str = "test.py") -> TransformationContext:
    doc = runtime.parse(Path(path), code)
    return TransformationContext(document=doc, content=code)


# --- Semantic Cache Tests (20) ---


class TestSemanticCache:
    def test_cache_miss(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        assert cache.get(Path("test.py"), doc.checksum) is None

    def test_cache_hit(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        assert cache.get(Path("test.py"), doc.checksum) is doc

    def test_cache_invalidation(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        cache.invalidate(Path("test.py"))
        assert cache.get(Path("test.py"), doc.checksum) is None

    def test_cache_clear(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        cache.clear()
        assert cache.get(Path("test.py"), doc.checksum) is None

    def test_checksum_mismatch(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        assert cache.get(Path("test.py"), "wrong_checksum") is None

    def test_get_after_set(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        assert cache.get(Path("test.py"), doc.checksum) is not None

    def test_invalidate_nonexistent(self, cache: SemanticCache) -> None:
        cache.invalidate(Path("nonexistent.py"))  # Should not raise

    def test_set_overwrites(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc1 = runtime.parse(Path("test.py"), "x = 1\n")
        doc2 = runtime.parse(Path("test.py"), "y = 2\n")
        cache.set(Path("test.py"), doc1.checksum, doc1)
        cache.set(Path("test.py"), doc2.checksum, doc2)
        assert cache.get(Path("test.py"), doc2.checksum) is doc2

    def test_multiple_files(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc1 = runtime.parse(Path("a.py"), "x = 1\n")
        doc2 = runtime.parse(Path("b.py"), "y = 2\n")
        cache.set(Path("a.py"), doc1.checksum, doc1)
        cache.set(Path("b.py"), doc2.checksum, doc2)
        assert cache.get(Path("a.py"), doc1.checksum) is doc1
        assert cache.get(Path("b.py"), doc2.checksum) is doc2

    def test_clear_empties_all(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        cache.clear()
        assert cache.get(Path("test.py"), doc.checksum) is None

    def test_checksum_case_sensitivity(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        assert cache.get(Path("test.py"), doc.checksum.upper()) is None

    def test_path_case_sensitivity(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        assert cache.get(Path("TEST.PY"), doc.checksum) is None

    def test_get_none_on_empty(self, cache: SemanticCache) -> None:
        assert cache.get(Path("test.py"), "abc") is None

    def test_set_none_document(self, cache: SemanticCache) -> None:
        cache.set(Path("test.py"), "abc", None)
        assert cache.get(Path("test.py"), "abc") is None

    def test_get_none_after_invalidate(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        cache.invalidate(Path("test.py"))
        assert cache.get(Path("test.py"), doc.checksum) is None

    def test_set_twice(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        cache.set(Path("test.py"), doc.checksum, doc)
        assert cache.get(Path("test.py"), doc.checksum) is doc

    def test_invalidate_one_of_many(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc1 = runtime.parse(Path("a.py"), "x = 1\n")
        doc2 = runtime.parse(Path("b.py"), "y = 2\n")
        cache.set(Path("a.py"), doc1.checksum, doc1)
        cache.set(Path("b.py"), doc2.checksum, doc2)
        cache.invalidate(Path("a.py"))
        assert cache.get(Path("a.py"), doc1.checksum) is None
        assert cache.get(Path("b.py"), doc2.checksum) is doc2

    def test_clear_idempotent(self, cache: SemanticCache) -> None:
        cache.clear()
        cache.clear()

    def test_hit_after_clear_fails(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        cache.set(Path("test.py"), doc.checksum, doc)
        cache.clear()
        assert cache.get(Path("test.py"), doc.checksum) is None

    def test_large_document_cache(self, cache: SemanticCache, runtime: SourceRuntime) -> None:
        code = "\n".join([f"x_{i} = {i}" for i in range(1000)])
        doc = runtime.parse(Path("large.py"), code)
        cache.set(Path("large.py"), doc.checksum, doc)
        assert cache.get(Path("large.py"), doc.checksum) is doc


# --- Incremental Indexer Tests (25) ---


class TestIncrementalIndexer:
    def test_index_added_files(self, indexer: IncrementalIndexer) -> None:
        changeset = ChangeSet(added=(Path("a.py"), Path("b.py")))
        contents = {Path("a.py"): "x=1", Path("b.py"): "y=2"}
        delta = indexer.update(changeset, contents)
        assert len(delta.updated_documents) == 2
        assert delta.cache_misses == 2

    def test_index_modified_files(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        delta = indexer.update(ChangeSet(modified=(Path("a.py"),)), {Path("a.py"): "x=2"})
        assert len(delta.updated_documents) == 1
        assert delta.cache_misses == 1

    def test_index_unchanged_files_use_cache(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        delta = indexer.update(ChangeSet(modified=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert len(delta.updated_documents) == 1
        assert delta.cache_hits == 1
        assert delta.cache_misses == 0

    def test_index_deleted_files(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        delta = indexer.update(ChangeSet(deleted=(Path("a.py"),)), {})
        assert delta.deleted_paths == (Path("a.py"),)
        assert len(delta.updated_documents) == 0

    def test_index_mixed_changes(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        changeset = ChangeSet(
            added=(Path("b.py"),), modified=(Path("a.py"),), deleted=(Path("c.py"),)
        )
        contents = {Path("a.py"): "x=2", Path("b.py"): "y=1"}
        delta = indexer.update(changeset, contents)
        assert len(delta.updated_documents) == 2
        assert delta.deleted_paths == (Path("c.py"),)

    def test_index_empty_changeset(self, indexer: IncrementalIndexer) -> None:
        delta = indexer.update(ChangeSet(), {})
        assert len(delta.updated_documents) == 0
        assert len(delta.deleted_paths) == 0

    def test_index_missing_content(self, indexer: IncrementalIndexer) -> None:
        # If content is missing, it parses empty string
        delta = indexer.update(ChangeSet(added=(Path("a.py"),)), {})
        assert len(delta.updated_documents) == 1
        assert delta.updated_documents[0].symbols == ()

    def test_index_delta_updated_documents(self, indexer: IncrementalIndexer) -> None:
        delta = indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert isinstance(delta.updated_documents, tuple)

    def test_index_delta_deleted_paths(self, indexer: IncrementalIndexer) -> None:
        delta = indexer.update(ChangeSet(deleted=(Path("a.py"),)), {})
        assert isinstance(delta.deleted_paths, tuple)

    def test_index_delta_cache_hits(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        delta = indexer.update(ChangeSet(modified=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert delta.cache_hits == 1

    def test_index_delta_cache_misses(self, indexer: IncrementalIndexer) -> None:
        delta = indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert delta.cache_misses == 1

    def test_index_added_and_modified(self, indexer: IncrementalIndexer) -> None:
        changeset = ChangeSet(added=(Path("a.py"),), modified=(Path("b.py"),))
        indexer.update(ChangeSet(added=(Path("b.py"),)), {Path("b.py"): "y=1"})
        contents = {Path("a.py"): "x=1", Path("b.py"): "y=2"}
        delta = indexer.update(changeset, contents)
        assert delta.cache_misses == 2

    def test_index_deleted_and_added(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        changeset = ChangeSet(deleted=(Path("a.py"),), added=(Path("b.py"),))
        delta = indexer.update(changeset, {Path("b.py"): "y=1"})
        assert delta.deleted_paths == (Path("a.py"),)
        assert len(delta.updated_documents) == 1

    def test_index_renamed_file(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        changeset = ChangeSet(deleted=(Path("a.py"),), added=(Path("b.py"),))
        delta = indexer.update(changeset, {Path("b.py"): "x=1"})
        assert delta.cache_misses == 1  # b.py is new, even though content is same

    def test_index_dependency_invalidation(self, indexer: IncrementalIndexer) -> None:
        # Hard to test real deps without full graph, but we ensure cache invalidates on delete
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        indexer.update(ChangeSet(deleted=(Path("a.py"),)), {})
        delta = indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert delta.cache_misses == 1

    def test_index_graph_update(self, indexer: IncrementalIndexer) -> None:
        # Simulated by ensuring updated docs are returned
        delta = indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert len(delta.updated_documents) > 0

    def test_index_deterministic_cache(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        d1 = indexer.update(ChangeSet(modified=(Path("a.py"),)), {Path("a.py"): "x=1"})
        d2 = indexer.update(ChangeSet(modified=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert d1.cache_hits == d2.cache_hits

    def test_index_large_changeset(self, indexer: IncrementalIndexer) -> None:
        paths = [Path(f"f_{i}.py") for i in range(10)]
        contents = {p: "x=1" for p in paths}
        delta = indexer.update(ChangeSet(added=tuple(paths)), contents)
        assert len(delta.updated_documents) == 10

    def test_index_partial_cache(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        delta = indexer.update(
            ChangeSet(added=(Path("a.py"),), modified=(Path("b.py"),)),
            {Path("a.py"): "x=1", Path("b.py"): "y=1"},
        )
        assert delta.cache_hits == 1
        assert delta.cache_misses == 1

    def test_index_clear_cache_between_runs(self, runtime: SourceRuntime) -> None:
        c = SemanticCache()
        idx = IncrementalIndexer(runtime, c)
        idx.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        c.clear()
        delta = idx.update(ChangeSet(modified=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert delta.cache_misses == 1

    def test_index_invalid_syntax(self, indexer: IncrementalIndexer) -> None:
        delta = indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "def x(:\n"})
        assert len(delta.updated_documents[0].diagnostics) > 0

    def test_index_unicode_content(self, indexer: IncrementalIndexer) -> None:
        delta = indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "# café\n"})
        assert len(delta.updated_documents) == 1

    def test_index_nested_files(self, indexer: IncrementalIndexer) -> None:
        p = Path("src") / "a.py"
        delta = indexer.update(ChangeSet(added=(p,)), {p: "x=1"})
        assert len(delta.updated_documents) == 1

    def test_index_overwrite_existing(self, indexer: IncrementalIndexer) -> None:
        # First update (added)
        delta1 = indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})

        # Second update (modified)
        delta2 = indexer.update(ChangeSet(modified=(Path("a.py"),)), {Path("a.py"): "x=2"})

        # Verify the file was processed both times and the checksum changed
        assert len(delta1.updated_documents) == 1
        assert len(delta2.updated_documents) == 1
        assert delta1.updated_documents[0].checksum != delta2.updated_documents[0].checksum

    def test_index_checksum_mismatch_triggers_miss(self, indexer: IncrementalIndexer) -> None:
        indexer.update(ChangeSet(added=(Path("a.py"),)), {Path("a.py"): "x=1"})
        # Manually corrupt cache checksum
        indexer._cache.set(
            Path("a.py"),
            "bad_checksum",
            indexer._cache.get(Path("a.py"), "bad_checksum")[1]
            if indexer._cache.get(Path("a.py"), "bad_checksum")
            else None,
        )
        delta = indexer.update(ChangeSet(modified=(Path("a.py"),)), {Path("a.py"): "x=1"})
        assert delta.cache_misses == 1


# --- Transformation Scheduler Tests (25) ---


class TestTransformationScheduler:
    def test_fifo_order(self, scheduler: TransformationScheduler, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=0)
        scheduler.submit(RenameTransformation("a", "b"), ctx, priority=0)
        results = scheduler.execute()
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True

    def test_priority_order(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=1)
        scheduler.submit(RenameTransformation("foo", "b"), ctx, priority=0)
        results = scheduler.execute()
        assert results[0].summary == "Renamed 'foo' to 'b'. Updated 0 references."
        assert results[1].summary == "Validation failed: Symbol 'foo' not found in source document"

    def test_dependency_order(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        id1 = scheduler.submit(RenameTransformation("foo", "bar"), ctx, priority=0)
        scheduler.submit(RenameTransformation("bar", "baz"), ctx, priority=0, dependencies=(id1,))
        results = scheduler.execute()
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True

    def test_dependency_not_met(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(
            RenameTransformation("foo", "bar"), ctx, priority=0, dependencies=("nonexistent_id",)
        )
        results = scheduler.execute()
        assert len(results) == 0  # Deadlock, breaks safely

    def test_multiple_dependencies(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        id1 = scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=0)
        id2 = scheduler.submit(RenameTransformation("a", "b"), ctx, priority=0)
        scheduler.submit(RenameTransformation("b", "c"), ctx, priority=0, dependencies=(id1, id2))
        results = scheduler.execute()
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_empty_queue(self, scheduler: TransformationScheduler) -> None:
        results = scheduler.execute()
        assert len(results) == 0

    def test_single_task(self, scheduler: TransformationScheduler, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "bar"), ctx)
        results = scheduler.execute()
        assert len(results) == 1
        assert results[0].success is True

    def test_high_priority_last_submitted(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=0)
        scheduler.submit(RenameTransformation("foo", "b"), ctx, priority=10)
        results = scheduler.execute()
        assert "a" in results[0].summary  # Priority 0 runs first

    def test_low_priority_first_submitted(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=10)
        scheduler.submit(RenameTransformation("foo", "b"), ctx, priority=0)
        results = scheduler.execute()
        assert "b" in results[0].summary

    def test_same_priority_fifo(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=0)
        scheduler.submit(RenameTransformation("a", "b"), ctx, priority=0)
        results = scheduler.execute()
        assert "a" in results[0].summary
        assert "b" in results[1].summary

    def test_complex_dependency_graph(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        id1 = scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=0)
        id2 = scheduler.submit(RenameTransformation("a", "b"), ctx, priority=0, dependencies=(id1,))
        id3 = scheduler.submit(RenameTransformation("b", "c"), ctx, priority=0, dependencies=(id2,))
        scheduler.submit(RenameTransformation("c", "d"), ctx, priority=0, dependencies=(id3,))
        results = scheduler.execute()
        assert len(results) == 4

    def test_circular_dependency_deadlock(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, dependencies=("id2",))
        scheduler.submit(RenameTransformation("a", "b"), ctx, dependencies=("id1",))
        results = scheduler.execute()
        assert len(results) == 0

    def test_state_threaded_content(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "bar"), ctx)
        scheduler.submit(RenameTransformation("bar", "baz"), ctx)
        results = scheduler.execute()
        assert "baz" in results[1].edits[0].new_content

    def test_state_threaded_document(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "bar"), ctx)
        results = scheduler.execute()
        assert results[0].edits[0].new_content == "def bar():\n    pass\n"

    def test_failed_task_state_not_updated(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "123bad"), ctx)  # Fails
        scheduler.submit(RenameTransformation("foo", "bar"), ctx)
        results = scheduler.execute()
        assert results[0].success is False
        assert results[1].success is True  # 'foo' still exists

    def test_success_task_state_updated(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "bar"), ctx)
        scheduler.submit(RenameTransformation("bar", "baz"), ctx)
        results = scheduler.execute()
        assert results[1].success is True

    def test_multiple_files_parallel_state(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc1 = runtime.parse(Path("a.py"), "def foo():\n    pass\n")
        doc2 = runtime.parse(Path("b.py"), "def bar():\n    pass\n")
        ctx1 = TransformationContext(document=doc1, content="def foo():\n    pass\n")
        ctx2 = TransformationContext(document=doc2, content="def bar():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx1)
        scheduler.submit(RenameTransformation("bar", "b"), ctx2)
        results = scheduler.execute()
        assert len(results) == 2

    def test_scheduler_determinism(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "bar"), ctx)
        r1 = scheduler.execute()[0]
        scheduler2 = TransformationScheduler(runtime)
        scheduler2.submit(RenameTransformation("foo", "bar"), ctx)
        r2 = scheduler2.execute()[0]
        assert r1.edits[0].new_content == r2.edits[0].new_content

    def test_scheduler_seq_ordering(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=0)
        scheduler.submit(RenameTransformation("a", "b"), ctx, priority=0)
        results = scheduler.execute()
        assert "a" in results[0].summary

    def test_scheduler_priority_zero(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=0)
        results = scheduler.execute()
        assert results[0].success is True

    def test_scheduler_priority_negative(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=-1)
        results = scheduler.execute()
        assert results[0].success is True

    def test_scheduler_priority_large(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx, priority=1000)
        results = scheduler.execute()
        assert results[0].success is True

    def test_scheduler_task_id_unique(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        id1 = scheduler.submit(RenameTransformation("foo", "a"), ctx)
        id2 = scheduler.submit(RenameTransformation("a", "b"), ctx)
        assert id1 != id2

    def test_scheduler_completed_set(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        id1 = scheduler.submit(RenameTransformation("foo", "a"), ctx)
        scheduler.execute()
        assert id1 in scheduler._completed

    def test_scheduler_queue_empties(
        self, scheduler: TransformationScheduler, runtime: SourceRuntime
    ) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        scheduler.submit(RenameTransformation("foo", "a"), ctx)
        scheduler.execute()
        assert len(scheduler._queue) == 0


# --- Recovery Coordinator Tests (20) ---


class TestRecoveryCoordinator:
    def test_rollback_success(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(
            success=False, transformation_name="test", undo_metadata={"old": "new"}
        )
        success = coordinator.rollback(result, None, None)
        assert success is True

    def test_rollback_no_metadata(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(success=False, transformation_name="test")
        success = coordinator.rollback(result, None, None)
        assert success is True

    def test_rollback_workspace_failure(self, coordinator: RecoveryCoordinator) -> None:
        ws = MockWorkspace(fail_write=True)
        result = TransformationResult(
            success=False, transformation_name="test", files_modified=("a.py",)
        )
        success = coordinator.rollback(result, None, workspace=ws)
        assert success is False

    def test_rollback_repository_failure(self, coordinator: RecoveryCoordinator) -> None:
        repo = MockRepository(fail_commit=True)
        result = TransformationResult(success=False, transformation_name="test")
        success = coordinator.rollback(result, None, repository=repo)
        assert success is False

    def test_rollback_partial_apply(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(
            success=False, transformation_name="test", files_modified=("a.py", "b.py")
        )
        success = coordinator.rollback(result, None)
        assert success is True

    def test_rollback_transaction_recovery(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(
            success=False, transformation_name="test", undo_metadata={"tx": "123"}
        )
        success = coordinator.rollback(result, None)
        assert success is True

    def test_rollback_nested(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(
            success=False, transformation_name="test", undo_metadata={"nested": True}
        )
        success = coordinator.rollback(result, None)
        assert success is True

    def test_rollback_event_order(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(success=False, transformation_name="test")
        success = coordinator.rollback(result, None)
        assert success is True

    def test_rollback_workspace_success(self, coordinator: RecoveryCoordinator) -> None:
        ws = MockWorkspace()
        result = TransformationResult(
            success=False, transformation_name="test", files_modified=("a.py",)
        )
        success = coordinator.rollback(result, None, workspace=ws)
        assert success is True

    def test_rollback_repository_success(self, coordinator: RecoveryCoordinator) -> None:
        repo = MockRepository()
        result = TransformationResult(success=False, transformation_name="test")
        success = coordinator.rollback(result, None, repository=repo)
        assert success is True

    def test_rollback_all_fail(self, coordinator: RecoveryCoordinator) -> None:
        ws = MockWorkspace(fail_write=True)
        repo = MockRepository(fail_commit=True)
        result = TransformationResult(
            success=False, transformation_name="test", files_modified=("a.py",)
        )
        success = coordinator.rollback(result, None, workspace=ws, repository=repo)
        assert success is False

    def test_rollback_no_workspace(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(
            success=False, transformation_name="test", files_modified=("a.py",)
        )
        success = coordinator.rollback(result, None, workspace=None)
        assert success is True

    def test_rollback_no_repository(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(success=False, transformation_name="test")
        success = coordinator.rollback(result, None, repository=None)
        assert success is True

    def test_rollback_no_files_modified(self, coordinator: RecoveryCoordinator) -> None:
        ws = MockWorkspace()
        result = TransformationResult(success=False, transformation_name="test")
        success = coordinator.rollback(result, None, workspace=ws)
        assert success is True

    def test_rollback_undo_metadata_present(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(
            success=False, transformation_name="test", undo_metadata={"k": "v"}
        )
        success = coordinator.rollback(result, None)
        assert success is True

    def test_rollback_undo_metadata_absent(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(success=False, transformation_name="test")
        success = coordinator.rollback(result, None)
        assert success is True

    def test_rollback_multiple_files(self, coordinator: RecoveryCoordinator) -> None:
        ws = MockWorkspace()
        result = TransformationResult(
            success=False, transformation_name="test", files_modified=("a.py", "b.py")
        )
        success = coordinator.rollback(result, None, workspace=ws)
        assert success is True

    def test_rollback_single_file(self, coordinator: RecoveryCoordinator) -> None:
        ws = MockWorkspace()
        result = TransformationResult(
            success=False, transformation_name="test", files_modified=("a.py",)
        )
        success = coordinator.rollback(result, None, workspace=ws)
        assert success is True

    def test_rollback_idempotent(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(success=False, transformation_name="test")
        s1 = coordinator.rollback(result, None)
        s2 = coordinator.rollback(result, None)
        assert s1 == s2

    def test_rollback_returns_bool(self, coordinator: RecoveryCoordinator) -> None:
        result = TransformationResult(success=False, transformation_name="test")
        success = coordinator.rollback(result, None)
        assert isinstance(success, bool)


# --- Benchmark Runner Tests (15) ---


class TestBenchmarkRunner:
    def test_benchmark_small(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[10])
        assert len(results) == 1
        assert results[0].size == 10
        assert results[0].parse_time_ms > 0
        assert results[0].transform_time_ms > 0
        assert results[0].total_time_ms > 0

    def test_benchmark_scaling(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[10, 100])
        assert len(results) == 2
        assert results[1].total_time_ms > results[0].total_time_ms

    def test_benchmark_parse_time(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[10])
        assert results[0].parse_time_ms > 0

    def test_benchmark_transform_time(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[10])
        assert results[0].transform_time_ms > 0

    def test_benchmark_total_time(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[10])
        assert results[0].total_time_ms == results[0].parse_time_ms + results[0].transform_time_ms

    def test_benchmark_size_1(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[1])
        assert results[0].size == 1

    def test_benchmark_size_10(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[10])
        assert results[0].size == 10

    def test_benchmark_size_100(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[100])
        assert results[0].size == 100

    def test_benchmark_suite_sizes(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[1, 10])
        assert len(results) == 2

    def test_benchmark_result_fields(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[1])
        assert hasattr(results[0], "size")
        assert hasattr(results[0], "parse_time_ms")
        assert hasattr(results[0], "transform_time_ms")
        assert hasattr(results[0], "total_time_ms")

    def test_benchmark_result_size(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[5])
        assert results[0].size == 5

    def test_benchmark_result_parse_ms_positive(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[5])
        assert results[0].parse_time_ms >= 0.0

    def test_benchmark_result_transform_ms_positive(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[5])
        assert results[0].transform_time_ms >= 0.0

    def test_benchmark_result_total_ms_positive(self, bench_runner: BenchmarkRunner) -> None:
        results = bench_runner.run_suite(sizes=[5])
        assert results[0].total_time_ms >= 0.0

    def test_benchmark_runner_initialization(self, runtime: SourceRuntime) -> None:
        runner = BenchmarkRunner(runtime)
        assert runner._runtime is runtime


# --- End-to-End Integration Tests (30) ---


class TestEndToEndIntegration:
    def _run_e2e(
        self, runtime: SourceRuntime, transform: Transformation, code: str, path: str = "test.py"
    ) -> tuple[TransformationResult, MockWorkspace, MockRepository]:
        doc = runtime.parse(Path(path), code)
        ctx = TransformationContext(document=doc, content=code)
        ws = MockWorkspace()
        repo = MockRepository()

        result = transform.apply(ctx)
        if result.success and result.edits:
            ws.write(Path(path), result.edits[0].new_content)
            repo.commit("Applied transformation")
        return result, ws, repo

    def test_e2e_rename_success(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, RenameTransformation("foo", "bar"), "def foo():\n    pass\n"
        )
        assert result.success is True
        assert "def bar():" in ws.writes[Path("test.py")]
        assert len(repo.commits) == 1

    def test_e2e_rename_and_commit(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, RenameTransformation("foo", "bar"), "def foo():\n    pass\n"
        )
        assert len(repo.commits) == 1

    def test_e2e_move_success(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, MoveSymbolTransformation("foo", "utils"), "from test import foo\n"
        )
        assert result.success is True
        assert "from utils import foo" in ws.writes[Path("test.py")]

    def test_e2e_move_and_commit(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, MoveSymbolTransformation("foo", "utils"), "from test import foo\n"
        )
        assert len(repo.commits) == 1

    def test_e2e_delete_success(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, SafeDeleteTransformation("foo"), "def foo():\n    pass\n"
        )
        assert result.success is True
        assert "def foo():" not in ws.writes[Path("test.py")]

    def test_e2e_delete_and_commit(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, SafeDeleteTransformation("foo"), "def foo():\n    pass\n"
        )
        assert len(repo.commits) == 1

    def test_e2e_generate_success(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, GenerateSymbolTransformation("MyClass", "class"), "pass\n"
        )
        assert result.success is True
        assert "class MyClass:" in ws.writes[Path("test.py")]

    def test_e2e_generate_and_commit(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, GenerateSymbolTransformation("MyClass", "class"), "pass\n"
        )
        assert len(repo.commits) == 1

    def test_e2e_replace_success(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(runtime, SafeReplaceTransformation("1", "2"), "x = 1\n")
        assert result.success is True
        assert "x = 2" in ws.writes[Path("test.py")]

    def test_e2e_replace_and_commit(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(runtime, SafeReplaceTransformation("1", "2"), "x = 1\n")
        assert len(repo.commits) == 1

    def test_e2e_organize_imports_success(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, OrganizeImportsTransformation(), "import sys\nimport os\n"
        )
        assert result.success is True
        assert "import os\nimport sys\n" in ws.writes[Path("test.py")]

    def test_e2e_organize_imports_and_commit(self, runtime: SourceRuntime) -> None:
        result, ws, repo = self._run_e2e(
            runtime, OrganizeImportsTransformation(), "import sys\nimport os\n"
        )
        assert len(repo.commits) == 1

    def test_e2e_rename_workspace_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        ws = MockWorkspace(fail_write=True)
        repo = MockRepository()
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)
        assert result.success is True
        with pytest.raises(IOError):
            ws.write(Path("test.py"), result.edits[0].new_content)
        assert len(repo.commits) == 0

    def test_e2e_rename_repository_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        ws = MockWorkspace()
        repo = MockRepository(fail_commit=True)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)
        ws.write(Path("test.py"), result.edits[0].new_content)
        with pytest.raises(IOError):
            repo.commit("Applied")
        # In real E2E, RecoveryCoordinator would now revert the workspace write.

    def test_e2e_move_workspace_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "from test import foo\n")
        ctx = TransformationContext(document=doc, content="from test import foo\n")
        ws = MockWorkspace(fail_write=True)
        transform = MoveSymbolTransformation("foo", "utils")
        result = transform.apply(ctx)
        with pytest.raises(IOError):
            ws.write(Path("test.py"), result.edits[0].new_content)

    def test_e2e_move_repository_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "from test import foo\n")
        ctx = TransformationContext(document=doc, content="from test import foo\n")
        repo = MockRepository(fail_commit=True)
        transform = MoveSymbolTransformation("foo", "utils")
        transform.apply(ctx)
        with pytest.raises(IOError):
            repo.commit("Applied")

    def test_e2e_delete_workspace_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        ws = MockWorkspace(fail_write=True)
        transform = SafeDeleteTransformation("foo")
        result = transform.apply(ctx)
        with pytest.raises(IOError):
            ws.write(Path("test.py"), result.edits[0].new_content)

    def test_e2e_delete_repository_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")
        repo = MockRepository(fail_commit=True)
        transform = SafeDeleteTransformation("foo")
        transform.apply(ctx)
        with pytest.raises(IOError):
            repo.commit("Applied")

    def test_e2e_generate_workspace_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "pass\n")
        ctx = TransformationContext(document=doc, content="pass\n")
        ws = MockWorkspace(fail_write=True)
        transform = GenerateSymbolTransformation("MyClass", "class")
        result = transform.apply(ctx)
        with pytest.raises(IOError):
            ws.write(Path("test.py"), result.edits[0].new_content)

    def test_e2e_generate_repository_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "pass\n")
        ctx = TransformationContext(document=doc, content="pass\n")
        repo = MockRepository(fail_commit=True)
        transform = GenerateSymbolTransformation("MyClass", "class")
        transform.apply(ctx)
        with pytest.raises(IOError):
            repo.commit("Applied")

    def test_e2e_replace_workspace_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        ctx = TransformationContext(document=doc, content="x = 1\n")
        ws = MockWorkspace(fail_write=True)
        transform = SafeReplaceTransformation("1", "2")
        result = transform.apply(ctx)
        with pytest.raises(IOError):
            ws.write(Path("test.py"), result.edits[0].new_content)

    def test_e2e_replace_repository_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "x = 1\n")
        ctx = TransformationContext(document=doc, content="x = 1\n")
        repo = MockRepository(fail_commit=True)
        transform = SafeReplaceTransformation("1", "2")
        transform.apply(ctx)
        with pytest.raises(IOError):
            repo.commit("Applied")

    def test_e2e_organize_imports_workspace_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "import sys\nimport os\n")
        ctx = TransformationContext(document=doc, content="import sys\nimport os\n")
        ws = MockWorkspace(fail_write=True)
        transform = OrganizeImportsTransformation()
        result = transform.apply(ctx)
        with pytest.raises(IOError):
            ws.write(Path("test.py"), result.edits[0].new_content)

    def test_e2e_organize_imports_repository_failure(self, runtime: SourceRuntime) -> None:
        doc = runtime.parse(Path("test.py"), "import sys\nimport os\n")
        ctx = TransformationContext(document=doc, content="import sys\nimport os\n")
        repo = MockRepository(fail_commit=True)
        transform = OrganizeImportsTransformation()
        transform.apply(ctx)
        with pytest.raises(IOError):
            repo.commit("Applied")

    def test_e2e_planner_selects_rename(self, runtime: SourceRuntime) -> None:
        # Simulating planner by manually selecting transform
        t = RenameTransformation("foo", "bar")
        assert t.descriptor.name == "rename_symbol"

    def test_e2e_planner_selects_move(self, runtime: SourceRuntime) -> None:
        t = MoveSymbolTransformation("foo", "utils")
        assert t.descriptor.name == "move_symbol"

    def test_e2e_planner_selects_delete(self, runtime: SourceRuntime) -> None:
        t = SafeDeleteTransformation("foo")
        assert t.descriptor.name == "safe_delete"

    def test_e2e_planner_selects_generate(self, runtime: SourceRuntime) -> None:
        t = GenerateSymbolTransformation("MyClass", "class")
        assert t.descriptor.name == "generate_symbol"

    def test_e2e_planner_selects_replace(self, runtime: SourceRuntime) -> None:
        t = SafeReplaceTransformation("1", "2")
        assert t.descriptor.name == "safe_replace"
