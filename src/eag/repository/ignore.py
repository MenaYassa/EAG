import fnmatch
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryIgnoreRules:
    directories: frozenset[str] = field(default_factory=frozenset)
    files: frozenset[str] = field(default_factory=frozenset)
    patterns: frozenset[str] = field(default_factory=frozenset)


class IgnoreEngine:
    DEFAULT_DIRECTORIES = frozenset(
        {
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "coverage",
            "dist",
            "build",
        }
    )
    DEFAULT_FILES = frozenset({".coverage", "coverage.xml"})
    DEFAULT_PATTERNS = frozenset({"*.pyc", "*.pyo", "*.pyd", "*.egg-info"})

    def __init__(self, rules: RepositoryIgnoreRules | None = None) -> None:
        self._rules = rules or RepositoryIgnoreRules(
            directories=self.DEFAULT_DIRECTORIES,
            files=self.DEFAULT_FILES,
            patterns=self.DEFAULT_PATTERNS,
        )
        self._directories = self._rules.directories
        self._files = self._rules.files
        self._patterns = self._rules.patterns

    def should_ignore(self, path: Path) -> bool:
        name = path.name
        if name in self._directories:
            return True
        if name in self._files:
            return True
        return any(fnmatch.fnmatch(name, pattern) for pattern in self._patterns)
