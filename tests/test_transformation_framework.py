"""Comprehensive tests for the Source Transformation Framework (Sprint 6.5B)."""

from pathlib import Path

import pytest

from eag.planner.enums import RiskLevel
from eag.source.errors import SourceError
from eag.source.models import (
    EngineeringSymbol,
    Language,
    Location,
    SourceDocument,
    SymbolKind,
    SymbolReference,
)
from eag.source.python import (
    RenameTransformation,
    Transformation,
    TransformationContext,
    TransformationEngine,
    TransformationPreview,
    TransformationRegistry,
    TransformationResult,
    TransformationValidator,
)

# --- Fixtures ---


@pytest.fixture
def simple_document() -> SourceDocument:
    """A document with a single function and a reference to it."""
    func_sym = EngineeringSymbol(
        id="fn:foo:1",
        name="foo",
        qualified_name="foo",
        kind=SymbolKind.FUNCTION,
        location=Location(line=1),
        references=(SymbolReference(source="bar", target="foo", line=5),),
    )
    return SourceDocument(
        path=Path("test.py"), language=Language.PYTHON, checksum="abc123", symbols=(func_sym,)
    )


@pytest.fixture
def complex_document() -> SourceDocument:
    """A document with a class, method, and cross-references."""
    cls_sym = EngineeringSymbol(
        id="cls:User:1",
        name="User",
        qualified_name="User",
        kind=SymbolKind.CLASS,
        location=Location(line=1),
        references=(SymbolReference(source="module", target="User", line=10),),
    )
    method_sym = EngineeringSymbol(
        id="fn:login:2",
        name="login",
        qualified_name="User.login",
        kind=SymbolKind.METHOD,
        location=Location(line=2),
        parent="User",
        references=(SymbolReference(source="logout", target="login", line=8),),
    )
    return SourceDocument(
        path=Path("app.py"),
        language=Language.PYTHON,
        checksum="def456",
        symbols=(cls_sym, method_sym),
    )


@pytest.fixture
def empty_document() -> SourceDocument:
    return SourceDocument(path=Path("empty.py"), language=Language.PYTHON, checksum="000")


@pytest.fixture
def context(empty_document: SourceDocument) -> TransformationContext:
    return TransformationContext(document=empty_document, content="", dry_run=True)


@pytest.fixture
def validator() -> TransformationValidator:
    return TransformationValidator()


@pytest.fixture
def registry() -> TransformationRegistry:
    return TransformationRegistry()


@pytest.fixture
def engine(registry: TransformationRegistry) -> TransformationEngine:
    return TransformationEngine(registry=registry)


# --- Model Tests ---


class TestTransformationModels:
    def test_context_immutable(self, empty_document: SourceDocument) -> None:
        ctx = TransformationContext(document=empty_document, content="")
        with pytest.raises((TypeError, AttributeError, Exception)):
            ctx.dry_run = False  # type: ignore[misc]

    def test_result_immutable(self) -> None:
        res = TransformationResult(success=True, transformation_name="test")
        with pytest.raises(AttributeError):
            res.success = False  # type: ignore[misc]

    def test_preview_immutable(self) -> None:
        prev = TransformationPreview(transformation_name="test", risk=RiskLevel.LOW)
        with pytest.raises(AttributeError):
            prev.risk = RiskLevel.HIGH  # type: ignore[misc]


# --- Registry Tests ---


class TestTransformationRegistry:
    def test_register_and_list(self, registry: TransformationRegistry) -> None:
        t = RenameTransformation("a", "b")
        registry.register(t)
        assert len(registry.list()) == 1

    def test_duplicate_register_raises(self, registry: TransformationRegistry) -> None:
        registry.register(RenameTransformation("a", "b"))
        with pytest.raises(SourceError, match="already registered"):
            registry.register(RenameTransformation("c", "d"))

    def test_find_success(
        self, registry: TransformationRegistry, context: TransformationContext
    ) -> None:
        registry.register(RenameTransformation("a", "b"))
        found = registry.find("rename_symbol", context)
        assert isinstance(found, RenameTransformation)

    def test_find_missing_raises(
        self, registry: TransformationRegistry, context: TransformationContext
    ) -> None:
        with pytest.raises(SourceError, match="not found"):
            registry.find("nonexistent", context)


# --- Validator Tests ---


class TestTransformationValidator:
    def test_valid_identifier(self, validator: TransformationValidator) -> None:
        assert validator.validate_identifier("valid_name") == ()

    def test_invalid_identifier_number(self, validator: TransformationValidator) -> None:
        errors = validator.validate_identifier("123_invalid")
        assert len(errors) == 1
        assert "not a valid" in errors[0]

    def test_invalid_identifier_space(self, validator: TransformationValidator) -> None:
        errors = validator.validate_identifier("invalid name")
        assert len(errors) == 1

    def test_keyword_identifier(self, validator: TransformationValidator) -> None:
        errors = validator.validate_identifier("class")
        assert "reserved Python keyword" in errors[0]

    def test_symbol_exists_success(
        self, validator: TransformationValidator, simple_document: SourceDocument
    ) -> None:
        ctx = TransformationContext(document=simple_document, content="")
        assert validator.validate_symbol_exists(ctx, "foo") == ()

    def test_symbol_exists_qualified(
        self, validator: TransformationValidator, complex_document: SourceDocument
    ) -> None:
        ctx = TransformationContext(document=complex_document, content="")
        assert validator.validate_symbol_exists(ctx, "User.login") == ()

    def test_symbol_missing(
        self, validator: TransformationValidator, context: TransformationContext
    ) -> None:
        errors = validator.validate_symbol_exists(context, "missing_sym")
        assert "not found" in errors[0]

    def test_collision_detected(
        self, validator: TransformationValidator, complex_document: SourceDocument
    ) -> None:
        ctx = TransformationContext(document=complex_document, content="")
        errors = validator.validate_no_collision(ctx, "User")
        assert "already exists" in errors[0]

    def test_no_collision_success(
        self, validator: TransformationValidator, complex_document: SourceDocument
    ) -> None:
        ctx = TransformationContext(document=complex_document, content="")
        assert validator.validate_no_collision(ctx, "NewName") == ()


# --- Rename Transformation Tests ---


class TestRenameTransformation:
    def test_supports_python(self, context: TransformationContext) -> None:
        transform = RenameTransformation("old", "new")
        assert transform.supports(context) is True

    def test_supports_unsupported_language(self, empty_document: SourceDocument) -> None:
        from eag.source.models import Language

        empty_document = SourceDocument(
            path=Path("test.ts"), language=Language.UNKNOWN, checksum="123"
        )
        ctx = TransformationContext(document=empty_document, content="")
        transform = RenameTransformation("old", "new")
        assert transform.supports(ctx) is False

    def test_preview_missing_symbol(self, context: TransformationContext) -> None:
        transform = RenameTransformation("missing", "new")
        preview = transform.preview(context)
        assert "not found" in preview.warnings[0]
        assert preview.risk == RiskLevel.HIGH

    def test_preview_single_file(self, simple_document: SourceDocument) -> None:
        ctx = TransformationContext(document=simple_document, content="")
        transform = RenameTransformation("foo", "bar")
        preview = transform.preview(ctx)

        assert preview.affected_files == ("test.py",)
        assert preview.affected_symbols == ("foo",)
        assert len(preview.affected_references) == 1
        assert preview.risk == RiskLevel.LOW

    def test_preview_deterministic(self, simple_document: SourceDocument) -> None:
        ctx = TransformationContext(document=simple_document, content="")
        transform = RenameTransformation("foo", "bar")
        p1 = transform.preview(ctx)
        p2 = transform.preview(ctx)
        assert p1 == p2

    def test_validate_fails_on_invalid_name(self, context: TransformationContext) -> None:
        transform = RenameTransformation("old", "123_bad")
        errors = transform.validate(context)
        assert any("not a valid" in e for e in errors)

    def test_validate_fails_on_missing_symbol(self, context: TransformationContext) -> None:
        transform = RenameTransformation("missing", "new")
        errors = transform.validate(context)
        assert any("not found" in e for e in errors)

    def test_validate_fails_on_collision(self, complex_document: SourceDocument) -> None:
        ctx = TransformationContext(document=complex_document, content="")
        transform = RenameTransformation("User.login", "User")  # Collides with class
        errors = transform.validate(ctx)
        assert any("already exists" in e for e in errors)

    def test_validate_success(self, simple_document: SourceDocument) -> None:
        ctx = TransformationContext(document=simple_document, content="")
        transform = RenameTransformation("foo", "bar")
        assert transform.validate(ctx) == ()

    def test_apply_fails_on_validation_error(self, context: TransformationContext) -> None:
        transform = RenameTransformation("old", "123_bad")
        result = transform.apply(context)
        assert result.success is False
        assert "Validation failed" in result.summary

    def test_apply_simulated_success(self, simple_document: SourceDocument) -> None:
        ctx = TransformationContext(document=simple_document, content="")
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)

        assert result.success is True
        assert "test.py" in result.files_modified
        assert result.undo_metadata["old_name"] == "foo"
        assert result.undo_metadata["new_name"] == "bar"

    def test_undo_simulated_success(self, simple_document: SourceDocument) -> None:
        ctx = TransformationContext(document=simple_document, content="")
        transform = RenameTransformation("foo", "bar")
        result = transform.apply(ctx)
        undo_result = transform.undo(ctx, result)

        assert undo_result.success is True
        assert "Undo simulated" in undo_result.summary


# --- Engine Tests ---


class TestTransformationEngine:
    def test_execute_success(
        self,
        engine: TransformationEngine,
        registry: TransformationRegistry,
        simple_document: SourceDocument,
    ) -> None:
        ctx = TransformationContext(document=simple_document, content="")
        registry.register(RenameTransformation("foo", "bar"))

        result = engine.execute("rename_symbol", ctx)
        assert result.success is True

    def test_execute_validation_failure(
        self,
        engine: TransformationEngine,
        registry: TransformationRegistry,
        context: TransformationContext,
    ) -> None:
        registry.register(RenameTransformation("missing", "new"))
        result = engine.execute("rename_symbol", context)
        assert result.success is False

    def test_execute_missing_transformation(
        self, engine: TransformationEngine, context: TransformationContext
    ) -> None:
        with pytest.raises(SourceError):
            engine.execute("nonexistent", context)

    def test_execute_unsupported_language(
        self, engine: TransformationEngine, registry: TransformationRegistry
    ) -> None:
        from eag.source.models import Language

        doc = SourceDocument(path=Path("test.ts"), language=Language.UNKNOWN, checksum="123")
        ctx = TransformationContext(document=doc, content="")

        registry.register(RenameTransformation("old", "new"))
        result = engine.execute("rename_symbol", ctx)
        assert result.success is False
        assert "not supported" in result.summary


# --- Protocol Tests ---


class TestTransformationProtocol:
    def test_rename_implements_protocol(self) -> None:
        transform = RenameTransformation("a", "b")
        assert isinstance(transform, Transformation)

    def test_dummy_transformation_protocol(self) -> None:
        class DummyTransform:
            @property
            def name(self) -> str:
                return "dummy"

            def supports(self, ctx):
                return True

            def preview(self, ctx):
                return TransformationPreview(transformation_name="dummy")

            def validate(self, ctx):
                return ()

            def apply(self, ctx):
                return TransformationResult(success=True, transformation_name="dummy")

            def undo(self, ctx, res):
                return TransformationResult(success=True, transformation_name="undo_dummy")

        assert isinstance(DummyTransform(), Transformation)


class TestRichPreview:
    def test_transformation_preview_richness(self, simple_document) -> None:
        context = TransformationContext(document=simple_document, content="")

        transform = RenameTransformation("old_name", "new_name")
        preview = (
            transform.preview(context)
            if hasattr(transform, "preview")
            else transform.validate(context)
        )

        assert hasattr(preview, "can_apply")
        assert hasattr(preview, "risk_level") or hasattr(preview, "risk")
        assert preview.rollback_complexity in ("LOW", "MEDIUM", "HIGH")
