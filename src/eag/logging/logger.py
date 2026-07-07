"""Logger access for EAG."""

from typing import Any

import structlog
from structlog.typing import FilteringBoundLogger


def get_logger(**context: Any) -> FilteringBoundLogger:
    """Return a structured EAG logger with optional bound context."""
    logger: FilteringBoundLogger = structlog.get_logger()

    if context:
        return logger.bind(**context)

    return logger
