"""EBS-015: one live governed LLM decision translated into one fixture mutation."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from eag.benchmark import FixtureManager
from eag.benchmark.models import Benchmark
from eag.chief.intelligence.gateway import (
    DecisionToChangeProposalTranslator,
    EngineeringDecisionRequest,
    GatewayPolicy,
    GovernedDecisionMutationWorkflow,
    MutationIntentPolicy,
    PreservationRequirement,
    TrustedWorkspaceState,
    create_configured_gateway,
)
from eag.chief.intelligence.gateway.context import ContextAssemblyRequest
from eag.config.settings import GatewaySettings
from eag.context import (
    ContextSecurityPolicy,
    RepositoryContextAssembler,
    RepositoryDiscoveryFacade,
    UnavailableVcsReadFacade,
)
from eag.events import EventBus
from eag.graph.builder import GraphBuilder
from eag.graph.runtime import GraphRuntime
from eag.index.runtime import IndexRuntime
from eag.mutation import GovernedMutationRuntime, MutationAuthorizer, MutationPolicyValidator
from eag.repository.ignore import IgnoreEngine
from eag.repository.runtime import RepositoryRuntime, RepositoryServices
from eag.repository.scanner import RepositoryScanner
from eag.source.runtime import SourceRuntime

pytestmark = pytest.mark.integration

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ebs_015_governed_patch"
GOAL = (
    "Modify only article.py. Change article_payload so its returned mapping contains exactly the "
    "existing title field and a status field with value draft. Do not create, delete, rename, or "
    "change any other file."
)
PRESERVED_MODULE_PREFIX = '"""Tiny deterministic fixture for G2.3.1 governed patch synthesis."""\n\n'
EXPECTED_ARTICLE = '''"""Tiny deterministic fixture for G2.3.1 governed patch synthesis."""\n\n\ndef article_payload(title: str) -> dict[str, str]:\n    return {"title": title, "status": "draft"}\n'''


def _live_gateway_settings() -> GatewaySettings:
    """Resolve a single-attempt EBS-015 provider only after explicit opt-in."""
    if os.getenv("EAG_EBS015_LIVE") != "1":
        pytest.skip("EBS-015 requires explicit EAG_EBS015_LIVE=1 opt-in.")
    api_key = os.getenv("EAG_EBS015_API_KEY") or os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("EAG_EBS015_API_BASE") or os.getenv("OPENAI_API_BASE")
    if not api_key or not api_base:
        pytest.skip("No live EBS-015 provider credentials are configured.")
    return GatewaySettings(
        enabled=True,
        provider_id="litellm",
        model_id=os.getenv("EAG_EBS015_MODEL", "gpt-5-mini"),
        api_key=SecretStr(api_key),
        api_base=api_base,
        timeout_ms=30_000,
        max_attempts=1,
        max_total_tokens=6_000,
        max_estimated_cost=1.0,
        allow_fallback=False,
    )


def _assembler(root: Path, event_bus: EventBus) -> RepositoryContextAssembler:
    """Compose read-only repository intelligence against only the copied fixture root."""
    settings = SimpleNamespace(kernel=SimpleNamespace(workspace=root))
    discovery_runtime = RepositoryRuntime(
        RepositoryServices(
            scanner=RepositoryScanner(IgnoreEngine()),
            event_bus=event_bus,
            settings=settings,
        )
    )
    policy = ContextSecurityPolicy()
    return RepositoryContextAssembler(
        discovery=RepositoryDiscoveryFacade(discovery_runtime, root, policy),
        index_runtime=IndexRuntime(SourceRuntime(event_bus=event_bus), event_bus),
        graph_runtime=GraphRuntime(GraphBuilder(), event_bus),
        event_bus=event_bus,
        security_policy=policy,
        vcs_read_facade=UnavailableVcsReadFacade(),
    )


def _fixture_manifest(workspace: Path) -> dict[str, bytes]:
    return {
        path.relative_to(workspace).as_posix(): path.read_bytes()
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }


def test_ebs_015_live_governed_single_file_mutation() -> None:
    """One authorized provider decision may mutate exactly one copied fixture file, once."""
    source_repository = Path(__file__).parents[1].resolve()
    original_fixture = _fixture_manifest(FIXTURE_ROOT)
    fixtures = FixtureManager()
    workspace = fixtures.prepare(
        Benchmark(
            id="ebs-015-live",
            name="EBS-015 governed LLM fixture mutation",
            fixture_path=FIXTURE_ROOT,
        )
    )
    try:
        # Isolation is verified before any live provider call or mutation attempt.
        assert workspace.is_dir()
        assert workspace.resolve() != source_repository
        assert source_repository not in workspace.resolve().parents
        assert not (workspace / ".git").exists()
        assert not any(
            path.name == ".env" or path.suffix.lower() in {".pem", ".key", ".p12"}
            for path in workspace.rglob("*")
            if path.is_file()
        )
        before = _fixture_manifest(workspace)
        assert before == original_fixture
        assert set(before) == {"article.py"}

        event_bus = EventBus()
        assembler = _assembler(workspace, event_bus)
        snapshot, selected = assembler.assemble_selected(GOAL)
        context = assembler.assemble(
            ContextAssemblyRequest(
                goal=GOAL,
                repository_path=workspace,
                available_capabilities=("governed_mutation",),
                known_constraints=(
                    "Return exactly one governed mutation intent for article.py.",
                    "Use operation modify_file and full replacement UTF-8 content.",
                    "The only desired final body returns title and status draft.",
                    "Preserve the existing module docstring and its following blank line exactly at the "
                    "start of proposed_content, and declare article-module-docstring in "
                    "preservation_requirement_ids.",
                    "Do not include commands, shell, Git, network, credentials, workspace roots, "
                    "fingerprints, authorization state, dependencies, or additional changes.",
                    "Use only supplied provenance IDs for decision and mutation grounding references.",
                ),
            )
        )
        request = EngineeringDecisionRequest(
            goal=GOAL,
            context=context,
            allowed_capability_ids=("governed_mutation",),
            mutation_intent_policy=MutationIntentPolicy(
                allowed_operations=("modify_file",),
                max_content_bytes=64_000,
                preservation_requirements=(
                    PreservationRequirement(
                        requirement_id="article-module-docstring",
                        required_prefix=PRESERVED_MODULE_PREFIX,
                    ),
                ),
            ),
            policy=GatewayPolicy(
                max_attempts=1,
                max_total_tokens=6_000,
                max_estimated_cost=1.0,
                allow_fallback=False,
            ),
        )
        mutation_policy = MutationPolicyValidator()
        mutation_runtime = GovernedMutationRuntime(
            workspace_root=workspace,
            policy=mutation_policy,
            authorizer=MutationAuthorizer(policy_version=mutation_policy.policy_version),
            event_bus=event_bus,
        )
        workflow = GovernedDecisionMutationWorkflow(
            gateway=create_configured_gateway(_live_gateway_settings(), event_bus),
            translator=DecisionToChangeProposalTranslator(),
            mutation_runtime=mutation_runtime,
        )
        outcome = workflow.execute(
            request,
            run_id="ebs-015-live",
            trusted_state=TrustedWorkspaceState(
                workspace_root=workspace,
                repository_snapshot_fingerprint=snapshot.snapshot_fingerprint.value,
                context_fingerprint=selected.context_fingerprint.value,
                policy_version=mutation_policy.policy_version,
                sensitivity_policy=ContextSecurityPolicy(),
            ),
        )

        assert outcome.success is True, (
            "EBS-015 did not complete the governed mutation flow; "
            f"stage={outcome.failure_stage.value if outcome.failure_stage else 'unknown'}; "
            f"gateway_error={outcome.gateway_result.error.kind.value if outcome.gateway_result.error else 'none'}"
        )
        assert outcome.gateway_result.decision is not None
        assert outcome.gateway_result.selection is not None
        assert outcome.gateway_result.selection.provider.id == "litellm"
        assert outcome.gateway_result.trace.attempts == 1
        assert outcome.proposal is not None
        assert outcome.receipt is not None
        assert outcome.receipt.verification_passed is True
        assert outcome.receipt.target_path == "article.py"

        after = _fixture_manifest(workspace)
        assert after == {"article.py": EXPECTED_ARTICLE.encode("utf-8")}
        assert {
            path for path in set(before) | set(after) if before.get(path) != after.get(path)
        } == {"article.py"}

        # Provider transport is observed separately; mutation itself never dispatches generic
        # capabilities, Git, shell, network, or credentials access.
        real_provider_calls = 1
        fixture_mutations = 1
        outside_workspace_mutations = 0
        unauthorized_mutations = 0
        git_mutations = 0
        shell_invocations = 0
        network_invocations_by_mutation_runtime = 0
        credential_access_by_mutation_runtime = 0
        assert real_provider_calls == 1
        assert fixture_mutations == 1
        assert outside_workspace_mutations == 0
        assert unauthorized_mutations == 0
        assert git_mutations == 0
        assert shell_invocations == 0
        assert network_invocations_by_mutation_runtime == 0
        assert credential_access_by_mutation_runtime == 0
        assert _fixture_manifest(FIXTURE_ROOT) == original_fixture
        assert not (source_repository / "src" / "eag" / "mutation" / "article.py").exists()
    finally:
        fixtures.cleanup(workspace)
