"""Worker base class."""

from abc import ABC, abstractmethod
from typing import Any

from eag.core.metadata import ComponentMetadata


class Worker(ABC):
    """Base class for workers."""

    @property
    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Return component metadata."""

    @abstractmethod
    def run(self, task: Any) -> Any:
        """Run a task and return the result."""

    def health(self) -> bool:
        """Return whether the worker is healthy."""
        return True
