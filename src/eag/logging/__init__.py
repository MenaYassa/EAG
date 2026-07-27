"""EAG structured logging package."""

from eag.logging.configure import configure_logging
from eag.logging.logger import get_logger

__all__ = [
    "configure_logging",
    "get_logger",
]
