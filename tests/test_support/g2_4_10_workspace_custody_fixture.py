"""Deterministic non-executing fixtures for G2.4.10 workspace custody evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eag.governed_workspace import (
    FileDurableWorkspaceCustodyStore,
    WorkspaceCustodyAttestation,
    WorkspaceCustodyClaim,
    WorkspaceCustodyRequest,
    WorkspaceCustodyStoreUnavailableError,
)


@dataclass(frozen=True, slots=True)
class CustodyBindings:
    request: WorkspaceCustodyRequest
    workspace_root: Path
    source_root: Path
    audit_root: Path
    control_root: Path


class UnavailableWorkspaceCustodyStore:
    """Structural store double that demonstrates fail-closed custody behavior."""

    def __init__(self, *, control_root: Path) -> None:
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        return self._control_root

    def claim(self, attestation: WorkspaceCustodyAttestation) -> WorkspaceCustodyClaim:
        del attestation
        raise WorkspaceCustodyStoreUnavailableError("deterministic unavailable custody store")

    def read(self, *, attestation_id: str) -> WorkspaceCustodyAttestation | None:
        del attestation_id
        raise WorkspaceCustodyStoreUnavailableError("deterministic unavailable custody store")


def custody_store(control_root: Path) -> FileDurableWorkspaceCustodyStore:
    control_root.mkdir(parents=True, exist_ok=True)
    return FileDurableWorkspaceCustodyStore(control_root=control_root)


def custody_bindings(tmp_path: Path, *, identity: str) -> CustodyBindings:
    workspace_root = tmp_path / "workspace"
    source_root = tmp_path / "source"
    audit_root = tmp_path / "audit"
    control_root = tmp_path / "control"
    for root in (workspace_root, source_root, audit_root, control_root):
        root.mkdir(parents=True, exist_ok=True)
    request = WorkspaceCustodyRequest(
        attestation_id=f"g2410-attestation-{identity}",
        execution_id=f"g2410-execution-{identity}",
        run_id=f"g2410-run-{identity}",
        workspace_id=f"g2410-workspace-{identity}",
        workspace_root=workspace_root,
        source_repository_root=source_root,
        audit_root=audit_root,
        control_root=control_root,
    )
    return CustodyBindings(
        request=request,
        workspace_root=workspace_root,
        source_root=source_root,
        audit_root=audit_root,
        control_root=control_root,
    )


__all__ = [
    "CustodyBindings",
    "UnavailableWorkspaceCustodyStore",
    "custody_bindings",
    "custody_store",
]
