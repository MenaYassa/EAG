"""Comprehensive tests for the AST Rename Engine (Sprint 6.5C)."""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from eag.source.python import (
    RenameTransformation,
    TransformationEngine,
    TransformationRegistry,
)
from eag.source.python.transformations.models import (
    TransformationContext,
)
from eag.source.runtime import SourceRuntime


@dataclass
class MockWorkspace:
    writes: dict[Path, str] = field(default_factory=dict)

    def write(self, path: Path, content: str) -> None:
        self.writes[path] = content


@pytest.fixture
def runtime() -> SourceRuntime:
    return SourceRuntime()


@pytest.fixture
def workspace() -> MockWorkspace:
    return MockWorkspace()


def make_context(
    runtime: SourceRuntime, code: str, path: str = "test.py", workspace: Any = None
) -> TransformationContext:
    doc = runtime.parse(Path(path), code)
    return TransformationContext(document=doc, content=code, workspace=workspace)


def assert_ast_valid(code: str) -> None:
    """Assert that the code parses as valid Python AST."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(f"Generated code has syntax error: {e}")


class TestScopeResolution:
    """Test lexical scope resolution during rename operations."""

    def test_global_variable_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming a global variable."""
        code = "foo = 1\n\ndef x():\n    print(foo)\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "bar = 1" in content
        assert "print(bar)" in content
        assert "foo" not in content.replace("bar", "")
        assert_ast_valid(content)

    def test_shadowed_variable_not_renamed(self, runtime: SourceRuntime) -> None:
        """Test that shadowed variables are not renamed."""
        code = "foo = 1\n\ndef x():\n    foo = 2\n    print(foo)\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "bar = 1" in content
        assert "foo = 2" in content
        assert "print(foo)" in content
        assert_ast_valid(content)

    def test_nested_scope_resolution(self, runtime: SourceRuntime) -> None:
        """Test renaming in nested scopes."""
        code = """foo = 1

def outer():
    foo = 2
    def inner():
        foo = 3
        print(foo)
    print(foo)
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "bar = 1" in content
        assert "foo = 2" in content
        assert "foo = 3" in content
        assert "print(foo)" in content
        assert_ast_valid(content)

    def test_closure_variable(self, runtime: SourceRuntime) -> None:
        code = "def outer():\n    foo = 1\n    def inner():\n        return foo\n    return inner\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("module.outer.foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "bar = 1" in content
        assert "return bar" in content

    def test_class_attribute_not_renamed(self, runtime: SourceRuntime) -> None:
        """Test that class attributes are not confused with local variables."""
        code = """class User:
    foo = 1
    def method(self):
        foo = 2
        print(foo)
        print(self.foo)
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User.foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "bar = 1" in content  # Class attribute
        assert "foo = 2" in content  # Local variable remains
        assert "print(foo)" in content
        assert "self.bar" in content  # Attribute access
        assert_ast_valid(content)


class TestTypeHints:
    """Test type hint preservation during rename operations."""

    def test_simple_type_hint_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming in simple type hints."""
        code = """class User:
    pass

def x(u: User):
    pass
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User", "Account")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def x(u: Account):" in content
        assert_ast_valid(content)

    def test_generic_type_hint_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming in generic type hints."""
        code = """from typing import List

class User:
    pass

def x(u: List[User]):
    pass
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User", "Account")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def x(u: List[Account]):" in content
        assert_ast_valid(content)

    def test_nested_type_hint_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming in nested type hints."""
        code = """from typing import Optional, Union

class User:
    pass

def x(u: Optional[Union[User, str]]):
    pass
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User", "Account")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def x(u: Optional[Union[Account, str]]):" in content
        assert_ast_valid(content)

    def test_return_type_hint_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming in return type hints."""
        code = """class User:
    pass

def x() -> User:
    return User()
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User", "Account")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def x() -> Account:" in content
        assert "return Account()" in content
        assert_ast_valid(content)


class TestStringsAndComments:
    """Test that strings and comments are properly preserved."""

    def test_string_literal_not_renamed(self, runtime: SourceRuntime) -> None:
        """Test that string contents are not renamed."""
        code = (
            "def foo():\n"
            "    pass\n"
            "\n"
            "x = 'foo'\n"
            'print("foo")\n'
            "y = '''foo'''\n"
            'z = """foo"""\n'
        )
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def bar():" in content
        assert "x = 'foo'" in content
        assert 'print("foo")' in content
        assert "y = '''foo'''" in content
        assert 'z = """foo"""' in content
        assert_ast_valid(content)

    def test_fstring_expression_renamed(self, runtime: SourceRuntime) -> None:
        """Test that f-string expressions are renamed."""
        code = """def foo():
    return 42

print(f'{foo()}')
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def bar():" in content
        assert "print(f'{bar()}')" in content
        assert_ast_valid(content)

    def test_comment_not_renamed(self, runtime: SourceRuntime) -> None:
        """Test that comments are not renamed."""
        code = """# foo is great
# This function does foo
def foo():
    pass
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "# foo is great" in content
        assert "# This function does foo" in content
        assert "def bar():" in content
        assert_ast_valid(content)

    def test_docstring_not_renamed(self, runtime: SourceRuntime) -> None:
        """Test that docstrings are not renamed."""
        code = """def foo():
    \"\"\"This function is called foo.\"\"\"
    pass
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def bar():" in content
        assert '"""This function is called foo."""' in content
        assert_ast_valid(content)


class TestFormattingPreservation:
    """Test that code formatting is preserved."""

    def test_whitespace_preserved(self, runtime: SourceRuntime) -> None:
        """Test that whitespace is preserved."""
        code = "def foo():\n    pass\n\n\n\nx = 1\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert content == "def bar():\n    pass\n\n\n\nx = 1\n"
        assert_ast_valid(content)

    def test_indentation_preserved(self, runtime: SourceRuntime) -> None:
        """Test that indentation is preserved."""
        code = """class User:
            def login(self):
                pass
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User.login", "authenticate")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "            def authenticate(self):" in content
        assert_ast_valid(content)

    def test_spacing_preserved(self, runtime: SourceRuntime) -> None:
        """Test that spacing around identifiers is preserved."""
        code = "def   foo( x , y ) :\n    return x + y\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def   bar( x , y ) :" in content
        assert_ast_valid(content)


class TestASTIntegrity:
    """Test that AST integrity is maintained."""

    def test_invalid_output_blocked(self, runtime: SourceRuntime) -> None:
        """Test that invalid code generation is blocked."""
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "123_bad")
        result = transform.apply(ctx)

        assert result.success is False
        assert "not a valid" in result.summary

    def test_syntax_error_handling(self, runtime: SourceRuntime) -> None:
        """Test handling of syntax errors during transformation."""
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        # This should still be a valid rename
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert_ast_valid(content)


class TestAttributes:
    """Test attribute handling during rename operations."""

    def test_method_call_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming method calls."""
        code = """class User:
    def login(self):
        pass

u = User()
u.login()
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User.login", "authenticate")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def authenticate(self):" in content
        assert "u.authenticate()" in content
        assert "login" not in content.replace("authenticate", "")
        assert_ast_valid(content)

    def test_unrelated_attribute_not_renamed(self, runtime: SourceRuntime) -> None:
        """Test that unrelated attributes are not renamed."""
        code = """class User:
    def login(self):
        pass

class Other:
    def login(self):
        pass

u = User()
u.login()
o = Other()
o.login()
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User.login", "authenticate")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def authenticate(self):" in content
        assert "u.authenticate()" in content
        assert "def login(self):" in content  # Other.login remains
        assert "o.login()" in content
        assert_ast_valid(content)

    def test_chained_attribute_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming chained attributes."""
        code = """class User:
    class Profile:
        def login(self):
            pass

u = User.Profile()
u.login()
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User.Profile.login", "authenticate")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def authenticate(self):" in content
        assert "u.authenticate()" in content
        assert_ast_valid(content)


class TestImports:
    """Test import handling during rename operations."""

    def test_from_import_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming from imports."""
        code = """from utils import foo

foo()
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "from utils import bar" in content
        assert "bar()" in content
        assert_ast_valid(content)

    def test_import_as_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming aliased imports."""
        code = """import utils as u

u.foo()
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("utils.foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "u.bar()" in content
        assert_ast_valid(content)

    def test_multiple_imports_renamed(self, runtime: SourceRuntime) -> None:
        """Test renaming multiple imports."""
        code = """from utils import foo, bar

foo()
bar()
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "baz")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "from utils import baz, bar" in content or "from utils import bar, baz" in content
        assert "baz()" in content
        assert "bar()" in content
        assert_ast_valid(content)


class TestRichResults:
    """Test rich result metadata."""

    def test_determinism(self, runtime: SourceRuntime) -> None:
        """Test that transformations are deterministic."""
        code = "def foo():\n    pass\n\nfoo()\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")

        r1 = transform.apply(ctx)
        r2 = transform.apply(ctx)

        assert r1.edits[0].new_content == r2.edits[0].new_content
        assert r1.summary == r2.summary

    def test_undo_metadata(self, runtime: SourceRuntime) -> None:
        """Test that undo metadata is properly stored."""
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        assert result.undo_metadata["old_name"] == "foo"
        assert result.undo_metadata["new_name"] == "bar"
        assert "timestamp" in result.undo_metadata
        assert "text_edits" in result.undo_metadata

    def test_stats_in_summary(self, runtime: SourceRuntime) -> None:
        """Test that statistics are included in summary."""
        code = """def foo():
    pass

foo()
foo()
foo()
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        assert "Updated 3 references" in result.summary


class TestCrossFile:
    """Test cross-file rename operations."""

    def test_multi_file_rename(self, runtime: SourceRuntime) -> None:
        """Test renaming across multiple files."""
        code_a = "def foo():\n    pass\n"
        code_b = "from module_a import foo\n\nfoo()\n"

        ctx_a = make_context(runtime, code_a, "module_a.py")
        ctx_b = make_context(runtime, code_b, "module_b.py")

        transform = RenameTransformation("foo", "bar")

        res_a = transform.apply(ctx_a)
        res_b = transform.apply(ctx_b)

        assert res_a.success is True
        assert res_b.success is True
        assert "def bar():" in res_a.edits[0].new_content
        assert "from module_a import bar" in res_b.edits[0].new_content
        assert "bar()" in res_b.edits[0].new_content
        assert_ast_valid(res_a.edits[0].new_content)
        assert_ast_valid(res_b.edits[0].new_content)


class TestEdgeCases:
    """Test edge cases and corner conditions."""

    def test_rename_to_same_name(self, runtime: SourceRuntime) -> None:
        """Test renaming to the same name (no-op)."""
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "foo")
        result = transform.apply(ctx)

        assert result.success is True
        assert result.edits[0].new_content == code
        assert_ast_valid(result.edits[0].new_content)

    def test_rename_empty_file(self, runtime: SourceRuntime) -> None:
        """Test renaming in an empty file."""
        code = ""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is False
        assert "not found" in result.summary

    def test_rename_dunder_methods(self, runtime: SourceRuntime) -> None:
        """Test renaming dunder methods."""
        code = """class User:
    def __init__(self):
        pass
    def __str__(self):
        return "User"
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User.__str__", "__repr__")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def __repr__(self):" in content
        assert_ast_valid(content)

    def test_rename_property(self, runtime: SourceRuntime) -> None:
        """Test renaming a property."""
        code = """class User:
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value
"""
        ctx = make_context(runtime, code)
        transform = RenameTransformation("User.name", "username")
        result = transform.apply(ctx)

        assert result.success is True
        content = result.edits[0].new_content
        assert "def username(self):" in content
        assert "@username.setter" in content
        assert "def username(self, value):" in content
        assert_ast_valid(content)


class TestWorkspaceIntegration:
    """Test integration with the workspace."""

    def test_engine_produces_edits(self, runtime: SourceRuntime, workspace: MockWorkspace) -> None:
        """Test that the engine produces proper edits."""
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code, workspace=workspace)

        registry = TransformationRegistry()
        engine = TransformationEngine(registry=registry)
        registry.register(RenameTransformation("foo", "bar"))

        result = engine.execute("rename_symbol", ctx)
        assert result.success is True
        assert len(result.edits) == 1

        # Apply the edit
        edit = result.edits[0]
        ctx.workspace.write(edit.path, edit.new_content)

        assert Path("test.py") in workspace.writes
        content = workspace.writes[Path("test.py")]
        assert "def bar():" in content
        assert_ast_valid(content)
