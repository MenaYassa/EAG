"""G2.4.4 observer-seam safety tests over the unchanged G2.3.2 default workflow fixtures."""

from __future__ import annotations

import pytest

from eag.chief.intelligence.gateway import DecisionToChangeProposalTranslator
from eag.chief.intelligence.gateway.mutation_workflow import (
    GovernedDecisionMutationWorkflow,
    GovernedWorkflowLifecycleRefused,
)
from tests.test_governed_decision_mutation import (
    StaticGateway,
    _decision,
    _request,
    _result,
    _runtime,
    _trusted_state,
    _write_article,
)


class _RefusingMutationObserver:
    def before_deciding(self, request) -> None:
        del request

    def before_proposing(self, request, result) -> None:
        del request, result

    def before_authorizing(self, proposal) -> None:
        del proposal

    def before_mutating(self, proposal, authorization) -> None:
        del proposal, authorization
        raise GovernedWorkflowLifecycleRefused("deterministic state gate refused mutation")


def test_observer_refusal_prevents_mutation_before_existing_runtime_is_called(tmp_path) -> None:
    before = _write_article(tmp_path)
    request = _request()
    workflow = GovernedDecisionMutationWorkflow(
        gateway=StaticGateway(_result(_decision())),
        translator=DecisionToChangeProposalTranslator(),
        mutation_runtime=_runtime(tmp_path),
    )

    with pytest.raises(GovernedWorkflowLifecycleRefused, match="refused mutation"):
        workflow.execute(
            request,
            run_id="run-1",
            trusted_state=_trusted_state(tmp_path),
            observer=_RefusingMutationObserver(),
        )

    assert (tmp_path / "article.py").read_text(encoding="utf-8") == before
