from enum import StrEnum


class IndexState(StrEnum):
    UNKNOWN = "unknown"
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"
