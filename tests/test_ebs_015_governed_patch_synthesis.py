"""Deterministic G2.3.1 EBS-015 contract; intentionally has no provider or LLM path."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from eag.events import EventBus
from eag.mutation import (
    ChangeProposal,
    GovernedMutationRuntime,
    MutationAuthorizer,
    MutationOperation,
    MutationPolicyValidator,
    MutationPrecondition,
    MutationResult,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ebs_015_governed_patch"


def test_ebs_015_deterministic_governed_patch_contract(tmp_path: Path) -> None:
    """One explicitly authorized fixture file changes; no shell, Git, network, or provider is used."""
    workspace = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, workspace)
    target = workspace / "article.py"
    before = target.read_text(encoding="utf-8")
    policy = MutationPolicyValidator()
    runtime = GovernedMutationRuntime(
        workspace_root=workspace,
        policy=policy,
        authorizer=MutationAuthorizer(policy_version=policy.policy_version),
        event_bus=EventBus(),
    )
    proposed = before.replace('return {"title": title}', 'return {"title": title, "status": "draft"}')
    proposal = ChangeProposal(
        run_id="ebs-015",
        decision_id="deterministic-contract",
        target_path="article.py",
        operation=MutationOperation.MODIFY_FILE,
        content=proposed,
        precondition=MutationPrecondition(
            expect_exists=True,
            expected_fingerprint=hashlib.sha256(before.encode()).hexdigest(),
        ),
        reason="add deterministic status field",
        provenance_ids=("file:article.py", "symbol:article_payload"),
    )

    receipt = runtime.execute(proposal)

    assert receipt.result is MutationResult.COMPLETED
    assert receipt.verification_passed is True
    assert receipt.target_path == "article.py"
    assert target.read_text(encoding="utf-8") == proposed
    assert len(tuple(workspace.iterdir())) == 1
    assert receipt.authorization_id is not None
    assert receipt.rollback_performed is False
