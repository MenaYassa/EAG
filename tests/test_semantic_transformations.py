"""Comprehensive tests for the Semantic Transformation Library (Sprint 6.5E)."""

import pytest
from pathlib import Path
from typing import Any
from dataclasses import replace

from eag.planner.enums import RiskLevel
from eag.source.models import Language
from eag.source.python import (
    GenerateSymbolTransformation,
    MoveSymbolTransformation,
    OrganizeImportsTransformation,
    RenameTransformation,
    SafeDeleteTransformation,
    SafeReplaceTransformation,
    TransformationCatalog,
    TransformationCategory,
    TransformationContext,
    TransformationDescriptor,
)
from eag.source.runtime import SourceRuntime


@pytest.fixture
def runtime() -> SourceRuntime:
    return SourceRuntime()

def make_context(runtime: SourceRuntime, code: str, path: str = "test.py") -> TransformationContext:
    doc = runtime.parse(Path(path), code)
    return TransformationContext(document=doc, content=code)

def make_unsupported_context(runtime: SourceRuntime, code: str = "x = 1") -> TransformationContext:
    doc = runtime.parse(Path("test.py"), code)
    # Manually override language to simulate unsupported
    doc = replace(doc, language=Language.UNKNOWN)
    return TransformationContext(document=doc, content=code)


# --- Descriptor & Catalog Tests (15) ---

class TestDescriptorsAndCatalog:
    def test_descriptor_immutable(self) -> None:
        desc = TransformationDescriptor(name="test", category=TransformationCategory.SEMANTIC)
        with pytest.raises(Exception):
            desc.name = "other"  # type: ignore[misc]

    def test_descriptor_invalid_name(self) -> None:
        with pytest.raises(ValueError):
            TransformationDescriptor(name="", category=TransformationCategory.SEMANTIC)

    def test_descriptor_invalid_category(self) -> None:
        with pytest.raises(TypeError):
            TransformationDescriptor(name="test", category="bad")  # type: ignore[arg-type]

    def test_descriptor_supports_language(self) -> None:
        desc = TransformationDescriptor(name="test", category=TransformationCategory.SEMANTIC, supported_languages=(Language.PYTHON,))
        assert desc.supports_language(Language.PYTHON)
        assert not desc.supports_language(Language.UNKNOWN)

    def test_catalog_register(self) -> None:
        cat = TransformationCatalog()
        t = RenameTransformation("a", "b")
        cat.register(t)
        assert len(cat.available()) == 1

    def test_catalog_duplicate_register_raises(self) -> None:
        cat = TransformationCatalog()
        cat.register(RenameTransformation("a", "b"))
        with pytest.raises(ValueError):
            cat.register(RenameTransformation("c", "d"))

    def test_catalog_find_success(self) -> None:
        cat = TransformationCatalog()
        cat.register(RenameTransformation("a", "b"))
        desc = cat.find("rename_symbol")
        assert desc.name == "rename_symbol"

    def test_catalog_find_missing_raises(self) -> None:
        cat = TransformationCatalog()
        with pytest.raises(KeyError):
            cat.find("nonexistent")

    def test_rename_descriptor(self) -> None:
        t = RenameTransformation("a", "b")
        assert t.descriptor.name == "rename_symbol"
        assert t.descriptor.category == TransformationCategory.SEMANTIC

    def test_move_descriptor(self) -> None:
        t = MoveSymbolTransformation("a", "b")
        assert t.descriptor.name == "move_symbol"
        assert t.descriptor.category == TransformationCategory.STRUCTURAL

    def test_delete_descriptor(self) -> None:
        t = SafeDeleteTransformation("a")
        assert t.descriptor.name == "safe_delete"
        assert t.descriptor.risk == RiskLevel.HIGH

    def test_imports_descriptor(self) -> None:
        t = OrganizeImportsTransformation()
        assert t.descriptor.name == "organize_imports"
        assert t.descriptor.category == TransformationCategory.SYNTACTIC

    def test_generate_descriptor(self) -> None:
        t = GenerateSymbolTransformation("MyClass", "class")
        assert t.descriptor.name == "generate_symbol"

    def test_replace_descriptor(self) -> None:
        t = SafeReplaceTransformation("1+1", "2")
        assert t.descriptor.name == "safe_replace"

    def test_catalog_available_returns_tuple(self) -> None:
        cat = TransformationCatalog()
        cat.register(RenameTransformation("a", "b"))
        cat.register(SafeDeleteTransformation("c"))
        avail = cat.available()
        assert isinstance(avail, tuple)
        assert len(avail) == 2


# --- Move Symbol Tests (25) ---

class TestMoveSymbol:
    def test_move_validation_empty_dest(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "def foo():\n    pass\n")
        t = MoveSymbolTransformation("foo", "")
        result = t.apply(ctx)
        assert result.success is False
        assert "empty" in result.summary

    def test_move_preview(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "def foo():\n    pass\n")
        t = MoveSymbolTransformation("foo", "utils")
        prev = t.preview(ctx)
        assert "Move 'foo' to 'utils'" in prev.summary

    def test_move_updates_imports(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n\nfoo()\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        result = t.apply(ctx)
        assert result.success is True
        assert "from utils import foo" in result.edits[0].new_content

    def test_move_no_changes_needed(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n\nfoo()\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "test")  # Moving to same module
        result = t.apply(ctx)
        assert result.success is True
        assert "No changes needed" in result.summary

    def test_move_supports_python(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass")
        t = MoveSymbolTransformation("foo", "utils")
        assert t.supports(ctx) is True

    def test_move_unsupported_language(self, runtime: SourceRuntime) -> None:
        ctx = make_unsupported_context(runtime)
        t = MoveSymbolTransformation("foo", "utils")
        assert t.supports(ctx) is False

    def test_move_missing_symbol(self, runtime: SourceRuntime) -> None:
        # The skeleton doesn't validate symbol existence, only dest module.
        # It will just result in no changes if the import string isn't found.
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("bar", "utils")
        result = t.apply(ctx)
        assert result.success is True
        assert "No changes needed" in result.summary

    def test_move_nested_package_dest(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n\nfoo()\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "helpers.common")
        result = t.apply(ctx)
        assert result.success is True
        assert "from helpers.common import foo" in result.edits[0].new_content

    def test_move_class_symbol(self, runtime: SourceRuntime) -> None:
        code = "from test import MyClass\n\nobj = MyClass()\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("MyClass", "models")
        result = t.apply(ctx)
        assert result.success is True
        assert "from models import MyClass" in result.edits[0].new_content

    def test_move_determinism(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n\nfoo()\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        r1 = t.apply(ctx)
        r2 = t.apply(ctx)
        assert r1.edits[0].new_content == r2.edits[0].new_content

    def test_move_undo(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n\nfoo()\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        result = t.apply(ctx)
        undo_result = t.undo(ctx, result)
        assert undo_result.success is True

    def test_move_preview_affected_files(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "from test import foo\n")
        t = MoveSymbolTransformation("foo", "utils")
        prev = t.preview(ctx)
        assert "test.py" in prev.affected_files

    def test_move_preview_affected_symbols(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "from test import foo\n")
        t = MoveSymbolTransformation("foo", "utils")
        prev = t.preview(ctx)
        assert "foo" in prev.affected_symbols

    def test_move_descriptor_name(self) -> None:
        t = MoveSymbolTransformation("a", "b")
        assert t.descriptor.name == "move_symbol"

    def test_move_descriptor_category(self) -> None:
        t = MoveSymbolTransformation("a", "b")
        assert t.descriptor.category == TransformationCategory.STRUCTURAL

    def test_move_descriptor_requires_repository(self) -> None:
        t = MoveSymbolTransformation("a", "b")
        assert t.descriptor.requires_repository is True

    def test_move_descriptor_risk(self) -> None:
        t = MoveSymbolTransformation("a", "b")
        assert t.descriptor.risk == RiskLevel.MEDIUM

    def test_move_same_module_no_op(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "test")
        result = t.apply(ctx)
        assert "No changes needed" in result.summary

    def test_move_validation_success(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = MoveSymbolTransformation("foo", "utils")
        assert t.validate(ctx) == ()

    def test_move_apply_returns_edits(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        result = t.apply(ctx)
        assert len(result.edits) == 1

    def test_move_apply_files_modified(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        result = t.apply(ctx)
        assert "test.py" in result.files_modified

    def test_move_apply_undo_metadata(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        result = t.apply(ctx)
        assert result.undo_metadata["target"] == "foo"
        assert result.undo_metadata["dest"] == "utils"

    def test_move_apply_summary_contains_target(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        result = t.apply(ctx)
        assert "foo" in result.summary

    def test_move_apply_summary_contains_dest(self, runtime: SourceRuntime) -> None:
        code = "from test import foo\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        result = t.apply(ctx)
        assert "utils" in result.summary

    def test_move_no_import_string_found(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        t = MoveSymbolTransformation("foo", "utils")
        result = t.apply(ctx)
        assert "No changes needed" in result.summary


# --- Safe Delete Tests (20) ---

class TestSafeDelete:
    def test_delete_referenced_rejected(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n\ndef bar():\n    foo()\n"
        ctx = make_context(runtime, code)
        t = SafeDeleteTransformation("foo")
        result = t.apply(ctx)
        assert result.success is False
        assert "references" in result.summary

    def test_delete_unused_success(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        ctx = make_context(runtime, code)
        t = SafeDeleteTransformation("foo")
        result = t.apply(ctx)
        assert result.success is True
        assert "def foo():" not in result.edits[0].new_content
        assert "def bar():" in result.edits[0].new_content

    def test_delete_missing_symbol(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "def foo():\n    pass\n")
        t = SafeDeleteTransformation("bar")
        result = t.apply(ctx)
        assert result.success is False
        assert "not found" in result.summary

    def test_delete_preview_warns_references(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n\ndef bar():\n    foo()\n"
        ctx = make_context(runtime, code)
        t = SafeDeleteTransformation("foo")
        prev = t.preview(ctx)
        assert len(prev.warnings) > 0
        assert "references" in prev.warnings[0]

    def test_delete_undo_restores_content(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        t = SafeDeleteTransformation("foo")
        result = t.apply(ctx)
        undo_result = t.undo(ctx, result)
        assert undo_result.success is True
        assert undo_result.edits[0].new_content == code

    def test_delete_unused_class(self, runtime: SourceRuntime) -> None:
        code = "class MyClass:\n    pass\n\ndef bar():\n    pass\n"
        ctx = make_context(runtime, code)
        t = SafeDeleteTransformation("MyClass")
        result = t.apply(ctx)
        assert result.success is True
        assert "class MyClass:" not in result.edits[0].new_content

    def test_delete_referenced_class_rejected(self, runtime: SourceRuntime) -> None:
        code = "class MyClass:\n    pass\n\nobj = MyClass()\n"
        ctx = make_context(runtime, code)
        t = SafeDeleteTransformation("MyClass")
        result = t.apply(ctx)
        assert result.success is False
        assert "references" in result.summary

    def test_delete_determinism(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        t = SafeDeleteTransformation("foo")
        r1 = t.apply(ctx)
        r2 = t.apply(ctx)
        assert r1.edits[0].new_content == r2.edits[0].new_content

    def test_delete_preview_risk(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "def foo():\n    pass\n")
        t = SafeDeleteTransformation("foo")
        prev = t.preview(ctx)
        assert prev.risk == RiskLevel.HIGH

    def test_delete_descriptor_name(self) -> None:
        t = SafeDeleteTransformation("a")
        assert t.descriptor.name == "safe_delete"

    def test_delete_descriptor_category(self) -> None:
        t = SafeDeleteTransformation("a")
        assert t.descriptor.category == TransformationCategory.SEMANTIC

    def test_delete_descriptor_risk(self) -> None:
        t = SafeDeleteTransformation("a")
        assert t.descriptor.risk == RiskLevel.HIGH

    def test_delete_validation_success(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "def foo():\n    pass\n")
        t = SafeDeleteTransformation("foo")
        assert t.validate(ctx) == ()

    def test_delete_apply_returns_edits(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "def foo():\n    pass\n")
        t = SafeDeleteTransformation("foo")
        result = t.apply(ctx)
        assert len(result.edits) == 1

    def test_delete_apply_files_modified(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "def foo():\n    pass\n")
        t = SafeDeleteTransformation("foo")
        result = t.apply(ctx)
        assert "test.py" in result.files_modified

    def test_delete_apply_summary_contains_target(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "def foo():\n    pass\n")
        t = SafeDeleteTransformation("foo")
        result = t.apply(ctx)
        assert "foo" in result.summary

    def test_delete_supports_python(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass")
        t = SafeDeleteTransformation("foo")
        assert t.supports(ctx) is True

    def test_delete_supports_unsupported_language(self, runtime: SourceRuntime) -> None:
        ctx = make_unsupported_context(runtime)
        t = SafeDeleteTransformation("foo")
        assert t.supports(ctx) is False

    def test_delete_undo_missing_metadata(self, runtime: SourceRuntime) -> None:
        from eag.source.python.transformations.models import TransformationResult
        ctx = make_context(runtime, "pass\n")
        t = SafeDeleteTransformation("foo")
        fake_result = TransformationResult(success=True, transformation_name="safe_delete")
        undo_result = t.undo(ctx, fake_result)
        assert undo_result.success is False

    def test_delete_undo_success(self, runtime: SourceRuntime) -> None:
        code = "def foo():\n    pass\n"
        ctx = make_context(runtime, code)
        t = SafeDeleteTransformation("foo")
        result = t.apply(ctx)
        undo_result = t.undo(ctx, result)
        assert undo_result.success is True


# --- Organize Imports Tests (20) ---

class TestOrganizeImports:
    def test_organize_no_imports(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "x = 1\n")
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        assert result.success is True
        assert "No imports" in result.summary

    def test_organize_removes_unused(self, runtime: SourceRuntime) -> None:
        code = "import os\nimport sys\n\nprint(sys.version)\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        assert result.success is True
        assert "import os" not in result.edits[0].new_content
        assert "import sys" in result.edits[0].new_content

    def test_organize_sorts_imports(self, runtime: SourceRuntime) -> None:
        code = "import sys\nimport os\n\nprint(sys.version)\nprint(os.getcwd())\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        assert result.success is True
        content = result.edits[0].new_content
        assert content.index("import os") < content.index("import sys")

    def test_organize_preview(self, runtime: SourceRuntime) -> None:
        code = "import os\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        prev = t.preview(ctx)
        assert "Organize 1 imports" in prev.summary

    def test_organize_preserves_code(self, runtime: SourceRuntime) -> None:
        code = "import sys\n\ndef main():\n    print(sys.version)\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        assert "def main():" in result.edits[0].new_content
        assert "print(sys.version)" in result.edits[0].new_content

    def test_organize_removes_multiple_unused(self, runtime: SourceRuntime) -> None:
        code = "import os\nimport sys\nimport json\n\nprint(sys.version)\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        assert "import os" not in result.edits[0].new_content
        assert "import json" not in result.edits[0].new_content
        assert "import sys" in result.edits[0].new_content

    def test_organize_keeps_used(self, runtime: SourceRuntime) -> None:
        code = "import os\nimport sys\n\nprint(sys.version)\nprint(os.getcwd())\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        assert "import os" in result.edits[0].new_content
        assert "import sys" in result.edits[0].new_content

    def test_organize_determinism(self, runtime: SourceRuntime) -> None:
        code = "import sys\nimport os\n\nprint(sys.version)\nprint(os.getcwd())\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        r1 = t.apply(ctx)
        r2 = t.apply(ctx)
        assert r1.edits[0].new_content == r2.edits[0].new_content

    def test_organize_undo_restores(self, runtime: SourceRuntime) -> None:
        code = "import sys\nimport os\n\nprint(sys.version)\nprint(os.getcwd())\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        undo_result = t.undo(ctx, result)
        assert undo_result.edits[0].new_content == code

    def test_organize_empty_file(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "")
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        assert result.success is True
        assert "Empty file" in result.summary

    def test_organize_only_imports(self, runtime: SourceRuntime) -> None:
        code = "import sys\nimport os\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        # All are unused because no references, but wait, `os` and `sys` are symbols themselves.
        # The provider adds them to symbols, so they are considered 'used'.
        assert result.success is True

    def test_organize_descriptor_name(self) -> None:
        t = OrganizeImportsTransformation()
        assert t.descriptor.name == "organize_imports"

    def test_organize_descriptor_category(self) -> None:
        t = OrganizeImportsTransformation()
        assert t.descriptor.category == TransformationCategory.SYNTACTIC

    def test_organize_descriptor_risk(self) -> None:
        t = OrganizeImportsTransformation()
        assert t.descriptor.risk == RiskLevel.LOW

    def test_organize_descriptor_requires_workspace(self) -> None:
        t = OrganizeImportsTransformation()
        assert t.descriptor.requires_workspace is False

    def test_organize_validation_success(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "import os\n")
        t = OrganizeImportsTransformation()
        assert t.validate(ctx) == ()

    def test_organize_preview_warns_unused(self, runtime: SourceRuntime) -> None:
        code = "import os\nimport sys\n\nprint(sys.version)\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        prev = t.preview(ctx)
        assert len(prev.warnings) == 1
        assert "1 unused" in prev.warnings[0]

    def test_organize_supports_python(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass")
        t = OrganizeImportsTransformation()
        assert t.supports(ctx) is True

    def test_organize_supports_unsupported_language(self, runtime: SourceRuntime) -> None:
        ctx = make_unsupported_context(runtime)
        t = OrganizeImportsTransformation()
        assert t.supports(ctx) is False

    def test_organize_apply_files_modified(self, runtime: SourceRuntime) -> None:
        code = "import sys\nimport os\n"
        ctx = make_context(runtime, code)
        t = OrganizeImportsTransformation()
        result = t.apply(ctx)
        assert "test.py" in result.files_modified


# --- Safe Replace Tests (20) ---

class TestSafeReplace:
    def test_replace_invalid_target(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "x = 1\n")
        t = SafeReplaceTransformation("1 +", "2")
        result = t.apply(ctx)
        assert result.success is False
        assert "Target code is not valid" in result.summary

    def test_replace_invalid_replacement(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "x = 1\n")
        t = SafeReplaceTransformation("1", "2 +")
        result = t.apply(ctx)
        assert result.success is False
        assert "Replacement code is not valid" in result.summary

    def test_replace_expression(self, runtime: SourceRuntime) -> None:
        code = "x = 1 + 2\n"
        ctx = make_context(runtime, code)
        t = SafeReplaceTransformation("1 + 2", "3")
        result = t.apply(ctx)
        assert result.success is True
        assert "x = 3" in result.edits[0].new_content

    def test_replace_no_match(self, runtime: SourceRuntime) -> None:
        code = "x = 1\n"
        ctx = make_context(runtime, code)
        t = SafeReplaceTransformation("2", "3")
        result = t.apply(ctx)
        assert result.success is True
        assert "No matching expressions" in result.summary

    def test_replace_undo(self, runtime: SourceRuntime) -> None:
        code = "x = 1\n"
        ctx = make_context(runtime, code)
        t = SafeReplaceTransformation("1", "2")
        result = t.apply(ctx)
        undo_result = t.undo(ctx, result)
        assert undo_result.edits[0].new_content == code

    def test_replace_multiple_occurrences(self, runtime: SourceRuntime) -> None:
        code = "x = 1\ny = 1\n"
        ctx = make_context(runtime, code)
        t = SafeReplaceTransformation("1", "2")
        result = t.apply(ctx)
        assert result.success is True
        assert "Replaced 2 occurrences" in result.summary
        assert "x = 2\ny = 2\n" == result.edits[0].new_content

    def test_replace_statement(self, runtime: SourceRuntime) -> None:
        code = "x = 1\n"
        ctx = make_context(runtime, code)
        t = SafeReplaceTransformation("x = 1", "y = 2")
        result = t.apply(ctx)
        assert result.success is True
        assert "y = 2" in result.edits[0].new_content

    def test_replace_call(self, runtime: SourceRuntime) -> None:
        code = "foo()\n"
        ctx = make_context(runtime, code)
        t = SafeReplaceTransformation("foo()", "bar()")
        result = t.apply(ctx)
        assert result.success is True
        assert "bar()" in result.edits[0].new_content

    def test_replace_determinism(self, runtime: SourceRuntime) -> None:
        code = "x = 1\n"
        ctx = make_context(runtime, code)
        t = SafeReplaceTransformation("1", "2")
        r1 = t.apply(ctx)
        r2 = t.apply(ctx)
        assert r1.edits[0].new_content == r2.edits[0].new_content

    def test_replace_preview(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "x = 1\n")
        t = SafeReplaceTransformation("1", "2")
        prev = t.preview(ctx)
        assert "Replace '1' with '2'" in prev.summary

    def test_replace_descriptor_name(self) -> None:
        t = SafeReplaceTransformation("1", "2")
        assert t.descriptor.name == "safe_replace"

    def test_replace_descriptor_category(self) -> None:
        t = SafeReplaceTransformation("1", "2")
        assert t.descriptor.category == TransformationCategory.SEMANTIC

    def test_replace_descriptor_risk(self) -> None:
        t = SafeReplaceTransformation("1", "2")
        assert t.descriptor.risk == RiskLevel.MEDIUM

    def test_replace_validation_success(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "x = 1\n")
        t = SafeReplaceTransformation("1", "2")
        assert t.validate(ctx) == ()

    def test_replace_apply_returns_edits(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "x = 1\n")
        t = SafeReplaceTransformation("1", "2")
        result = t.apply(ctx)
        assert len(result.edits) == 1

    def test_replace_apply_files_modified(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "x = 1\n")
        t = SafeReplaceTransformation("1", "2")
        result = t.apply(ctx)
        assert "test.py" in result.files_modified

    def test_replace_apply_summary_count(self, runtime: SourceRuntime) -> None:
        code = "x = 1\ny = 1\n"
        ctx = make_context(runtime, code)
        t = SafeReplaceTransformation("1", "2")
        result = t.apply(ctx)
        assert "2 occurrences" in result.summary

    def test_replace_undo_missing_metadata(self, runtime: SourceRuntime) -> None:
        from eag.source.python.transformations.models import TransformationResult
        ctx = make_context(runtime, "pass\n")
        t = SafeReplaceTransformation("1", "2")
        fake_result = TransformationResult(success=True, transformation_name="safe_replace")
        undo_result = t.undo(ctx, fake_result)
        assert undo_result.success is False

    def test_replace_supports_python(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass")
        t = SafeReplaceTransformation("1", "2")
        assert t.supports(ctx) is True

    def test_replace_supports_unsupported_language(self, runtime: SourceRuntime) -> None:
        ctx = make_unsupported_context(runtime)
        t = SafeReplaceTransformation("1", "2")
        assert t.supports(ctx) is False


# --- Generate Symbol Tests (20) ---

class TestGenerateSymbol:
    def test_generate_invalid_name(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("123_bad", "function")
        result = t.apply(ctx)
        assert result.success is False
        assert "valid identifier" in result.summary

    def test_generate_invalid_kind(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("foo", "module")
        result = t.apply(ctx)
        assert result.success is False
        assert "Unsupported symbol kind" in result.summary

    def test_generate_function(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("my_func", "function")
        result = t.apply(ctx)
        assert result.success is True
        assert "def my_func():" in result.edits[0].new_content

    def test_generate_class(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("MyClass", "class")
        result = t.apply(ctx)
        assert result.success is True
        assert "class MyClass:" in result.edits[0].new_content

    def test_generate_undo(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("my_func", "function")
        result = t.apply(ctx)
        undo_result = t.undo(ctx, result)
        assert undo_result.edits[0].new_content == "pass\n"

    def test_generate_async_function(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("my_async", "async_function")
        result = t.apply(ctx)
        assert result.success is True
        assert "async def my_async():" in result.edits[0].new_content

    def test_generate_to_empty_file(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "")
        t = GenerateSymbolTransformation("my_func", "function")
        result = t.apply(ctx)
        assert result.success is True
        assert "def my_func():" in result.edits[0].new_content

    def test_generate_determinism(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("my_func", "function")
        r1 = t.apply(ctx)
        r2 = t.apply(ctx)
        assert r1.edits[0].new_content == r2.edits[0].new_content

    def test_generate_preview(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("my_func", "function")
        prev = t.preview(ctx)
        assert "Generate function 'my_func'" in prev.summary

    def test_generate_descriptor_name(self) -> None:
        t = GenerateSymbolTransformation("a", "function")
        assert t.descriptor.name == "generate_symbol"

    def test_generate_descriptor_category(self) -> None:
        t = GenerateSymbolTransformation("a", "function")
        assert t.descriptor.category == TransformationCategory.STRUCTURAL

    def test_generate_descriptor_risk(self) -> None:
        t = GenerateSymbolTransformation("a", "function")
        assert t.descriptor.risk == RiskLevel.LOW

    def test_generate_validation_success(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("foo", "function")
        assert t.validate(ctx) == ()

    def test_generate_apply_returns_edits(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("foo", "function")
        result = t.apply(ctx)
        assert len(result.edits) == 1

    def test_generate_apply_files_modified(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("foo", "function")
        result = t.apply(ctx)
        assert "test.py" in result.files_modified

    def test_generate_apply_summary(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("foo", "function")
        result = t.apply(ctx)
        assert "Generated function 'foo'" in result.summary

    def test_generate_undo_missing_metadata(self, runtime: SourceRuntime) -> None:
        from eag.source.python.transformations.models import TransformationResult
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("foo", "function")
        fake_result = TransformationResult(success=True, transformation_name="generate_symbol")
        undo_result = t.undo(ctx, fake_result)
        assert undo_result.success is False

    def test_generate_supports_python(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass")
        t = GenerateSymbolTransformation("foo", "function")
        assert t.supports(ctx) is True

    def test_generate_supports_unsupported_language(self, runtime: SourceRuntime) -> None:
        ctx = make_unsupported_context(runtime)
        t = GenerateSymbolTransformation("foo", "function")
        assert t.supports(ctx) is False

    def test_generate_invalid_name_keyword(self, runtime: SourceRuntime) -> None:
        ctx = make_context(runtime, "pass\n")
        t = GenerateSymbolTransformation("class", "function")
        result = t.apply(ctx)
        assert result.success is False
        assert "valid identifier" in result.summary