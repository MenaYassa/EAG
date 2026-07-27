"""Workspace profiling utilities."""

import os
from collections import Counter
from pathlib import Path

from eag.plugins.builtin.workspace.ignore import (
    DEFAULT_IGNORED_DIRECTORIES,
    should_ignore_directory,
)
from eag.plugins.builtin.workspace.models import (
    LanguageStat,
    WorkspaceProfile,
)

LANGUAGE_BY_SUFFIX = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".go": "Go",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".md": "Markdown",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sh": "Shell",
    ".sql": "SQL",
    ".swift": "Swift",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vue": "Vue",
    ".yaml": "YAML",
    ".yml": "YAML",
}

PROJECT_MARKERS = {
    "Cargo.toml",
    "Dockerfile",
    "Makefile",
    "README.md",
    "compose.yaml",
    "docker-compose.yml",
    "go.mod",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
}


class WorkspaceProfiler:
    """Analyze the high-level structure of a workspace."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace.resolve()

    def profile(self) -> WorkspaceProfile:
        """Build a workspace profile."""

        language_counts: Counter[str] = Counter()
        markers: list[str] = []
        total_files = 0
        total_directories = 0

        for root, directories, files in os.walk(self._workspace):
            directories[:] = [name for name in directories if not should_ignore_directory(name)]

            total_directories += len(directories)

            root_path = Path(root)

            for filename in files:
                path = root_path / filename
                relative = path.relative_to(self._workspace)

                if not path.is_file():
                    continue

                total_files += 1

                language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower())

                if language is not None:
                    language_counts[language] += 1

                if len(relative.parts) == 1 and filename in PROJECT_MARKERS:
                    markers.append(filename)

        languages = tuple(
            LanguageStat(
                language=language,
                files=count,
            )
            for language, count in sorted(
                language_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )

        return WorkspaceProfile(
            root=str(self._workspace),
            total_files=total_files,
            total_directories=total_directories,
            languages=languages,
            markers=tuple(sorted(markers)),
            ignored_directories=tuple(sorted(DEFAULT_IGNORED_DIRECTORIES)),
        )

    @staticmethod
    def _is_ignored(relative: Path) -> bool:
        """Return whether a relative path crosses ignored directories."""
        return any(should_ignore_directory(part) for part in relative.parts[:-1])
