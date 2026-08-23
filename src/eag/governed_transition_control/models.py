"""Immutable evidence-only contracts for G2.4.17 external transition control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from eag.governed_transition_control.canonical import (
    TRANSITION_CONTROL_SCHEMA_VERSION,
    TransitionControlEvidenceError,
    canonical_digest,
    canonical_timestamp,
    control_key_digest,
    require_non_empty,
    require_sha256,
)


class TransitionControlProfile(StrEnum):
    """The one narrow transition-control profile supported by G2.4.17."""

    EXTERNAL_ARTIFACT_TRANSITION_CONTROL_V1 = "external_artifact_transition_control_v1"


class TransitionControlDisposition(StrEnum):
    """Control evidence outcomes; none is a permit or execution command."""

    CLAIMED = "claimed"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    AMBIGUOUS = "ambiguous"
    NOT_CONTROLLABLE = "not_controllable"
    UNSUPPORTED_PROFILE = "unsupported_profile"


class TransitionControlRecordState(StrEnum):
    """Persisted pre-execution control states, deliberately excluding completion."""

    CLAIMED = "claimed"
    AMBIGUOUS = "ambiguous"


class TransitionControlFindingCode(StrEnum):
    """Typed fail-closed findings produced without external interaction."""

    AUTHORIZATION_EVIDENCE_INVALID = "authorization_evidence_invalid"
    AUTHORIZATION_BINDING_MISMATCH = "authorization_binding_mismatch"
    TRANSITION_BINDING_MISMATCH = "transition_binding_mismatch"
    ARTIFACT_IDENTITY_MISMATCH = "artifact_identity_mismatch"
    DESTINATION_BINDING_MISMATCH = "destination_binding_mismatch"
    POLICY_BINDING_MISMATCH = "policy_binding_mismatch"
    IDEMPOTENCY_KEY_INVALID = "idempotency_key_invalid"
    DUPLICATE_CONTROL = "duplicate_control"
    CONFLICTING_CONTROL = "conflicting_control"
    AMBIGUOUS_CONTROL = "ambiguous_control"
    CONTROL_STORE_UNAVAILABLE = "control_store_unavailable"
    CONTROL_STORE_CORRUPT = "control_store_corrupt"
    UNSUPPORTED_PROFILE = "unsupported_profile"


def _ordered_unique_strings(
    values: tuple[str, ...], field_name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TransitionControlEvidenceError(f"{field_name} must be a tuple")
    normalized = tuple(require_non_empty(value, field_name) for value in values)
    if not allow_empty and not normalized:
        raise TransitionControlEvidenceError(f"{field_name} cannot be empty")
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise TransitionControlEvidenceError(f"{field_name} must be strictly ordered and unique")
    return normalized


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalTransitionControlRequest:
    """Exact pre-execution control evidence; it has no client, permit, or executor."""

    control_request_id: str
    authorization_id: str
    authorization_binding_digest: str
    authorization_assessment_id: str
    authorization_assessment_digest: str
    transition_intent_id: str
    artifact_id: str
    artifact_fingerprint: str
    destination_identity: str
    promotion_policy_digest: str
    authorization_policy_digest: str
    idempotency_key: str
    transition_profile: TransitionControlProfile | str
    occurred_at: datetime
    execution_id: str | None = None
    run_id: str | None = None
    schema_version: str = TRANSITION_CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "control_request_id",
            "authorization_id",
            "authorization_assessment_id",
            "transition_intent_id",
            "artifact_id",
            "destination_identity",
            "idempotency_key",
        ):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        for field_name in (
            "authorization_binding_digest",
            "authorization_assessment_digest",
            "artifact_fingerprint",
            "promotion_policy_digest",
            "authorization_policy_digest",
        ):
            object.__setattr__(self, field_name, require_sha256(getattr(self, field_name), field_name))
        for field_name in ("execution_id", "run_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_non_empty(value, field_name))
        if not isinstance(self.transition_profile, (TransitionControlProfile, str)):
            raise TransitionControlEvidenceError(
                "transition_profile must be a TransitionControlProfile or non-empty string"
            )
        if isinstance(self.transition_profile, str) and not isinstance(
            self.transition_profile, TransitionControlProfile
        ):
            object.__setattr__(
                self,
                "transition_profile",
                require_non_empty(self.transition_profile, "transition_profile"),
            )
        object.__setattr__(self, "occurred_at", canonical_timestamp(self.occurred_at, "occurred_at"))
        if self.schema_version != TRANSITION_CONTROL_SCHEMA_VERSION:
            raise TransitionControlEvidenceError("unsupported transition control request schema_version")

    @property
    def control_key(self) -> str:
        """Return the durable key for exact canonical authorized transition identity.

        ``idempotency_key`` remains immutable request evidence only. It is not a
        control-key authority and therefore cannot create another durable identity
        for the same authorized transition.
        """
        return control_key_digest(transition_identity=self.to_control_identity_payload())

    def to_control_identity_payload(self) -> dict[str, str | None]:
        """Return every G2.4.16/G2.4.17 identity field that controls one transition."""
        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "artifact_id": self.artifact_id,
            "authorization_assessment_digest": self.authorization_assessment_digest,
            "authorization_assessment_id": self.authorization_assessment_id,
            "authorization_binding_digest": self.authorization_binding_digest,
            "authorization_id": self.authorization_id,
            "authorization_policy_digest": self.authorization_policy_digest,
            "destination_identity": self.destination_identity,
            "execution_id": self.execution_id,
            "promotion_policy_digest": self.promotion_policy_digest,
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "transition_intent_id": self.transition_intent_id,
            "transition_profile": self.transition_profile.value
            if isinstance(self.transition_profile, TransitionControlProfile)
            else self.transition_profile,
        }

    @property
    def binding_digest(self) -> str:
        """Return the exact canonical binding digest used to detect conflicts."""
        return canonical_digest(self.to_binding_payload())

    def to_binding_payload(self) -> dict[str, str | None]:
        """Return the complete redacted canonical binding, never a transition command."""
        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "artifact_id": self.artifact_id,
            "authorization_assessment_digest": self.authorization_assessment_digest,
            "authorization_assessment_id": self.authorization_assessment_id,
            "authorization_binding_digest": self.authorization_binding_digest,
            "authorization_id": self.authorization_id,
            "authorization_policy_digest": self.authorization_policy_digest,
            "destination_identity": self.destination_identity,
            "execution_id": self.execution_id,
            "idempotency_key": self.idempotency_key,
            "occurred_at": self.occurred_at.isoformat(),
            "promotion_policy_digest": self.promotion_policy_digest,
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "transition_intent_id": self.transition_intent_id,
            "transition_profile": self.transition_profile.value
            if isinstance(self.transition_profile, TransitionControlProfile)
            else self.transition_profile,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class TransitionControlRecord:
    """One immutable durable control record; it never claims an external outcome."""

    control_id: str
    control_key: str
    binding_digest: str
    request_digest: str
    state: TransitionControlRecordState
    occurred_at: datetime
    record_digest: str
    schema_version: str = TRANSITION_CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "control_id", require_non_empty(self.control_id, "control_id"))
        for field_name in ("control_key", "binding_digest", "request_digest", "record_digest"):
            object.__setattr__(self, field_name, require_sha256(getattr(self, field_name), field_name))
        if not isinstance(self.state, TransitionControlRecordState):
            raise TypeError("state must be a TransitionControlRecordState")
        object.__setattr__(self, "occurred_at", canonical_timestamp(self.occurred_at, "occurred_at"))
        if self.schema_version != TRANSITION_CONTROL_SCHEMA_VERSION:
            raise TransitionControlEvidenceError("unsupported transition control record schema_version")
        if self.record_digest != self.calculate_digest():
            raise TransitionControlEvidenceError("record_digest does not match canonical control record")

    @classmethod
    def create(
        cls,
        *,
        control_id: str,
        request: ExternalTransitionControlRequest,
        state: TransitionControlRecordState,
        occurred_at: datetime,
    ) -> TransitionControlRecord:
        canonical_time = canonical_timestamp(occurred_at, "occurred_at")
        request_digest = canonical_digest(request.to_binding_payload())
        payload = {
            "binding_digest": request.binding_digest,
            "control_id": control_id,
            "control_key": request.control_key,
            "occurred_at": canonical_time.isoformat(),
            "request_digest": request_digest,
            "schema_version": TRANSITION_CONTROL_SCHEMA_VERSION,
            "state": state.value,
        }
        return cls(
            control_id=control_id,
            control_key=request.control_key,
            binding_digest=request.binding_digest,
            request_digest=request_digest,
            state=state,
            occurred_at=canonical_time,
            record_digest=canonical_digest(payload),
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            {
                "binding_digest": self.binding_digest,
                "control_id": self.control_id,
                "control_key": self.control_key,
                "occurred_at": self.occurred_at.isoformat(),
                "request_digest": self.request_digest,
                "schema_version": self.schema_version,
                "state": self.state.value,
            }
        )

    def to_payload(self) -> dict[str, str]:
        """Return exact redacted durable representation for strict parsing."""
        return {
            "binding_digest": self.binding_digest,
            "control_id": self.control_id,
            "control_key": self.control_key,
            "occurred_at": self.occurred_at.isoformat(),
            "record_digest": self.record_digest,
            "request_digest": self.request_digest,
            "schema_version": self.schema_version,
            "state": self.state.value,
        }

    @classmethod
    def from_payload(cls, payload: object) -> TransitionControlRecord:
        """Parse only complete exact durable records; all deviations are corruption."""
        required = {
            "binding_digest",
            "control_id",
            "control_key",
            "occurred_at",
            "record_digest",
            "request_digest",
            "schema_version",
            "state",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise TransitionControlEvidenceError("control record payload has unexpected fields")
        try:
            return cls(
                control_id=payload["control_id"],
                control_key=payload["control_key"],
                binding_digest=payload["binding_digest"],
                request_digest=payload["request_digest"],
                state=TransitionControlRecordState(payload["state"]),
                occurred_at=datetime.fromisoformat(payload["occurred_at"]),
                record_digest=payload["record_digest"],
                schema_version=payload["schema_version"],
            )
        except (KeyError, TypeError, ValueError, TransitionControlEvidenceError) as error:
            raise TransitionControlEvidenceError("invalid control record payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class TransitionControlFinding:
    """One typed evidence-only transition-control finding."""

    code: TransitionControlFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, TransitionControlFindingCode):
            raise TypeError("code must be a TransitionControlFindingCode")
        object.__setattr__(self, "evidence_reference", require_non_empty(self.evidence_reference, "evidence_reference"))

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class TransitionControlDecision:
    """Immutable control evidence with no permit, executor, destination, or release handle."""

    decision_id: str
    control_id: str | None
    control_key: str
    disposition: TransitionControlDisposition
    findings: tuple[TransitionControlFinding, ...]
    evidence_refs: tuple[str, ...]
    recommendations: tuple[str, ...]
    decision_digest: str
    timestamp: datetime
    schema_version: str = TRANSITION_CONTROL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", require_non_empty(self.decision_id, "decision_id"))
        if self.control_id is not None:
            object.__setattr__(self, "control_id", require_non_empty(self.control_id, "control_id"))
        object.__setattr__(self, "control_key", require_sha256(self.control_key, "control_key"))
        if not isinstance(self.disposition, TransitionControlDisposition):
            raise TypeError("disposition must be a TransitionControlDisposition")
        if any(not isinstance(finding, TransitionControlFinding) for finding in self.findings):
            raise TypeError("findings must contain TransitionControlFinding values")
        keys = tuple((finding.code.value, finding.evidence_reference) for finding in self.findings)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise TransitionControlEvidenceError("findings must be strictly ordered and unique")
        object.__setattr__(self, "evidence_refs", _ordered_unique_strings(self.evidence_refs, "evidence_refs", allow_empty=True))
        object.__setattr__(self, "recommendations", _ordered_unique_strings(self.recommendations, "recommendations", allow_empty=True))
        object.__setattr__(self, "decision_digest", require_sha256(self.decision_digest, "decision_digest"))
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != TRANSITION_CONTROL_SCHEMA_VERSION:
            raise TransitionControlEvidenceError("unsupported control decision schema_version")
        if self.decision_digest != self.calculate_digest():
            raise TransitionControlEvidenceError("decision_digest does not match canonical control decision")

    @classmethod
    def issue(
        cls,
        *,
        decision_id: str,
        request: ExternalTransitionControlRequest,
        control_id: str | None,
        disposition: TransitionControlDisposition,
        findings: tuple[TransitionControlFinding, ...],
        evidence_refs: tuple[str, ...],
        recommendations: tuple[str, ...],
        timestamp: datetime,
    ) -> TransitionControlDecision:
        canonical_time = canonical_timestamp(timestamp, "timestamp")
        payload = {
            "control_id": control_id,
            "control_key": request.control_key,
            "decision_id": decision_id,
            "disposition": disposition.value,
            "evidence_refs": list(evidence_refs),
            "findings": [finding.to_payload() for finding in findings],
            "recommendations": list(recommendations),
            "schema_version": TRANSITION_CONTROL_SCHEMA_VERSION,
            "timestamp": canonical_time.isoformat(),
        }
        return cls(
            decision_id=decision_id,
            control_id=control_id,
            control_key=request.control_key,
            disposition=disposition,
            findings=findings,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            decision_digest=canonical_digest(payload),
            timestamp=canonical_time,
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            {
                "control_id": self.control_id,
                "control_key": self.control_key,
                "decision_id": self.decision_id,
                "disposition": self.disposition.value,
                "evidence_refs": list(self.evidence_refs),
                "findings": [finding.to_payload() for finding in self.findings],
                "recommendations": list(self.recommendations),
                "schema_version": self.schema_version,
                "timestamp": self.timestamp.isoformat(),
            }
        )


__all__ = [
    "ExternalTransitionControlRequest",
    "TransitionControlDecision",
    "TransitionControlDisposition",
    "TransitionControlEvidenceError",
    "TransitionControlFinding",
    "TransitionControlFindingCode",
    "TransitionControlProfile",
    "TransitionControlRecord",
    "TransitionControlRecordState",
]
