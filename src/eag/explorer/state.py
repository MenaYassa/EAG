from enum import StrEnum


class ExplorerState(StrEnum):
    IDLE = "idle"
    QUERYING = "querying"
    FORMATTING = "formatting"
    READY = "ready"
    FAILED = "failed"
