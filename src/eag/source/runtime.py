"""Source runtime for EAG."""

import time
from pathlib import Path, PurePosixPath
from typing import Any

from eag.events import EventBus
from eag.source.analyzer import AnalysisContext
from eag.source.events import (
    SourceAnalysisCompleted,
    SourceAnalysisFailed,
    SourceAnalysisStarted,
    SourceParsed,
)
from eag.source.metrics import AnalysisMetrics
from eag.source.models import (
    AnalysisDiagnostic,
    AnalysisResult,
    Dependency,
    DependencyKind,
    Diagnostic,
    ModuleIdentity,
    SourceDocument,
    SourceFileIdentity,
    SourceHealth,
    SourceLocation,
    SourceMetrics,
    Symbol,
    SymbolIdentity,
)
from eag.source.python.provider import PythonSourceProvider
from eag.source.registry import SourceRegistry


class SourceRuntime:
    """The public API for the Source Intelligence Platform."""

    def __init__(
        self, registry: SourceRegistry | None = None, event_bus: EventBus | None = None
    ) -> None:
        self._registry = registry or SourceRegistry()
        self._event_bus = event_bus
        self._metrics = SourceMetrics()

        # Register built-in Python provider if the registry is empty
        if not self._registry.list():
            self._registry.register(PythonSourceProvider())

    def supported_languages(self) -> tuple[str, ...]:
        return self._registry.supported_languages()

    def parse(self, path: Path, content: str) -> SourceDocument:
        start_time = time.monotonic()
        provider = self._registry.find(path)
        doc = provider.parse(path, content)
        elapsed_ms = (time.monotonic() - start_time) * 1000

        self._metrics = SourceMetrics(
            files_parsed=self._metrics.files_parsed + 1,
            symbols_extracted=self._metrics.symbols_extracted + len(doc.symbols),
            imports_extracted=self._metrics.imports_extracted + len(doc.imports),
            parse_failures=self._metrics.parse_failures + (1 if doc.diagnostics else 0),
            parse_time_ms=self._metrics.parse_time_ms + elapsed_ms,
        )

        # Fire telemetry safely
        if self._event_bus:
            self._event_bus.publish(
                SourceParsed(  # type: ignore[arg-type]
                    path=str(path),
                    language=doc.language.value,
                    symbol_count=len(doc.symbols),
                    import_count=len(doc.imports),
                    success=not doc.diagnostics,
                )
            )

        return doc

    def validate(self, document: SourceDocument) -> tuple[Diagnostic, ...]:
        provider = self._registry.find(document.path)
        return provider.validate(document)

    def metrics(self) -> SourceMetrics:
        return self._metrics

    def health(self) -> SourceHealth:
        return SourceHealth(providers_loaded=len(self._registry.list()))

    def explain(self) -> str:
        m = self.metrics()
        h = self.health()
        return (
            f"Source Intelligence Platform\n"
            f"────────────────────────────────\n"
            f"Providers: {h.providers_loaded}\n"
            f"Files Parsed: {m.files_parsed}\n"
            f"Symbols Extracted: {m.symbols_extracted}\n"
            f"Imports Extracted: {m.imports_extracted}\n"
            f"Parse Failures: {m.parse_failures}\n"
            f"Total Parse Time: {m.parse_time_ms:.2f}ms\n"
        )

    def analyze_file(
        self,
        path: Path,
        repository_root: Path,
        settings: Any,
        cache: Any,
        content: str | None = None,
    ) -> AnalysisResult:
        if self._event_bus:
            self._event_bus.publish(SourceAnalysisStarted(path=path))  # type: ignore[arg-type]

        try:
            provider = self._registry.detect(path)
            context = AnalysisContext(
                path=path,
                repository_root=repository_root,
                settings=settings,
                cache=cache,
            )

            if hasattr(provider, "analyze"):
                result: AnalysisResult = provider.analyze(context)
            else:
                if content is None:
                    content = path.read_text(encoding="utf-8")
                # Route through the telemetry-enabled parse
                doc = self.parse(path, content)
                _diagnostics = self.validate(doc)

                # Project existing parser output into the established semantic result model.
                # This is a SourceRuntime adapter, not a second parser or indexer.
                absolute_path = path.resolve()
                relative_path = PurePosixPath(
                    absolute_path.relative_to(repository_root.resolve()).as_posix()
                )
                module_name = relative_path.with_suffix("").as_posix().replace("/", ".")
                symbols = tuple(
                    Symbol(
                        identity=SymbolIdentity(
                            qualified_name=symbol.qualified_name,
                            module=module_name,
                            kind=symbol.kind,
                        ),
                        location=SourceLocation(
                            path=relative_path,
                            line=max(symbol.location.line, 1),
                            column=max(symbol.location.column, 0),
                            end_line=max(symbol.location.end_line, symbol.location.line, 1),
                            end_column=max(symbol.location.end_column, 0),
                        ),
                        visibility=symbol.visibility,
                    )
                    for symbol in doc.symbols
                )
                dependencies = tuple(
                    Dependency(
                        source=module_name,
                        target=import_model.module,
                        kind=DependencyKind.IMPORT,
                        resolved=False,
                    )
                    for import_model in doc.imports
                    if import_model.module
                )
                diagnostics = tuple(
                    AnalysisDiagnostic(
                        severity=diagnostic.severity,
                        message=diagnostic.message,
                        location=SourceLocation(
                            path=relative_path,
                            line=max(diagnostic.location.line, 1),
                            column=max(diagnostic.location.column, 0),
                            end_line=max(
                                diagnostic.location.end_line,
                                diagnostic.location.line,
                                1,
                            ),
                            end_column=max(diagnostic.location.end_column, 0),
                        ),
                        rule=diagnostic.rule,
                        provider=diagnostic.provider,
                    )
                    for diagnostic in doc.diagnostics
                )
                result = AnalysisResult(
                    identity=SourceFileIdentity(
                        absolute_path=absolute_path,
                        repository_path=relative_path,
                        language=doc.language,
                        fingerprint=doc.checksum,
                    ),
                    module=ModuleIdentity(name=module_name, path=relative_path),
                    symbols=symbols,
                    dependencies=dependencies,
                    diagnostics=diagnostics,
                    metrics=AnalysisMetrics(
                        lines=len(content.splitlines()),
                        blank_lines=0,
                        comment_lines=0,
                        symbols=len(symbols),
                        dependencies=len(dependencies),
                    ),
                    semantic_relationships=(),
                )

            if self._event_bus:
                self._event_bus.publish(SourceAnalysisCompleted(path=path, result=result))  # type: ignore[arg-type]

            return result

        except Exception as e:
            if self._event_bus:
                self._event_bus.publish(SourceAnalysisFailed(path=path, error=str(e)))  # type: ignore[arg-type]
            raise

    def analyze(
        self,
        path: Path,
        repository_root: Path,
        settings: Any,
        cache: Any,
        content: str | None = None,
    ) -> AnalysisResult:
        return self.analyze_file(path, repository_root, settings, cache, content)
