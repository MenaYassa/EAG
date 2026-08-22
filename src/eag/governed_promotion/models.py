"""Immutable evidence-only contracts for G2.4.15 promotion eligibility assessment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from eag.governed_promotion.canonical import (
    PROMOTION_SCHEMA_VERSION,
    canonical_digest,
    canonical_timestamp,
    require_non_empty,
    require_sha256,
)


class PromotionEvidenceError(ValueError):
    """Raised when supplied promotion eligibility evidence is structurally invalid."""


class PromotionProfile(StrEnum):
    """The one narrow evidence-only transition profile supported by G2.4.15."""

    ARTIFACT_TRANSITION_ELIGIBILITY_V1 = "artifact_transition_eligibility_v1"


class PromotionEligibilityDisposition(StrEnum):
    """Evidence-only outcomes that never grant or perform a transition."""

    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    UNSUPPORTED_DESTINATION = "unsupported_destination"


class PromotionFindingCode(StrEnum):
    """Typed deterministic refusals produced without external interaction."""

    ARTIFACT_IDENTITY_MISMATCH = "artifact_identity_mismatch"
    NOT_READY_ARTIFACT = "not_ready_artifact"
    READINESS_EVIDENCE_INVALID = "readiness_evidence_invalid"
    LINEAGE_BINDING_MISMATCH = "lineage_binding_mismatch"
    UNSUPPORTED_DESTINATION = "unsupported_destination"
    DESTINATION_IDENTITY_INVALID = "destination_identity_invalid"
    UNSUPPORTED_PROFILE = "unsupported_profile"


_ALLOWED_DESTINATIONS = frozenset({"artifact-store-A", "internal-registry", "pypi-production"})
_FORBIDDEN_DESTINATION_MARKERS = ("://", "@", "token", "secret", "password", "credential", "auth")


def _validate_destination(value: str) -> str:
    """Retain the supplied identity for assessor-side fail-closed validation."""
    return require_non_empty(value, "destination_identity")


def is_supported_destination(value: str) -> bool:
    """Return whether an identity is one supported non-secret logical destination."""
    normalized = value.lower()
    return value in _ALLOWED_DESTINATIONS and not any(
        marker in normalized for marker in _FORBIDDEN_DESTINATION_MARKERS
    )


def _ordered_unique_strings(
    values: tuple[str, ...], field_name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise PromotionEvidenceError(f"{field_name} must be a tuple")
    normalized = tuple(require_non_empty(value, field_name) for value in values)
    if not allow_empty and not normalized:
        raise PromotionEvidenceError(f"{field_name} cannot be empty")
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise PromotionEvidenceError(f"{field_name} must be strictly ordered and unique")
    return normalized


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactLineageReference:
    """A declared evidence linkage, never a claim that a runtime physically produced an artifact."""

    artifact_identity: str
    source_evidence_refs: tuple[str, ...]
    composition_reference: str | None
    readiness_reference: str
    custody_reference: str | None
    lineage_digest: str
    schema_version: str = PROMOTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_identity", require_non_empty(self.artifact_identity, "artifact_identity"))
        object.__setattr__(
            self,
            "source_evidence_refs",
            _ordered_unique_strings(self.source_evidence_refs, "source_evidence_refs"),
        )
        for field_name in ("composition_reference", "custody_reference"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_non_empty(value, field_name))
        object.__setattr__(
            self, "readiness_reference", require_non_empty(self.readiness_reference, "readiness_reference")
        )
        object.__setattr__(self, "lineage_digest", require_sha256(self.lineage_digest, "lineage_digest"))
        if self.schema_version != PROMOTION_SCHEMA_VERSION:
            raise PromotionEvidenceError("unsupported lineage schema_version")

    @classmethod
    def declare(
        cls,
        *,
        artifact_identity: str,
        source_evidence_refs: tuple[str, ...],
        composition_reference: str | None,
        readiness_reference: str,
        custody_reference: str | None,
    ) -> ArtifactLineageReference:
        normalized_sources = _ordered_unique_strings(source_evidence_refs, "source_evidence_refs")
        payload = {
            "artifact_identity": artifact_identity,
            "composition_reference": composition_reference,
            "custody_reference": custody_reference,
            "readiness_reference": readiness_reference,
            "schema_version": PROMOTION_SCHEMA_VERSION,
            "source_evidence_refs": list(normalized_sources),
        }
        return cls(
            artifact_identity=artifact_identity,
            source_evidence_refs=normalized_sources,
            composition_reference=composition_reference,
            readiness_reference=readiness_reference,
            custody_reference=custody_reference,
            lineage_digest=canonical_digest(payload),
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            {
                "artifact_identity": self.artifact_identity,
                "composition_reference": self.composition_reference,
                "custody_reference": self.custody_reference,
                "readiness_reference": self.readiness_reference,
                "schema_version": self.schema_version,
                "source_evidence_refs": list(self.source_evidence_refs),
            }
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PromotionEligibilityRequest:
    """Immutable transition intent; it is not a permit, approval, reservation, or promotion command."""

    intent_id: str
    artifact_id: str
    artifact_fingerprint: str
    readiness_evidence_reference: str
    lineage_reference: str
    destination_identity: str
    promotion_policy_digest: str
    promotion_profile: PromotionProfile | str
    schema_version: str = PROMOTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "intent_id",
            "artifact_id",
            "readiness_evidence_reference",
            "lineage_reference",
        ):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        object.__setattr__(
            self, "artifact_fingerprint", require_sha256(self.artifact_fingerprint, "artifact_fingerprint")
        )
        object.__setattr__(self, "destination_identity", _validate_destination(self.destination_identity))
        object.__setattr__(
            self,
            "promotion_policy_digest",
            require_sha256(self.promotion_policy_digest, "promotion_policy_digest"),
        )
        if not isinstance(self.promotion_profile, (PromotionProfile, str)):
            raise PromotionEvidenceError("promotion_profile must be a PromotionProfile or non-empty string")
        if isinstance(self.promotion_profile, str) and not isinstance(
            self.promotion_profile, PromotionProfile
        ):
            object.__setattr__(
                self,
                "promotion_profile",
                require_non_empty(self.promotion_profile, "promotion_profile"),
            )
        if self.schema_version != PROMOTION_SCHEMA_VERSION:
            raise PromotionEvidenceError("unsupported request schema_version")


@dataclass(frozen=True, slots=True, kw_only=True)
class PromotionEligibilityFinding:
    """One typed finding from the evidence-only promotion eligibility boundary."""

    code: PromotionFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, PromotionFindingCode):
            raise TypeError("code must be a PromotionFindingCode")
        object.__setattr__(
            self, "evidence_reference", require_non_empty(self.evidence_reference, "evidence_reference")
        )

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class PromotionEligibilityAssessment:
    """Immutable eligibility evidence with no operational method or transition state authority."""

    assessment_id: str
    artifact_identity: str
    destination_identity: str
    disposition: PromotionEligibilityDisposition
    findings: tuple[PromotionEligibilityFinding, ...]
    evidence_refs: tuple[str, ...]
    recommendations: tuple[str, ...]
    assessment_digest: str
    timestamp: datetime
    schema_version: str = PROMOTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("assessment_id", "artifact_identity"):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        object.__setattr__(self, "destination_identity", _validate_destination(self.destination_identity))
        if not isinstance(self.disposition, PromotionEligibilityDisposition):
            raise TypeError("disposition must be a PromotionEligibilityDisposition")
        if any(not isinstance(finding, PromotionEligibilityFinding) for finding in self.findings):
            raise TypeError("findings must contain PromotionEligibilityFinding values")
        finding_keys = tuple((finding.code.value, finding.evidence_reference) for finding in self.findings)
        if finding_keys != tuple(sorted(finding_keys)) or len(set(finding_keys)) != len(finding_keys):
            raise PromotionEvidenceError("findings must be strictly ordered and unique")
        object.__setattr__(self, "evidence_refs", _ordered_unique_strings(self.evidence_refs, "evidence_refs"))
        object.__setattr__(
            self,
            "recommendations",
            _ordered_unique_strings(self.recommendations, "recommendations", allow_empty=True),
        )
        object.__setattr__(
            self, "assessment_digest", require_sha256(self.assessment_digest, "assessment_digest")
        )
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != PROMOTION_SCHEMA_VERSION:
            raise PromotionEvidenceError("unsupported assessment schema_version")
        if self.assessment_digest != self.calculate_digest():
            raise PromotionEvidenceError("assessment_digest does not match canonical assessment")

    @classmethod
    def issue(
        cls,
        *,
        assessment_id: str,
        artifact_identity: str,
        destination_identity: str,
        disposition: PromotionEligibilityDisposition,
        findings: tuple[PromotionEligibilityFinding, ...],
        evidence_refs: tuple[str, ...],
        recommendations: tuple[str, ...],
        timestamp: datetime,
    ) -> PromotionEligibilityAssessment:
        canonical_time = canonical_timestamp(timestamp, "timestamp")
        payload = {
            "artifact_identity": artifact_identity,
            "assessment_id": assessment_id,
            "destination_identity": destination_identity,
            "disposition": disposition.value,
            "evidence_refs": list(evidence_refs),
            "findings": [finding.to_payload() for finding in findings],
            "recommendations": list(recommendations),
            "schema_version": PROMOTION_SCHEMA_VERSION,
            "timestamp": canonical_time.isoformat(),
        }
        return cls(
            assessment_id=assessment_id,
            artifact_identity=artifact_identity,
            destination_identity=destination_identity,
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
                "artifact_identity": self.artifact_identity,
                "assessment_id": self.assessment_id,
                "destination_identity": self.destination_identity,
                "disposition": self.disposition.value,
                "evidence_refs": list(self.evidence_refs),
                "findings": [finding.to_payload() for finding in self.findings],
                "recommendations": list(self.recommendations),
                "schema_version": self.schema_version,
                "timestamp": self.timestamp.isoformat(),
            }
        )


__all__ = [
    "ArtifactLineageReference",
    "PromotionEligibilityAssessment",
    "PromotionEligibilityDisposition",
    "PromotionEligibilityFinding",
    "PromotionEligibilityRequest",
    "PromotionEvidenceError",
    "PromotionFindingCode",
    "PromotionProfile",
    "is_supported_destination",
]
