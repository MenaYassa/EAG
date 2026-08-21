"""Deterministic G2.3.2 decision-to-proposal and governed mutation coverage."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from eag.chief.intelligence.gateway import (
    DecisionToChangeProposalTranslator,
    EngineeringContext,
    EngineeringDecision,
    EngineeringDecisionRequest,
    EngineeringDecisionResult,
    EngineeringRisk,
    GatewayError,
    GatewayErrorKind,
    GatewayTrace,
    GovernedDecisionMutationWorkflow,
    GovernedMutationFailureStage,
    MutationIntent,
    MutationIntentPolicy,
    MutationTranslationError,
    PolicyValidationError,
    PolicyViolationCode,
    PreservationRequirement,
    ProposedPlanStep,
    RiskSeverity,
    TrustedWorkspaceState,
    parse_engineering_decision,
    validate_decision_policy,
)
from eag.context import ContextSecurityPolicy
from eag.events import EventBus
from eag.mutation import (
    GovernedMutationRuntime,
    MutationAuthorizer,
    MutationPolicySettings,
    MutationPolicyValidator,
    MutationResult,
)


@dataclass
class StaticGateway:
    """Controlled gateway double for composing an already governed result."""

    result: EngineeringDecisionResult
    calls: int = 0

    def decide(self, request: EngineeringDecisionRequest) -> EngineeringDecisionResult:
        del request
        self.calls += 1
        return self.result


def _request(
    *,
    max_content_bytes: int = 64_000,
    preservation_requirements: tuple[PreservationRequirement, ...] = (),
) -> EngineeringDecisionRequest:
    return EngineeringDecisionRequest(
        goal="Change only the controlled article fixture.",
        context=EngineeringContext(
            repository_identity="g2.3.2-fixture",
            provenance={
                "file:article.py": "source",
                "symbol:article_payload": "index",
                "snapshot_fingerprint": "snapshot-123",
                "context_fingerprint": "context-123",
            },
            truncation_metadata={
                "snapshot_fingerprint": "snapshot-123",
                "context_fingerprint": "context-123",
            },
        ),
        allowed_capability_ids=("governed_mutation",),
        mutation_intent_policy=MutationIntentPolicy(
            max_content_bytes=max_content_bytes,
            preservation_requirements=preservation_requirements,
        ),
    )


def _decision(
    *,
    target_path: str = "article.py",
    operation: str = "modify_file",
    content: str = 'def article_payload(title: str) -> dict[str, str]:\n    return {"title": title, "status": "draft"}\n',
    intent_count: int = 1,
    intent_dependencies: tuple[str, ...] = (),
    step_dependencies: tuple[str, ...] = (),
    step_id: str = "mutate-article",
    capability_id: str = "governed_mutation",
    preservation_requirement_ids: tuple[str, ...] = (),
) -> EngineeringDecision:
    intents = tuple(
        MutationIntent(
            intent_id=f"intent-{index}",
            step_id=step_id,
            target_path=target_path,
            operation=operation,
            proposed_content=content,
            rationale="Update the controlled article payload only.",
            grounding_references=("file:article.py", "symbol:article_payload"),
            dependencies=intent_dependencies,
            preservation_requirement_ids=preservation_requirement_ids,
        )
        for index in range(intent_count)
    )
    return EngineeringDecision(
        interpreted_goal="Update the controlled article payload.",
        assumptions=("The fixture target exists.",),
        proposed_approach="Apply one full-file replacement to the fixture target.",
        ordered_plan=(
            ProposedPlanStep(
                step_id=step_id,
                title="Mutate controlled article fixture",
                capability_id=capability_id,
                dependencies=step_dependencies,
                expected_evidence=("One verified mutation receipt.",),
            ),
        ),
        required_capabilities=(capability_id,),
        risks=(
            EngineeringRisk(
                description="The target might be stale.",
                severity=RiskSeverity.MEDIUM,
                mitigation="Use the governed precondition and authorization boundary.",
            ),
        ),
        confidence=0.9,
        grounding_references=("file:article.py", "symbol:article_payload"),
        mutation_intents=intents,
    )


def _result(decision: EngineeringDecision) -> EngineeringDecisionResult:
    return EngineeringDecisionResult(
        success=True,
        decision=decision,
        trace=GatewayTrace(trace_id="trace-1", request_id="request-1"),
    )


def _trusted_state(workspace: Path) -> TrustedWorkspaceState:
    return TrustedWorkspaceState(
        workspace_root=workspace,
        repository_snapshot_fingerprint="snapshot-123",
        context_fingerprint="context-123",
        policy_version="1.0",
        sensitivity_policy=ContextSecurityPolicy(),
    )


def _runtime(workspace: Path, *, authorizer_policy_version: str | None = None, max_content_bytes: int = 64_000) -> GovernedMutationRuntime:
    policy = MutationPolicyValidator(settings=MutationPolicySettings(max_content_bytes=max_content_bytes))
    return GovernedMutationRuntime(
        workspace_root=workspace,
        policy=policy,
        authorizer=MutationAuthorizer(policy_version=authorizer_policy_version or policy.policy_version),
        event_bus=EventBus(),
    )


def _write_article(workspace: Path) -> str:
    before = 'def article_payload(title: str) -> dict[str, str]:\n    return {"title": title}\n'
    (workspace / "article.py").write_text(before, encoding="utf-8")
    return before


def test_valid_governed_decision_translates_to_deterministic_proposal(tmp_path: Path) -> None:
    before = _write_article(tmp_path)
    request = _request()
    decision = _decision()
    validate_decision_policy(decision, request)

    proposal = DecisionToChangeProposalTranslator().translate(
        _result(decision), request, run_id="run-1", trusted_state=_trusted_state(tmp_path)
    )

    assert proposal.run_id == "run-1"
    assert proposal.decision_id == decision.digest
    assert proposal.target_path == "article.py"
    assert proposal.precondition.expected_fingerprint
    assert proposal.precondition.expected_fingerprint != proposal.content_fingerprint
    assert proposal.expected_postcondition.expected_fingerprint == proposal.content_fingerprint
    assert proposal.provenance_ids == ("file:article.py", "symbol:article_payload")
    assert proposal.repository_snapshot_fingerprint == "snapshot-123"
    assert proposal.context_fingerprint == "context-123"
    assert proposal.authorization_metadata["policy_version"] == "1.0"
    assert proposal.content != before


def test_repeated_identical_translation_has_identical_proposal_digest(tmp_path: Path) -> None:
    _write_article(tmp_path)
    request = _request()
    result = _result(_decision())
    translator = DecisionToChangeProposalTranslator()

    first = translator.translate(result, request, run_id="run-1", trusted_state=_trusted_state(tmp_path))
    second = translator.translate(result, request, run_id="run-1", trusted_state=_trusted_state(tmp_path))

    assert first.digest == second.digest
    assert first.workspace_fingerprint == second.workspace_fingerprint


def test_translation_performs_zero_mutation(tmp_path: Path) -> None:
    before = _write_article(tmp_path)

    DecisionToChangeProposalTranslator().translate(
        _result(_decision()), _request(), run_id="run-1", trusted_state=_trusted_state(tmp_path)
    )

    assert (tmp_path / "article.py").read_text(encoding="utf-8") == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["article.py"]


@pytest.mark.parametrize(
    "intent_count",
    [0, 2],
)
def test_policy_rejects_missing_or_multiple_mutation_intents(intent_count: int) -> None:
    with pytest.raises(PolicyValidationError) as raised:
        validate_decision_policy(_decision(intent_count=intent_count), _request())

    assert raised.value.violation.code == PolicyViolationCode.MUTATION_INTENT_COUNT_INVALID


def test_policy_rejects_mutation_dependencies() -> None:
    with pytest.raises(PolicyValidationError) as raised:
        validate_decision_policy(_decision(intent_dependencies=("prior",)), _request())

    assert raised.value.violation.code == PolicyViolationCode.MUTATION_INTENT_STEP_DEPENDENCIES_FORBIDDEN


def test_policy_rejects_unsupported_operation() -> None:
    with pytest.raises(PolicyValidationError) as raised:
        validate_decision_policy(_decision(operation="delete_file"), _request())

    assert raised.value.violation.code == PolicyViolationCode.MUTATION_INTENT_OPERATION_UNSUPPORTED


@pytest.mark.parametrize("target_path", ["/tmp/outside.py", "../outside.py", "folder\\outside.py"])
def test_policy_rejects_invalid_mutation_targets(target_path: str) -> None:
    with pytest.raises(PolicyValidationError) as raised:
        validate_decision_policy(_decision(target_path=target_path), _request())

    assert raised.value.violation.code == PolicyViolationCode.MUTATION_INTENT_TARGET_INVALID


def test_schema_rejects_provider_controlled_workspace_or_fingerprint() -> None:
    payload = {
        "interpreted_goal": "mutate fixture",
        "assumptions": ["fixture exists"],
        "proposed_approach": "one mutation",
        "ordered_plan": [
            {
                "step_id": "mutate-article",
                "title": "mutate",
                "capability_id": "governed_mutation",
                "dependencies": [],
                "expected_evidence": ["receipt"],
            }
        ],
        "required_capabilities": ["governed_mutation"],
        "risks": [{"description": "stale", "severity": "medium", "mitigation": "precondition"}],
        "confidence": 0.9,
        "grounding_references": ["file:article.py"],
        "mutation_intents": [
            {
                "intent_id": "intent-1",
                "step_id": "mutate-article",
                "target_path": "article.py",
                "operation": "modify_file",
                "proposed_content": "safe",
                "rationale": "safe",
                "grounding_references": ["file:article.py"],
                "dependencies": [],
                "schema_version": "1.0",
                "workspace_root": "/tmp/provider-controlled",
                "repository_snapshot_fingerprint": "provider-controlled",
            }
        ],
        "schema_version": "1.0",
    }

    with pytest.raises(ValueError, match="fields do not match schema"):
        parse_engineering_decision(json.dumps(payload))


def test_translator_inserts_trusted_binding_values(tmp_path: Path) -> None:
    _write_article(tmp_path)
    proposal = DecisionToChangeProposalTranslator().translate(
        _result(_decision()), _request(), run_id="trusted-run", trusted_state=_trusted_state(tmp_path)
    )

    assert proposal.run_id == "trusted-run"
    assert proposal.repository_snapshot_fingerprint == "snapshot-123"
    assert proposal.context_fingerprint == "context-123"
    assert proposal.workspace_fingerprint == _trusted_state(tmp_path).workspace_fingerprint
    assert proposal.authorization_metadata["policy_version"] == "1.0"


def test_translator_rejects_inconsistent_trusted_fingerprint_binding(tmp_path: Path) -> None:
    _write_article(tmp_path)
    mismatched = TrustedWorkspaceState(
        workspace_root=tmp_path,
        repository_snapshot_fingerprint="different-snapshot",
        context_fingerprint="context-123",
        policy_version="1.0",
        sensitivity_policy=ContextSecurityPolicy(),
    )

    with pytest.raises(MutationTranslationError, match="snapshot binding"):
        DecisionToChangeProposalTranslator().translate(
            _result(_decision()), _request(), run_id="run-1", trusted_state=mismatched
        )


def test_translator_rejects_unsuccessful_gateway_result_without_workspace_effect(tmp_path: Path) -> None:
    before = _write_article(tmp_path)
    failed = EngineeringDecisionResult(
        success=False,
        error=GatewayError(kind=GatewayErrorKind.PROVIDER_TIMEOUT, message="timeout"),
        trace=GatewayTrace(trace_id="trace", request_id="request"),
    )

    with pytest.raises(MutationTranslationError, match="successful governed decision"):
        DecisionToChangeProposalTranslator().translate(
            failed, _request(), run_id="run-1", trusted_state=_trusted_state(tmp_path)
        )

    assert (tmp_path / "article.py").read_text(encoding="utf-8") == before


def test_existing_mutation_policy_rejects_translated_oversized_content(tmp_path: Path) -> None:
    _write_article(tmp_path)
    request = _request(max_content_bytes=64_000)
    decision = _decision(content="x" * 64)
    validate_decision_policy(decision, request)
    proposal = DecisionToChangeProposalTranslator().translate(
        _result(decision), request, run_id="run-1", trusted_state=_trusted_state(tmp_path)
    )
    workflow = GovernedDecisionMutationWorkflow(
        gateway=StaticGateway(_result(decision)),
        translator=DecisionToChangeProposalTranslator(),
        mutation_runtime=_runtime(tmp_path, max_content_bytes=8),
    )

    outcome = workflow.execute(request, run_id="run-1", trusted_state=_trusted_state(tmp_path))

    assert proposal.content_bytes > 8
    assert outcome.receipt is not None
    assert outcome.receipt.result is MutationResult.REJECTED
    assert outcome.failure_stage is GovernedMutationFailureStage.POLICY_REJECTED


def test_existing_authorization_boundary_rejects_tampered_authorization(tmp_path: Path) -> None:
    _write_article(tmp_path)
    request = _request()
    decision = _decision()
    runtime = _runtime(tmp_path)
    proposal = DecisionToChangeProposalTranslator().translate(
        _result(decision), request, run_id="run-1", trusted_state=_trusted_state(tmp_path)
    )
    validated = runtime.validate(proposal)
    authorization = runtime.authorize(validated)

    receipt = runtime.mutate(validated, replace(authorization, policy_version="mismatched"))

    assert receipt.result is MutationResult.REJECTED
    assert receipt.failure_code == "authorization_mismatch"


def test_successful_workflow_reaches_existing_mutation_runtime_and_receipt(tmp_path: Path) -> None:
    before = _write_article(tmp_path)
    request = _request()
    decision = _decision()
    gateway = StaticGateway(_result(decision))
    workflow = GovernedDecisionMutationWorkflow(
        gateway=gateway,
        translator=DecisionToChangeProposalTranslator(),
        mutation_runtime=_runtime(tmp_path),
    )

    outcome = workflow.execute(request, run_id="run-1", trusted_state=_trusted_state(tmp_path))

    assert gateway.calls == 1
    assert outcome.success is True
    assert outcome.proposal is not None
    assert outcome.receipt is not None
    assert outcome.receipt.result is MutationResult.COMPLETED
    assert outcome.receipt.verification_passed is True
    assert (tmp_path / "article.py").read_text(encoding="utf-8") != before
    assert "status" in (tmp_path / "article.py").read_text(encoding="utf-8")


def test_workflow_preserves_gateway_timeout_as_distinct_non_mutation_failure(tmp_path: Path) -> None:
    before = _write_article(tmp_path)
    timeout = EngineeringDecisionResult(
        success=False,
        error=GatewayError(kind=GatewayErrorKind.PROVIDER_TIMEOUT, message="timeout"),
        trace=GatewayTrace(trace_id="trace", request_id="request"),
    )
    workflow = GovernedDecisionMutationWorkflow(
        gateway=StaticGateway(timeout),
        translator=DecisionToChangeProposalTranslator(),
        mutation_runtime=_runtime(tmp_path),
    )

    outcome = workflow.execute(_request(), run_id="run-1", trusted_state=_trusted_state(tmp_path))

    assert outcome.proposal is None
    assert outcome.receipt is None
    assert outcome.failure_stage is GovernedMutationFailureStage.PROVIDER_TIMEOUT
    assert (tmp_path / "article.py").read_text(encoding="utf-8") == before


def test_create_file_intent_translates_and_reaches_existing_mutation_runtime(tmp_path: Path) -> None:
    request = _request()
    content = 'VALUE = "created by governed mutation"\n'
    decision = _decision(
        target_path="created.py",
        operation="create_file",
        content=content,
    )
    workflow = GovernedDecisionMutationWorkflow(
        gateway=StaticGateway(_result(decision)),
        translator=DecisionToChangeProposalTranslator(),
        mutation_runtime=_runtime(tmp_path),
    )

    outcome = workflow.execute(request, run_id="run-create", trusted_state=_trusted_state(tmp_path))

    assert outcome.success is True
    assert outcome.proposal is not None
    assert outcome.proposal.precondition.expect_exists is False
    assert outcome.receipt is not None
    assert outcome.receipt.result is MutationResult.COMPLETED
    assert (tmp_path / "created.py").read_text(encoding="utf-8") == content


@pytest.mark.parametrize("missing_field", ["target_path", "proposed_content"])
def test_schema_rejects_missing_required_mutation_intent_fields(missing_field: str) -> None:
    intent = {
        "intent_id": "intent-1",
        "step_id": "mutate-article",
        "target_path": "article.py",
        "operation": "modify_file",
        "proposed_content": "safe replacement",
        "rationale": "safe",
        "grounding_references": ["file:article.py"],
        "dependencies": [],
        "schema_version": "1.0",
    }
    del intent[missing_field]
    payload = {
        "interpreted_goal": "mutate fixture",
        "assumptions": ["fixture exists"],
        "proposed_approach": "one mutation",
        "ordered_plan": [
            {
                "step_id": "mutate-article",
                "title": "mutate",
                "capability_id": "governed_mutation",
                "dependencies": [],
                "expected_evidence": ["receipt"],
            }
        ],
        "required_capabilities": ["governed_mutation"],
        "risks": [{"description": "stale", "severity": "medium", "mitigation": "precondition"}],
        "confidence": 0.9,
        "grounding_references": ["file:article.py"],
        "mutation_intents": [intent],
        "schema_version": "1.0",
    }

    with pytest.raises(ValueError, match="fields do not match schema"):
        parse_engineering_decision(json.dumps(payload))


PRESERVED_MODULE_PREFIX = '"""Controlled preserved module contract."""\n\n'


def _preservation_requirement() -> PreservationRequirement:
    return PreservationRequirement(
        requirement_id="module-docstring",
        required_prefix=PRESERVED_MODULE_PREFIX,
    )


def _write_preserved_article(workspace: Path) -> str:
    before = (
        f"{PRESERVED_MODULE_PREFIX}"
        "def article_payload(title: str) -> dict[str, str]:\n"
        '    return {"title": title}\n'
    )
    (workspace / "article.py").write_text(before, encoding="utf-8")
    return before


def test_complete_bound_full_replacement_is_accepted_and_verified(tmp_path: Path) -> None:
    _write_preserved_article(tmp_path)
    requirement = _preservation_requirement()
    request = _request(preservation_requirements=(requirement,))
    content = (
        f"{PRESERVED_MODULE_PREFIX}"
        "def article_payload(title: str) -> dict[str, str]:\n"
        '    return {"title": title, "status": "draft"}\n'
    )
    decision = _decision(
        content=content,
        preservation_requirement_ids=(requirement.requirement_id,),
    )
    validate_decision_policy(decision, request)
    workflow = GovernedDecisionMutationWorkflow(
        gateway=StaticGateway(_result(decision)),
        translator=DecisionToChangeProposalTranslator(),
        mutation_runtime=_runtime(tmp_path),
    )

    outcome = workflow.execute(request, run_id="preserve-complete", trusted_state=_trusted_state(tmp_path))

    assert outcome.success is True
    assert outcome.receipt is not None
    assert outcome.receipt.result is MutationResult.COMPLETED
    assert (tmp_path / "article.py").read_text(encoding="utf-8") == content


def test_protected_prefix_omission_is_rejected_before_authorization_or_mutation(tmp_path: Path) -> None:
    before = _write_preserved_article(tmp_path)
    requirement = _preservation_requirement()
    request = _request(preservation_requirements=(requirement,))
    incomplete = 'def article_payload(title: str) -> dict[str, str]:\n    return {"title": title, "status": "draft"}\n'
    decision = _decision(
        content=incomplete,
        preservation_requirement_ids=(requirement.requirement_id,),
    )
    validate_decision_policy(decision, request)
    event_bus = EventBus()
    authorized: list[object] = []
    from eag.mutation.events import MutationAuthorized

    event_bus.subscribe(MutationAuthorized, authorized.append)
    policy = MutationPolicyValidator()
    workflow = GovernedDecisionMutationWorkflow(
        gateway=StaticGateway(_result(decision)),
        translator=DecisionToChangeProposalTranslator(),
        mutation_runtime=GovernedMutationRuntime(
            workspace_root=tmp_path,
            policy=policy,
            authorizer=MutationAuthorizer(policy_version=policy.policy_version),
            event_bus=event_bus,
        ),
    )

    outcome = workflow.execute(request, run_id="preserve-reject", trusted_state=_trusted_state(tmp_path))

    assert outcome.success is False
    assert outcome.proposal is None
    assert outcome.receipt is None
    assert outcome.failure_stage is GovernedMutationFailureStage.TRANSLATION_FAILURE
    assert outcome.translation_violation is not None
    assert outcome.translation_violation.code.value == "preservation_requirement_invalid"
    assert authorized == []
    assert (tmp_path / "article.py").read_text(encoding="utf-8") == before


def test_gateway_policy_rejects_missing_required_preservation_binding() -> None:
    requirement = _preservation_requirement()
    request = _request(preservation_requirements=(requirement,))

    with pytest.raises(PolicyValidationError) as raised:
        validate_decision_policy(_decision(), request)

    assert raised.value.violation.code == PolicyViolationCode.MUTATION_INTENT_PRESERVATION_BINDING_MISSING
