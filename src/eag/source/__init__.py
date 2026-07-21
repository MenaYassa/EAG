"""Source Intelligence Platform for EAG."""

from eag.source.analyzer import AnalysisContext
from eag.source.errors import (
    AnalysisFailedError,
    AnalyzerNotFoundError,
    SourceError,
    SourceParseError,
    SourceValidationError,
    UnsupportedLanguageError,
)
from eag.source.events import (
    SourceAnalysisCompleted,
    SourceAnalysisFailed,
    SourceAnalysisStarted,
    SourceEvent,
    SourceParsed,
)

# Fix: Import AnalysisMetrics from metrics instead of models
from eag.source.metrics import AnalysisMetrics
from eag.source.models import (
    AnalysisDiagnostic,
    AnalysisResult,
    Dependency,
    DependencyKind,
    Diagnostic,
    DiagnosticSeverity,
    Documentation,
    EngineeringSymbol,
    ImportModel,
    Language,
    Location,
    ModuleIdentity,
    SemanticKind,
    SemanticRelationship,
    SourceDocument,
    SourceFileIdentity,
    SourceHealth,
    SourceLocation,
    SourceMetrics,
    Symbol,
    SymbolIdentity,
    SymbolKind,
    SymbolReference,
    SymbolVisibility,
    Visibility,
)
from eag.source.protocol import SourceProvider
from eag.source.python import (
    PythonSourceProvider,
    RenameTransformation,
    RenameVisitor,
    Transformation,
    TransformationEngine,
    TransformationRegistry,
    TransformationValidator,
    apply_text_edits,
)
from eag.source.python.transformations.models import (
    SourceEdit,
    TextEdit,
    TransformationContext,
    TransformationPreview,
    TransformationResult,
)
from eag.source.registry import SourceRegistry
from eag.source.runtime import SourceRuntime

__all__ = [
    # Enums
    "DependencyKind",
    "DiagnosticSeverity",
    "Language",
    "SemanticKind",
    "SymbolKind",
    "SymbolVisibility",
    "Visibility",
    # Errors
    "AnalysisFailedError",
    "AnalyzerNotFoundError",
    "SourceError",
    "SourceParseError",
    "SourceValidationError",
    "UnsupportedLanguageError",
    # Models (Primitives & Identity)
    "Documentation",
    "Location",
    "ModuleIdentity",
    "SourceFileIdentity",
    "SourceLocation",
    "SymbolIdentity",
    # Models (AST & Semantic Architecture)
    "AnalysisDiagnostic",
    "Dependency",
    "Diagnostic",
    "EngineeringSymbol",
    "ImportModel",
    "SemanticRelationship",
    "Symbol",
    "SymbolReference",
    # Models (Payloads & Context)
    "AnalysisContext",
    "AnalysisMetrics",
    "AnalysisResult",
    "SourceDocument",
    "SourceHealth",
    "SourceMetrics",
    # Events
    "SourceAnalysisCompleted",
    "SourceAnalysisFailed",
    "SourceAnalysisStarted",
    "SourceEvent",
    "SourceParsed",
    # Runtime & Providers
    "PythonSourceProvider",
    "SourceProvider",
    "SourceRegistry",
    "SourceRuntime",
    # Transformations
    "RenameTransformation",
    "RenameVisitor",
    "Transformation",
    "TransformationContext",
    "TransformationEngine",
    "TransformationPreview",
    "TransformationRegistry",
    "TransformationResult",
    "TransformationValidator",
    "apply_text_edits",
    "SourceEdit",
    "TextEdit",
]
