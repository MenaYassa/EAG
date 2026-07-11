from enum import StrEnum


class RepositoryState(StrEnum):
    UNKNOWN = "unknown"
    DISCOVERING = "discovering"
    SCANNING = "scanning"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class RepositoryHealth(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"


class RepositoryKind(StrEnum):
    UNKNOWN = "unknown"
    PYTHON = "python"
    NODE = "node"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    MIXED = "mixed"


class ProjectLayout(StrEnum):
    FLAT = "flat"
    SRC_LAYOUT = "src_layout"
    MONOREPO = "monorepo"
    UNKNOWN = "unknown"


class FileCategory(StrEnum):
    SOURCE = "source"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    UNKNOWN = "unknown"
