"""The sole G2.4.22 create-only descriptor-relative filesystem effect owner."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass

from eag.governed_construction_work_order import (
    CONSTRUCTION_WORK_ORDER_ASSESSMENT_SCHEMA_VERSION,
    ConstructionWorkOrderDisposition,
)
from eag.governed_file_construction.models import (
    ConstructionActionReceipt,
    ConstructionAuthorizationDecision,
    ConstructionAuthorizationDisposition,
    ConstructionAuthorizationRequest,
    ConstructionBatchDisposition,
    ConstructionBatchReceipt,
    ConstructionFinding,
    ConstructionFindingCode,
)
from eag.governed_workspace import (
    WorkspaceCustodyHandleError,
    WorkspaceCustodyRootHandle,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructionPlatformCapabilities:
    """Fail-closed descriptor-relative construction prerequisites, not capability providers."""

    live_root_handle_consumption: bool
    descriptor_relative_open: bool
    no_follow: bool
    exclusive_create: bool
    regular_file_verification: bool
    link_count_verification: bool

    @classmethod
    def detect(cls) -> ConstructionPlatformCapabilities:
        return cls(
            live_root_handle_consumption=True,
            descriptor_relative_open=hasattr(os, "open") and os.open in getattr(os, "supports_dir_fd", set()),
            no_follow=hasattr(os, "O_NOFOLLOW"),
            exclusive_create=hasattr(os, "O_EXCL"),
            regular_file_verification=hasattr(os, "fstat") and hasattr(stat, "S_ISREG"),
            link_count_verification=hasattr(os, "fstat") and hasattr(stat, "ST_NLINK"),
        )

    @property
    def supported(self) -> bool:
        return all(
            (
                self.live_root_handle_consumption,
                self.descriptor_relative_open,
                self.no_follow,
                self.exclusive_create,
                self.regular_file_verification,
                self.link_count_verification,
            )
        )


@dataclass(frozen=True, slots=True)
class _ActionAttempt:
    """Private action result that distinguishes no-effect refusal from possible effect state."""

    finding: ConstructionFindingCode
    effect_started: bool


class BoundedWorkspaceFileConstructor:
    """Consume one matching G2.4.10 handle to create only declared new text files."""

    def __init__(self, *, platform_capabilities: ConstructionPlatformCapabilities | None = None) -> None:
        if platform_capabilities is not None and not isinstance(platform_capabilities, ConstructionPlatformCapabilities):
            raise TypeError("platform_capabilities must be ConstructionPlatformCapabilities or None")
        detected = ConstructionPlatformCapabilities.detect()
        self._platform_capabilities = detected if platform_capabilities is None else _capability_intersection(
            detected,
            platform_capabilities,
        )

    def construct(
        self,
        *,
        authorization: ConstructionAuthorizationRequest,
        handle: WorkspaceCustodyRootHandle,
    ) -> ConstructionBatchReceipt:
        """Take handle closure ownership, then create one exact ordered file prefix or stop."""
        if not isinstance(authorization, ConstructionAuthorizationRequest):
            raise TypeError("authorization must be ConstructionAuthorizationRequest")
        if not isinstance(handle, WorkspaceCustodyRootHandle):
            raise TypeError("handle must be WorkspaceCustodyRootHandle")
        try:
            decision = self._authorize(authorization=authorization, handle=handle)
            if decision.disposition is ConstructionAuthorizationDisposition.REFUSED:
                return _refused_batch(authorization=authorization, finding=decision.findings[0].code)
            if not self._platform_capabilities.supported:
                return _refused_batch(
                    authorization=authorization,
                    finding=ConstructionFindingCode.CONSTRUCTION_CAPABILITY_UNSUPPORTED,
                )
            try:
                root_descriptor = handle.consume_for_g2_4_22(binding=authorization.custody_root_binding)
            except WorkspaceCustodyHandleError:
                return _refused_batch(authorization=authorization, finding=ConstructionFindingCode.HANDLE_REJECTED)

            receipts: list[ConstructionActionReceipt] = []
            for action in authorization.plan.actions:
                content_digest = _content_digest(action.content_digest)
                byte_count = _byte_count(action.byte_count)
                attempt = _create_one_file(
                    root_descriptor=root_descriptor,
                    relative_path=action.relative_path,
                    content=action.content,
                    expected_digest=content_digest,
                )
                if attempt is not None:
                    partial = bool(receipts) or attempt.effect_started
                    return _batch_receipt(
                        authorization=authorization,
                        disposition=(
                            ConstructionBatchDisposition.PARTIAL_CONSTRUCTION_STOPPED
                            if partial
                            else ConstructionBatchDisposition.CONSTRUCTION_REFUSED
                        ),
                        action_receipts=tuple(receipts),
                        first_failure=attempt.finding,
                    )
                receipts.append(
                    ConstructionActionReceipt(
                        sequence=action.sequence,
                        relative_path=action.relative_path,
                        content_digest=content_digest,
                        byte_count=byte_count,
                        occurred_at=authorization.timestamp,
                    )
                )
            return _batch_receipt(
                authorization=authorization,
                disposition=ConstructionBatchDisposition.CONSTRUCTION_FILES_CREATED,
                action_receipts=tuple(receipts),
                first_failure=None,
            )
        finally:
            handle.close()

    def _authorize(
        self,
        *,
        authorization: ConstructionAuthorizationRequest,
        handle: WorkspaceCustodyRootHandle,
    ) -> ConstructionAuthorizationDecision:
        """Validate immutable evidence and exact handle binding without custody reacquisition."""
        assessment_request = authorization.assessment_request
        assessment = authorization.assessment
        custody_request = authorization.custody_request
        custody_attestation = authorization.custody_attestation
        root_binding = authorization.custody_root_binding
        plan = authorization.plan
        work_order = assessment_request.work_order

        if not _immutable_evidence_is_self_validating(authorization):
            return _refusal(authorization, ConstructionFindingCode.ASSESSMENT_INVALID, "evidence_self_validation")
        if assessment.schema_version != CONSTRUCTION_WORK_ORDER_ASSESSMENT_SCHEMA_VERSION:
            return _refusal(authorization, ConstructionFindingCode.ASSESSMENT_INVALID, "assessment_schema")
        if not assessment.assessed_request_id or not assessment.assessed_request_digest:
            return _refusal(authorization, ConstructionFindingCode.ASSESSMENT_INVALID, "assessment_provenance")
        if (
            assessment.assessed_request_id != assessment_request.assessment_request_id
            or assessment.assessed_request_digest != assessment_request.request_digest
        ):
            return _refusal(authorization, ConstructionFindingCode.REQUEST_PROVENANCE_MISMATCH, "assessment_request")
        if assessment.disposition is not ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED:
            return _refusal(authorization, ConstructionFindingCode.ASSESSMENT_NOT_ATTESTED, "assessment_disposition")
        if (
            assessment_request.workspace_custody_attestation != custody_attestation
            or assessment_request.work_order != work_order
            or assessment.work_order_id != work_order.work_order_id
            or assessment.workspace_id != work_order.workspace_id
        ):
            return _refusal(authorization, ConstructionFindingCode.WORK_ORDER_BINDING_MISMATCH, "assessment_work_order")
        if (
            work_order.action_plan_digest != plan.plan_digest
            or work_order.max_command_actions != 0
            or plan.file_count > work_order.max_file_actions
            or plan.total_bytes > work_order.max_total_bytes
            or authorization.timestamp >= work_order.expires_at
        ):
            return _refusal(authorization, ConstructionFindingCode.PLAN_BINDING_MISMATCH, "plan_work_order")
        if (
            work_order.workspace_custody_attestation_id != custody_attestation.attestation_id
            or work_order.workspace_custody_binding_digest != custody_attestation.binding_digest
            or work_order.workspace_id != custody_attestation.workspace_id
            or work_order.execution_id != custody_attestation.execution_id
            or work_order.run_id != custody_attestation.run_id
            or work_order.workspace_root_identity != custody_attestation.workspace_root_identity
        ):
            return _refusal(authorization, ConstructionFindingCode.WORK_ORDER_BINDING_MISMATCH, "work_order_custody")
        if (
            custody_attestation.custody_request_id != custody_request.custody_request_id
            or custody_attestation.custody_request_digest != custody_request.request_digest
            or custody_attestation.execution_id != custody_request.execution_id
            or custody_attestation.run_id != custody_request.run_id
            or custody_attestation.workspace_id != custody_request.workspace_id
            or custody_attestation.custody_policy_digest != custody_request.policy.digest
        ):
            return _refusal(authorization, ConstructionFindingCode.CUSTODY_HANDOFF_MISMATCH, "request_attestation")
        if (
            root_binding.custody_request_id != custody_request.custody_request_id
            or root_binding.custody_request_digest != custody_request.request_digest
            or root_binding.custody_attestation_id != custody_attestation.attestation_id
            or root_binding.custody_attestation_binding_digest != custody_attestation.binding_digest
            or root_binding.workspace_object_identity != custody_attestation.workspace_object_identity
        ):
            return _refusal(authorization, ConstructionFindingCode.CUSTODY_HANDOFF_MISMATCH, "attestation_binding")
        if handle.binding_digest != root_binding.binding_digest:
            return _refusal(authorization, ConstructionFindingCode.HANDLE_REJECTED, "handle_binding")
        return _decision(authorization=authorization, disposition=ConstructionAuthorizationDisposition.ATTESTED, findings=())


def _capability_intersection(
    detected: ConstructionPlatformCapabilities,
    requested: ConstructionPlatformCapabilities,
) -> ConstructionPlatformCapabilities:
    """Tests may disable a primitive but cannot make an unavailable primitive available."""
    return ConstructionPlatformCapabilities(
        live_root_handle_consumption=detected.live_root_handle_consumption and requested.live_root_handle_consumption,
        descriptor_relative_open=detected.descriptor_relative_open and requested.descriptor_relative_open,
        no_follow=detected.no_follow and requested.no_follow,
        exclusive_create=detected.exclusive_create and requested.exclusive_create,
        regular_file_verification=detected.regular_file_verification and requested.regular_file_verification,
        link_count_verification=detected.link_count_verification and requested.link_count_verification,
    )


def _immutable_evidence_is_self_validating(authorization: ConstructionAuthorizationRequest) -> bool:
    """Refuse altered immutable evidence; never re-assess or reopen custody roots."""
    try:
        return (
            authorization.authorization_digest == authorization.calculate_digest()
            and authorization.plan.plan_digest == authorization.plan.calculate_digest()
            and authorization.assessment_request.request_digest == authorization.assessment_request.calculate_digest()
            and authorization.assessment.assessment_digest == authorization.assessment.calculate_digest()
            and authorization.assessment_request.work_order.work_order_digest
            == authorization.assessment_request.work_order.calculate_digest()
            and authorization.custody_request.request_digest == authorization.custody_request.request_digest
            and authorization.custody_attestation.binding_digest
            == authorization.custody_attestation.calculate_binding_digest()
            and authorization.custody_root_binding.binding_digest
            == authorization.custody_root_binding.calculate_binding_digest()
        )
    except (TypeError, ValueError):
        return False


def _decision(
    *,
    authorization: ConstructionAuthorizationRequest,
    disposition: ConstructionAuthorizationDisposition,
    findings: tuple[ConstructionFinding, ...],
) -> ConstructionAuthorizationDecision:
    work_order = authorization.assessment_request.work_order
    return ConstructionAuthorizationDecision(
        disposition=disposition,
        findings=findings,
        authorization_id=authorization.authorization_id,
        authorization_digest=_authorization_digest(authorization),
        plan_digest=_plan_digest(authorization),
        work_order_digest=work_order.work_order_digest,
        assessment_digest=authorization.assessment.assessment_digest,
        custody_attestation_binding_digest=authorization.custody_attestation.binding_digest,
        custody_root_binding_digest=authorization.custody_root_binding.binding_digest,
    )


def _refusal(
    authorization: ConstructionAuthorizationRequest,
    code: ConstructionFindingCode,
    evidence_reference: str,
) -> ConstructionAuthorizationDecision:
    return _decision(
        authorization=authorization,
        disposition=ConstructionAuthorizationDisposition.REFUSED,
        findings=(ConstructionFinding(code=code, evidence_reference=evidence_reference),),
    )


def _refused_batch(
    *,
    authorization: ConstructionAuthorizationRequest,
    finding: ConstructionFindingCode,
) -> ConstructionBatchReceipt:
    return _batch_receipt(
        authorization=authorization,
        disposition=ConstructionBatchDisposition.CONSTRUCTION_REFUSED,
        action_receipts=(),
        first_failure=finding,
    )


def _batch_receipt(
    *,
    authorization: ConstructionAuthorizationRequest,
    disposition: ConstructionBatchDisposition,
    action_receipts: tuple[ConstructionActionReceipt, ...],
    first_failure: ConstructionFindingCode | None,
) -> ConstructionBatchReceipt:
    return ConstructionBatchReceipt(
        disposition=disposition,
        authorization_id=authorization.authorization_id,
        authorization_digest=_authorization_digest(authorization),
        plan_digest=_plan_digest(authorization),
        work_order_digest=authorization.assessment_request.work_order.work_order_digest,
        assessment_digest=authorization.assessment.assessment_digest,
        custody_attestation_binding_digest=authorization.custody_attestation.binding_digest,
        custody_root_binding_digest=authorization.custody_root_binding.binding_digest,
        action_receipts=action_receipts,
        occurred_at=authorization.timestamp,
        first_failure=first_failure,
    )


def _authorization_digest(authorization: ConstructionAuthorizationRequest) -> str:
    if authorization.authorization_digest is None:
        raise ValueError("validated authorization is missing authorization_digest")
    return authorization.authorization_digest


def _plan_digest(authorization: ConstructionAuthorizationRequest) -> str:
    if authorization.plan.plan_digest is None:
        raise ValueError("validated construction plan is missing plan_digest")
    return authorization.plan.plan_digest


def _content_digest(value: str | None) -> str:
    if value is None:
        raise ValueError("validated action is missing content_digest")
    return value


def _byte_count(value: int | None) -> int:
    if value is None:
        raise ValueError("validated action is missing byte_count")
    return value


def _create_one_file(
    *,
    root_descriptor: int,
    relative_path: str,
    content: str,
    expected_digest: str,
) -> _ActionAttempt | None:
    """Create one regular file and truthfully classify whether any owned effect began."""
    parts = relative_path.split("/")
    directory_descriptor = root_descriptor
    owns_directory_descriptor = False
    effect_started = False
    try:
        for part in parts[:-1]:
            next_descriptor: int | None = None
            try:
                try:
                    os.mkdir(part, 0o700, dir_fd=directory_descriptor)
                    effect_started = True
                except FileExistsError:
                    pass
                next_descriptor = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory_descriptor,
                )
                metadata = os.fstat(next_descriptor)
                if not stat.S_ISDIR(metadata.st_mode):
                    return _ActionAttempt(ConstructionFindingCode.PATH_UNSAFE, effect_started)
            except OSError:
                return _ActionAttempt(ConstructionFindingCode.PATH_UNSAFE, effect_started)
            if owns_directory_descriptor:
                os.close(directory_descriptor)
            directory_descriptor = next_descriptor
            owns_directory_descriptor = True

        try:
            descriptor = os.open(
                parts[-1],
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_descriptor,
            )
        except FileExistsError:
            return _ActionAttempt(ConstructionFindingCode.TARGET_EXISTS, effect_started)
        except OSError:
            return _ActionAttempt(ConstructionFindingCode.FILESYSTEM_FAILURE, effect_started)
        effect_started = True
        try:
            encoded = content.encode("utf-8", "strict")
            written = 0
            while written < len(encoded):
                count = os.write(descriptor, encoded[written:])
                if count <= 0:
                    return _ActionAttempt(ConstructionFindingCode.FILESYSTEM_FAILURE, effect_started)
                written += count
            os.fsync(descriptor)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                return _ActionAttempt(ConstructionFindingCode.POSTWRITE_VERIFICATION_FAILED, effect_started)
            os.lseek(descriptor, 0, os.SEEK_SET)
            observed = bytearray()
            while len(observed) < len(encoded):
                chunk = os.read(descriptor, len(encoded) - len(observed))
                if not chunk:
                    break
                observed.extend(chunk)
            if len(observed) != len(encoded) or hashlib.sha256(observed).hexdigest() != expected_digest:
                return _ActionAttempt(ConstructionFindingCode.POSTWRITE_VERIFICATION_FAILED, effect_started)
        except OSError:
            return _ActionAttempt(ConstructionFindingCode.FILESYSTEM_FAILURE, effect_started)
        finally:
            os.close(descriptor)
        return None
    finally:
        if owns_directory_descriptor:
            os.close(directory_descriptor)


__all__ = ["BoundedWorkspaceFileConstructor", "ConstructionPlatformCapabilities"]
