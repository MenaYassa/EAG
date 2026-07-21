"""Comprehensive tests for the Transformation Platform (Sprint 6.5D)."""

from pathlib import Path
from typing import Any

import pytest

from eag.source.python import (
    CompositeEdit,
    ConflictDetector,
    DiffEngine,
    EditEngine,
    EditTransaction,
    EditType,
    ImportEdit,
    SymbolEdit,
    TextEdit,
    TransactionError,
    TransformationBatch,
)
from eag.source.python.transformations.transaction import TransactionState


@pytest.fixture
def detector() -> ConflictDetector:
    return ConflictDetector()


@pytest.fixture
def engine() -> EditEngine:
    return EditEngine()


@pytest.fixture
def diff_engine() -> DiffEngine:
    return DiffEngine()


@pytest.fixture
def transaction() -> EditTransaction:
    return EditTransaction()


@pytest.fixture
def runtime() -> Any:
    from eag.source.runtime import SourceRuntime

    return SourceRuntime()


# --- Edit Model Tests (15) ---


class TestEditModels:
    def test_text_edit_immutable(self) -> None:
        edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        with pytest.raises(Exception):
            edit.new_text = "b"  # type: ignore[misc]

    def test_symbol_edit_immutable(self) -> None:
        edit = SymbolEdit(file=Path("test.py"), symbol_id="foo", old_name="foo", new_name="bar")
        with pytest.raises(Exception):
            edit.new_name = "baz"  # type: ignore[misc]

    def test_import_edit_immutable(self) -> None:
        edit = ImportEdit(file=Path("test.py"), module="utils", old_import="foo", new_import="bar")
        with pytest.raises(Exception):
            edit.module = "os"  # type: ignore[misc]

    def test_composite_edit_immutable(self) -> None:
        t_edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        comp = CompositeEdit(file=Path("test.py"), edits=(t_edit,))
        with pytest.raises(Exception):
            comp.edits = ()  # type: ignore[misc]

    def test_edit_invalid_file_type(self) -> None:
        with pytest.raises(TypeError):
            TextEdit(file="test.py", start_line=1, start_col=1, end_line=1, end_col=2, new_text="a")  # type: ignore[arg-type]

    def test_edit_invalid_metadata_type(self) -> None:
        with pytest.raises(TypeError):
            TextEdit(
                file=Path("test.py"),
                start_line=1,
                start_col=1,
                end_line=1,
                end_col=2,
                new_text="a",
                metadata="data",
            )  # type: ignore[arg-type]

    def test_edit_equality(self) -> None:
        e1 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        assert e1 == e2

    def test_edit_inequality(self) -> None:
        e1 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="b"
        )
        assert e1 != e2

    def test_text_edit_ordering(self) -> None:
        e1 = TextEdit(
            file=Path("test.py"), start_line=2, start_col=1, end_line=2, end_col=2, new_text="a"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="b"
        )
        assert e2 < e1

    def test_symbol_edit_creation(self) -> None:
        edit = SymbolEdit(file=Path("test.py"), symbol_id="foo", old_name="foo", new_name="bar")
        assert edit.edit_type == EditType.SYMBOL

    def test_import_edit_creation(self) -> None:
        edit = ImportEdit(file=Path("test.py"), module="utils", old_import="foo", new_import="bar")
        assert edit.edit_type == EditType.IMPORT

    def test_composite_edit_holds_edits(self) -> None:
        t_edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        comp = CompositeEdit(file=Path("test.py"), edits=(t_edit,))
        assert len(comp.edits) == 1

    def test_edit_has_unique_id(self) -> None:
        e1 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        assert e1.id != e2.id

    def test_edit_default_priority(self) -> None:
        e1 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        assert e1.priority == 100

    def test_edit_metadata_mapping(self) -> None:
        e1 = TextEdit(
            file=Path("test.py"),
            start_line=1,
            start_col=1,
            end_line=1,
            end_col=2,
            new_text="a",
            metadata={"key": "val"},
        )
        assert e1.metadata["key"] == "val"


# --- Edit Engine Tests (12) ---


class TestEditEngine:
    def test_apply_single_edit(self, engine: EditEngine) -> None:
        content = "def foo():\n    pass\n"
        edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=4, end_line=1, end_col=7, new_text="bar"
        )
        new_content = engine.apply(content, [edit])
        assert "def bar():" in new_content

    def test_apply_multiple_edits(self, engine: EditEngine) -> None:
        content = "def foo():\n    pass\n\nfoo()\n"
        e1 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=4, end_line=1, end_col=7, new_text="bar"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=4, start_col=0, end_line=4, end_col=3, new_text="bar"
        )
        new_content = engine.apply(content, [e1, e2])
        assert "def bar():" in new_content
        assert "bar()" in new_content

    def test_apply_multi_line_edit(self, engine: EditEngine) -> None:
        content = "def foo():\n    pass\n"
        edit = TextEdit(
            file=Path("test.py"),
            start_line=2,
            start_col=4,
            end_line=2,
            end_col=8,
            new_text="return 42",
        )
        new_content = engine.apply(content, [edit])
        assert "return 42" in new_content

    def test_apply_insertion_edit(self, engine: EditEngine) -> None:
        content = "def foo():\n    pass\n"
        # Insert at col 0 of line 2
        edit = TextEdit(
            file=Path("test.py"),
            start_line=2,
            start_col=0,
            end_line=2,
            end_col=0,
            new_text="    # Comment\n",
        )
        new_content = engine.apply(content, [edit])
        assert "# Comment" in new_content

    def test_apply_deletion_edit(self, engine: EditEngine) -> None:
        content = "def foo():\n    pass\n"
        # Delete the whole line (including newline)
        edit = TextEdit(
            file=Path("test.py"), start_line=2, start_col=0, end_line=2, end_col=9, new_text=""
        )
        new_content = engine.apply(content, [edit])
        assert new_content == "def foo():\n"

    def test_apply_empty_edits(self, engine: EditEngine) -> None:
        content = "def foo():\n    pass\n"
        new_content = engine.apply(content, [])
        assert new_content == content

    def test_apply_edits_reverse_order_safety(self, engine: EditEngine) -> None:
        content = "abc"
        e1 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=0, end_line=1, end_col=1, new_text="X"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="Y"
        )
        new_content = engine.apply(content, [e1, e2])
        assert new_content == "XYc"

    def test_apply_full_file_replacement(self, engine: EditEngine) -> None:
        content = "old content"
        edit = TextEdit(
            file=Path("test.py"),
            start_line=1,
            start_col=0,
            end_line=1,
            end_col=11,
            new_text="new content",
        )
        new_content = engine.apply(content, [edit])
        assert new_content == "new content"

    def test_apply_preserves_unmodified_lines(self, engine: EditEngine) -> None:
        content = "line1\nline2\nline3\n"
        edit = TextEdit(
            file=Path("test.py"), start_line=2, start_col=0, end_line=2, end_col=5, new_text="LINE2"
        )
        new_content = engine.apply(content, [edit])
        assert new_content == "line1\nLINE2\nline3\n"

    def test_apply_overlapping_safe(self, engine: EditEngine) -> None:
        content = "abc"
        e1 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=0, end_line=1, end_col=1, new_text="X"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="Y"
        )
        # The engine applies them in reverse, so the first edit doesn't affect the col of the second
        new_content = engine.apply(content, [e1, e2])
        assert new_content == "XYc"

    def test_apply_multi_file_isolation(self, engine: EditEngine) -> None:
        # The engine only applies to the content string provided; file path is metadata
        content = "test"
        edit = TextEdit(
            file=Path("other.py"),
            start_line=1,
            start_col=0,
            end_line=1,
            end_col=4,
            new_text="other",
        )
        new_content = engine.apply(content, [edit])
        assert new_content == "other"

    def test_apply_unicode_content(self, engine: EditEngine) -> None:
        content = "def café():\n    pass\n"
        edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=4, end_line=1, end_col=8, new_text="tea"
        )
        new_content = engine.apply(content, [edit])
        assert "def tea():" in new_content


# --- Conflict Detection Tests (10) ---


class TestConflictDetection:
    def test_no_conflict_different_files(self, detector: ConflictDetector) -> None:
        e1 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=5, new_text="a"
        )
        e2 = TextEdit(
            file=Path("b.py"), start_line=1, start_col=1, end_line=1, end_col=5, new_text="b"
        )
        assert detector.check([e1, e2]) == []

    def test_no_conflict_same_file_different_lines(self, detector: ConflictDetector) -> None:
        e1 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        e2 = TextEdit(
            file=Path("a.py"), start_line=2, start_col=1, end_line=2, end_col=2, new_text="b"
        )
        assert detector.check([e1, e2]) == []

    def test_overlap_conflict_exact_same_range(self, detector: ConflictDetector) -> None:
        e1 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=5, new_text="a"
        )
        e2 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=5, new_text="b"
        )
        conflicts = detector.check([e1, e2])
        assert len(conflicts) == 1
        assert "Overlap" in conflicts[0]

    def test_overlap_conflict_partial(self, detector: ConflictDetector) -> None:
        e1 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=5, new_text="a"
        )
        e2 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=3, end_line=1, end_col=4, new_text="b"
        )
        conflicts = detector.check([e1, e2])
        assert len(conflicts) == 1
        assert "Overlap" in conflicts[0]

    def test_symbol_conflict_different_names(self, detector: ConflictDetector) -> None:
        e1 = SymbolEdit(file=Path("a.py"), symbol_id="foo", old_name="foo", new_name="bar")
        e2 = SymbolEdit(file=Path("a.py"), symbol_id="foo", old_name="foo", new_name="baz")
        conflicts = detector.check([e1, e2])
        assert len(conflicts) == 1
        assert "Symbol conflict" in conflicts[0]

    def test_no_symbol_conflict_same_name(self, detector: ConflictDetector) -> None:
        e1 = SymbolEdit(file=Path("a.py"), symbol_id="foo", old_name="foo", new_name="bar")
        e2 = SymbolEdit(file=Path("a.py"), symbol_id="foo", old_name="foo", new_name="bar")
        assert detector.check([e1, e2]) == []

    def test_import_conflict_different_targets(self, detector: ConflictDetector) -> None:
        e1 = ImportEdit(file=Path("a.py"), module="utils", old_import="foo", new_import="bar")
        e2 = ImportEdit(file=Path("a.py"), module="utils", old_import="foo", new_import="baz")
        conflicts = detector.check([e1, e2])
        assert len(conflicts) == 1
        assert "Import conflict" in conflicts[0]

    def test_composite_conflict_detected(self, detector: ConflictDetector) -> None:
        e1 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=5, new_text="a"
        )
        e2 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=2, end_line=1, end_col=3, new_text="b"
        )
        comp = CompositeEdit(file=Path("a.py"), edits=(e1,))
        conflicts = detector.check([comp, e2])
        assert len(conflicts) == 1

    def test_boundary_adjacent_no_conflict(self, detector: ConflictDetector) -> None:
        # Edit 1 ends at col 5, Edit 2 starts at col 5. Should not conflict.
        e1 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=5, new_text="a"
        )
        e2 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=5, end_line=1, end_col=6, new_text="b"
        )
        assert detector.check([e1, e2]) == []

    def test_multiple_conflicts_returned(self, detector: ConflictDetector) -> None:
        e1 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=5, new_text="a"
        )
        e2 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=2, end_line=1, end_col=3, new_text="b"
        )
        e3 = SymbolEdit(file=Path("a.py"), symbol_id="foo", old_name="foo", new_name="bar")
        e4 = SymbolEdit(file=Path("a.py"), symbol_id="foo", old_name="foo", new_name="baz")
        conflicts = detector.check([e1, e2, e3, e4])
        assert len(conflicts) == 2


# --- Batch Operations Tests (10) ---


class TestBatchOperations:
    def test_empty_batch(self, runtime: Any) -> None:
        from eag.source.python import TransformationContext

        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")

        batch = TransformationBatch([])
        results = batch.execute(ctx)
        assert len(results) == 0

    def test_single_transformation_success(self, runtime: Any) -> None:
        from eag.source.python import RenameTransformation, TransformationContext

        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")

        batch = TransformationBatch([RenameTransformation("foo", "bar")])
        results = batch.execute(ctx)
        assert len(results) == 1
        assert results[0].success is True

    def test_multiple_transformations_success(self, runtime: Any) -> None:
        from eag.source.python import RenameTransformation, TransformationContext

        code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        doc = runtime.parse(Path("test.py"), code)
        ctx = TransformationContext(document=doc, content=code)

        batch = TransformationBatch(
            [RenameTransformation("foo", "func1"), RenameTransformation("bar", "func2")]
        )
        results = batch.execute(ctx)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_deterministic_ordering(self, runtime: Any) -> None:
        from eag.source.python import RenameTransformation, TransformationContext

        code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        doc = runtime.parse(Path("test.py"), code)
        ctx = TransformationContext(document=doc, content=code)

        t1 = RenameTransformation("foo", "func1")
        t2 = RenameTransformation("bar", "func2")
        batch = TransformationBatch([t1, t2])
        results = batch.execute(ctx)

        # The first result should be for 'foo'
        assert "func1" in results[0].summary

    def test_stops_on_failure(self, runtime: Any) -> None:
        from eag.source.python import RenameTransformation, TransformationContext

        code = "def foo():\n    pass\n"
        doc = runtime.parse(Path("test.py"), code)
        ctx = TransformationContext(document=doc, content=code)

        batch = TransformationBatch(
            [RenameTransformation("foo", "bar"), RenameTransformation("nonexistent", "error")]
        )
        results = batch.execute(ctx)
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False

    def test_unsupported_skipped(self, runtime: Any) -> None:
        from eag.source.python import TransformationContext, TransformationResult

        class UnsupportedTransform:
            @property
            def name(self) -> str:
                return "unsupported"

            def supports(self, ctx) -> bool:
                return False

            def preview(self, ctx) -> Any:
                pass

            def validate(self, ctx) -> tuple:
                return ()

            def apply(self, ctx) -> TransformationResult:
                pass

            def undo(self, ctx, res) -> TransformationResult:
                pass

        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")

        batch = TransformationBatch([UnsupportedTransform()])
        results = batch.execute(ctx)
        assert len(results) == 0  # Skipped, not failed

    def test_partial_failure_context_preserved(self, runtime: Any) -> None:
        from eag.source.python import RenameTransformation, TransformationContext

        code = "def foo():\n    pass\n"
        doc = runtime.parse(Path("test.py"), code)
        ctx = TransformationContext(document=doc, content=code)

        batch = TransformationBatch(
            [
                RenameTransformation("foo", "bar"),
                RenameTransformation(
                    "bar", "baz"
                ),  # Will fail because 'bar' wasn't committed to ctx
            ]
        )
        results = batch.execute(ctx)
        assert results[1].success is False

    def test_batch_results_length_matches_executed(self, runtime: Any) -> None:
        from eag.source.python import RenameTransformation, TransformationContext

        code = "def foo():\n    pass\n"
        doc = runtime.parse(Path("test.py"), code)
        ctx = TransformationContext(document=doc, content=code)

        batch = TransformationBatch(
            [RenameTransformation("foo", "bar"), RenameTransformation("missing", "err")]
        )
        results = batch.execute(ctx)
        assert len(results) == 2

    def test_batch_all_unsupported(self, runtime: Any) -> None:
        from eag.source.python import TransformationContext, TransformationResult

        class UnsupportedTransform:
            @property
            def name(self) -> str:
                return "unsupported"

            def supports(self, ctx) -> bool:
                return False

            def preview(self, ctx) -> Any:
                pass

            def validate(self, ctx) -> tuple:
                return ()

            def apply(self, ctx) -> TransformationResult:
                pass

            def undo(self, ctx, res) -> TransformationResult:
                pass

        doc = runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        ctx = TransformationContext(document=doc, content="def foo():\n    pass\n")

        batch = TransformationBatch([UnsupportedTransform(), UnsupportedTransform()])
        results = batch.execute(ctx)
        assert len(results) == 0

    def test_batch_executes_in_sequence(self, runtime: Any) -> None:
        from eag.source.python import RenameTransformation, TransformationContext

        code = "def foo():\n    pass\n"
        doc = runtime.parse(Path("test.py"), code)
        TransformationContext(document=doc, content=code)

        # Manually update context content AND document to simulate sequence
        code2 = "def bar():\n    pass\n"
        doc2 = runtime.parse(Path("test.py"), code2)
        ctx2 = TransformationContext(document=doc2, content=code2)

        batch = TransformationBatch([RenameTransformation("bar", "baz")])
        results = batch.execute(ctx2)
        assert results[0].success is True


# --- Preview/Diff Tests (10) ---


class TestPreviewDiff:
    def test_diff_single_file(self, diff_engine: DiffEngine) -> None:
        edits = [
            TextEdit(
                file=Path("test.py"),
                start_line=1,
                start_col=1,
                end_line=1,
                end_col=4,
                new_text="bar",
            )
        ]
        diff = diff_engine.create_diff("test.py", edits)
        assert diff.file == "test.py"
        assert len(diff.changes) == 1

    def test_diff_multiple_files(self, diff_engine: DiffEngine) -> None:
        e1 = TextEdit(
            file=Path("a.py"), start_line=1, start_col=1, end_line=1, end_col=4, new_text="bar"
        )
        e2 = TextEdit(
            file=Path("b.py"), start_line=1, start_col=1, end_line=1, end_col=4, new_text="baz"
        )
        diff1 = diff_engine.create_diff("a.py", [e1])
        diff2 = diff_engine.create_diff("b.py", [e2])
        assert diff1.file != diff2.file

    def test_diff_deterministic(self, diff_engine: DiffEngine) -> None:
        edits = [
            TextEdit(
                file=Path("test.py"),
                start_line=1,
                start_col=1,
                end_line=1,
                end_col=4,
                new_text="bar",
            )
        ]
        diff1 = diff_engine.create_diff("test.py", edits)
        diff2 = diff_engine.create_diff("test.py", edits)
        assert diff1 == diff2

    def test_diff_ordering(self, diff_engine: DiffEngine) -> None:
        e1 = TextEdit(
            file=Path("test.py"), start_line=2, start_col=1, end_line=2, end_col=4, new_text="bar"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=4, new_text="foo"
        )
        diff = diff_engine.create_diff("test.py", [e1, e2])
        # Diff engine just reports them in the order provided
        assert "2-2" in diff.changes[0]

    def test_diff_summary_stats(self, diff_engine: DiffEngine) -> None:
        edits = [
            TextEdit(
                file=Path("test.py"),
                start_line=1,
                start_col=1,
                end_line=1,
                end_col=4,
                new_text="bar",
            ),
            TextEdit(
                file=Path("test.py"),
                start_line=2,
                start_col=1,
                end_line=2,
                end_col=4,
                new_text="baz",
            ),
        ]
        diff = diff_engine.create_diff("test.py", edits)
        assert len(diff.changes) == 2

    def test_preview_contains_files(self) -> None:
        from eag.source.python import TransformationPreview

        prev = TransformationPreview(transformation_name="test", affected_files=("a.py", "b.py"))
        assert "a.py" in prev.affected_files

    def test_preview_contains_symbols(self) -> None:
        from eag.source.python import TransformationPreview

        prev = TransformationPreview(transformation_name="test", affected_symbols=("foo",))
        assert "foo" in prev.affected_symbols

    def test_preview_contains_imports(self) -> None:
        from eag.source.python import TransformationPreview

        prev = TransformationPreview(transformation_name="test", affected_imports=("os",))
        assert "os" in prev.affected_imports

    def test_preview_contains_warnings(self) -> None:
        from eag.source.python import TransformationPreview

        prev = TransformationPreview(transformation_name="test", warnings=("Low risk",))
        assert "Low risk" in prev.warnings

    def test_preview_contains_risk(self) -> None:
        from eag.planner.enums import RiskLevel
        from eag.source.python import TransformationPreview

        prev = TransformationPreview(transformation_name="test", risk=RiskLevel.HIGH)
        assert prev.risk == RiskLevel.HIGH


# --- Transaction Tests (12) ---


class TestEditTransactions:
    def test_transaction_initial_state(self, transaction: EditTransaction) -> None:
        assert transaction.state == TransactionState.READY

    def test_begin_sets_active(self, transaction: EditTransaction) -> None:
        transaction.begin()
        assert transaction.state == TransactionState.ACTIVE

    def test_commit_sets_committed(self, transaction: EditTransaction) -> None:
        transaction.begin()
        transaction.commit()
        assert transaction.state == TransactionState.COMMITTED

    def test_rollback_sets_rolled_back(self, transaction: EditTransaction) -> None:
        transaction.begin()
        transaction.rollback()
        assert transaction.state == TransactionState.ROLLED_BACK

    def test_add_edit_outside_active_raises(self, transaction: EditTransaction) -> None:
        edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        with pytest.raises(TransactionError):
            transaction.add_edit(edit)

    def test_double_begin_raises(self, transaction: EditTransaction) -> None:
        transaction.begin()
        with pytest.raises(TransactionError):
            transaction.begin()

    def test_commit_without_begin_raises(self, transaction: EditTransaction) -> None:
        with pytest.raises(TransactionError):
            transaction.commit()

    def test_rollback_without_begin_raises(self, transaction: EditTransaction) -> None:
        with pytest.raises(TransactionError):
            transaction.rollback()

    def test_commit_returns_edits(self, transaction: EditTransaction) -> None:
        transaction.begin()
        edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        transaction.add_edit(edit)
        edits = transaction.commit()
        assert len(edits) == 1

    def test_rollback_clears_edits(self, transaction: EditTransaction) -> None:
        transaction.begin()
        edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        transaction.add_edit(edit)
        transaction.rollback()
        # If we try to begin again and commit, it should be empty
        transaction.begin()
        edits = transaction.commit()
        assert len(edits) == 0

    def test_add_edit_to_committed_raises(self, transaction: EditTransaction) -> None:
        transaction.begin()
        transaction.commit()
        edit = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        with pytest.raises(TransactionError):
            transaction.add_edit(edit)

    def test_add_multiple_edits(self, transaction: EditTransaction) -> None:
        transaction.begin()
        e1 = TextEdit(
            file=Path("test.py"), start_line=1, start_col=1, end_line=1, end_col=2, new_text="a"
        )
        e2 = TextEdit(
            file=Path("test.py"), start_line=2, start_col=1, end_line=2, end_col=2, new_text="b"
        )
        transaction.add_edit(e1)
        transaction.add_edit(e2)
        edits = transaction.commit()
        assert len(edits) == 2
