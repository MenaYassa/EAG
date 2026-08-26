"""Real typed prerequisite inputs for G2.4.23 presentation-boundary tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from eag.governed_composition import RuntimeCompositionAttestation, RuntimeCompositionGate
from eag.governed_presentation import FixedProfilePresentationSubmission
from eag.governed_workspace import WorkspaceCustodyGate
from test_support.g2_4_10_workspace_custody_fixture import custody_bindings, custody_store
from test_support.g2_4_11_composition_fixture import composition_manifest, composition_store


@dataclass(frozen=True, slots=True)
class FixedProfilePresentationFixture:
    submission: FixedProfilePresentationSubmission
    workspace_root: Path
    control_root: Path


def fixed_profile_presentation_fixture(
    tmp_path: Path,
    *,
    identity: str = "g2423-presentation",
    selected_profile_token: str = "modern_todo_static_v1",
    composition_attestation: RuntimeCompositionAttestation | None = None,
) -> FixedProfilePresentationFixture:
    """Return real typed prerequisites while leaving handoff and construction to production code."""
    custody = custody_bindings(tmp_path, identity=identity)
    timestamp = datetime.now(UTC)
    if composition_attestation is None:
        base_manifest = composition_manifest(identity=identity)
        manifest = type(base_manifest)(
            composition_id=base_manifest.composition_id,
            execution_id=custody.request.execution_id,
            run_id=custody.request.run_id,
            runtime_id=base_manifest.runtime_id,
            executor_identity=base_manifest.executor_identity,
            component_identities=base_manifest.component_identities,
            dependency_bindings=base_manifest.dependency_bindings,
            composition_policy_digest=base_manifest.composition_policy_digest,
            invocation_binding_digest=base_manifest.invocation_binding_digest,
        )
        admission = RuntimeCompositionGate(
            composition_store=composition_store(tmp_path / "composition-control")
        ).attest(
            attestation_id=f"g2423-composition-{identity}",
            manifest=manifest,
            occurred_at=timestamp,
        )
        assert admission.attestation is not None
        composition_attestation = admission.attestation
    return FixedProfilePresentationFixture(
        submission=FixedProfilePresentationSubmission(
            submission_id=f"g2423-submission-{identity}",
            selected_profile_token=selected_profile_token,
            requested_at=timestamp,
            expires_at=timestamp + timedelta(minutes=10),
            custody_gate=WorkspaceCustodyGate(custody_store=custody_store(custody.control_root)),
            custody_request=custody.request,
            runtime_composition_attestation=composition_attestation,
        ),
        workspace_root=custody.workspace_root,
        control_root=custody.control_root,
    )


__all__ = ["FixedProfilePresentationFixture", "fixed_profile_presentation_fixture"]
