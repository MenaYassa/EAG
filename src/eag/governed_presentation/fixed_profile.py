"""Thin G2.4.23 terminal presentation around accepted fixed-profile boundaries.

This module relays a caller-selected token to G2.4.21 and renders immutable evidence
and receipt facts. It does not define source content, materialize a plan, inspect a
workspace, or create filesystem effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from eag.governed_composition import RuntimeCompositionAttestation
from eag.governed_construction_work_order import (
    ConstructionWorkOrderEvidenceError,
    FixedConstructionIntentDisposition,
    FixedConstructionIntentProfile,
    FixedProfileConstructionIntentAssessment,
    FixedProfileConstructionIntentAssessor,
    FixedProfileConstructionIntentIssuer,
    FixedProfileConstructionIntentRequest,
    IntentBoundConstructionWorkOrderAssessment,
    IntentBoundConstructionWorkOrderAssessmentRequest,
    IntentBoundConstructionWorkOrderAssessor,
    IntentBoundLocalConstructionWorkOrderEvidence,
    IntentBoundWorkOrderDisposition,
)
from eag.governed_file_construction import (
    ConstructionBatchDisposition,
    ConstructionBatchReceipt,
    FixedProfileConstructionAuthorization,
    FixedProfileWorkspaceFileConstructor,
)
from eag.governed_workspace import (
    WorkspaceCustodyGate,
    WorkspaceCustodyRequest,
    WorkspaceCustodyRootHandoff,
)


class FixedProfilePresentationDisposition(StrEnum):
    """Terminal presentation state; it is not a construction or runtime authority."""

    RECEIPT_AVAILABLE = "receipt_available"
    UPSTREAM_REFUSED = "upstream_refused"
    HANDOFF_REFUSED = "handoff_refused"


class FixedProfilePresentationFailureStage(StrEnum):
    """Owner-bound terminal stage for a returned immutable presentation view."""

    PROFILE_ISSUANCE = "g2_4_21_profile_issuance"
    INTENT_ASSESSMENT = "g2_4_21_intent_assessment"
    CUSTODY_HANDOFF = "g2_4_10_custody_handoff"
    WORK_ORDER_ISSUANCE = "g2_4_21_work_order_issuance"
    WORK_ORDER_ASSESSMENT = "g2_4_21_work_order_assessment"
    COMPATIBILITY_AUTHORIZATION = "g2_4_22_compatibility_authorization"


@dataclass(frozen=True, slots=True, kw_only=True)
class FixedProfilePresentationSubmission:
    """Integration inputs carried to public owners; no input conveys a live handle."""

    submission_id: str
    selected_profile_token: FixedConstructionIntentProfile | str
    requested_at: datetime
    expires_at: datetime
    custody_gate: WorkspaceCustodyGate
    custody_request: WorkspaceCustodyRequest
    runtime_composition_attestation: RuntimeCompositionAttestation

    def __post_init__(self) -> None:
        if not isinstance(self.submission_id, str) or not self.submission_id:
            raise ValueError("submission_id must be a non-empty string")
        if not isinstance(self.selected_profile_token, (FixedConstructionIntentProfile, str)):
            raise TypeError("selected_profile_token must be a fixed-profile enum or string")
        if not isinstance(self.requested_at, datetime) or not isinstance(self.expires_at, datetime):
            raise TypeError("requested_at and expires_at must be datetimes")
        if not isinstance(self.custody_gate, WorkspaceCustodyGate):
            raise TypeError("custody_gate must be WorkspaceCustodyGate")
        if not isinstance(self.custody_request, WorkspaceCustodyRequest):
            raise TypeError("custody_request must be WorkspaceCustodyRequest")
        if not isinstance(self.runtime_composition_attestation, RuntimeCompositionAttestation):
            raise TypeError("runtime_composition_attestation must be RuntimeCompositionAttestation")


@dataclass(frozen=True, slots=True, kw_only=True)
class TerminalReceiptFile:
    """Receipt-backed completed file fact; no filesystem inspection is performed here."""

    relative_path: str
    content_digest: str
    byte_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class FixedProfileTerminalView:
    """Immutable presentation projection containing declaration and receipt facts only."""

    disposition: FixedProfilePresentationDisposition
    selected_profile: str
    profile_version: str | None
    source_specification_digest: str | None
    intent_request_id: str | None
    intent_request_digest: str | None
    intent_assessment_id: str | None
    intent_assessment_digest: str | None
    work_order_id: str | None
    work_order_digest: str | None
    work_order_assessment_id: str | None
    work_order_assessment_digest: str | None
    work_order_expires_at: datetime | None
    authorization_id: str | None
    authorization_digest: str | None
    plan_digest: str | None
    construction_disposition: ConstructionBatchDisposition | None
    construction_failure: str | None
    receipt_files: tuple[TerminalReceiptFile, ...]
    failure_stage: FixedProfilePresentationFailureStage | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, FixedProfilePresentationDisposition):
            raise TypeError("disposition must be FixedProfilePresentationDisposition")
        if not isinstance(self.selected_profile, str):
            raise TypeError("selected_profile must be text")
        if self.construction_disposition is not None and not isinstance(
            self.construction_disposition, ConstructionBatchDisposition
        ):
            raise TypeError("construction_disposition must be ConstructionBatchDisposition or None")
        if any(not isinstance(item, TerminalReceiptFile) for item in self.receipt_files):
            raise TypeError("receipt_files must contain TerminalReceiptFile values")
        if self.disposition is FixedProfilePresentationDisposition.RECEIPT_AVAILABLE:
            if self.construction_disposition is None or self.failure_stage is not None or self.failure_code is not None:
                raise ValueError("receipt-backed presentation requires a construction receipt only")
        elif self.construction_disposition is not None or self.receipt_files:
            raise ValueError("pre-construction presentation refusal cannot carry construction facts")


def submit_fixed_profile_construction(
    *, submission: FixedProfilePresentationSubmission
) -> FixedProfileTerminalView:
    """Relay one exact token through public owners and return a receipt-backed projection."""
    if not isinstance(submission, FixedProfilePresentationSubmission):
        raise TypeError("submission must be FixedProfilePresentationSubmission")

    issuer = FixedProfileConstructionIntentIssuer()
    try:
        intent = issuer.issue_intent_request(
            intent_request_id=f"{submission.submission_id}-intent",
            profile=submission.selected_profile_token,
            requested_at=submission.requested_at,
        )
    except ConstructionWorkOrderEvidenceError as error:
        return _upstream_refusal(
            submission=submission,
            stage=FixedProfilePresentationFailureStage.PROFILE_ISSUANCE,
            code=str(error),
        )

    intent_assessment = FixedProfileConstructionIntentAssessor().assess(
        intent_assessment_id=f"{submission.submission_id}-intent-assessment",
        request=intent,
        assessed_at=submission.requested_at,
    )
    if intent_assessment.disposition is not FixedConstructionIntentDisposition.FIXED_PROFILE_CONSTRUCTION_INTENT_ATTESTED:
        return _upstream_refusal(
            submission=submission,
            stage=FixedProfilePresentationFailureStage.INTENT_ASSESSMENT,
            code=intent_assessment.disposition.value,
            intent=intent,
            intent_assessment=intent_assessment,
        )

    handoff = submission.custody_gate.attest_and_acquire_root_handoff(request=submission.custody_request)
    if handoff.reason is not None:
        return FixedProfileTerminalView(
            disposition=FixedProfilePresentationDisposition.HANDOFF_REFUSED,
            selected_profile=intent.profile,
            profile_version=intent.profile_version,
            source_specification_digest=intent.source_specification_digest,
            intent_request_id=intent.intent_request_id,
            intent_request_digest=intent.intent_request_digest,
            intent_assessment_id=intent_assessment.intent_assessment_id,
            intent_assessment_digest=intent_assessment.intent_assessment_digest,
            work_order_id=None,
            work_order_digest=None,
            work_order_assessment_id=None,
            work_order_assessment_digest=None,
            work_order_expires_at=None,
            authorization_id=None,
            authorization_digest=None,
            plan_digest=None,
            construction_disposition=None,
            construction_failure=None,
            receipt_files=(),
            failure_stage=FixedProfilePresentationFailureStage.CUSTODY_HANDOFF,
            failure_code=handoff.reason.value,
        )
    if handoff.attestation is None or handoff.binding is None or handoff.handle is None:
        raise RuntimeError("successful G2.4.10 handoff is missing a required output")

    return continue_fixed_profile_after_handoff(
        submission=submission,
        issuer=issuer,
        intent=intent,
        intent_assessment=intent_assessment,
        handoff=handoff,
    )


def continue_fixed_profile_after_handoff(
    *,
    submission: FixedProfilePresentationSubmission,
    issuer: FixedProfileConstructionIntentIssuer,
    intent: FixedProfileConstructionIntentRequest,
    intent_assessment: FixedProfileConstructionIntentAssessment,
    handoff: WorkspaceCustodyRootHandoff,
) -> FixedProfileTerminalView:
    """Continue one successful handoff without exposing its handle to presentation."""
    if handoff.attestation is None or handoff.binding is None or handoff.handle is None:
        raise RuntimeError("successful G2.4.10 handoff is missing a required output")
    with handoff.handle:
        try:
            work_order = issuer.issue_work_order(
                work_order_id=f"{submission.submission_id}-work-order",
                execution_id=handoff.attestation.execution_id,
                run_id=handoff.attestation.run_id,
                workspace_id=handoff.attestation.workspace_id,
                workspace_root_identity=handoff.attestation.workspace_root_identity,
                workspace_custody_attestation_id=handoff.attestation.attestation_id,
                workspace_custody_binding_digest=handoff.attestation.binding_digest,
                runtime_composition_attestation_id=submission.runtime_composition_attestation.attestation_id,
                runtime_composition_binding_digest=submission.runtime_composition_attestation.binding_digest,
                intent_request=intent,
                intent_assessment=intent_assessment,
                issued_at=handoff.attestation.occurred_at,
                expires_at=submission.expires_at,
            )
        except ConstructionWorkOrderEvidenceError as error:
            return _upstream_refusal(
                submission=submission,
                stage=FixedProfilePresentationFailureStage.WORK_ORDER_ISSUANCE,
                code=str(error),
                intent=intent,
                intent_assessment=intent_assessment,
            )

        work_order_request = IntentBoundConstructionWorkOrderAssessmentRequest(
            assessment_request_id=f"{submission.submission_id}-work-order-request",
            workspace_custody_attestation=handoff.attestation,
            runtime_composition_attestation=submission.runtime_composition_attestation,
            fixed_profile_intent_request=intent,
            fixed_profile_intent_assessment=intent_assessment,
            intent_bound_local_construction_work_order=work_order,
            timestamp=handoff.attestation.occurred_at,
        )
        work_order_assessment = IntentBoundConstructionWorkOrderAssessor().assess(
            assessment_id=f"{submission.submission_id}-work-order-assessment",
            request=work_order_request,
        )
        if work_order_assessment.disposition is not IntentBoundWorkOrderDisposition.INTENT_BOUND_LOCAL_CONSTRUCTION_WORK_ORDER_ATTESTED:
            return _upstream_refusal(
                submission=submission,
                stage=FixedProfilePresentationFailureStage.WORK_ORDER_ASSESSMENT,
                code=work_order_assessment.disposition.value,
                intent=intent,
                intent_assessment=intent_assessment,
                work_order_id=work_order.work_order_id,
                work_order_digest=work_order.work_order_digest,
                work_order_assessment_id=work_order_assessment.assessment_id,
                work_order_assessment_digest=work_order_assessment.assessment_digest,
                work_order_expires_at=work_order.expires_at,
            )

        try:
            authorization = FixedProfileConstructionAuthorization.issue(
                authorization_id=f"{submission.submission_id}-authorization",
                intent_request=intent,
                intent_assessment=intent_assessment,
                work_order_request=work_order_request,
                work_order_assessment=work_order_assessment,
                custody_request=submission.custody_request,
                custody_attestation=handoff.attestation,
                custody_root_binding=handoff.binding,
                timestamp=handoff.attestation.occurred_at,
            )
        except (ConstructionWorkOrderEvidenceError, ValueError) as error:
            return _upstream_refusal(
                submission=submission,
                stage=FixedProfilePresentationFailureStage.COMPATIBILITY_AUTHORIZATION,
                code=str(error),
                intent=intent,
                intent_assessment=intent_assessment,
                work_order_id=work_order.work_order_id,
                work_order_digest=work_order.work_order_digest,
                work_order_assessment_id=work_order_assessment.assessment_id,
                work_order_assessment_digest=work_order_assessment.assessment_digest,
                work_order_expires_at=work_order.expires_at,
            )

        receipt = FixedProfileWorkspaceFileConstructor().construct(
            authorization=authorization,
            handle=handoff.handle,
        )

    return _receipt_view(
        intent=intent,
        intent_assessment=intent_assessment,
        work_order=work_order,
        work_order_assessment=work_order_assessment,
        authorization=authorization,
        receipt=receipt,
    )


def render_fixed_profile_terminal_view(view: FixedProfileTerminalView) -> str:
    """Render only immutable declaration and receipt facts for the local terminal."""
    if not isinstance(view, FixedProfileTerminalView):
        raise TypeError("view must be FixedProfileTerminalView")
    lines = [
        "Governed Fixed Profile Construction",
        f"Profile: {view.selected_profile}" + (
            "" if view.profile_version is None else f" ({view.profile_version})"
        ),
        f"Presentation disposition: {view.disposition.value}",
    ]
    for label, value in (
        ("Source specification digest", view.source_specification_digest),
        ("Intent request", view.intent_request_id),
        ("Intent request digest", view.intent_request_digest),
        ("Intent assessment", view.intent_assessment_id),
        ("Intent assessment digest", view.intent_assessment_digest),
        ("Work order", view.work_order_id),
        ("Work order digest", view.work_order_digest),
        ("Work order assessment", view.work_order_assessment_id),
        ("Work order assessment digest", view.work_order_assessment_digest),
        ("Work order expiry", None if view.work_order_expires_at is None else view.work_order_expires_at.isoformat()),
        ("Authorization", view.authorization_id),
        ("Authorization digest", view.authorization_digest),
        ("Plan digest", view.plan_digest),
        ("Construction disposition", None if view.construction_disposition is None else view.construction_disposition.value),
        ("Construction failure", view.construction_failure),
        ("Failure stage", None if view.failure_stage is None else view.failure_stage.value),
        ("Failure code", view.failure_code),
    ):
        if value is not None:
            lines.append(f"{label}: {value}")
    if view.receipt_files:
        lines.append("Completed receipt-backed files:")
        lines.extend(
            f"  {item.relative_path}  {item.content_digest}  {item.byte_count} bytes"
            for item in view.receipt_files
        )
    return "\n".join(lines)


def _receipt_view(
    *,
    intent: FixedProfileConstructionIntentRequest,
    intent_assessment: FixedProfileConstructionIntentAssessment,
    work_order: IntentBoundLocalConstructionWorkOrderEvidence,
    work_order_assessment: IntentBoundConstructionWorkOrderAssessment,
    authorization: FixedProfileConstructionAuthorization,
    receipt: ConstructionBatchReceipt,
) -> FixedProfileTerminalView:
    return FixedProfileTerminalView(
        disposition=FixedProfilePresentationDisposition.RECEIPT_AVAILABLE,
        selected_profile=intent.profile,
        profile_version=intent.profile_version,
        source_specification_digest=intent.source_specification_digest,
        intent_request_id=intent.intent_request_id,
        intent_request_digest=intent.intent_request_digest,
        intent_assessment_id=intent_assessment.intent_assessment_id,
        intent_assessment_digest=intent_assessment.intent_assessment_digest,
        work_order_id=work_order.work_order_id,
        work_order_digest=work_order.work_order_digest,
        work_order_assessment_id=work_order_assessment.assessment_id,
        work_order_assessment_digest=work_order_assessment.assessment_digest,
        work_order_expires_at=work_order.expires_at,
        authorization_id=authorization.authorization_id,
        authorization_digest=authorization.authorization_digest,
        plan_digest=authorization.plan.plan_digest,
        construction_disposition=receipt.disposition,
        construction_failure=None if receipt.first_failure is None else receipt.first_failure.value,
        receipt_files=tuple(
            TerminalReceiptFile(
                relative_path=item.relative_path,
                content_digest=item.content_digest,
                byte_count=item.byte_count,
            )
            for item in receipt.action_receipts
        ),
    )


def _upstream_refusal(
    *,
    submission: FixedProfilePresentationSubmission,
    stage: FixedProfilePresentationFailureStage,
    code: str,
    intent: FixedProfileConstructionIntentRequest | None = None,
    intent_assessment: FixedProfileConstructionIntentAssessment | None = None,
    work_order_id: str | None = None,
    work_order_digest: str | None = None,
    work_order_assessment_id: str | None = None,
    work_order_assessment_digest: str | None = None,
    work_order_expires_at: datetime | None = None,
) -> FixedProfileTerminalView:
    selected_profile = (
        submission.selected_profile_token.value
        if isinstance(submission.selected_profile_token, FixedConstructionIntentProfile)
        else submission.selected_profile_token
    )
    return FixedProfileTerminalView(
        disposition=FixedProfilePresentationDisposition.UPSTREAM_REFUSED,
        selected_profile=selected_profile,
        profile_version=None if intent is None else intent.profile_version,
        source_specification_digest=None if intent is None else intent.source_specification_digest,
        intent_request_id=None if intent is None else intent.intent_request_id,
        intent_request_digest=None if intent is None else intent.intent_request_digest,
        intent_assessment_id=None if intent_assessment is None else intent_assessment.intent_assessment_id,
        intent_assessment_digest=None if intent_assessment is None else intent_assessment.intent_assessment_digest,
        work_order_id=work_order_id,
        work_order_digest=work_order_digest,
        work_order_assessment_id=work_order_assessment_id,
        work_order_assessment_digest=work_order_assessment_digest,
        work_order_expires_at=work_order_expires_at,
        authorization_id=None,
        authorization_digest=None,
        plan_digest=None,
        construction_disposition=None,
        construction_failure=None,
        receipt_files=(),
        failure_stage=stage,
        failure_code=code,
    )


__all__ = [
    "FixedProfilePresentationDisposition",
    "FixedProfilePresentationFailureStage",
    "FixedProfilePresentationSubmission",
    "FixedProfileTerminalView",
    "TerminalReceiptFile",
    "render_fixed_profile_terminal_view",
    "submit_fixed_profile_construction",
    "continue_fixed_profile_after_handoff",
]
