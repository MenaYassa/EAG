"""G2.2 read-only repository-context contracts and integration coverage."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from eag.chief.intelligence.gateway.context import ContextAssemblyRequest
from eag.chief.intelligence.gateway.models import EngineeringContext
from eag.chief.intelligence.gateway.runtime import _context_fingerprint
from eag.context import (
    ContextBudget,
    ContextSecurityPolicy,
    ProvidedVcsReadFacade,
    RepositoryContextAssembler,
    RepositoryDiscoveryFacade,
    RepositoryStateEvidence,
    StaleContextError,
    UnavailableVcsReadFacade,
)
from eag.context.events import RepositoryContextAssemblyCompleted, RepositoryContextStaleDetected
from eag.context.sensitivity import SensitivityDecision
from eag.events import EventBus
from eag.graph.builder import GraphBuilder
from eag.graph.runtime import GraphRuntime
from eag.index.runtime import IndexRuntime
from eag.repository.ignore import IgnoreEngine
from eag.repository.runtime import RepositoryRuntime, RepositoryServices
from eag.repository.scanner import RepositoryScanner
from eag.source.runtime import SourceRuntime


class MutableReadFacade:
    """Test-only pre-captured VCS state: context reads it but cannot invoke VCS operations."""

    def __init__(self, evidence: RepositoryStateEvidence) -> None:
        self.evidence = evidence
        self.calls = 0

    def snapshot(self) -> RepositoryStateEvidence:
        self.calls += 1
        return self.evidence


def _write_fixture(root: Path) -> None:
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'article-fixture'\nrequires-python = '>=3.12'\n"
    )
    (root / "README.md").write_text("# Article Fixture\n")
    (root / "src" / "models.py").write_text(
        "from dataclasses import dataclass\n\n"
        "@dataclass\n"
        "class Article:\n"
        "    identifier: int\n"
        "    title: str\n"
    )
    (root / "src" / "service.py").write_text(
        "from models import Article\n\n"
        "def list_articles(offset: int = 0, limit: int = 20) -> list[Article]:\n"
        "    return []\n"
    )
    (root / "src" / "articles.py").write_text(
        "from service import list_articles\n\n"
        "def article_list_endpoint(offset: int = 0, limit: int = 20) -> list[object]:\n"
        "    return list_articles(offset=offset, limit=limit)\n"
    )
    (root / "tests" / "test_articles.py").write_text(
        "from src.articles import article_list_endpoint\n\n"
        "def test_article_list_endpoint_preserves_list_response() -> None:\n"
        "    assert article_list_endpoint() == []\n"
    )


def _make_assembler(
    root: Path,
    *,
    budget: ContextBudget | None = None,
    security_policy: ContextSecurityPolicy | None = None,
    vcs_read_facade=None,
) -> tuple[RepositoryContextAssembler, EventBus]:
    event_bus = EventBus()
    settings = SimpleNamespace(kernel=SimpleNamespace(workspace=root))
    discovery_runtime = RepositoryRuntime(
        RepositoryServices(
            scanner=RepositoryScanner(IgnoreEngine()),
            event_bus=event_bus,
            settings=settings,
        )
    )
    policy = security_policy or ContextSecurityPolicy()
    discovery = RepositoryDiscoveryFacade(discovery_runtime, root, policy)
    index_runtime = IndexRuntime(SourceRuntime(event_bus=event_bus), event_bus)
    graph_runtime = GraphRuntime(GraphBuilder(), event_bus)
    return (
        RepositoryContextAssembler(
            discovery=discovery,
            index_runtime=index_runtime,
            graph_runtime=graph_runtime,
            event_bus=event_bus,
            security_policy=policy,
            budget=budget,
            vcs_read_facade=vcs_read_facade or UnavailableVcsReadFacade(),
        ),
        event_bus,
    )


def test_security_policy_excludes_sensitive_paths_and_redacts_values(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    policy = ContextSecurityPolicy(configured_sensitive_paths=frozenset({"private/*"}))
    paths = {
        ".env": "sensitive_filename",
        ".env.local": "sensitive_filename",
        "secrets/config.py": "sensitive_directory",
        "credentials/service.json": "sensitive_directory",
        "private/value.py": "configured_sensitive_path",
        "key.pem": "sensitive_suffix",
    }
    for relative, reason in paths.items():
        candidate = root / relative
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("API_KEY=do-not-leak")
        decision = policy.classify_path(candidate, root)
        assert decision.action == "excluded"
        assert decision.reason == reason
        assert "do-not-leak" not in repr(decision)

    allowed = root / "src.py"
    allowed.write_text("API_KEY=do-not-leak\nauthorization = 'safe'\nBearer abcdefghijklmnop\n")
    sanitized = policy.read_sanitized(allowed, root)
    assert sanitized.decision.action == "redacted"
    assert sanitized.redaction_count >= 2
    assert sanitized.content is not None
    assert "do-not-leak" not in sanitized.content
    assert "abcdefghijklmnop" not in sanitized.content


def test_security_policy_excludes_binary_and_oversized_content(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    binary = root / "blob.py"
    binary.write_bytes(b"\x00binary")
    oversized = root / "large.py"
    oversized.write_text("x" * 32)
    policy = ContextSecurityPolicy(max_file_bytes=8)

    assert policy.read_sanitized(binary, root).decision.reason == "binary_file"
    assert policy.read_sanitized(oversized, root).decision.reason == "oversized_file"


def test_context_assembly_uses_actual_repository_source_index_and_graph(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    assembler, event_bus = _make_assembler(tmp_path)
    completed = []
    event_bus.subscribe(RepositoryContextAssemblyCompleted, completed.append)

    snapshot, selected = assembler.assemble_selected(
        "Plan pagination support for article_list_endpoint in articles.py while preserving tests."
    )

    assert snapshot.repository_profile.identity.name == tmp_path.name
    assert snapshot.index.statistics.files >= 4
    assert snapshot.graph is not None
    assert snapshot.source_artifacts
    assert any(item.repository_path == "src/articles.py" for item in selected.files)
    assert any(item.repository_path == "tests/test_articles.py" for item in selected.files)
    assert any("article_list_endpoint" in item.qualified_name for item in selected.symbols)
    assert selected.provenance
    assert all(not record.location_path or not record.location_path.startswith("/") for record in selected.provenance)
    assert completed and completed[-1].snapshot_fingerprint == snapshot.snapshot_fingerprint.value
    assert completed[-1].context_fingerprint == selected.context_fingerprint.value


def test_projection_is_generic_bounded_and_contains_no_absolute_host_path(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    assembler, _ = _make_assembler(tmp_path)
    context = assembler.assemble(
        ContextAssemblyRequest(
            goal="Plan pagination support for article_list_endpoint in articles.py.",
            repository_path=tmp_path,
            available_capabilities=("repository", "workspace"),
        )
    )

    assert isinstance(context, EngineeringContext)
    assert context.repository_identity == tmp_path.name
    assert str(tmp_path) not in repr(context)
    assert context.truncation_metadata["snapshot_fingerprint"]
    assert context.truncation_metadata["context_fingerprint"]
    assert "Do not execute capabilities" in context.known_constraints[1]
    assert _context_fingerprint(
        type("Request", (), {"context": context, "allowed_capability_ids": (), "schema_version": "1.0"})()
    ) == context.truncation_metadata["context_fingerprint"]


def test_snapshot_and_context_fingerprints_are_stable_without_timestamp_inputs(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    assembler, _ = _make_assembler(tmp_path)

    first_snapshot, first_selected = assembler.assemble_selected(
        "Plan article_list_endpoint pagination in articles.py."
    )
    second_snapshot, second_selected = assembler.assemble_selected(
        "Plan article_list_endpoint pagination in articles.py."
    )

    assert first_snapshot.snapshot_fingerprint == second_snapshot.snapshot_fingerprint
    assert first_selected.context_fingerprint == second_selected.context_fingerprint


def test_stale_selected_file_is_rejected_and_rebuilt(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    assembler, event_bus = _make_assembler(tmp_path)
    stale_events = []
    event_bus.subscribe(RepositoryContextStaleDetected, stale_events.append)
    prior, _ = assembler.assemble_selected("Plan article_list_endpoint pagination in articles.py.")
    (tmp_path / "src" / "articles.py").write_text(
        "from service import list_articles\n\n"
        "def article_list_endpoint(offset: int = 0, limit: int = 20) -> list[object]:\n"
        "    return list_articles(offset=offset, limit=limit)\n\n"
        "def pagination_contract() -> str:\n"
        "    return 'stable'\n"
    )

    with pytest.raises(StaleContextError):
        assembler.ensure_fresh(prior)
    rebuilt = assembler.rebuild_if_stale(prior)
    assert rebuilt.snapshot_fingerprint != prior.snapshot_fingerprint
    assert stale_events


def test_stale_vcs_state_and_policy_version_invalidate_snapshot(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    state = MutableReadFacade(
        RepositoryStateEvidence(
            available=True,
            branch="main",
            head="a" * 40,
            state_fingerprint="state-a",
        )
    )
    assembler, _ = _make_assembler(tmp_path, vcs_read_facade=state)
    prior = assembler.assemble_snapshot()
    state.evidence = replace(
        state.evidence,
        changed_paths=("src/articles.py",),
        state_fingerprint="state-b",
    )
    with pytest.raises(StaleContextError):
        assembler.ensure_fresh(prior)

    updated_policy_assembler, _ = _make_assembler(
        tmp_path,
        security_policy=ContextSecurityPolicy(policy_version="2.0"),
        vcs_read_facade=ProvidedVcsReadFacade(state.evidence),
    )
    assert updated_policy_assembler.assemble_snapshot().snapshot_fingerprint != prior.snapshot_fingerprint


def test_budget_enforcement_is_deterministic_and_records_omissions(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    budget = ContextBudget(
        max_files=1,
        max_symbols=1,
        max_dependencies=1,
        max_excerpts=1,
        max_excerpt_lines=2,
        max_excerpt_characters=32,
        max_total_characters=180,
    )
    assembler, _ = _make_assembler(tmp_path, budget=budget)

    _, selected = assembler.assemble_selected(
        "Plan pagination support for article_list_endpoint in articles.py while preserving tests."
    )
    assert len(selected.files) <= 1
    assert len(selected.symbols) <= 1
    assert len(selected.dependencies) <= 1
    assert len(selected.excerpts) <= 1
    assert selected.truncation.truncated is True
    assert selected.truncation.omitted_counts["files"] >= 1
    assert selected.truncation.actual_usage["total_characters"] <= budget.max_total_characters


def test_context_assembly_excludes_sensitive_files_before_source_runtime(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=super-secret-value")
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "vault.py").write_text("token = 'super-secret-value'")
    assembler, _ = _make_assembler(tmp_path)

    snapshot, selected = assembler.assemble_selected("Plan article_list_endpoint pagination in articles.py.")
    all_artifacts = {item.repository_path for item in snapshot.source_artifacts}
    provider_text = repr(selected)
    assert ".env" not in all_artifacts
    assert "secrets/vault.py" not in all_artifacts
    assert "super-secret-value" not in provider_text


def test_context_assembly_has_no_capability_workspace_git_or_shell_hooks(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    assembler, _ = _make_assembler(tmp_path)
    snapshot, selected = assembler.assemble_selected("Plan article_list_endpoint pagination in articles.py.")

    assert snapshot.repository_state.available is False
    assert selected.context_fingerprint.value
    assert not hasattr(assembler, "execute")
    assert not hasattr(assembler, "write")
    assert not hasattr(assembler, "commit")
    assert not hasattr(assembler, "push")
    assert not hasattr(assembler, "run")


def test_empty_repository_returns_explicit_insufficiency_without_effects(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Empty\n")
    assembler, _ = _make_assembler(tmp_path)

    _, selected = assembler.assemble_selected("Plan an API change.")
    assert selected.truncation.insufficient is True
    assert not selected.files
    assert selected.context_fingerprint.value


def test_sensitive_decision_rejects_absolute_repository_paths() -> None:
    with pytest.raises(ValueError):
        SensitivityDecision(action="included", reason="allowed", repository_path="/host/private.py")


def test_unsupported_language_repository_records_insufficient_safe_context(tmp_path: Path) -> None:
    """A repository with no supported source files must return explicit insufficiency, not invented facts."""
    (tmp_path / "README.md").write_text("# JavaScript-only fixture\n")
    (tmp_path / "app.js").write_text("export const articleList = () => [];\n")
    assembler, _ = _make_assembler(tmp_path)

    snapshot, selected = assembler.assemble_selected("Plan article pagination.")
    assert snapshot.index.statistics.files == 0
    assert not snapshot.source_artifacts
    assert selected.truncation.insufficient is True
    assert not selected.files


def test_discovery_facade_excludes_sensitive_candidates_before_analysis(tmp_path: Path) -> None:
    """Safe candidate discovery retains only allowed source paths and never reads secret content."""
    _write_fixture(tmp_path)
    (tmp_path / ".env").write_text("TOKEN=not-for-provider")
    (tmp_path / "credentials").mkdir()
    (tmp_path / "credentials" / "client.py").write_text("secret = 'not-for-provider'\n")
    assembler, _ = _make_assembler(tmp_path)

    snapshot = assembler.assemble_snapshot()
    artifact_paths = {item.repository_path for item in snapshot.source_artifacts}
    assert "src/articles.py" in artifact_paths
    assert ".env" not in artifact_paths
    assert "credentials/client.py" not in artifact_paths
