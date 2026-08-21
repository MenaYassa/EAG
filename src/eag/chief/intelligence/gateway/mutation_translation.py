"""Pure translation from a governed decision result to one untrusted ChangeProposal."""

from __future__ import annotations

import hashlib
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from eag.chief.intelligence.gateway.models import (
    EngineeringDecision,
    EngineeringDecisionRequest,
    EngineeringDecisionResult,
    MutationIntent,
    PreservationRequirement,
)
from eag.context.sensitivity import ContextSecurityPolicy
from eag.mutation import (
    ChangeProposal,
    MutationOperation,
    MutationPostcondition,
    MutationPrecondition,
    MutationRisk,
)


class TranslationViolationCode(StrEnum):
    """Stable, sanitized failure categories at the decision-to-proposal boundary."""

    GATEWAY_RESULT_INVALID = "gateway_result_invalid"
    MUTATION_MODE_DISABLED = "mutation_mode_disabled"
    MUTATION_INTENT_COUNT_INVALID = "mutation_intent_count_invalid"
    MUTATION_INTENT_STEP_INVALID = "mutation_intent_step_invalid"
    MUTATION_INTENT_DEPENDENCIES_FORBIDDEN = "mutation_intent_dependencies_forbidden"
    MUTATION_OPERATION_UNSUPPORTED = "mutation_operation_unsupported"
    TARGET_PATH_INVALID = "target_path_invalid"
    TARGET_PARENT_INVALID = "target_parent_invalid"
    TARGET_NOT_REGULAR_FILE = "target_not_regular_file"
    TARGET_NOT_UTF8 = "target_not_utf8"
    SENSITIVE_TARGET = "sensitive_target"
    TRUSTED_BINDING_INVALID = "trusted_binding_invalid"
    PRESERVATION_REQUIREMENT_INVALID = "preservation_requirement_invalid"


@dataclass(frozen=True, slots=True, kw_only=True)
class TranslationViolation:
    """Redacted translation rejection that never stores provider content or host paths."""

    code: TranslationViolationCode
    message: str
    target_path: str | None = None


class MutationTranslationError(ValueError):
    """Raised when a governed decision cannot safely form one ChangeProposal."""

    def __init__(self, violation: TranslationViolation) -> None:
        super().__init__(violation.message)
        self.violation = violation


@dataclass(frozen=True, slots=True, kw_only=True)
class TrustedWorkspaceState:
    """Trusted, read-only bindings supplied outside provider control.

    The workspace root, provenance fingerprints, policy version, and sensitivity policy are
    injected by composition. Provider-derived mutation data has no field capable of changing
    these bindings.
    """

    workspace_root: Path
    repository_snapshot_fingerprint: str
    context_fingerprint: str
    policy_version: str
    sensitivity_policy: ContextSecurityPolicy

    def __post_init__(self) -> None:
        root = self.workspace_root.resolve(strict=True)
        if not self.repository_snapshot_fingerprint.strip():
            raise ValueError("repository_snapshot_fingerprint cannot be empty")
        if not self.context_fingerprint.strip():
            raise ValueError("context_fingerprint cannot be empty")
        if not self.policy_version.strip():
            raise ValueError("policy_version cannot be empty")
        object.__setattr__(self, "workspace_root", root)

    @property
    def workspace_fingerprint(self) -> str:
        """Return a deterministic root identity without exposing an absolute path."""
        root_stat = self.workspace_root.stat()
        return _sha256_text(f"{root_stat.st_dev}:{root_stat.st_ino}")

    def read_target_state(self, target_path: str) -> tuple[bool, str | None, str | None]:
        """Safely derive current target state without changing the workspace."""
        relative = _safe_relative_path(target_path)
        current = self.workspace_root
        for component in relative.parts[:-1]:
            current = current / component
            if not current.exists():
                _reject(
                    TranslationViolationCode.TARGET_PARENT_INVALID,
                    "target parent directory does not exist",
                    target_path,
                )
            mode = current.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                _reject(
                    TranslationViolationCode.TARGET_PARENT_INVALID,
                    "target parent is not a safe directory",
                    target_path,
                )
        target = current / relative.parts[-1]
        try:
            target.parent.resolve(strict=True).relative_to(self.workspace_root)
        except ValueError:
            _reject(
                TranslationViolationCode.TARGET_PATH_INVALID,
                "target path escapes the trusted workspace root",
                target_path,
            )
        sensitivity = self.sensitivity_policy.classify_path(target, self.workspace_root)
        if sensitivity.action == "excluded":
            _reject(
                TranslationViolationCode.SENSITIVE_TARGET,
                "target is protected by sensitivity policy",
                target_path,
            )
        if not target.exists():
            return False, None, None
        mode = target.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            _reject(
                TranslationViolationCode.TARGET_NOT_REGULAR_FILE,
                "target is not a safe regular file",
                target_path,
            )
        data = target.read_bytes()
        if b"\x00" in data:
            _reject(
                TranslationViolationCode.TARGET_NOT_UTF8,
                "target is not a supported UTF-8 text file",
                target_path,
            )
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            _reject(
                TranslationViolationCode.TARGET_NOT_UTF8,
                "target is not a supported UTF-8 text file",
                target_path,
            )
        return True, _sha256_text(content), content


class DecisionToChangeProposalTranslator:
    """Convert one successful governed decision to one untrusted G2.3.1 proposal.

    This class is intentionally pure with respect to mutation: its only filesystem interaction
    is a bounded read through TrustedWorkspaceState to derive a precondition. It does not call
    a gateway, policy validator, authorizer, mutation runtime, shell, Git, network, or credential API.
    """

    def translate(
        self,
        result: EngineeringDecisionResult,
        request: EngineeringDecisionRequest,
        *,
        run_id: str,
        trusted_state: TrustedWorkspaceState,
    ) -> ChangeProposal:
        """Return exactly one deterministic proposal or raise a sanitized rejection."""
        if not result.success or result.decision is None or result.error is not None:
            _reject(
                TranslationViolationCode.GATEWAY_RESULT_INVALID,
                "translation requires a successful governed decision result",
            )
        if not run_id.strip():
            _reject(
                TranslationViolationCode.TRUSTED_BINDING_INVALID,
                "trusted run identity is required",
            )
        _validate_trusted_bindings(request, trusted_state)
        policy = request.mutation_intent_policy
        if policy is None:
            _reject(
                TranslationViolationCode.MUTATION_MODE_DISABLED,
                "mutation intent mode is not enabled for this request",
            )
        assert policy is not None
        decision = result.decision
        assert decision is not None
        if len(decision.mutation_intents) != 1:
            _reject(
                TranslationViolationCode.MUTATION_INTENT_COUNT_INVALID,
                "exactly one mutation intent is required",
            )
        intent = decision.mutation_intents[0]
        self._validate_intent_shape(intent, decision, policy.capability_id, policy.allowed_operations)
        exists, current_fingerprint, current_content = trusted_state.read_target_state(
            intent.target_path
        )
        operation = _operation(intent)
        self._validate_preservation(
            intent,
            policy.preservation_requirements,
            target_exists=exists,
            current_content=current_content,
        )
        precondition = MutationPrecondition(
            expect_exists=exists,
            expected_fingerprint=current_fingerprint,
        )
        content_fingerprint = _sha256_text(intent.proposed_content)
        return ChangeProposal(
            proposal_id=_proposal_id(
                run_id=run_id,
                decision_id=decision.digest,
                intent=intent,
                trusted_state=trusted_state,
            ),
            run_id=run_id,
            decision_id=decision.digest,
            target_path=intent.target_path,
            operation=operation,
            content=intent.proposed_content,
            precondition=precondition,
            reason=intent.rationale,
            provenance_ids=intent.grounding_references,
            risk=_risk_from_decision(decision),
            authorization_metadata={
                "mutation_intent_id": intent.intent_id,
                "mutation_intent_schema_version": intent.schema_version,
                "gateway_request_id": request.request_id,
                "policy_version": trusted_state.policy_version,
            },
            expected_postcondition=MutationPostcondition(
                expect_exists=True,
                expected_fingerprint=content_fingerprint,
            ),
            context_fingerprint=trusted_state.context_fingerprint,
            repository_snapshot_fingerprint=trusted_state.repository_snapshot_fingerprint,
            workspace_fingerprint=trusted_state.workspace_fingerprint,
        )

    @staticmethod
    def _validate_intent_shape(
        intent: MutationIntent,
        decision: EngineeringDecision,
        mutation_capability_id: str,
        allowed_operations: tuple[str, ...],
    ) -> None:
        steps = {step.step_id: step for step in decision.ordered_plan}
        step = steps.get(intent.step_id)
        if step is None or step.capability_id != mutation_capability_id:
            _reject(
                TranslationViolationCode.MUTATION_INTENT_STEP_INVALID,
                "mutation intent does not match the configured mutation step",
                intent.target_path,
            )
        assert step is not None
        if step.dependencies or intent.dependencies:
            _reject(
                TranslationViolationCode.MUTATION_INTENT_DEPENDENCIES_FORBIDDEN,
                "mutation intent dependencies are not supported",
                intent.target_path,
            )
        if intent.operation not in allowed_operations:
            _reject(
                TranslationViolationCode.MUTATION_OPERATION_UNSUPPORTED,
                "mutation intent operation is not supported",
                intent.target_path,
            )
        _safe_relative_path(intent.target_path)

    @staticmethod
    def _validate_preservation(
        intent: MutationIntent,
        requirements: tuple[PreservationRequirement, ...],
        *,
        target_exists: bool,
        current_content: str | None,
    ) -> None:
        """Reject omission of trusted immutable leading content without repairing provider output."""
        declared_ids = set(intent.preservation_requirement_ids)
        expected_ids = {requirement.requirement_id for requirement in requirements}
        if declared_ids != expected_ids:
            _reject(
                TranslationViolationCode.PRESERVATION_REQUIREMENT_INVALID,
                "mutation intent preservation bindings do not match trusted requirements",
                intent.target_path,
            )
        if not requirements:
            return
        if not target_exists or current_content is None:
            _reject(
                TranslationViolationCode.PRESERVATION_REQUIREMENT_INVALID,
                "trusted preservation requirements need an existing text target",
                intent.target_path,
            )
        assert current_content is not None
        for requirement in requirements:
            if not current_content.startswith(requirement.required_prefix):
                _reject(
                    TranslationViolationCode.PRESERVATION_REQUIREMENT_INVALID,
                    "trusted preservation requirement does not match the current target",
                    intent.target_path,
                )
            if not intent.proposed_content.startswith(requirement.required_prefix):
                _reject(
                    TranslationViolationCode.PRESERVATION_REQUIREMENT_INVALID,
                    "proposed replacement omits required preserved leading content",
                    intent.target_path,
                )


def _validate_trusted_bindings(
    request: EngineeringDecisionRequest,
    trusted_state: TrustedWorkspaceState,
) -> None:
    """Require runtime-provided snapshot/context bindings to agree with the gateway request."""
    metadata = request.context.truncation_metadata
    snapshot = metadata.get("snapshot_fingerprint")
    context = metadata.get("context_fingerprint")
    if not isinstance(snapshot, str) or snapshot != trusted_state.repository_snapshot_fingerprint:
        _reject(
            TranslationViolationCode.TRUSTED_BINDING_INVALID,
            "trusted repository snapshot binding does not match the governed request",
        )
    if not isinstance(context, str) or context != trusted_state.context_fingerprint:
        _reject(
            TranslationViolationCode.TRUSTED_BINDING_INVALID,
            "trusted context binding does not match the governed request",
        )


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        Path(value).is_absolute()
        or path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or "\x00" in value
        or any("\\" in part for part in path.parts)
    ):
        _reject(TranslationViolationCode.TARGET_PATH_INVALID, "target path is invalid", value)
    return path


def _operation(intent: MutationIntent) -> MutationOperation:
    try:
        return MutationOperation(intent.operation)
    except ValueError:
        _reject(
            TranslationViolationCode.MUTATION_OPERATION_UNSUPPORTED,
            "mutation intent operation is not supported by the mutation boundary",
            intent.target_path,
        )
    raise AssertionError("unreachable after translation rejection")


def _risk_from_decision(decision: EngineeringDecision) -> MutationRisk:
    severities = {risk.severity.value for risk in decision.risks}
    if severities & {"critical", "high"}:
        return MutationRisk.HIGH
    if severities == {"low"}:
        return MutationRisk.LOW
    return MutationRisk.MEDIUM


def _proposal_id(
    *,
    run_id: str,
    decision_id: str,
    intent: MutationIntent,
    trusted_state: TrustedWorkspaceState,
) -> str:
    """Derive a stable proposal identity so repeated identical translation preserves digest."""
    payload = "\x1f".join(
        (
            run_id,
            decision_id,
            intent.intent_id,
            intent.target_path,
            intent.operation,
            _sha256_text(intent.proposed_content),
            trusted_state.context_fingerprint,
            trusted_state.repository_snapshot_fingerprint,
            trusted_state.workspace_fingerprint,
            trusted_state.policy_version,
        )
    )
    return f"proposal-{_sha256_text(payload)}"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reject(code: TranslationViolationCode, message: str, target_path: str | None = None) -> None:
    raise MutationTranslationError(
        TranslationViolation(code=code, message=message, target_path=target_path)
    )
