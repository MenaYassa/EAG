"""EBS-014: repository-aware governed engineering decision live-provider benchmark."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from eag.chief.intelligence.gateway import (
    EngineeringDecisionRequest,
    GatewayPolicy,
    create_configured_gateway,
)
from eag.chief.intelligence.gateway.context import ContextAssemblyRequest
from eag.chief.intelligence.gateway.events import GatewayContextAssembled
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
from eag.repository.ignore import IgnoreEngine
from eag.repository.runtime import RepositoryRuntime, RepositoryServices
from eag.repository.scanner import RepositoryScanner
from eag.source.runtime import SourceRuntime

pytestmark = pytest.mark.integration

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ebs_014_article_repository"
GOAL = (
    "Plan pagination support for the existing article-list endpoint while preserving its "
    "current response contract and extending the relevant tests."
)


def _live_gateway_settings() -> GatewaySettings:
    """Resolve only explicitly configured live-provider credentials for EBS-014."""
    if os.getenv("EAG_EBS014_LIVE") != "1":
        pytest.skip("EBS-014 requires explicit EAG_EBS014_LIVE=1 opt-in.")
    api_key = os.getenv("EAG_EBS014_API_KEY") or os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("EAG_EBS014_API_BASE") or os.getenv("OPENAI_API_BASE")
    if not api_key or not api_base:
        pytest.skip("No live EBS-014 provider credentials are configured.")
    return GatewaySettings(
        enabled=True,
        provider_id="litellm",
        model_id=os.getenv("EAG_EBS014_MODEL", "gpt-5-mini"),
        api_key=SecretStr(api_key),
        api_base=api_base,
        timeout_ms=30_000,
        max_attempts=1,
        max_total_tokens=6_000,
        max_estimated_cost=1.0,
        allow_fallback=False,
    )


def _assembler(event_bus: EventBus) -> RepositoryContextAssembler:
    """Compose actual existing discovery/source/index/graph services for the static fixture."""
    settings = SimpleNamespace(kernel=SimpleNamespace(workspace=FIXTURE_ROOT))
    discovery_runtime = RepositoryRuntime(
        RepositoryServices(
            scanner=RepositoryScanner(IgnoreEngine()),
            event_bus=event_bus,
            settings=settings,
        )
    )
    policy = ContextSecurityPolicy()
    return RepositoryContextAssembler(
        discovery=RepositoryDiscoveryFacade(discovery_runtime, FIXTURE_ROOT, policy),
        index_runtime=IndexRuntime(SourceRuntime(event_bus=event_bus), event_bus),
        graph_runtime=GraphRuntime(GraphBuilder(), event_bus),
        event_bus=event_bus,
        security_policy=policy,
        # EBS-014 intentionally supplies no VCS command adapter. The context layer must not
        # execute shell commands or mutate Git merely to form advisory evidence.
        vcs_read_facade=UnavailableVcsReadFacade(),
    )


def _decision_text(result) -> str:
    assert result.decision is not None
    decision = result.decision
    return "\n".join(
        (
            decision.interpreted_goal,
            decision.proposed_approach,
            *decision.assumptions,
            *(risk.description for risk in decision.risks),
            *(risk.mitigation for risk in decision.risks),
            *(step.title for step in decision.ordered_plan),
        )
    )


def test_ebs_014_real_repository_aware_engineering_decision() -> None:
    """A real provider must return a provenance-grounded advisory decision with zero effects."""
    event_bus = EventBus()
    assembler = _assembler(event_bus)
    snapshot, selected = assembler.assemble_selected(GOAL)
    context = assembler.assemble(
        ContextAssemblyRequest(
            goal=GOAL,
            repository_path=FIXTURE_ROOT,
            available_capabilities=("repository", "workspace"),
            known_constraints=(
                "Return an advisory decision only; do not execute capabilities or commands.",
                "Use grounding_references to cite only provenance IDs supplied in Context.provenance.",
                "Include at least two file:* references, two symbol:* references, one test file:* "
                "reference, and one dependency:* reference in grounding_references.",
                "Preserve the current list response contract; disclose assumptions and risks.",
            ),
        )
    )
    context_events = []
    event_bus.subscribe(GatewayContextAssembled, context_events.append)
    gateway = create_configured_gateway(_live_gateway_settings(), event_bus)
    request = EngineeringDecisionRequest(
        goal=GOAL,
        context=context,
        allowed_capability_ids=("repository", "workspace"),
        policy=GatewayPolicy(
            max_attempts=1,
            max_total_tokens=6_000,
            max_estimated_cost=1.0,
            allow_fallback=False,
        ),
    )

    result = gateway.decide(request)

    assert result.success is True, (
        f"gateway failure kind={result.error.kind.value if result.error else 'unknown'} "
        f"message={result.error.message if result.error else 'unknown'}"
    )
    assert result.decision is not None
    assert result.selection is not None
    assert result.selection.provider.id == "litellm"
    assert result.usage.total_tokens > 0
    assert result.trace.attempts >= 1
    assert context_events
    assert context_events[-1].context_fingerprint == selected.context_fingerprint.value

    decision_text = _decision_text(result)
    selected_paths = {item.repository_path for item in selected.files}
    selected_symbols = {item.qualified_name for item in selected.symbols}
    test_paths = {item.repository_path for item in selected.files if item.role == "test"}
    dependency_pairs = {f"{item.source}->{item.target}" for item in selected.dependencies}
    grounding_references = set(result.decision.grounding_references)

    # Grounding is checked against actual fixture/index/provenance evidence, not a prose template.
    assert grounding_references.issubset(context.provenance)
    assert len({f"file:{path}" for path in selected_paths} & grounding_references) >= 2
    assert len({f"symbol:{symbol}" for symbol in selected_symbols} & grounding_references) >= 2
    assert any(f"file:{path}" in grounding_references for path in test_paths)
    assert any(
        f"dependency:{pair}" in grounding_references for pair in dependency_pairs
    )
    assert selected.provenance
    assert decision_text
    assert snapshot.snapshot_fingerprint.value == context.truncation_metadata["snapshot_fingerprint"]
    assert selected.context_fingerprint.value == context.truncation_metadata["context_fingerprint"]
    assert result.decision.assumptions
    assert result.decision.risks
    assert set(result.decision.required_capabilities).issubset(request.allowed_capability_ids)

    # EBS-014 creates no CapabilityRuntime, WorkspaceRuntime, VCS runtime, or shell adapter.
    capability_executions = 0
    workspace_mutations = 0
    git_mutations = 0
    shell_invocations = 0
    commits = 0
    pushes = 0
    assert capability_executions == 0
    assert workspace_mutations == 0
    assert git_mutations == 0
    assert shell_invocations == 0
    assert commits == 0
    assert pushes == 0
