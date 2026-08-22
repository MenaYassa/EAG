"""Deterministic non-executing fixtures for G2.4.11 composition provenance evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path

from eag.governed_composition import (
    FileDurableRuntimeCompositionStore,
    RuntimeComponentIdentity,
    RuntimeCompositionAttestation,
    RuntimeCompositionClaim,
    RuntimeCompositionManifest,
    RuntimeCompositionStoreUnavailableError,
    RuntimeDependencyBinding,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class UnavailableRuntimeCompositionStore:
    """Structural durable-store double that demonstrates fail-closed composition behavior."""

    def __init__(self, *, control_root: Path) -> None:
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        return self._control_root

    def claim(self, attestation: RuntimeCompositionAttestation) -> RuntimeCompositionClaim:
        del attestation
        raise RuntimeCompositionStoreUnavailableError("deterministic unavailable composition store")

    def read(self, *, attestation_id: str) -> RuntimeCompositionAttestation | None:
        del attestation_id
        raise RuntimeCompositionStoreUnavailableError("deterministic unavailable composition store")


def composition_store(control_root: Path) -> FileDurableRuntimeCompositionStore:
    control_root.mkdir(parents=True, exist_ok=True)
    return FileDurableRuntimeCompositionStore(control_root=control_root)


def composition_manifest(*, identity: str, runtime_id: str = "g2411-runtime") -> RuntimeCompositionManifest:
    roles = (
        "adaptive_planner",
        "context_factory",
        "decision_request_factory",
        "mutation_workflow",
        "reflection_runtime",
        "state_machine",
        "verification_specification_factory",
        "verifier",
    )
    components = tuple(
        RuntimeComponentIdentity(
            role=role,
            component_id=f"g2411-{identity}-{role}",
            version="v1",
            digest=_digest(f"g2411:{identity}:{role}:v1"),
        )
        for role in roles
    )
    dependencies = (
        RuntimeDependencyBinding(
            component_role="adaptive_planner",
            dependency_role="reflection_runtime",
            binding_digest=_digest(f"g2411:{identity}:planner-reflection"),
        ),
        RuntimeDependencyBinding(
            component_role="decision_request_factory",
            dependency_role="context_factory",
            binding_digest=_digest(f"g2411:{identity}:decision-context"),
        ),
        RuntimeDependencyBinding(
            component_role="mutation_workflow",
            dependency_role="state_machine",
            binding_digest=_digest(f"g2411:{identity}:mutation-state"),
        ),
        RuntimeDependencyBinding(
            component_role="verification_specification_factory",
            dependency_role="verifier",
            binding_digest=_digest(f"g2411:{identity}:spec-verifier"),
        ),
    )
    return RuntimeCompositionManifest(
        composition_id=f"g2411-composition-{identity}",
        execution_id=f"g2411-execution-{identity}",
        run_id=f"g2411-run-{identity}",
        runtime_id=runtime_id,
        executor_identity=f"g2411-executor-{identity}",
        component_identities=components,
        dependency_bindings=dependencies,
        composition_policy_digest=_digest(f"g2411:policy:{identity}"),
        invocation_binding_digest=_digest(f"g2411:invocation:{identity}"),
    )


__all__ = [
    "UnavailableRuntimeCompositionStore",
    "composition_manifest",
    "composition_store",
]
