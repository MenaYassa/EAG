"""Tests for workspace intelligence."""

from pathlib import Path

import pytest

from eag.core import RuntimeContext
from eag.plugins import PluginManager
from eag.plugins.builtin.filesystem import (
    WorkspaceBoundaryError,
)
from eag.plugins.builtin.workspace import (
    WORKSPACE_INSPECT,
    WORKSPACE_PROFILE,
    WORKSPACE_SEARCH,
    WORKSPACE_TREE,
    WorkspacePlugin,
    WorkspaceTool,
)


def test_tree_excludes_ignored_directories(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "main.pyc").touch()

    tool = WorkspaceTool(workspace=tmp_path)

    entries = tool.tree()

    paths = {entry.path for entry in entries}

    assert "src" in paths
    assert "src/main.py" in paths
    assert "__pycache__" not in paths
    assert "__pycache__/main.pyc" not in paths


def test_tree_rejects_path_escape(
    tmp_path: Path,
) -> None:
    tool = WorkspaceTool(workspace=tmp_path)

    with pytest.raises(WorkspaceBoundaryError):
        tool.tree("../")


def test_search_finds_literal_text(
    tmp_path: Path,
) -> None:
    source = tmp_path / "main.py"
    source.write_text(
        "first line\nEAG is here\nthird line\n",
        encoding="utf-8",
    )

    tool = WorkspaceTool(workspace=tmp_path)

    matches = tool.search("EAG")

    assert len(matches) == 1
    assert matches[0].path == "main.py"
    assert matches[0].line_number == 2
    assert matches[0].line == "EAG is here"


def test_search_skips_binary_files(
    tmp_path: Path,
) -> None:
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xff\xfe\x00\x00")

    tool = WorkspaceTool(workspace=tmp_path)

    matches = tool.search("EAG")

    assert matches == ()


def test_search_respects_max_results(
    tmp_path: Path,
) -> None:
    source = tmp_path / "main.py"
    source.write_text(
        "EAG\nEAG\nEAG\n",
        encoding="utf-8",
    )

    tool = WorkspaceTool(workspace=tmp_path)

    matches = tool.search(
        "EAG",
        max_results=2,
    )

    assert len(matches) == 2


def test_profile_detects_python_project(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example'\n",
        encoding="utf-8",
    )

    src = tmp_path / "src"
    src.mkdir()

    (src / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    tool = WorkspaceTool(workspace=tmp_path)

    profile = tool.profile()

    assert profile.total_files == 2
    assert "pyproject.toml" in profile.markers
    assert any(
        language.language == "Python" and language.files == 1 for language in profile.languages
    )


def test_inspect_detects_important_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").touch()
    (tmp_path / "pyproject.toml").touch()

    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").touch()

    tool = WorkspaceTool(workspace=tmp_path)

    inspection = tool.inspect()

    assert "README.md" in inspection.important_files
    assert "pyproject.toml" in inspection.important_files
    assert "src/main.py" in inspection.likely_entry_points


def test_workspace_plugin_registers_capabilities(
    runtime_context: RuntimeContext,
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(WorkspacePlugin())

    plugin_manager.load("workspace")

    registry = runtime_context.capability_registry

    assert registry.has(WORKSPACE_TREE)
    assert registry.has(WORKSPACE_SEARCH)
    assert registry.has(WORKSPACE_PROFILE)
    assert registry.has(WORKSPACE_INSPECT)


def test_workspace_plugin_unregisters_capabilities(
    runtime_context: RuntimeContext,
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(WorkspacePlugin())

    plugin_manager.load("workspace")
    plugin_manager.unload("workspace")

    registry = runtime_context.capability_registry

    assert registry.has(WORKSPACE_TREE) is False
    assert registry.has(WORKSPACE_SEARCH) is False
    assert registry.has(WORKSPACE_PROFILE) is False
    assert registry.has(WORKSPACE_INSPECT) is False
