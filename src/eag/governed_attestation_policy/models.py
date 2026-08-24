"""Immutable G2.4.20 destination-contract attestation-policy evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from eag.governed_attestation_policy.canonical import (
    ATTESTATION_POLICY_SCHEMA_VERSION,
    AttestationPolicyEvidenceError,
    canonical_digest,
    canonical_timestamp,
    require_identifier,
    require_non_empty,
    require_sha256,
)
from eag.governed_destination_contract import (
    DestinationContractAssessment,
    DestinationContractAssessmentRequest,
)
from eag.governed_outcome_policy import (
    OutcomeSemanticsAssessment,
    OutcomeSemanticsAssessmentRequest,
)


class AttestationPolicyProfile(StrEnum):
    """The sole static profile for declared issuer/reference policy evidence."""

    DECLARED_ATTESTATION_POLICY_V1 = "declared_attestation_policy_v1"


class AttestationPolicyDisposition(StrEnum):
    """Evidence-only outcomes; neither establishes trust nor execution readiness."""

    ATTESTATION_POLICY_ATTESTED = "attestation_policy_attested"
    NOT_ATTESTED = "not_attested"
    UNSUPPORTED_ATTESTATION_POLICY = "unsupported_attestation_policy"


class AttestationPolicyFindingCode(StrEnum):
    """Typed deterministic findings without authentication or external operation claims."""

    POLICY_EVIDENCE_INVALID = "policy_evidence_invalid"
    POLICY_EXPIRED = "policy_expired"
    CONTRACT_ASSESSMENT_INVALID = "contract_assessment_invalid"
    CONTRACT_BINDING_MISMATCH = "contract_binding_mismatch"
    OUTCOME_POLICY_ASSESSMENT_INVALID = "outcome_policy_assessment_invalid"
    OUTCOME_POLICY_BINDING_MISMATCH = "outcome_policy_binding_mismatch"
    DESTINATION_BINDING_MISMATCH = "destination_binding_mismatch"
    ATTESTATION_ISSUER_BINDING_MISMATCH = "attestation_issuer_binding_mismatch"
    ATTESTATION_REFERENCE_BINDING_MISMATCH = "attestation_reference_binding_mismatch"
    UNSUPPORTED_ATTESTATION_PROFILE = "unsupported_attestation_profile"


def _enum_value(value: StrEnum | str, field_name: str) -> str:
    if not isinstance(value, (StrEnum, str)):
        raise AttestationPolicyEvidenceError(f"{field_name} must be a declaration identifier")
    return require_identifier(value.value if isinstance(value, StrEnum) else value, field_name)


def _ordered_unique_values(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise AttestationPolicyEvidenceError(f"{field_name} must be a tuple")
    normalized = tuple(require_non_empty(value, field_name) for value in values)
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise AttestationPolicyEvidenceError(f"{field_name} must be strictly ordered and unique")
    return normalized


@dataclass(frozen=True, slots=True, kw_only=True)
class DestinationContractAttestationPolicyEvidence:
    """Immutable policy for declared G2.4.18 attestation metadata, never trust evidence.

    This declaration neither authenticates an issuer nor establishes contract, destination,
    signature, source, or external truth. It contains no key, certificate, endpoint,
    account, credential, request, receipt, completion, or operational handle.
    """

    attestation_policy_id: str
    destination_contract_id: str
    destination_contract_digest: str
    destination_contract_assessment_id: str
    destination_contract_assessment_digest: str
    outcome_policy_id: str
    outcome_policy_digest: str
    outcome_policy_assessment_id: str
    outcome_policy_assessment_digest: str
    destination_identity: str
    declared_attestation_issuer_identity: str
    declared_attestation_reference: str
    attestation_policy_profile: AttestationPolicyProfile | str
    issued_at: datetime
    expires_at: datetime
    policy_digest: str
    schema_version: str = ATTESTATION_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "attestation_policy_id",
            "destination_contract_id",
            "destination_contract_assessment_id",
            "outcome_policy_id",
            "outcome_policy_assessment_id",
            "destination_identity",
            "declared_attestation_issuer_identity",
            "declared_attestation_reference",
        ):
            object.__setattr__(self, field_name, require_identifier(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "attestation_policy_profile",
            _enum_value(self.attestation_policy_profile, "attestation_policy_profile"),
        )
        for field_name in (
            "destination_contract_digest",
            "destination_contract_assessment_digest",
            "outcome_policy_digest",
            "outcome_policy_assessment_digest",
        ):
            object.__setattr__(self, field_name, require_sha256(getattr(self, field_name), field_name))
        object.__setattr__(self, "issued_at", canonical_timestamp(self.issued_at, "issued_at"))
        object.__setattr__(self, "expires_at", canonical_timestamp(self.expires_at, "expires_at"))
        if self.expires_at <= self.issued_at:
            raise AttestationPolicyEvidenceError("expires_at must be after issued_at")
        if self.schema_version != ATTESTATION_POLICY_SCHEMA_VERSION:
            raise AttestationPolicyEvidenceError("unsupported attestation policy schema_version")
        object.__setattr__(self, "policy_digest", require_sha256(self.policy_digest, "policy_digest"))
        if self.policy_digest != self.calculate_digest():
            raise AttestationPolicyEvidenceError("policy_digest does not match canonical attestation policy evidence")

    @classmethod
    def issue(
        cls,
        *,
        attestation_policy_id: str,
        destination_contract_id: str,
        destination_contract_digest: str,
        destination_contract_assessment_id: str,
        destination_contract_assessment_digest: str,
        outcome_policy_id: str,
        outcome_policy_digest: str,
        outcome_policy_assessment_id: str,
        outcome_policy_assessment_digest: str,
        destination_identity: str,
        declared_attestation_issuer_identity: str,
        declared_attestation_reference: str,
        attestation_policy_profile: AttestationPolicyProfile | str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> DestinationContractAttestationPolicyEvidence:
        canonical_issued = canonical_timestamp(issued_at, "issued_at")
        canonical_expires = canonical_timestamp(expires_at, "expires_at")
        payload = _policy_payload(
            attestation_policy_id=attestation_policy_id,
            destination_contract_id=destination_contract_id,
            destination_contract_digest=destination_contract_digest,
            destination_contract_assessment_id=destination_contract_assessment_id,
            destination_contract_assessment_digest=destination_contract_assessment_digest,
            outcome_policy_id=outcome_policy_id,
            outcome_policy_digest=outcome_policy_digest,
            outcome_policy_assessment_id=outcome_policy_assessment_id,
            outcome_policy_assessment_digest=outcome_policy_assessment_digest,
            destination_identity=destination_identity,
            declared_attestation_issuer_identity=declared_attestation_issuer_identity,
            declared_attestation_reference=declared_attestation_reference,
            attestation_policy_profile=attestation_policy_profile,
            issued_at=canonical_issued,
            expires_at=canonical_expires,
            schema_version=ATTESTATION_POLICY_SCHEMA_VERSION,
        )
        return cls(
            attestation_policy_id=attestation_policy_id,
            destination_contract_id=destination_contract_id,
            destination_contract_digest=destination_contract_digest,
            destination_contract_assessment_id=destination_contract_assessment_id,
            destination_contract_assessment_digest=destination_contract_assessment_digest,
            outcome_policy_id=outcome_policy_id,
            outcome_policy_digest=outcome_policy_digest,
            outcome_policy_assessment_id=outcome_policy_assessment_id,
            outcome_policy_assessment_digest=outcome_policy_assessment_digest,
            destination_identity=destination_identity,
            declared_attestation_issuer_identity=declared_attestation_issuer_identity,
            declared_attestation_reference=declared_attestation_reference,
            attestation_policy_profile=attestation_policy_profile,
            issued_at=canonical_issued,
            expires_at=canonical_expires,
            policy_digest=canonical_digest(payload),
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            _policy_payload(
                attestation_policy_id=self.attestation_policy_id,
                destination_contract_id=self.destination_contract_id,
                destination_contract_digest=self.destination_contract_digest,
                destination_contract_assessment_id=self.destination_contract_assessment_id,
                destination_contract_assessment_digest=self.destination_contract_assessment_digest,
                outcome_policy_id=self.outcome_policy_id,
                outcome_policy_digest=self.outcome_policy_digest,
                outcome_policy_assessment_id=self.outcome_policy_assessment_id,
                outcome_policy_assessment_digest=self.outcome_policy_assessment_digest,
                destination_identity=self.destination_identity,
                declared_attestation_issuer_identity=self.declared_attestation_issuer_identity,
                declared_attestation_reference=self.declared_attestation_reference,
                attestation_policy_profile=self.attestation_policy_profile,
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                schema_version=self.schema_version,
            )
        )

    def to_payload(self) -> dict[str, str]:
        return {
            **_policy_payload(
                attestation_policy_id=self.attestation_policy_id,
                destination_contract_id=self.destination_contract_id,
                destination_contract_digest=self.destination_contract_digest,
                destination_contract_assessment_id=self.destination_contract_assessment_id,
                destination_contract_assessment_digest=self.destination_contract_assessment_digest,
                outcome_policy_id=self.outcome_policy_id,
                outcome_policy_digest=self.outcome_policy_digest,
                outcome_policy_assessment_id=self.outcome_policy_assessment_id,
                outcome_policy_assessment_digest=self.outcome_policy_assessment_digest,
                destination_identity=self.destination_identity,
                declared_attestation_issuer_identity=self.declared_attestation_issuer_identity,
                declared_attestation_reference=self.declared_attestation_reference,
                attestation_policy_profile=self.attestation_policy_profile,
                issued_at=self.issued_at,
                expires_at=self.expires_at,
                schema_version=self.schema_version,
            ),
            "policy_digest": self.policy_digest,
        }

    @classmethod
    def from_payload(cls, payload: object) -> DestinationContractAttestationPolicyEvidence:
        required = {
            "attestation_policy_id",
            "attestation_policy_profile",
            "declared_attestation_issuer_identity",
            "declared_attestation_reference",
            "destination_contract_assessment_digest",
            "destination_contract_assessment_id",
            "destination_contract_digest",
            "destination_contract_id",
            "destination_identity",
            "expires_at",
            "issued_at",
            "outcome_policy_assessment_digest",
            "outcome_policy_assessment_id",
            "outcome_policy_digest",
            "outcome_policy_id",
            "policy_digest",
            "schema_version",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise AttestationPolicyEvidenceError("attestation policy payload has unexpected fields")
        try:
            return cls(
                attestation_policy_id=payload["attestation_policy_id"],
                destination_contract_id=payload["destination_contract_id"],
                destination_contract_digest=payload["destination_contract_digest"],
                destination_contract_assessment_id=payload["destination_contract_assessment_id"],
                destination_contract_assessment_digest=payload["destination_contract_assessment_digest"],
                outcome_policy_id=payload["outcome_policy_id"],
                outcome_policy_digest=payload["outcome_policy_digest"],
                outcome_policy_assessment_id=payload["outcome_policy_assessment_id"],
                outcome_policy_assessment_digest=payload["outcome_policy_assessment_digest"],
                destination_identity=payload["destination_identity"],
                declared_attestation_issuer_identity=payload["declared_attestation_issuer_identity"],
                declared_attestation_reference=payload["declared_attestation_reference"],
                attestation_policy_profile=payload["attestation_policy_profile"],
                issued_at=datetime.fromisoformat(payload["issued_at"]),
                expires_at=datetime.fromisoformat(payload["expires_at"]),
                policy_digest=payload["policy_digest"],
                schema_version=payload["schema_version"],
            )
        except (KeyError, TypeError, ValueError, AttestationPolicyEvidenceError) as error:
            raise AttestationPolicyEvidenceError("invalid attestation policy payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class AttestationPolicyAssessmentRequest:
    """Exact G2.4.18/G2.4.19 evidence plus one static policy declaration only."""

    assessment_request_id: str
    destination_contract_request: DestinationContractAssessmentRequest
    destination_contract_assessment: DestinationContractAssessment
    outcome_policy_request: OutcomeSemanticsAssessmentRequest
    outcome_policy_assessment: OutcomeSemanticsAssessment
    policy: DestinationContractAttestationPolicyEvidence
    timestamp: datetime
    request_digest: str | None = None
    schema_version: str = ATTESTATION_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assessment_request_id",
            require_identifier(self.assessment_request_id, "assessment_request_id"),
        )
        for field_name, expected_type in (
            ("destination_contract_request", DestinationContractAssessmentRequest),
            ("destination_contract_assessment", DestinationContractAssessment),
            ("outcome_policy_request", OutcomeSemanticsAssessmentRequest),
            ("outcome_policy_assessment", OutcomeSemanticsAssessment),
            ("policy", DestinationContractAttestationPolicyEvidence),
        ):
            if not isinstance(getattr(self, field_name), expected_type):
                raise TypeError(f"{field_name} must be an immutable {expected_type.__name__}")
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != ATTESTATION_POLICY_SCHEMA_VERSION:
            raise AttestationPolicyEvidenceError("unsupported attestation policy request schema_version")
        calculated = self.calculate_digest()
        if self.request_digest is None:
            object.__setattr__(self, "request_digest", calculated)
        else:
            object.__setattr__(self, "request_digest", require_sha256(self.request_digest, "request_digest"))
            if self.request_digest != calculated:
                raise AttestationPolicyEvidenceError(
                    "request_digest does not match canonical attestation policy request"
                )

    def calculate_digest(self) -> str:
        return canonical_digest(_request_payload(self))

    def to_payload(self) -> dict[str, Any]:
        return {**_request_payload(self), "request_digest": self.request_digest}


@dataclass(frozen=True, slots=True, kw_only=True)
class AttestationPolicyFinding:
    """One typed policy/evidence finding with no authentication or operational remediation."""

    code: AttestationPolicyFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, AttestationPolicyFindingCode):
            raise TypeError("code must be an AttestationPolicyFindingCode")
        object.__setattr__(
            self,
            "evidence_reference",
            require_non_empty(self.evidence_reference, "evidence_reference"),
        )

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class AttestationPolicyAssessment:
    """Immutable policy-only assessment, never issuer authentication or trust evidence."""

    assessment_id: str
    destination_identity: str
    policy_id: str | None
    disposition: AttestationPolicyDisposition
    findings: tuple[AttestationPolicyFinding, ...]
    evidence_refs: tuple[str, ...]
    recommendations: tuple[str, ...]
    assessment_digest: str
    timestamp: datetime
    schema_version: str = ATTESTATION_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "assessment_id", require_identifier(self.assessment_id, "assessment_id"))
        object.__setattr__(
            self,
            "destination_identity",
            require_identifier(self.destination_identity, "destination_identity"),
        )
        if self.policy_id is not None:
            object.__setattr__(self, "policy_id", require_identifier(self.policy_id, "policy_id"))
        if not isinstance(self.disposition, AttestationPolicyDisposition):
            raise TypeError("disposition must be an AttestationPolicyDisposition")
        if any(not isinstance(item, AttestationPolicyFinding) for item in self.findings):
            raise TypeError("findings must contain AttestationPolicyFinding values")
        finding_keys = tuple((item.code.value, item.evidence_reference) for item in self.findings)
        if finding_keys != tuple(sorted(finding_keys)) or len(set(finding_keys)) != len(finding_keys):
            raise AttestationPolicyEvidenceError("findings must be strictly ordered and unique")
        object.__setattr__(self, "evidence_refs", _ordered_unique_values(self.evidence_refs, "evidence_refs"))
        object.__setattr__(
            self,
            "recommendations",
            _ordered_unique_values(self.recommendations, "recommendations"),
        )
        object.__setattr__(self, "assessment_digest", require_sha256(self.assessment_digest, "assessment_digest"))
        object.__setattr__(self, "timestamp", canonical_timestamp(self.timestamp, "timestamp"))
        if self.schema_version != ATTESTATION_POLICY_SCHEMA_VERSION:
            raise AttestationPolicyEvidenceError("unsupported attestation policy assessment schema_version")
        if self.assessment_digest != self.calculate_digest():
            raise AttestationPolicyEvidenceError(
                "assessment_digest does not match canonical attestation policy assessment"
            )

    @classmethod
    def issue(
        cls,
        *,
        assessment_id: str,
        destination_identity: str,
        policy_id: str | None,
        disposition: AttestationPolicyDisposition,
        findings: tuple[AttestationPolicyFinding, ...],
        evidence_refs: tuple[str, ...],
        recommendations: tuple[str, ...],
        timestamp: datetime,
    ) -> AttestationPolicyAssessment:
        canonical_time = canonical_timestamp(timestamp, "timestamp")
        payload = _assessment_payload(
            assessment_id=assessment_id,
            destination_identity=destination_identity,
            policy_id=policy_id,
            disposition=disposition,
            findings=findings,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            timestamp=canonical_time,
            schema_version=ATTESTATION_POLICY_SCHEMA_VERSION,
        )
        return cls(
            assessment_id=assessment_id,
            destination_identity=destination_identity,
            policy_id=policy_id,
            disposition=disposition,
            findings=findings,
            evidence_refs=evidence_refs,
            recommendations=recommendations,
            assessment_digest=canonical_digest(payload),
            timestamp=canonical_time,
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            _assessment_payload(
                assessment_id=self.assessment_id,
                destination_identity=self.destination_identity,
                policy_id=self.policy_id,
                disposition=self.disposition,
                findings=self.findings,
                evidence_refs=self.evidence_refs,
                recommendations=self.recommendations,
                timestamp=self.timestamp,
                schema_version=self.schema_version,
            )
        )


def _policy_payload(
    *,
    attestation_policy_id: str,
    destination_contract_id: str,
    destination_contract_digest: str,
    destination_contract_assessment_id: str,
    destination_contract_assessment_digest: str,
    outcome_policy_id: str,
    outcome_policy_digest: str,
    outcome_policy_assessment_id: str,
    outcome_policy_assessment_digest: str,
    destination_identity: str,
    declared_attestation_issuer_identity: str,
    declared_attestation_reference: str,
    attestation_policy_profile: AttestationPolicyProfile | str,
    issued_at: datetime,
    expires_at: datetime,
    schema_version: str,
) -> dict[str, str]:
    return {
        "attestation_policy_id": require_identifier(attestation_policy_id, "attestation_policy_id"),
        "attestation_policy_profile": _enum_value(
            attestation_policy_profile,
            "attestation_policy_profile",
        ),
        "declared_attestation_issuer_identity": require_identifier(
            declared_attestation_issuer_identity,
            "declared_attestation_issuer_identity",
        ),
        "declared_attestation_reference": require_identifier(
            declared_attestation_reference,
            "declared_attestation_reference",
        ),
        "destination_contract_assessment_digest": require_sha256(
            destination_contract_assessment_digest,
            "destination_contract_assessment_digest",
        ),
        "destination_contract_assessment_id": require_identifier(
            destination_contract_assessment_id,
            "destination_contract_assessment_id",
        ),
        "destination_contract_digest": require_sha256(
            destination_contract_digest,
            "destination_contract_digest",
        ),
        "destination_contract_id": require_identifier(destination_contract_id, "destination_contract_id"),
        "destination_identity": require_identifier(destination_identity, "destination_identity"),
        "expires_at": canonical_timestamp(expires_at, "expires_at").isoformat(),
        "issued_at": canonical_timestamp(issued_at, "issued_at").isoformat(),
        "outcome_policy_assessment_digest": require_sha256(
            outcome_policy_assessment_digest,
            "outcome_policy_assessment_digest",
        ),
        "outcome_policy_assessment_id": require_identifier(
            outcome_policy_assessment_id,
            "outcome_policy_assessment_id",
        ),
        "outcome_policy_digest": require_sha256(outcome_policy_digest, "outcome_policy_digest"),
        "outcome_policy_id": require_identifier(outcome_policy_id, "outcome_policy_id"),
        "schema_version": schema_version,
    }


def _request_payload(request: AttestationPolicyAssessmentRequest) -> dict[str, Any]:
    contract_request = request.destination_contract_request
    contract_assessment = request.destination_contract_assessment
    outcome_request = request.outcome_policy_request
    outcome_assessment = request.outcome_policy_assessment
    policy = request.policy
    return {
        "destination_contract_assessment": {
            "assessment_digest": contract_assessment.assessment_digest,
            "assessment_id": contract_assessment.assessment_id,
            "disposition": contract_assessment.disposition.value,
            "schema_version": contract_assessment.schema_version,
        },
        "destination_contract_request": {
            "request_digest": contract_request.request_digest,
            "schema_version": contract_request.schema_version,
        },
        "outcome_policy_assessment": {
            "assessment_digest": outcome_assessment.assessment_digest,
            "assessment_id": outcome_assessment.assessment_id,
            "disposition": outcome_assessment.disposition.value,
            "schema_version": outcome_assessment.schema_version,
        },
        "outcome_policy_request": {
            "request_digest": outcome_request.request_digest,
            "schema_version": outcome_request.schema_version,
        },
        "policy": {
            "attestation_policy_id": policy.attestation_policy_id,
            "policy_digest": policy.policy_digest,
            "schema_version": policy.schema_version,
        },
        "schema_version": request.schema_version,
        "timestamp": request.timestamp.isoformat(),
    }


def _assessment_payload(
    *,
    assessment_id: str,
    destination_identity: str,
    policy_id: str | None,
    disposition: AttestationPolicyDisposition,
    findings: tuple[AttestationPolicyFinding, ...],
    evidence_refs: tuple[str, ...],
    recommendations: tuple[str, ...],
    timestamp: datetime,
    schema_version: str,
) -> dict[str, Any]:
    return {
        "assessment_id": assessment_id,
        "destination_identity": destination_identity,
        "disposition": disposition.value,
        "evidence_refs": list(evidence_refs),
        "findings": [item.to_payload() for item in findings],
        "policy_id": policy_id,
        "recommendations": list(recommendations),
        "schema_version": schema_version,
        "timestamp": canonical_timestamp(timestamp, "timestamp").isoformat(),
    }


__all__ = [
    "AttestationPolicyAssessment",
    "AttestationPolicyAssessmentRequest",
    "AttestationPolicyDisposition",
    "AttestationPolicyEvidenceError",
    "AttestationPolicyFinding",
    "AttestationPolicyFindingCode",
    "AttestationPolicyProfile",
    "DestinationContractAttestationPolicyEvidence",
]
