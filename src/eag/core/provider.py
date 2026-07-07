"""Provider base class."""

from abc import ABC, abstractmethod

from eag.core.metadata import ComponentMetadata


class Provider(ABC):
    """Base class for capability providers."""

    @property
    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Return component metadata."""

    @abstractmethod
    def health(self) -> bool:
        """Return whether the provider is healthy."""
