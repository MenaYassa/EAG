from enum import StrEnum


class AnalysisState(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class SymbolKind(StrEnum):
    MODULE = "module"
    PACKAGE = "package"
    CLASS = "class"
    INTERFACE = "interface"
    PROTOCOL = "protocol"
    ENUM = "enum"
    DATACLASS = "dataclass"
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    FIELD = "field"
    VARIABLE = "variable"
    CONSTANT = "constant"
    TYPE_ALIAS = "type_alias"


class Visibility(StrEnum):
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    INTERNAL = "internal"


class DependencyKind(StrEnum):
    IMPORT = "import"
    EXPORT = "export"
    CALL = "call"
    INHERITANCE = "inheritance"
    IMPLEMENTATION = "implementation"
    REFERENCE = "reference"


class AnalysisSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SemanticKind(StrEnum):
    CALLS = "calls"
    INHERITS = "inherits"
    USES = "uses"
    PUBLISHES_EVENT = "publishes_event"
    SUBSCRIBES_EVENT = "subscribes_event"
