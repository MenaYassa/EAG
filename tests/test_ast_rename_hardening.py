"""Compiler conformance tests for the AST Rename Engine (Sprint 6.5C Hardening)."""

from pathlib import Path

import pytest

from eag.source.python import RenameTransformation, TransformationContext
from eag.source.runtime import SourceRuntime


@pytest.fixture
def runtime() -> SourceRuntime:
    return SourceRuntime()


def make_context(runtime: SourceRuntime, code: str, path: str = "test.py") -> TransformationContext:
    doc = runtime.parse(Path(path), code)
    return TransformationContext(document=doc, content=code)


class TestInheritance:
    def test_super_call_renamed(self, runtime: SourceRuntime) -> None:
        code = (
            "class Base:\n    def process(self):\n        pass\n\n"
            "class Child(Base):\n    def run(self):\n        super().process()\n"
        )
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.Base.process", "execute")
        result = transform.apply(ctx)

        assert result.success is True
        assert "super().execute()" in result.edits[0].new_content

    def test_override_not_renamed(self, runtime: SourceRuntime) -> None:
        code = (
            "class Base:\n    def process(self):\n        pass\n\n"
            "class Child(Base):\n    def process(self):\n        pass\n"
        )
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.Base.process", "execute")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        # Base.process should be renamed
        assert "class Base:\n    def execute(self):" in content
        # Child.process should NOT be renamed
        assert "class Child(Base):\n    def process(self):" in content


class TestDecorators:
    def test_decorator_reference_renamed(self, runtime: SourceRuntime) -> None:
        code = "def cache_result(func):\n    return func\n\n@cache_result\ndef foo():\n    pass\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.cache_result", "cached")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def cached(func):" in content
        assert "@cached" in content


class TestRelativeImports:
    def test_relative_import_renamed(self, runtime: SourceRuntime) -> None:
        code = "from .utils import foo\n\nfoo()\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("utils.foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "from .utils import bar" in content
        assert "bar()" in content


class TestExceptionVariables:
    def test_exception_variable_renamed(self, runtime: SourceRuntime) -> None:
        code = "try:\n    pass\nexcept Exception as err:\n    print(err)\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.<local>.err", "error")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "except Exception as error:" in content
        assert "print(error)" in content


class TestComprehensionScope:
    def test_comprehension_variable_renamed(self, runtime: SourceRuntime) -> None:
        code = "items = [x for x in range(10)]\nprint(items)\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.<local>.x", "y")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "[y for y in range(10)]" in content


class TestLambdaScope:
    def test_lambda_argument_renamed(self, runtime: SourceRuntime) -> None:
        code = "f = lambda user: user.name\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.<lambda>.user", "u")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "lambda u: u.name" in content


class TestPatternMatching:
    def test_pattern_match_variable_renamed(self, runtime: SourceRuntime) -> None:
        code = "match value:\n    case User(name=x):\n        print(x)\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.<local>.x", "username")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "case User(name=username):" in content
        assert "print(username)" in content


class TestIdempotency:
    def test_rename_twice_yields_no_changes(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.foo", "bar")

        result1 = transform.apply(ctx)
        assert result1.success is True

        # Create new context from result1
        ctx2 = make_context(runtime, result1.edits[0].new_content)
        transform2 = RenameTransformation("module.foo", "bar")
        result2 = transform2.apply(ctx2)

        # Should succeed but make no changes
        assert result2.success is True
        assert (
            "No changes needed" in result2.summary
            or result2.edits[0].new_content == result1.edits[0].new_content
        )


class TestUndoVerification:
    def test_undo_restores_byte_for_byte(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n\nfoo()\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.foo", "bar")

        result = transform.apply(ctx)
        assert result.success is True

        undo_ctx = TransformationContext(document=ctx.document, content=result.edits[0].new_content)
        undo_result = transform.undo(undo_ctx, result)

        assert undo_result.success is True
        assert undo_result.edits[0].new_content == code


class TestTransactionBehavior:
    def test_partial_failure_rollback(self, runtime: SourceRuntime) -> None:
        # Simulate a multi-file transformation where file 2 fails validation
        code_a = "def foo():\n    pass\n"
        code_b = "from module_a import foo\nfoo()\n"

        ctx_a = make_context(runtime, code_a, "module_a.py")
        ctx_b = make_context(runtime, code_b, "module_b.py")

        transform_a = RenameTransformation("module.foo", "bar")
        transform_b = RenameTransformation("nonexistent", "bar")  # Will fail

        res_a = transform_a.apply(ctx_a)
        res_b = transform_b.apply(ctx_b)

        # In a real Execution Runtime, if res_b fails, res_a's edits are discarded.
        # Here we just verify the results correctly report success/failure.
        assert res_a.success is True
        assert res_b.success is False
        assert "not found" in res_b.summary
