"""Deterministic evidence-only fixtures for G2.4.14 artifact readiness tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from eag.governed_artifact_readiness import (
    ArtifactFileManifestEntry,
    ArtifactHygieneClassification,
    ArtifactPackagingProfile,
    ArtifactReadinessRequest,
    ArtifactSnapshotEvidence,
    ArtifactValidationClass,
    ArtifactValidationReceipt,
    ArtifactValidationResult,
    calculate_artifact_fingerprint,
    calculate_snapshot_manifest_digest,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ArtifactReadinessBindings:
    request: ArtifactReadinessRequest
    snapshot: ArtifactSnapshotEvidence
    receipts: tuple[ArtifactValidationReceipt, ...]
    observed_hygiene_paths: tuple[str, ...]


def calculator_snapshot(
    *,
    identity: str,
    corrected: bool,
    backend: str = "setuptools.build_meta",
    calculator_source: str = "def main():\n    return 0\n",
    entrypoint: str = "calc=calculator:main",
    pyproject_suffix: str = "",
) -> ArtifactSnapshotEvidence:
    """Return supplied calculator evidence only; no project files are created or scanned."""
    pyproject = (
        "[build-system]\nrequires=[\"setuptools\"]\nbuild-backend=\"setuptools.build_meta\"\n"
        "[project]\nname=\"calculator\"\nversion=\"0.1.0\"\n"
        f"[project.scripts]\n{entrypoint.split('=', maxsplit=1)[0]}=\"{entrypoint.split('=', maxsplit=1)[1]}\"\n"
    )
    if corrected:
        pyproject += "[tool.setuptools]\npy-modules=[\"calculator\"]\n"
    pyproject += pyproject_suffix
    entries = tuple(
        sorted(
            (
                ArtifactFileManifestEntry(path="calculator.py", digest=_digest(calculator_source)),
                ArtifactFileManifestEntry(path="pyproject.toml", digest=_digest(pyproject)),
                ArtifactFileManifestEntry(
                    path="test_calculator.py",
                    digest=_digest("from calculator import main\n\ndef test_main():\n    assert main() == 0\n"),
                ),
            ),
            key=lambda entry: entry.path,
        )
    )
    snapshot_id = f"g2414-snapshot-{identity}"
    manifest_digest = calculate_snapshot_manifest_digest(
        snapshot_id=snapshot_id,
        canonical_file_manifest=entries,
        metadata_files=("pyproject.toml",),
        declared_outputs=(),
        packaging_backend=backend,
        setuptools_py_modules=("calculator",) if corrected else (),
        declared_entrypoints=(entrypoint,),
    )
    return ArtifactSnapshotEvidence(
        snapshot_id=snapshot_id,
        canonical_file_manifest=entries,
        manifest_digest=manifest_digest,
        metadata_files=("pyproject.toml",),
        pyproject_digest=next(entry.digest for entry in entries if entry.path == "pyproject.toml"),
        declared_outputs=(),
        packaging_backend=backend,
        setuptools_py_modules=("calculator",) if corrected else (),
        declared_entrypoints=(entrypoint,),
    )


def readiness_request(
    *,
    identity: str,
    snapshot: ArtifactSnapshotEvidence,
    hygiene_policy: dict[str, ArtifactHygieneClassification] | None = None,
) -> ArtifactReadinessRequest:
    """Return an exact immutable request bound to one supplied snapshot identity."""
    artifact_id = f"g2414-artifact-{identity}"
    root_identity = f"g2414-root-{identity}"
    fingerprint = calculate_artifact_fingerprint(
        artifact_id=artifact_id,
        snapshot_id=snapshot.snapshot_id,
        root_identity=root_identity,
        manifest_digest=snapshot.manifest_digest,
        pyproject_digest=snapshot.pyproject_digest,
    )
    policy = hygiene_policy or {
        "*.egg-info": ArtifactHygieneClassification.ALLOWED_IGNORED,
        ".venv": ArtifactHygieneClassification.ALLOWED_IGNORED,
        "build": ArtifactHygieneClassification.ALLOWED_IGNORED,
        "dist": ArtifactHygieneClassification.RETAINED_DELIVERABLE,
        "uv.lock": ArtifactHygieneClassification.ALLOWED_IGNORED,
    }
    return ArtifactReadinessRequest(
        artifact_id=artifact_id,
        snapshot_id=snapshot.snapshot_id,
        root_identity=root_identity,
        artifact_fingerprint=fingerprint,
        packaging_profile=ArtifactPackagingProfile.SETUPTOOLS_FLAT_MODULE,
        expected_entrypoints=("calc=calculator:main",),
        required_validation_classes=tuple(sorted(ArtifactValidationClass, key=str)),
        hygiene_policy=dict(sorted(policy.items())),
    )


def matching_receipts(*, fingerprint: str) -> tuple[ArtifactValidationReceipt, ...]:
    """Return complete deterministic external receipt evidence; no command is run here."""
    timestamp = datetime(2026, 8, 22, tzinfo=UTC)
    return tuple(
        ArtifactValidationReceipt.issue(
            receipt_id=f"g2414-receipt-{receipt_type.value}",
            receipt_type=receipt_type,
            producer_identity="deterministic-fixture-producer",
            producer_version="1.0",
            artifact_fingerprint=fingerprint,
            command_class=receipt_type.value,
            result=ArtifactValidationResult.PASSED,
            output_digest=_digest(f"g2414-output:{receipt_type.value}"),
            timestamp=timestamp,
        )
        for receipt_type in sorted(ArtifactValidationClass, key=str)
    )


def corrected_bindings(*, identity: str = "calculator") -> ArtifactReadinessBindings:
    """Return valid corrected calculator evidence and all required external receipts."""
    snapshot = calculator_snapshot(identity=identity, corrected=True)
    request = readiness_request(identity=identity, snapshot=snapshot)
    return ArtifactReadinessBindings(
        request=request,
        snapshot=snapshot,
        receipts=matching_receipts(fingerprint=request.artifact_fingerprint),
        observed_hygiene_paths=(".venv", "build", "dist", "calculator.egg-info", "uv.lock"),
    )


__all__ = [
    "ArtifactReadinessBindings",
    "calculator_snapshot",
    "corrected_bindings",
    "matching_receipts",
    "readiness_request",
]
