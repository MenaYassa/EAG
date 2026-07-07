"""Tool base class."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from eag.core.metadata import ComponentMetadata
from eag.registry import Capability


class Tool(ABC):
    """Base class for tools."""

    @property
    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Return component metadata."""

    @property
    @abstractmethod
    def capabilities(self) -> tuple[Capability, ...]:
        """Return capabilities provided by this tool."""

    @abstractmethod
    def execute(self, capability: Capability, arguments: Mapping[str, Any]) -> Any:
        """Execute a capability with given arguments."""

    def health(self) -> bool:
        """Return whether the tool is healthy."""
        return True
