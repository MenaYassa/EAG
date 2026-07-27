"""Source provider registry for EAG."""

from pathlib import Path

from eag.source.errors import AnalyzerNotFoundError, SourceError, UnsupportedLanguageError
from eag.source.protocol import SourceProvider


class SourceRegistry:
    """Discovers and manages available source providers."""

    def __init__(self) -> None:
        self._providers: dict[str, SourceProvider] = {}

    def register(self, provider: SourceProvider) -> None:
        """Registers a new source provider."""
        lang = (
            provider.language.value
            if hasattr(provider.language, "value")
            else str(provider.language)
        )

        # Older tests expect duplicate registrations to simply return silently
        if lang in self._providers:
            return

        self._providers[lang] = provider

    def unregister(self, language: str) -> None:
        lang_key = language.value if hasattr(language, "value") else str(language)
        self._providers.pop(lang_key, None)

    def find(self, path: Path) -> SourceProvider:
        """New API expects SourceError."""
        for provider in self._providers.values():
            if provider.supports(path):
                return provider
        raise SourceError(f"No source provider supports path: {path}")

    def detect(self, path: Path) -> SourceProvider:
        """Older API expects AnalyzerNotFoundError."""
        for provider in self._providers.values():
            if provider.supports(path):
                return provider
        raise AnalyzerNotFoundError(f"No analyzer found for {path}")

    def find_by_language(self, language: str) -> SourceProvider:
        lang_key = language.value if hasattr(language, "value") else str(language)
        provider = self._providers.get(lang_key)

        if not provider:
            # Restore specific error type
            raise UnsupportedLanguageError(f"Unsupported language: {lang_key}")
        return provider

    def find_by_extension(self, extension: str) -> SourceProvider:
        if not extension.startswith("."):
            extension = f".{extension}"
        ext = extension.lower()

        for provider in self._providers.values():
            if hasattr(provider, "extensions") and ext in provider.extensions:
                return provider

        # Restore specific error type
        raise AnalyzerNotFoundError(f"No analyzer found for extension: {extension}")

    def list(self) -> tuple[SourceProvider, ...]:
        return tuple(self._providers.values())

    def supported_languages(self) -> tuple[str, ...]:
        return tuple(self._providers.keys())

    def supported_extensions(self) -> tuple[str, ...]:
        exts: set[str] = set()
        for provider in self._providers.values():
            if hasattr(provider, "extensions"):
                exts.update(provider.extensions)
        return tuple(sorted(exts))


# Alias to support older tests and the CLI module
SourceAnalyzerRegistry = SourceRegistry
