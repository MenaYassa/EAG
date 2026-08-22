"""Immutable evidence-only contracts for G2.4.16 external transition authorization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from eag.governed_transition_authorization.canonical import (
    TRANSITION_AUTHORIZATION_SCHEMA_VERSION,
    canonical_digest,
    canonical_timestamp,
    require_non_empty,
    require_sha256,
)


class TransitionAuthorizationEvidenceError(ValueError):
    """Raised when supplied transition authorization evidence is structurally invalid."""


class ExternalTransitionProfile(StrEnum):
    """The one evidence-only external transition profile supported by G2.4.16."""

    EXTERNAL_ARTIFACT_TRANSITION_V1 = "external_artifact_transition_v1"


class HumanAuthorizationDecision(StrEnum):
    """The explicit human decision represented by an immutable evidence receipt."""

    AUTHORIZED = "authorized"
    DENIED = "denied"


class TransitionAuthorizationDisposition(StrEnum):
    """Evidence-only authorization conclusions that grant no executable capability."""

    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not_authorized"
    UNSUPPORTED_TRANSITION = "unsupported_transition"


class TransitionAuthorizationFindingCode(StrEnum):
    """Typed fail-closed findings produced without external interaction."""

    ELIGIBILITY_EVIDENCE_INVALID = "eligibility_evidence_invalid"
    TRANSITION_INTENT_BINDING_MISMATCH = "transition_intent_binding_mismatch"
    ARTIFACT_IDENTITY_MISMATCH = "artifact_identity_mismatch"
    DESTINATION_BINDING_MISMATCH = "destination_binding_mismatch"
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_DENIED = "authorization_denied"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    AUTHORIZATION_BINDING_MISMATCH = "authorization_binding_mismatch"
    AUTHORIZATION_DUPLICATE = "authorization_duplicate"
    AUTHORIZATION_CONFLICT = "authorization_conflict"
    AUTHORIZATION_STORE_UNAVAILABLE = "authorization_store_unavailable"
    AUTHORIZATION_STORE_CORRUPT = "authorization_store_corrupt"
    IDEMPOTENCY_KEY_INVALID = "idempotency_key_invalid"
    UNSUPPORTED_TRANSITION_PROFILE = "unsupported_transition_profile"


def _ordered_unique_strings(
    values: tuple[str, ...], field_name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TransitionAuthorizationEvidenceError(f"{field_name} must be a tuple")
    normalized = tuple(require_non_empty(value, field_name) for value in values)
    if not allow_empty and not normalized:
        raise TransitionAuthorizationEvidenceError(f"{field_name} cannot be empty")
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise TransitionAuthorizationEvidenceError(f"{field_name} must be strictly ordered and unique")
    return normalized


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalTransitionIntentEvidence:
    """Immutable transition intent; it has no destination client, permit, or execution method."""

    transition_intent_id: str
    artifact_id: str
    artifact_fingerprint: str
    destination_identity: str
    eligibility_assessment_id: str
    eligibility_assessment_digest: str
    promotion_policy_digest: str
    authorization_policy_digest: str
    idempotency_key: str
    transition_profile: ExternalTransitionProfile | str
    execution_id: str | None = None
    run_id: str | None = None
    schema_version: str = TRANSITION_AUTHORIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "transition_intent_id",
            "artifact_id",
            "destination_identity",
            "eligibility_assessment_id",
            "idempotency_key",
        ):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        for field_name in (
            "artifact_fingerprint",
            "eligibility_assessment_digest",
            "promotion_policy_digest",
            "authorization_policy_digest",
        ):
            object.__setattr__(self, field_name, require_sha256(getattr(self, field_name), field_name))
        for field_name in ("execution_id", "run_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_non_empty(value, field_name))
        if not isinstance(self.transition_profile, (ExternalTransitionProfile, str)):
            raise TransitionAuthorizationEvidenceError(
                "transition_profile must be an ExternalTransitionProfile or non-empty string"
            )
        if isinstance(self.transition_profile, str) and not isinstance(
            self.transition_profile, ExternalTransitionProfile
        ):
            object.__setattr__(
                self,
                "transition_profile",
                require_non_empty(self.transition_profile, "transition_profile"),
            )
        if self.schema_version != TRANSITION_AUTHORIZATION_SCHEMA_VERSION:
            raise TransitionAuthorizationEvidenceError("unsupported transition intent schema_version")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalTransitionAuthorizationReceipt:
    """Self-validating, redacted human decision evidence; it is not a permit or execution command."""

    authorization_id: str
    approver_identity: str
    decision: HumanAuthorizationDecision
    occurred_at: datetime
    expires_at: datetime
    transition_intent_id: str
    artifact_id: str
    artifact_fingerprint: str
    destination_identity: str
    eligibility_assessment_id: str
    eligibility_assessment_digest: str
    promotion_policy_digest: str
    authorization_policy_digest: str
    execution_id: str | None
    run_id: str | None
    binding_digest: str
    schema_version: str = TRANSITION_AUTHORIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "authorization_id",
            "approver_identity",
            "transition_intent_id",
            "artifact_id",
            "destination_identity",
            "eligibility_assessment_id",
        ):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        for field_name in (
            "artifact_fingerprint",
            "eligibility_assessment_digest",
            "promotion_policy_digest",
            "authorization_policy_digest",
            "binding_digest",
        ):
            object.__setattr__(self, field_name, require_sha256(getattr(self, field_name), field_name))
        for field_name in ("execution_id", "run_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_non_empty(value, field_name))
        if not isinstance(self.decision, HumanAuthorizationDecision):
            raise TypeError("decision must be a HumanAuthorizationDecision")
        object.__setattr__(self, "occurred_at", canonical_timestamp(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "expires_at", canonical_timestamp(self.expires_at, "expires_at"))
        if self.expires_at <= self.occurred_at:
            raise TransitionAuthorizationEvidenceError("expires_at must be after occurred_at")
        if self.schema_version != TRANSITION_AUTHORIZATION_SCHEMA_VERSION:
            raise TransitionAuthorizationEvidenceError("unsupported authorization receipt schema_version")
        if self.binding_digest != self.calculate_binding_digest():
            raise TransitionAuthorizationEvidenceError("binding_digest does not match canonical authorization receipt")

    @classmethod
    def issue(
        cls,
        *,
        authorization_id: str,
        approver_identity: str,
        decision: HumanAuthorizationDecision,
        occurred_at: datetime,
        expires_at: datetime,
        transition_intent: ExternalTransitionIntentEvidence,
    ) -> ExternalTransitionAuthorizationReceipt:
        if not isinstance(transition_intent, ExternalTransitionIntentEvidence):
            raise TypeError("transition_intent must be an ExternalTransitionIntentEvidence")
        canonical_occurred = canonical_timestamp(occurred_at, "occurred_at")
        canonical_expires = canonical_timestamp(expires_at, "expires_at")
        payload = _receipt_payload(
            authorization_id=authorization_id,
            approver_identity=approver_identity,
            decision=decision,
            occurred_at=canonical_occurred,
            expires_at=canonical_expires,
            transition_intent=transition_intent,
            schema_version=TRANSITION_AUTHORIZATION_SCHEMA_VERSION,
        )
        return cls(
            authorization_id=authorization_id,
            approver_identity=approver_identity,
            decision=decision,
            occurred_at=canonical_occurred,
            expires_at=canonical_expires,
            transition_intent_id=transition_intent.transition_intent_id,
            artifact_id=transition_intent.artifact_id,
            artifact_fingerprint=transition_intent.artifact_fingerprint,
            destination_identity=transition_intent.destination_identity,
            eligibility_assessment_id=transition_intent.eligibility_assessment_id,
            eligibility_assessment_digest=transition_intent.eligibility_assessment_digest,
            promotion_policy_digest=transition_intent.promotion_policy_digest,
            authorization_policy_digest=transition_intent.authorization_policy_digest,
            execution_id=transition_intent.execution_id,
            run_id=transition_intent.run_id,
            binding_digest=canonical_digest(payload),
        )

    def calculate_binding_digest(self) -> str:
        return canonical_digest(
            {
                "approver_identity": self.approver_identity,
                "artifact_fingerprint": self.artifact_fingerprint,
                "artifact_id": self.artifact_id,
                "authorization_id": self.authorization_id,
                "authorization_policy_digest": self.authorization_policy_digest,
                "decision": self.decision.value,
                "destination_identity": self.destination_identity,
                "eligibility_assessment_digest": self.eligibility_assessment_digest,
                "eligibility_assessment_id": self.eligibility_assessment_id,
                "execution_id": self.execution_id,
                "expires_at": self.expires_at.isoformat(),
                "occurred_at": self.occurred_at.isoformat(),
                "promotion_policy_digest": self.promotion_policy_digest,
                "run_id": self.run_id,
                "schema_version": self.schema_version,
                "transition_intent_id": self.transition_intent_id,
            }
        )

    def to_payload(self) -> dict[str, str | None]:
        """Return the exact durable redacted evidence representation."""
        return {
            "approver_identity": self.approver_identity,
            "artifact_fingerprint": self.artifact_fingerprint,
            "artifact_id": self.artifact_id,
            "authorization_id": self.authorization_id,
            "authorization_policy_digest": self.authorization_policy_digest,
            "binding_digest": self.binding_digest,
            "decision": self.decision.value,
            "destination_identity": self.destination_identity,
            "eligibility_assessment_digest": self.eligibility_assessment_digest,
            "eligibility_assessment_id": self.eligibility_assessment_id,
            "execution_id": self.execution_id,
            "expires_at": self.expires_at.isoformat(),
            "occurred_at": self.occurred_at.isoformat(),
            "promotion_policy_digest": self.promotion_policy_digest,
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "transition_intent_id": self.transition_intent_id,
        }

    @classmethod
    def from_payload(cls, payload: object) -> ExternalTransitionAuthorizationReceipt:
        """Parse only exact canonical durable evidence; deviations are corruption."""
        required = {
            "approver_identity",
            "artifact_fingerprint",
            "artifact_id",
            "authorization_id",
            "authorization_policy_digest",
            "binding_digest",
            "decision",
            "destination_identity",
            "eligibility_assessment_digest",
            "eligibility_assessment_id",
            "execution_id",
            "expires_at",
            "occurred_at",
            "promotion_policy_digest",
            "run_id",
            "schema_version",
            "transition_intent_id",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise TransitionAuthorizationEvidenceError("authorization payload has unexpected fields")
        try:
            return cls(
                authorization_id=payload["authorization_id"],
                approver_identity=payload["approver_identity"],
                decision=HumanAuthorizationDecision(payload["decision"]),
                occurred_at=datetime.fromisoformat(payload["occurred_at"]),
                expires_at=datetime.fromisoformat(payload["expires_at"]),
                transition_intent_id=payload["transition_intent_id"],
                artifact_id=payload["artifact_id"],
                artifact_fingerprint=payload["artifact_fingerprint"],
                destination_identity=payload["destination_identity"],
                eligibility_assessment_id=payload["eligibility_assessment_id"],
                eligibility_assessment_digest=payload["eligibility_assessment_digest"],
                promotion_policy_digest=payload["promotion_policy_digest"],
                authorization_policy_digest=payload["authorization_policy_digest"],
                execution_id=payload["execution_id"],
                run_id=payload["run_id"],
                binding_digest=payload["binding_digest"],
                schema_version=payload["schema_version"],
            )
        except (KeyError, TypeError, ValueError, TransitionAuthorizationEvidenceError) as error:
            raise TransitionAuthorizationEvidenceError("invalid authorization payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class TransitionAuthorizationFinding:
    """One typed evidence-only authorization finding."""

    code: TransitionAuthorizationFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, TransitionAuthorizationFindingCode):
            raise TypeError("code must be a TransitionAuthorizationFindingCode")
        object.__setattr__(self, "evidence_reference", require_non_empty(self.evidence_reference, "evidence_reference"))

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class TransitionAuthorizationAssessment:
    """Immutable authorization evidence result with no permit, transition, or operational method."""

    assessment_id: str
    authorization_id: str | None
    artifact_id: str
    artifact_fingerprint: str
    destination_identity: str
    disposition: TransitionAuthorizationDisposition
    findings: tuple[TransitionAuthorizationFinding, ...]
    evidence_refs: tuple[str, ...]
    recommendations: tuple[str, ...]
    assessment_digest: str
    timestamp: datetime
    schema_version: str = TRANSITION_AUTHORIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("assessment_id", "artifact_id", "destination_identity"):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        if self.authorization_id is not None:
            object.__setattr__(self, "authorization_id", require_non_empty(self.authorization_id, "authorization_id"))
        object.__setattr__(self, "artifact_fingerprint", require_sha256(self.artifact_fingerprint, "artifact_fingerprint"))
        if not isinstance(self.disposition, TransitionAuthorizationDisposition):
            raise TypeError("disposition must be a TransitionAuthorizationDisposition")
        if any(not isinstance(finding, TransitionAuthorizationFinding) for finding in self.findings):
            raise TypeError("findings must contain TransitionAuthorizationFinding values")
        keys = tuple((finding.code.value, finding.evidence_reference) for finding in self.findings)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise TransitionAuthorizationEvidenceError("findings must be strictly ordered and unique")
        object.__setattr__(self, "evidence_refs", _ordered_unique_strings(self.evidence_refs, "evidence_refs", allow_empty=True))
        object.__setattr__(self, "recommendations", _ordered_unique_strings(self.recommendations, "recommendations", allow_empty=True))
        object.__setattr__(self, "assessment_digest", require_sha256(self.assessment_digest, "assessment_digest"))
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != TRANSITION_AUTHORIZATION_SCHEMA_VERSION:
            raise TransitionAuthorizationEvidenceError("unsupported assessment schema_version")
        if self.assessment_digest != self.calculate_digest():
            raise TransitionAuthorizationEvidenceError("assessment_digest does not match canonical assessment")

    @classmethod
    def issue(
        cls,
        *,
        assessment_id: str,
        authorization_id: str | None,
        intent: ExternalTransitionIntentEvidence,
        disposition: TransitionAuthorizationDisposition,
        findings: tuple[TransitionAuthorizationFinding, ...],
        evidence_refs: tuple[str, ...],
        recommendations: tuple[str, ...],
        timestamp: datetime,
    ) -> TransitionAuthorizationAssessment:
        canonical_time = canonical_timestamp(timestamp, "timestamp")
        payload = {
            "artifact_fingerprint": intent.artifact_fingerprint,
            "artifact_id": intent.artifact_id,
            "assessment_id": assessment_id,
            "authorization_id": authorization_id,
            "destination_identity": intent.destination_identity,
            "disposition": disposition.value,
            "evidence_refs": list(evidence_refs),
            "findings": [finding.to_payload() for finding in findings],
            "recommendations": list(recommendations),
            "schema_version": TRANSITION_AUTHORIZATION_SCHEMA_VERSION,
            "timestamp": canonical_time.isoformat(),
        }
        return cls(
            assessment_id=assessment_id,
            authorization_id=authorization_id,
            artifact_id=intent.artifact_id,
            artifact_fingerprint=intent.artifact_fingerprint,
            destination_identity=intent.destination_identity,
            disposition=disposition,
            findings=findings,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            assessment_digest=canonical_digest(payload),
            timestamp=canonical_time,
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            {
                "artifact_fingerprint": self.artifact_fingerprint,
                "artifact_id": self.artifact_id,
                "assessment_id": self.assessment_id,
                "authorization_id": self.authorization_id,
                "destination_identity": self.destination_identity,
                "disposition": self.disposition.value,
                "evidence_refs": list(self.evidence_refs),
                "findings": [finding.to_payload() for finding in self.findings],
                "recommendations": list(self.recommendations),
                "schema_version": self.schema_version,
                "timestamp": self.timestamp.isoformat(),
            }
        )


def _receipt_payload(
    *,
    authorization_id: str,
    approver_identity: str,
    decision: HumanAuthorizationDecision,
    occurred_at: datetime,
    expires_at: datetime,
    transition_intent: ExternalTransitionIntentEvidence,
    schema_version: str,
) -> dict[str, str | None]:
    return {
        "approver_identity": approver_identity,
        "artifact_fingerprint": transition_intent.artifact_fingerprint,
        "artifact_id": transition_intent.artifact_id,
        "authorization_id": authorization_id,
        "authorization_policy_digest": transition_intent.authorization_policy_digest,
        "decision": decision.value,
        "destination_identity": transition_intent.destination_identity,
        "eligibility_assessment_digest": transition_intent.eligibility_assessment_digest,
        "eligibility_assessment_id": transition_intent.eligibility_assessment_id,
        "execution_id": transition_intent.execution_id,
        "expires_at": expires_at.isoformat(),
        "occurred_at": occurred_at.isoformat(),
        "promotion_policy_digest": transition_intent.promotion_policy_digest,
        "run_id": transition_intent.run_id,
        "schema_version": schema_version,
        "transition_intent_id": transition_intent.transition_intent_id,
    }


__all__ = [
    "ExternalTransitionAuthorizationReceipt",
    "ExternalTransitionIntentEvidence",
    "ExternalTransitionProfile",
    "HumanAuthorizationDecision",
    "TransitionAuthorizationAssessment",
    "TransitionAuthorizationDisposition",
    "TransitionAuthorizationEvidenceError",
    "TransitionAuthorizationFinding",
    "TransitionAuthorizationFindingCode",
]
