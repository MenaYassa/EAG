"""Pure fail-closed assessment for G2.4.21 construction work-order evidence."""

from __future__ import annotations

from datetime import UTC

from eag.governed_composition import RuntimeCompositionDisposition
from eag.governed_construction_work_order.models import (
    _SUPPORTED_CAPABILITIES,
    ConstructionWorkOrderAssessment,
    ConstructionWorkOrderAssessmentRequest,
    ConstructionWorkOrderDisposition,
    ConstructionWorkOrderFinding,
    ConstructionWorkOrderFindingCode,
    ConstructionWorkOrderProfile,
)
from eag.governed_destination_contract import DestinationContractDisposition
from eag.governed_outcome_policy import OutcomePolicyDisposition
from eag.governed_workspace import WorkspaceCustodyDisposition


class ConstructionWorkOrderAssessor:
    """Assess static construction intent evidence without workspace or command authority."""

    def assess(
        self,
        *,
        assessment_id: str,
        request: ConstructionWorkOrderAssessmentRequest,
    ) -> ConstructionWorkOrderAssessment:
        """Return immutable evidence only; never provision, mutate, execute, or recover."""
        if not isinstance(request, ConstructionWorkOrderAssessmentRequest):
            raise TypeError("request must be a ConstructionWorkOrderAssessmentRequest")

        findings: list[ConstructionWorkOrderFinding] = []
        references = _references(request)
        _validate_workspace_custody(request, findings)
        _validate_runtime_composition(request, findings)
        _validate_destination_contract_evidence(request, findings)
        _validate_outcome_policy_evidence(request, findings)
        _validate_work_order_policy(request, findings)
        return _assessment(
            assessment_id=assessment_id,
            request=request,
            findings=findings,
            references=references,
        )


def _references(request: ConstructionWorkOrderAssessmentRequest) -> list[str]:
    custody = request.workspace_custody_attestation
    composition = request.runtime_composition_attestation
    contract_assessment = request.destination_contract_assessment
    outcome_assessment = request.outcome_policy_assessment
    work_order = request.work_order
    return [
        f"workspace_custody:{custody.attestation_id}:{custody.binding_digest}",
        f"runtime_composition:{composition.attestation_id}:{composition.binding_digest}",
        f"destination_contract_request:{request.destination_contract_request.assessment_request_id}:{request.destination_contract_request.request_digest}",
        f"destination_contract_assessment:{contract_assessment.assessment_id}:{contract_assessment.assessment_digest}",
        f"outcome_policy_request:{request.outcome_policy_request.assessment_request_id}:{request.outcome_policy_request.request_digest}",
        f"outcome_policy_assessment:{outcome_assessment.assessment_id}:{outcome_assessment.assessment_digest}",
        f"construction_work_order:{work_order.work_order_id}:{work_order.work_order_digest}",
    ]


def _validate_workspace_custody(
    request: ConstructionWorkOrderAssessmentRequest,
    findings: list[ConstructionWorkOrderFinding],
) -> None:
    custody = request.workspace_custody_attestation
    work_order = request.work_order
    if custody.disposition is not WorkspaceCustodyDisposition.ATTESTED:
        findings.append(_finding(ConstructionWorkOrderFindingCode.WORKSPACE_CUSTODY_INVALID, custody.attestation_id))
    if (
        custody.attestation_id != work_order.workspace_custody_attestation_id
        or custody.binding_digest != work_order.workspace_custody_binding_digest
    ):
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.WORKSPACE_CUSTODY_BINDING_MISMATCH, work_order.work_order_id)
        )
    if custody.workspace_root_identity != work_order.workspace_root_identity or custody.workspace_id != work_order.workspace_id:
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.WORKSPACE_BINDING_MISMATCH, work_order.workspace_id)
        )
    if custody.execution_id != work_order.execution_id or custody.run_id != work_order.run_id:
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.WORKSPACE_BINDING_MISMATCH, work_order.execution_id)
        )


def _validate_runtime_composition(
    request: ConstructionWorkOrderAssessmentRequest,
    findings: list[ConstructionWorkOrderFinding],
) -> None:
    composition = request.runtime_composition_attestation
    manifest = composition.manifest
    work_order = request.work_order
    if composition.disposition is not RuntimeCompositionDisposition.ATTESTED:
        findings.append(_finding(ConstructionWorkOrderFindingCode.RUNTIME_COMPOSITION_INVALID, composition.attestation_id))
    if (
        composition.attestation_id != work_order.runtime_composition_attestation_id
        or composition.binding_digest != work_order.runtime_composition_binding_digest
    ):
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.RUNTIME_COMPOSITION_BINDING_MISMATCH, work_order.work_order_id)
        )
    if manifest.execution_id != work_order.execution_id or manifest.run_id != work_order.run_id:
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.RUNTIME_COMPOSITION_BINDING_MISMATCH, work_order.execution_id)
        )


def _validate_destination_contract_evidence(
    request: ConstructionWorkOrderAssessmentRequest,
    findings: list[ConstructionWorkOrderFinding],
) -> None:
    contract_request = request.destination_contract_request
    contract_assessment = request.destination_contract_assessment
    contract = contract_request.contract
    work_order = request.work_order
    if contract_assessment.disposition is not DestinationContractDisposition.CONTRACT_ATTESTED:
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.CONTRACT_ASSESSMENT_INVALID, contract_assessment.assessment_id)
        )
    if contract_assessment.contract_id != contract.destination_contract_id:
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH, "contract_assessment_id")
        )
    if contract_assessment.assessed_request_id != contract_request.assessment_request_id:
        findings.append(
            _finding(
                ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH,
                "contract_assessed_request_id",
            )
        )
    if contract_assessment.assessed_request_digest != contract_request.request_digest:
        findings.append(
            _finding(
                ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH,
                "contract_assessed_request_digest",
            )
        )
    if (
        work_order.destination_contract_id != contract.destination_contract_id
        or work_order.destination_contract_digest != contract.contract_digest
        or work_order.destination_contract_assessment_id != contract_assessment.assessment_id
        or work_order.destination_contract_assessment_digest != contract_assessment.assessment_digest
    ):
        findings.append(_finding(ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH, work_order.work_order_id))


def _validate_outcome_policy_evidence(
    request: ConstructionWorkOrderAssessmentRequest,
    findings: list[ConstructionWorkOrderFinding],
) -> None:
    outcome_request = request.outcome_policy_request
    outcome_assessment = request.outcome_policy_assessment
    work_order = request.work_order
    policy = outcome_request.policy
    if outcome_assessment.disposition is not OutcomePolicyDisposition.OUTCOME_POLICY_ATTESTED:
        findings.append(
            _finding(
                ConstructionWorkOrderFindingCode.OUTCOME_POLICY_ASSESSMENT_INVALID,
                outcome_assessment.assessment_id,
            )
        )
    if outcome_assessment.assessed_request_id != outcome_request.assessment_request_id:
        findings.append(
            _finding(
                ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "outcome_policy_assessed_request_id",
            )
        )
    if outcome_assessment.assessed_request_digest != outcome_request.request_digest:
        findings.append(
            _finding(
                ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
                "outcome_policy_assessed_request_digest",
            )
        )
    if outcome_request.destination_contract_request.request_digest != request.destination_contract_request.request_digest:
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH, "destination_contract_request")
        )
    if outcome_request.destination_contract_assessment.assessment_digest != request.destination_contract_assessment.assessment_digest:
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH, "destination_contract_assessment")
        )
    if (
        work_order.outcome_policy_id != policy.outcome_policy_id
        or work_order.outcome_policy_digest != policy.policy_digest
        or work_order.outcome_policy_assessment_id != outcome_assessment.assessment_id
        or work_order.outcome_policy_assessment_digest != outcome_assessment.assessment_digest
    ):
        findings.append(
            _finding(ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH, work_order.work_order_id)
        )


def _validate_work_order_policy(
    request: ConstructionWorkOrderAssessmentRequest,
    findings: list[ConstructionWorkOrderFinding],
) -> None:
    work_order = request.work_order
    if request.timestamp.astimezone(UTC) >= work_order.expires_at:
        findings.append(_finding(ConstructionWorkOrderFindingCode.WORK_ORDER_EXPIRED, work_order.work_order_id))
    if work_order.construction_profile != ConstructionWorkOrderProfile.DISPOSABLE_LOCAL_CONSTRUCTION_WORK_ORDER_V1.value:
        findings.append(
            _finding(
                ConstructionWorkOrderFindingCode.UNSUPPORTED_CONSTRUCTION_PROFILE,
                work_order.construction_profile,
            )
        )
    if work_order.declared_capability_ids != _SUPPORTED_CAPABILITIES:
        findings.append(
            _finding(
                ConstructionWorkOrderFindingCode.UNSUPPORTED_CAPABILITY_DECLARATION,
                work_order.work_order_id,
            )
        )
    if (
        work_order.max_file_actions > 32
        or work_order.max_total_bytes > 1_000_000
        or work_order.max_command_actions != 0
    ):
        findings.append(_finding(ConstructionWorkOrderFindingCode.INVALID_STATIC_LIMITS, work_order.work_order_id))


def _assessment(
    *,
    assessment_id: str,
    request: ConstructionWorkOrderAssessmentRequest,
    findings: list[ConstructionWorkOrderFinding],
    references: list[str],
) -> ConstructionWorkOrderAssessment:
    disposition = _disposition_for(findings)
    recommendations = (
        ("construction_work_order_evidence_only",)
        if disposition is ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED
        else ("stop_without_automatic_progress",)
    )
    ordered_findings = tuple(sorted(findings, key=lambda item: (item.code.value, item.evidence_reference)))
    return ConstructionWorkOrderAssessment.issue(
        assessment_id=assessment_id,
        assessed_request=request,
        workspace_id=request.work_order.workspace_id,
        work_order_id=request.work_order.work_order_id,
        disposition=disposition,
        findings=ordered_findings,
        evidence_refs=tuple(sorted(set(references))),
        recommendations=recommendations,
        timestamp=request.timestamp,
    )


def _disposition_for(
    findings: list[ConstructionWorkOrderFinding],
) -> ConstructionWorkOrderDisposition:
    if not findings:
        return ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED
    if any(item.code is ConstructionWorkOrderFindingCode.UNSUPPORTED_CONSTRUCTION_PROFILE for item in findings):
        return ConstructionWorkOrderDisposition.UNSUPPORTED_CONSTRUCTION_PROFILE
    return ConstructionWorkOrderDisposition.NOT_ATTESTED


def _finding(
    code: ConstructionWorkOrderFindingCode,
    evidence_reference: str,
) -> ConstructionWorkOrderFinding:
    return ConstructionWorkOrderFinding(code=code, evidence_reference=evidence_reference)


__all__ = ["ConstructionWorkOrderAssessor"]
