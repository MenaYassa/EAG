from pathlib import Path

from eag.source.analyzer import SourceAnalyzer
from eag.source.errors import AnalyzerNotFoundError, UnsupportedLanguageError


class SourceAnalyzerRegistry:
    def __init__(self) -> None:
        self._analyzers: dict[str, SourceAnalyzer] = {}

    def register(self, analyzer: SourceAnalyzer) -> None:
        if analyzer.language in self._analyzers:
            return
        self._analyzers[analyzer.language] = analyzer

    def unregister(self, language: str) -> None:
        self._analyzers.pop(language, None)

    def find_by_language(self, language: str) -> SourceAnalyzer:
        analyzer = self._analyzers.get(language)
        if not analyzer:
            raise UnsupportedLanguageError(f"Unsupported language: {language}")
        return analyzer

    def find_by_extension(self, extension: str) -> SourceAnalyzer:
        if not extension.startswith("."):
            extension = f".{extension}"
        ext = extension.lower()
        for analyzer in self._analyzers.values():
            if ext in analyzer.extensions:
                return analyzer
        raise AnalyzerNotFoundError(f"No analyzer found for extension: {extension}")

    def detect(self, path: Path) -> SourceAnalyzer:
        ext = path.suffix.lower()
        for analyzer in self._analyzers.values():
            if ext in analyzer.extensions:
                return analyzer
        raise AnalyzerNotFoundError(f"No analyzer found for {path}")

    def supported_languages(self) -> list[str]:
        return list(self._analyzers.keys())

    def supported_extensions(self) -> list[str]:
        exts: set[str] = set()
        for analyzer in self._analyzers.values():
            exts.update(analyzer.extensions)
        return sorted(exts)
