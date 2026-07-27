from enum import StrEnum


class GraphNodeKind(StrEnum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    FILE = "file"
    PACKAGE = "package"
    DEPENDENCY = "dependency"
    TEST = "test"


class RelationshipType(StrEnum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    DEPENDS_ON = "depends_on"
    USES = "uses"
    CALLS = "calls"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    REFERENCES = "references"
    PUBLISHES_EVENT = "publishes_event"
    SUBSCRIBES_EVENT = "subscribes_event"


class GraphState(StrEnum):
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"
