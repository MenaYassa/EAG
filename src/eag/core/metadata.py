"""Component metadata definition."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentMetadata:
    """Metadata for a component (tool, provider, plugin, worker)."""

    name: str
    version: str
    description: str = ""

    def __post_init__(self) -> None:
        """Validate metadata fields."""
        if not self.name.strip():
            raise ValueError("Component name cannot be empty")
        if not self.version.strip():
            raise ValueError("Component version cannot be empty")
