"""Data models for workspace intelligence."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceEntry:
    """Describe one entry in a workspace tree."""

    path: str
    kind: str
    depth: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchMatch:
    """Describe a text search match."""

    path: str
    line_number: int
    line: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LanguageStat:
    """Describe detected language usage."""

    language: str
    files: int


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceProfile:
    """Summarize the structure of a workspace."""

    root: str
    total_files: int
    total_directories: int
    languages: tuple[LanguageStat, ...]
    markers: tuple[str, ...]
    ignored_directories: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceInspection:
    """Provide a compact high-level workspace inspection."""

    profile: WorkspaceProfile
    likely_entry_points: tuple[str, ...]
    important_files: tuple[str, ...]
