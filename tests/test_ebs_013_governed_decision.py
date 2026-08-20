"""EBS-013: Governed Engineering Decision live-provider benchmark boundary."""

from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from eag.chief.intelligence.gateway import (
    EngineeringContext,
    EngineeringDecisionRequest,
    GatewayPolicy,
    create_configured_gateway,
)
from eag.config.settings import GatewaySettings
from eag.events import EventBus

pytestmark = pytest.mark.integration


def _live_gateway_settings() -> GatewaySettings:
    """Resolve only explicitly configured live-provider credentials for EBS-013."""
    if os.getenv("EAG_EBS013_LIVE") != "1":
        pytest.skip("EBS-013 requires explicit EAG_EBS013_LIVE=1 opt-in.")
    api_key = os.getenv("EAG_EBS013_API_KEY") or os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("EAG_EBS013_API_BASE") or os.getenv("OPENAI_API_BASE")
    if not api_key or not api_base:
        pytest.skip("No live EBS-013 provider credentials are configured.")
    return GatewaySettings(
        enabled=True,
        provider_id="litellm",
        model_id=os.getenv("EAG_EBS013_MODEL", "gpt-5-mini"),
        api_key=SecretStr(api_key),
        api_base=api_base,
        timeout_ms=30_000,
        max_attempts=1,
        max_total_tokens=6_000,
        max_estimated_cost=1.0,
        allow_fallback=False,
    )


def test_ebs_013_real_governed_engineering_decision() -> None:
    """A real routed provider must return a validated advisory decision without effects."""
    gateway = create_configured_gateway(_live_gateway_settings(), EventBus())
    request = EngineeringDecisionRequest(
        goal="Plan a safe documentation-only repository change.",
        context=EngineeringContext(
            repository_summary="Controlled EBS-013 context; no workspace is supplied.",
            available_capabilities=("repository", "workspace"),
            known_constraints=(
                "Do not execute capabilities.",
                "Do not mutate workspace or Git state.",
                "Return a decision only.",
            ),
            provenance={"benchmark": "EBS-013 controlled fixture"},
        ),
        allowed_capability_ids=("repository", "workspace"),
        policy=GatewayPolicy(
            max_attempts=1,
            max_total_tokens=6_000,
            max_estimated_cost=1.0,
            allow_fallback=False,
        ),
    )

    result = gateway.decide(request)

    assert result.success is True
    assert result.decision is not None
    assert result.selection is not None
    assert result.selection.provider.id == "litellm"
    assert result.usage.total_tokens > 0
    assert result.trace.attempts >= 1
    assert result.decision.risks
    assert 0.0 <= result.decision.confidence <= 1.0
    assert set(result.decision.required_capabilities).issubset(request.allowed_capability_ids)
    assert result.decision.ordered_plan
    for index, step in enumerate(result.decision.ordered_plan):
        prior_steps = {prior.step_id for prior in result.decision.ordered_plan[:index]}
        assert set(step.dependencies).issubset(prior_steps)

    # EBS-013 creates no CapabilityRuntime, workspace, repository, or Git runtime.
    # A passing result is a validated decision only, never an effectful execution.
    assert result.decision is not None
