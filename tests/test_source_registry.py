from pathlib import Path

import pytest

from eag.source.errors import AnalyzerNotFoundError, UnsupportedLanguageError
from eag.source.registry import SourceAnalyzerRegistry


class MockAnalyzer:
    language = "python"
    extensions = frozenset({".py", ".pyi"})

    def supports(self, path: Path) -> bool:
        return path.suffix in self.extensions

    def analyze(self, context):
        pass  # pragma: no cover


class TestSourceAnalyzerRegistry:
    def setup_method(self):
        self.registry = SourceAnalyzerRegistry()
        self.analyzer = MockAnalyzer()

    def test_register(self):
        self.registry.register(self.analyzer)
        assert "python" in self.registry.supported_languages()

    def test_duplicate_register_ignored(self):
        self.registry.register(self.analyzer)
        self.registry.register(self.analyzer)
        assert len(self.registry.supported_languages()) == 1

    def test_unregister(self):
        self.registry.register(self.analyzer)
        self.registry.unregister("python")
        assert "python" not in self.registry.supported_languages()

    def test_find_by_language(self):
        self.registry.register(self.analyzer)
        found = self.registry.find_by_language("python")
        assert found == self.analyzer

    def test_find_by_language_not_found(self):
        with pytest.raises(UnsupportedLanguageError):
            self.registry.find_by_language("rust")

    def test_find_by_extension(self):
        self.registry.register(self.analyzer)
        found = self.registry.find_by_extension(".py")
        assert found == self.analyzer

    def test_find_by_extension_no_dot(self):
        self.registry.register(self.analyzer)
        found = self.registry.find_by_extension("py")
        assert found == self.analyzer

    def test_find_by_extension_not_found(self):
        with pytest.raises(AnalyzerNotFoundError):
            self.registry.find_by_extension(".rs")

    def test_detect(self):
        self.registry.register(self.analyzer)
        found = self.registry.detect(Path("src/main.py"))
        assert found == self.analyzer

    def test_detect_not_found(self):
        with pytest.raises(AnalyzerNotFoundError):
            self.registry.detect(Path("src/main.rs"))

    def test_supported_extensions(self):
        self.registry.register(self.analyzer)
        exts = self.registry.supported_extensions()
        assert ".py" in exts
        assert ".pyi" in exts
