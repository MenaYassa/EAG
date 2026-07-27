"""Ignore rules for workspace intelligence."""

DEFAULT_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "target",
        "vendor",
    }
)


def should_ignore_directory(name: str) -> bool:
    """Return whether a directory should be ignored."""
    return name in DEFAULT_IGNORED_DIRECTORIES
