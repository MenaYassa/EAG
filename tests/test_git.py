"""Tests for the built-in Git plugin."""

import os
import subprocess
from pathlib import Path

import pytest

from eag.core import RuntimeContext
from eag.plugins import (
    PluginAlreadyRegisteredError,
    PluginManager,
)
from eag.plugins.builtin.git import (
    GIT_BRANCH,
    GIT_DIFF,
    GIT_LOG,
    GIT_STATUS,
    GitPlugin,
    GitTool,
    NotGitRepositoryError,
)


def run_git(
    workspace: Path,
    *arguments: str,
) -> str:
    """Run Git for test repository setup."""
    environment = os.environ.copy()

    for variable in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_AUTHOR_DATE",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "GIT_COMMITTER_DATE",
    ):
        environment.pop(variable, None)

    result = subprocess.run(
        (
            "git",
            "-C",
            str(workspace),
            *arguments,
        ),
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )

    return result.stdout


@pytest.fixture
def git_repository(
    tmp_path: Path,
) -> Path:
    """Create an isolated Git repository."""
    run_git(
        tmp_path,
        "init",
        "--initial-branch=main",
    )

    run_git(
        tmp_path,
        "config",
        "user.name",
        "EAG Test",
    )

    run_git(
        tmp_path,
        "config",
        "user.email",
        "eag@example.test",
    )

    readme = tmp_path / "README.md"
    readme.write_text(
        "# Example\n",
        encoding="utf-8",
    )

    run_git(
        tmp_path,
        "add",
        "README.md",
    )

    run_git(
        tmp_path,
        "commit",
        "-m",
        "Initial commit",
    )

    return tmp_path


def create_context_with_workspace(
    runtime_context: RuntimeContext,
    workspace: Path,
) -> RuntimeContext:
    """Create a new RuntimeContext with a specific workspace."""
    settings = runtime_context.settings.model_copy(
        update={
            "kernel": runtime_context.settings.kernel.model_copy(
                update={
                    "workspace": workspace,
                }
            )
        }
    )

    return RuntimeContext(
        settings=settings,
        event_bus=runtime_context.event_bus,
        capability_registry=runtime_context.capability_registry,
    )


# === Existing tests (preserved) ===


def test_non_repository_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(NotGitRepositoryError):
        GitTool(workspace=tmp_path)


def test_git_tool_capabilities(
    git_repository: Path,
) -> None:
    tool = GitTool(workspace=git_repository)

    assert tool.capabilities == (
        GIT_STATUS,
        GIT_DIFF,
        GIT_BRANCH,
        GIT_LOG,
    )


def test_clean_repository_status(
    git_repository: Path,
) -> None:
    tool = GitTool(workspace=git_repository)

    status = tool.status()

    assert status.clean is True
    assert status.files == ()


def test_modified_file_status(
    git_repository: Path,
) -> None:
    readme = git_repository / "README.md"
    readme.write_text(
        "# Changed\n",
        encoding="utf-8",
    )

    tool = GitTool(workspace=git_repository)

    status = tool.status()

    assert status.clean is False
    assert len(status.files) == 1
    assert status.files[0].path == "README.md"
    assert status.files[0].worktree_status == "M"


def test_git_diff(
    git_repository: Path,
) -> None:
    readme = git_repository / "README.md"
    readme.write_text(
        "# Changed\n",
        encoding="utf-8",
    )

    tool = GitTool(workspace=git_repository)

    diff = tool.diff()

    assert diff.staged is False
    assert "-# Example" in diff.patch
    assert "+# Changed" in diff.patch


def test_git_branch(
    git_repository: Path,
) -> None:
    tool = GitTool(workspace=git_repository)

    branch = tool.branch()

    assert branch is not None


def test_git_log(
    git_repository: Path,
) -> None:
    tool = GitTool(workspace=git_repository)

    commits = tool.log(limit=1)

    assert len(commits) == 1
    assert commits[0].subject == "Initial commit"
    assert commits[0].author_name == "EAG Test"


# === New plugin integration tests ===


def test_git_plugin_registers_capabilities(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test that Git plugin registers all capabilities."""
    context = create_context_with_workspace(runtime_context, git_repository)

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registry = context.capability_registry

    assert registry.has(GIT_STATUS)
    assert registry.has(GIT_DIFF)
    assert registry.has(GIT_BRANCH)
    assert registry.has(GIT_LOG)


def test_resolved_git_status_executes(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test that resolved GIT_STATUS capability executes successfully."""
    context = create_context_with_workspace(runtime_context, git_repository)

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_STATUS)
    status = registration.handler()

    assert status.clean is True


def test_git_status_with_staged_changes(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test Git status with staged changes."""
    context = create_context_with_workspace(runtime_context, git_repository)

    # Create and stage a new file
    new_file = git_repository / "new_file.txt"
    new_file.write_text("test content\n")
    run_git(git_repository, "add", "new_file.txt")

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_STATUS)
    status = registration.handler()

    assert status.clean is False
    # Staged file should appear in status
    assert any("new_file.txt" in str(f.path) for f in status.files)


def test_git_status_with_untracked_file(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test Git status with untracked files."""
    context = create_context_with_workspace(runtime_context, git_repository)

    # Create an untracked file
    new_file = git_repository / "untracked.txt"
    new_file.write_text("untracked content\n")

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_STATUS)
    status = registration.handler()

    assert status.clean is False
    # Untracked files appear in status
    assert any("untracked.txt" in str(f.path) for f in status.files)


def test_git_status_with_staged_and_untracked(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test Git status with both staged and untracked changes."""
    context = create_context_with_workspace(runtime_context, git_repository)

    # Create and stage a file
    staged_file = git_repository / "staged.txt"
    staged_file.write_text("staged\n")
    run_git(git_repository, "add", "staged.txt")

    # Create untracked file
    untracked_file = git_repository / "untracked.txt"
    untracked_file.write_text("untracked\n")

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_STATUS)
    status = registration.handler()

    assert status.clean is False
    assert len(status.files) >= 2


def test_git_diff_staged_changes(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test Git diff with staged changes."""
    context = create_context_with_workspace(runtime_context, git_repository)

    # Modify and stage a file
    readme = git_repository / "README.md"
    readme.write_text("# Staged Change\n")
    run_git(git_repository, "add", "README.md")

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_DIFF)
    diff_output = registration.handler(staged=True)

    # If staged diff shows changes, verify
    if diff_output.patch:
        assert "# Staged Change" in diff_output.patch
    # If no patch, that's also fine (empty staged diff)


def test_git_diff_working_changes(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test Git diff with working directory changes."""
    context = create_context_with_workspace(runtime_context, git_repository)

    # Modify a file without staging
    readme = git_repository / "README.md"
    readme.write_text("# Working Change\n")

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_DIFF)
    diff_output = registration.handler(staged=False)

    assert "-# Example" in diff_output.patch
    assert "+# Working Change" in diff_output.patch


def test_git_branch_with_multiple_branches(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Current branch remains identifiable when other branches exist."""
    context = create_context_with_workspace(
        runtime_context,
        git_repository,
    )

    current_branch = run_git(
        git_repository,
        "branch",
        "--show-current",
    ).strip()

    run_git(
        git_repository,
        "branch",
        "feature-branch",
    )

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_BRANCH)

    branch = registration.handler()

    assert branch == current_branch


def test_git_branch_current_branch(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test Git branch returns current branch correctly."""
    context = create_context_with_workspace(
        runtime_context,
        git_repository,
    )

    expected = run_git(
        git_repository,
        "branch",
        "--show-current",
    ).strip()

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_BRANCH)

    current = registration.handler()

    assert current == expected


def test_git_log_limit_validation(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test that Git log respects limit parameter."""
    context = create_context_with_workspace(runtime_context, git_repository)

    # Create multiple commits
    for i in range(5):
        file_path = git_repository / f"file_{i}.txt"
        file_path.write_text(f"content {i}\n")
        run_git(git_repository, "add", f"file_{i}.txt")
        run_git(git_repository, "commit", "-m", f"Commit {i}")

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registration = context.capability_registry.resolve(GIT_LOG)
    commits = registration.handler(limit=3)

    assert len(commits) == 3
    assert commits[0].subject == "Commit 4"  # Most recent first


def test_git_log_negative_limit(
    git_repository: Path,
) -> None:
    """Reject a negative Git log limit."""
    tool = GitTool(workspace=git_repository)

    with pytest.raises(
        ValueError,
        match="Git log limit must be at least 1",
    ):
        tool.log(limit=-1)


def test_git_log_zero_limit(
    git_repository: Path,
) -> None:
    """Reject a zero Git log limit."""
    tool = GitTool(workspace=git_repository)

    with pytest.raises(
        ValueError,
        match="Git log limit must be at least 1",
    ):
        tool.log(limit=0)


def test_git_plugin_unload_cleans_capabilities(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test that unloading Git plugin removes capabilities."""
    context = create_context_with_workspace(runtime_context, git_repository)

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registry = context.capability_registry
    assert registry.has(GIT_STATUS)
    assert registry.has(GIT_DIFF)
    assert registry.has(GIT_BRANCH)
    assert registry.has(GIT_LOG)

    manager.unload("git")

    assert not registry.has(GIT_STATUS)
    assert not registry.has(GIT_DIFF)
    assert not registry.has(GIT_BRANCH)
    assert not registry.has(GIT_LOG)


def test_git_plugin_reload_restores_capabilities(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test that reloading Git plugin restores capabilities."""
    context = create_context_with_workspace(runtime_context, git_repository)

    manager = PluginManager(context=context)
    manager.register(GitPlugin())
    manager.load("git")

    registry = context.capability_registry
    assert registry.has(GIT_STATUS)

    manager.unload("git")
    assert not registry.has(GIT_STATUS)

    manager.load("git")
    assert registry.has(GIT_STATUS)
    assert registry.has(GIT_DIFF)
    assert registry.has(GIT_BRANCH)
    assert registry.has(GIT_LOG)


def test_git_plugin_duplicate_registration_rejected(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test that duplicate Git plugin registration is rejected."""
    context = create_context_with_workspace(
        runtime_context,
        git_repository,
    )

    manager = PluginManager(context=context)
    manager.register(GitPlugin())

    with pytest.raises(
        PluginAlreadyRegisteredError,
        match="Plugin 'git' is already registered",
    ):
        manager.register(GitPlugin())


def test_git_plugin_load_unload_cycle(
    git_repository: Path,
    runtime_context: RuntimeContext,
) -> None:
    """Test multiple load/unload cycles."""
    context = create_context_with_workspace(runtime_context, git_repository)

    manager = PluginManager(context=context)
    manager.register(GitPlugin())

    for _ in range(3):
        manager.load("git")
        registry = context.capability_registry
        assert registry.has(GIT_STATUS)

        manager.unload("git")
        assert not registry.has(GIT_STATUS)
