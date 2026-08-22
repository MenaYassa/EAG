"""Immutable contracts for the G2.4.14 artifact readiness evidence boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from eag.governed_artifact_readiness.canonical import (
    ARTIFACT_READINESS_SCHEMA_VERSION,
    canonical_digest,
    require_non_empty,
    require_relative_path,
    require_sha256,
)


class ArtifactReadinessError(ValueError):
    """Raised when artifact readiness evidence is structurally invalid."""


class ArtifactPackagingProfile(StrEnum):
    """The narrow, explicit packaging profile set supported by G2.4.14."""

    SETUPTOOLS_FLAT_MODULE = "setuptools_flat_module"


class ArtifactValidationClass(StrEnum):
    """External validation classes that may be required by a readiness request."""

    TEST_EXECUTION = "test_execution"
    EDITABLE_INSTALL = "editable_install"
    WHEEL_BUILD = "wheel_build"
    SDIST_BUILD = "sdist_build"
    WHEEL_INSTALL = "wheel_install"
    ENTRYPOINT_VALIDATION = "entrypoint_validation"


class ArtifactValidationResult(StrEnum):
    """One redacted external validation receipt outcome."""

    PASSED = "passed"
    FAILED = "failed"


class ArtifactHygieneClassification(StrEnum):
    """Policy-directed classification of one declared artifact output class."""

    ABSENT = "absent"
    ALLOWED_IGNORED = "allowed_ignored"
    RETAINED_DELIVERABLE = "retained_deliverable"
    POLICY_VIOLATION = "policy_violation"


class ArtifactReadinessDisposition(StrEnum):
    """Evidence-only readiness outcomes that grant no execution or publication authority."""

    READY = "ready"
    NOT_READY = "not_ready"
    UNSUPPORTED_PROFILE = "unsupported_profile"


class ArtifactReadinessFindingCode(StrEnum):
    """Typed, deterministic readiness findings with no provider-controlled text."""

    PACKAGE_LAYOUT_AMBIGUOUS = "package_layout_ambiguous"
    PACKAGE_CONFIGURATION_MISSING = "package_configuration_missing"
    UNSUPPORTED_PACKAGING_PROFILE = "unsupported_packaging_profile"
    ARTIFACT_FINGERPRINT_MISMATCH = "artifact_fingerprint_mismatch"
    SNAPSHOT_MANIFEST_MISMATCH = "snapshot_manifest_mismatch"
    PYPROJECT_DIGEST_MISMATCH = "pyproject_digest_mismatch"
    ENTRYPOINT_MISSING = "entrypoint_missing"
    RECEIPT_MISSING = "receipt_missing"
    RECEIPT_UNKNOWN_CLASS = "receipt_unknown_class"
    RECEIPT_DUPLICATE = "receipt_duplicate"
    RECEIPT_INVALID = "receipt_invalid"
    RECEIPT_FAILED = "receipt_failed"
    HYGIENE_POLICY_VIOLATION = "hygiene_policy_violation"


def calculate_snapshot_manifest_digest(
    *,
    snapshot_id: str,
    canonical_file_manifest: tuple[ArtifactFileManifestEntry, ...],
    metadata_files: tuple[str, ...],
    declared_outputs: tuple[str, ...],
    packaging_backend: str,
    setuptools_py_modules: tuple[str, ...],
    declared_entrypoints: tuple[str, ...],
    schema_version: str = ARTIFACT_READINESS_SCHEMA_VERSION,
) -> str:
    """Return the deterministic supplied-snapshot digest without accessing a filesystem."""
    return canonical_digest(
        {
            "canonical_file_manifest": [entry.to_payload() for entry in canonical_file_manifest],
            "declared_entrypoints": list(declared_entrypoints),
            "declared_outputs": list(declared_outputs),
            "metadata_files": list(metadata_files),
            "packaging_backend": packaging_backend,
            "schema_version": schema_version,
            "setuptools_py_modules": list(setuptools_py_modules),
            "snapshot_id": snapshot_id,
        }
    )


def calculate_artifact_fingerprint(
    *,
    artifact_id: str,
    snapshot_id: str,
    root_identity: str,
    manifest_digest: str,
    pyproject_digest: str,
) -> str:
    """Return the exact artifact identity digest used for receipt binding."""
    return canonical_digest(
        {
            "artifact_id": artifact_id,
            "manifest_digest": manifest_digest,
            "pyproject_digest": pyproject_digest,
            "root_identity": root_identity,
            "snapshot_id": snapshot_id,
        }
    )


def calculate_receipt_digest(
    *,
    receipt_id: str,
    receipt_type: str,
    producer_identity: str,
    producer_version: str,
    artifact_fingerprint: str,
    command_class: str,
    result: str,
    output_digest: str,
    timestamp: datetime,
    schema_version: str = ARTIFACT_READINESS_SCHEMA_VERSION,
) -> str:
    """Return the canonical digest of one external receipt without executing it."""
    return canonical_digest(
        {
            "artifact_fingerprint": artifact_fingerprint,
            "command_class": command_class,
            "output_digest": output_digest,
            "producer_identity": producer_identity,
            "producer_version": producer_version,
            "receipt_id": receipt_id,
            "receipt_type": receipt_type,
            "result": result,
            "schema_version": schema_version,
            "timestamp": timestamp.isoformat(),
        }
    )


def _as_utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ArtifactReadinessError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _strict_enum_tuple[T: StrEnum](
    values: tuple[T, ...],
    enum_type: type[T],
    field_name: str,
    *,
    require_non_empty_values: bool,
) -> tuple[T, ...]:
    if not isinstance(values, tuple) or any(not isinstance(value, enum_type) for value in values):
        raise ArtifactReadinessError(f"{field_name} must contain {enum_type.__name__} values")
    if require_non_empty_values and not values:
        raise ArtifactReadinessError(f"{field_name} cannot be empty")
    if tuple(sorted(values, key=str)) != values or len(set(values)) != len(values):
        raise ArtifactReadinessError(f"{field_name} must be strictly ordered and unique")
    return values


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactFileManifestEntry:
    """One declared immutable artifact file identity; the validator never reads it from disk."""

    path: str
    digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", require_relative_path(self.path, "path"))
        object.__setattr__(self, "digest", require_sha256(self.digest, "digest"))

    def to_payload(self) -> dict[str, str]:
        return {"digest": self.digest, "path": self.path}


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactSnapshotEvidence:
    """Supplied immutable snapshot description; it contains no workspace handle or read operation."""

    snapshot_id: str
    canonical_file_manifest: tuple[ArtifactFileManifestEntry, ...]
    manifest_digest: str
    metadata_files: tuple[str, ...]
    pyproject_digest: str
    declared_outputs: tuple[str, ...]
    packaging_backend: str
    setuptools_py_modules: tuple[str, ...]
    declared_entrypoints: tuple[str, ...]
    schema_version: str = ARTIFACT_READINESS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_id", require_non_empty(self.snapshot_id, "snapshot_id"))
        if not self.canonical_file_manifest or any(
            not isinstance(entry, ArtifactFileManifestEntry) for entry in self.canonical_file_manifest
        ):
            raise ArtifactReadinessError(
                "canonical_file_manifest must contain at least one ArtifactFileManifestEntry"
            )
        paths = tuple(entry.path for entry in self.canonical_file_manifest)
        if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
            raise ArtifactReadinessError("canonical_file_manifest must be strictly path-ordered and unique")
        object.__setattr__(self, "manifest_digest", require_sha256(self.manifest_digest, "manifest_digest"))
        metadata_files = tuple(require_relative_path(path, "metadata_files") for path in self.metadata_files)
        if metadata_files != tuple(sorted(metadata_files)) or len(set(metadata_files)) != len(metadata_files):
            raise ArtifactReadinessError("metadata_files must be strictly ordered and unique")
        object.__setattr__(self, "metadata_files", metadata_files)
        object.__setattr__(self, "pyproject_digest", require_sha256(self.pyproject_digest, "pyproject_digest"))
        declared_outputs = tuple(require_relative_path(path, "declared_outputs") for path in self.declared_outputs)
        if declared_outputs != tuple(sorted(declared_outputs)) or len(set(declared_outputs)) != len(declared_outputs):
            raise ArtifactReadinessError("declared_outputs must be strictly ordered and unique")
        object.__setattr__(self, "declared_outputs", declared_outputs)
        object.__setattr__(self, "packaging_backend", require_non_empty(self.packaging_backend, "packaging_backend"))
        py_modules = tuple(require_non_empty(module, "setuptools_py_modules") for module in self.setuptools_py_modules)
        if py_modules != tuple(sorted(py_modules)) or len(set(py_modules)) != len(py_modules):
            raise ArtifactReadinessError("setuptools_py_modules must be strictly ordered and unique")
        object.__setattr__(self, "setuptools_py_modules", py_modules)
        entrypoints = tuple(require_non_empty(entrypoint, "declared_entrypoints") for entrypoint in self.declared_entrypoints)
        if entrypoints != tuple(sorted(entrypoints)) or len(set(entrypoints)) != len(entrypoints):
            raise ArtifactReadinessError("declared_entrypoints must be strictly ordered and unique")
        object.__setattr__(self, "declared_entrypoints", entrypoints)
        if self.schema_version != ARTIFACT_READINESS_SCHEMA_VERSION:
            raise ArtifactReadinessError("unsupported snapshot schema_version")
        if self.manifest_digest != self.calculate_manifest_digest():
            raise ArtifactReadinessError("manifest_digest does not match canonical_file_manifest")
        if "pyproject.toml" not in paths:
            raise ArtifactReadinessError("canonical_file_manifest must include pyproject.toml")
        pyproject = next(entry for entry in self.canonical_file_manifest if entry.path == "pyproject.toml")
        if self.pyproject_digest != pyproject.digest:
            raise ArtifactReadinessError("pyproject_digest must match the pyproject.toml manifest digest")

    def calculate_manifest_digest(self) -> str:
        return calculate_snapshot_manifest_digest(
            snapshot_id=self.snapshot_id,
            canonical_file_manifest=self.canonical_file_manifest,
            metadata_files=self.metadata_files,
            declared_outputs=self.declared_outputs,
            packaging_backend=self.packaging_backend,
            setuptools_py_modules=self.setuptools_py_modules,
            declared_entrypoints=self.declared_entrypoints,
            schema_version=self.schema_version,
        )

    @property
    def file_paths(self) -> tuple[str, ...]:
        """Return only the supplied manifest paths; no filesystem scan occurs."""
        return tuple(entry.path for entry in self.canonical_file_manifest)


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactReadinessRequest:
    """Immutable declared readiness profile for one exact supplied artifact snapshot."""

    artifact_id: str
    snapshot_id: str
    root_identity: str
    artifact_fingerprint: str
    packaging_profile: ArtifactPackagingProfile | str
    expected_entrypoints: tuple[str, ...]
    required_validation_classes: tuple[ArtifactValidationClass, ...]
    hygiene_policy: Mapping[str, ArtifactHygieneClassification]
    schema_version: str = ARTIFACT_READINESS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("artifact_id", "snapshot_id", "root_identity"):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        object.__setattr__(
            self, "artifact_fingerprint", require_sha256(self.artifact_fingerprint, "artifact_fingerprint")
        )
        if not isinstance(self.packaging_profile, (ArtifactPackagingProfile, str)):
            raise ArtifactReadinessError("packaging_profile must be an ArtifactPackagingProfile or non-empty string")
        if isinstance(self.packaging_profile, str) and not isinstance(
            self.packaging_profile, ArtifactPackagingProfile
        ):
            object.__setattr__(
                self,
                "packaging_profile",
                require_non_empty(self.packaging_profile, "packaging_profile"),
            )
        entrypoints = tuple(require_non_empty(entrypoint, "expected_entrypoints") for entrypoint in self.expected_entrypoints)
        if entrypoints != tuple(sorted(entrypoints)) or len(set(entrypoints)) != len(entrypoints):
            raise ArtifactReadinessError("expected_entrypoints must be strictly ordered and unique")
        object.__setattr__(self, "expected_entrypoints", entrypoints)
        object.__setattr__(
            self,
            "required_validation_classes",
            _strict_enum_tuple(
                self.required_validation_classes,
                ArtifactValidationClass,
                "required_validation_classes",
                require_non_empty_values=True,
            ),
        )
        if not isinstance(self.hygiene_policy, Mapping):
            raise ArtifactReadinessError("hygiene_policy must be a mapping")
        normalized_policy: dict[str, ArtifactHygieneClassification] = {}
        for path, classification in self.hygiene_policy.items():
            safe_path = require_relative_path(path, "hygiene_policy key")
            if not isinstance(classification, ArtifactHygieneClassification):
                raise ArtifactReadinessError("hygiene_policy values must be ArtifactHygieneClassification")
            normalized_policy[safe_path] = classification
        if tuple(normalized_policy) != tuple(sorted(normalized_policy)):
            raise ArtifactReadinessError("hygiene_policy keys must be strictly ordered")
        object.__setattr__(self, "hygiene_policy", dict(normalized_policy))
        if self.schema_version != ARTIFACT_READINESS_SCHEMA_VERSION:
            raise ArtifactReadinessError("unsupported request schema_version")


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactValidationReceipt:
    """Immutable external validation evidence; this contract never runs a command."""

    receipt_id: str
    receipt_type: ArtifactValidationClass | str
    producer_identity: str
    producer_version: str
    artifact_fingerprint: str
    command_class: str
    result: ArtifactValidationResult | str
    output_digest: str
    timestamp: datetime
    receipt_digest: str
    schema_version: str = ARTIFACT_READINESS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("receipt_id", "producer_identity", "producer_version", "command_class"):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        if not isinstance(self.receipt_type, (ArtifactValidationClass, str)):
            raise ArtifactReadinessError("receipt_type must be an ArtifactValidationClass or non-empty string")
        if isinstance(self.receipt_type, str) and not isinstance(
            self.receipt_type, ArtifactValidationClass
        ):
            object.__setattr__(
                self,
                "receipt_type",
                require_non_empty(self.receipt_type, "receipt_type"),
            )
        object.__setattr__(
            self, "artifact_fingerprint", require_sha256(self.artifact_fingerprint, "artifact_fingerprint")
        )
        if not isinstance(self.result, (ArtifactValidationResult, str)):
            raise ArtifactReadinessError("result must be an ArtifactValidationResult or non-empty string")
        if isinstance(self.result, str) and not isinstance(self.result, ArtifactValidationResult):
            object.__setattr__(self, "result", require_non_empty(self.result, "result"))
        object.__setattr__(self, "output_digest", require_sha256(self.output_digest, "output_digest"))
        object.__setattr__(self, "timestamp", _as_utc(self.timestamp, "timestamp"))
        object.__setattr__(self, "receipt_digest", require_sha256(self.receipt_digest, "receipt_digest"))
        if self.schema_version != ARTIFACT_READINESS_SCHEMA_VERSION:
            raise ArtifactReadinessError("unsupported receipt schema_version")

    @classmethod
    def issue(
        cls,
        *,
        receipt_id: str,
        receipt_type: ArtifactValidationClass,
        producer_identity: str,
        producer_version: str,
        artifact_fingerprint: str,
        command_class: str,
        result: ArtifactValidationResult,
        output_digest: str,
        timestamp: datetime,
    ) -> ArtifactValidationReceipt:
        canonical_timestamp = _as_utc(timestamp, "timestamp")
        receipt_digest = calculate_receipt_digest(
            receipt_id=receipt_id,
            receipt_type=receipt_type.value,
            producer_identity=producer_identity,
            producer_version=producer_version,
            artifact_fingerprint=artifact_fingerprint,
            command_class=command_class,
            result=result.value,
            output_digest=output_digest,
            timestamp=canonical_timestamp,
        )
        return cls(
            receipt_id=receipt_id,
            receipt_type=receipt_type,
            producer_identity=producer_identity,
            producer_version=producer_version,
            artifact_fingerprint=artifact_fingerprint,
            command_class=command_class,
            result=result,
            output_digest=output_digest,
            timestamp=canonical_timestamp,
            receipt_digest=receipt_digest,
        )

    @property
    def digest(self) -> str:
        return calculate_receipt_digest(
            receipt_id=self.receipt_id,
            receipt_type=(
                self.receipt_type.value
                if isinstance(self.receipt_type, ArtifactValidationClass)
                else self.receipt_type
            ),
            producer_identity=self.producer_identity,
            producer_version=self.producer_version,
            artifact_fingerprint=self.artifact_fingerprint,
            command_class=self.command_class,
            result=(
                self.result.value if isinstance(self.result, ArtifactValidationResult) else self.result
            ),
            output_digest=self.output_digest,
            timestamp=self.timestamp,
            schema_version=self.schema_version,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactHygieneObservation:
    """One supplied hygiene observation; it classifies evidence and cannot clean it."""

    path: str
    classification: ArtifactHygieneClassification

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", require_relative_path(self.path, "path"))
        if not isinstance(self.classification, ArtifactHygieneClassification):
            raise ArtifactReadinessError("classification must be an ArtifactHygieneClassification")


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactReadinessFinding:
    """Typed deterministic readiness observation without mutable remediation behavior."""

    code: ArtifactReadinessFindingCode
    evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, ArtifactReadinessFindingCode):
            raise TypeError("code must be an ArtifactReadinessFindingCode")
        object.__setattr__(
            self, "evidence_reference", require_non_empty(self.evidence_reference, "evidence_reference")
        )

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "evidence_reference": self.evidence_reference}


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactReadinessAssessment:
    """Immutable artifact readiness conclusion; it is not a completion, permit, or publication decision."""

    assessment_id: str
    artifact_identity: str
    disposition: ArtifactReadinessDisposition
    findings: tuple[ArtifactReadinessFinding, ...]
    evidence_references: tuple[str, ...]
    hygiene_observations: tuple[ArtifactHygieneObservation, ...]
    recommendations: tuple[str, ...]
    digest: str
    schema_version: str = ARTIFACT_READINESS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("assessment_id", "artifact_identity"):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))
        if not isinstance(self.disposition, ArtifactReadinessDisposition):
            raise TypeError("disposition must be an ArtifactReadinessDisposition")
        if any(not isinstance(finding, ArtifactReadinessFinding) for finding in self.findings):
            raise TypeError("findings must contain ArtifactReadinessFinding values")
        finding_payloads = tuple((finding.code.value, finding.evidence_reference) for finding in self.findings)
        if finding_payloads != tuple(sorted(finding_payloads)) or len(set(finding_payloads)) != len(finding_payloads):
            raise ArtifactReadinessError("findings must be strictly ordered and unique")
        references = tuple(require_non_empty(reference, "evidence_references") for reference in self.evidence_references)
        if references != tuple(sorted(references)) or len(set(references)) != len(references):
            raise ArtifactReadinessError("evidence_references must be strictly ordered and unique")
        object.__setattr__(self, "evidence_references", references)
        if any(not isinstance(observation, ArtifactHygieneObservation) for observation in self.hygiene_observations):
            raise TypeError("hygiene_observations must contain ArtifactHygieneObservation values")
        hygiene_paths = tuple(observation.path for observation in self.hygiene_observations)
        if hygiene_paths != tuple(sorted(hygiene_paths)) or len(set(hygiene_paths)) != len(hygiene_paths):
            raise ArtifactReadinessError("hygiene_observations must be strictly path-ordered and unique")
        recommendations = tuple(require_non_empty(item, "recommendations") for item in self.recommendations)
        if recommendations != tuple(sorted(recommendations)) or len(set(recommendations)) != len(recommendations):
            raise ArtifactReadinessError("recommendations must be strictly ordered and unique")
        object.__setattr__(self, "recommendations", recommendations)
        object.__setattr__(self, "digest", require_sha256(self.digest, "digest"))
        if self.schema_version != ARTIFACT_READINESS_SCHEMA_VERSION:
            raise ArtifactReadinessError("unsupported assessment schema_version")
        if self.digest != self.calculate_digest():
            raise ArtifactReadinessError("digest does not match canonical readiness assessment")

    @classmethod
    def issue(
        cls,
        *,
        assessment_id: str,
        artifact_identity: str,
        disposition: ArtifactReadinessDisposition,
        findings: tuple[ArtifactReadinessFinding, ...],
        evidence_references: tuple[str, ...],
        hygiene_observations: tuple[ArtifactHygieneObservation, ...],
        recommendations: tuple[str, ...],
    ) -> ArtifactReadinessAssessment:
        template = {
            "assessment_id": assessment_id,
            "artifact_identity": artifact_identity,
            "disposition": disposition.value,
            "findings": [finding.to_payload() for finding in findings],
            "evidence_references": list(evidence_references),
            "hygiene_observations": [
                {"classification": observation.classification.value, "path": observation.path}
                for observation in hygiene_observations
            ],
            "recommendations": list(recommendations),
            "schema_version": ARTIFACT_READINESS_SCHEMA_VERSION,
        }
        return cls(
            assessment_id=assessment_id,
            artifact_identity=artifact_identity,
            disposition=disposition,
            findings=findings,
            evidence_references=evidence_references,
            hygiene_observations=hygiene_observations,
            recommendations=recommendations,
            digest=canonical_digest(template),
        )

    def calculate_digest(self) -> str:
        return canonical_digest(
            {
                "assessment_id": self.assessment_id,
                "artifact_identity": self.artifact_identity,
                "disposition": self.disposition.value,
                "evidence_references": list(self.evidence_references),
                "findings": [finding.to_payload() for finding in self.findings],
                "hygiene_observations": [
                    {"classification": observation.classification.value, "path": observation.path}
                    for observation in self.hygiene_observations
                ],
                "recommendations": list(self.recommendations),
                "schema_version": self.schema_version,
            }
        )


__all__ = [
    "ArtifactFileManifestEntry",
    "ArtifactHygieneClassification",
    "ArtifactHygieneObservation",
    "ArtifactPackagingProfile",
    "ArtifactReadinessAssessment",
    "ArtifactReadinessDisposition",
    "ArtifactReadinessError",
    "ArtifactReadinessFinding",
    "ArtifactReadinessFindingCode",
    "ArtifactReadinessRequest",
    "ArtifactSnapshotEvidence",
    "ArtifactValidationClass",
    "ArtifactValidationReceipt",
    "ArtifactValidationResult",
    "calculate_artifact_fingerprint",
    "calculate_receipt_digest",
    "calculate_snapshot_manifest_digest",
]
