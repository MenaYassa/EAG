"""Typer registration for the G2.4.23 receipt-backed fixed-profile presentation slice."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer

from eag.governed_composition import RuntimeCompositionAttestation, RuntimeCompositionError
from eag.governed_presentation.fixed_profile import (
    FixedProfilePresentationDisposition,
    FixedProfilePresentationSubmission,
    render_fixed_profile_terminal_view,
    submit_fixed_profile_construction,
)
from eag.governed_workspace import (
    FileDurableWorkspaceCustodyStore,
    WorkspaceCustodyGate,
    WorkspaceCustodyRequest,
)


def register_fixed_profile_presentation_command(app: typer.Typer) -> None:
    """Register one local terminal command; it owns no profile, plan, or handle authority."""

    @app.command(name="construct-fixed-profile")
    def construct_fixed_profile(
        profile: str = typer.Argument(..., help="Exact fixed profile token to relay unchanged."),
        submission_id: str = typer.Option(..., "--submission-id"),
        attestation_id: str = typer.Option(..., "--attestation-id"),
        execution_id: str = typer.Option(..., "--execution-id"),
        run_id: str = typer.Option(..., "--run-id"),
        workspace_id: str = typer.Option(..., "--workspace-id"),
        workspace_root: Path = typer.Option(..., "--workspace-root"),  # noqa: B008
        source_repository_root: Path = typer.Option(..., "--source-repository-root"),  # noqa: B008
        audit_root: Path = typer.Option(..., "--audit-root"),  # noqa: B008
        control_root: Path = typer.Option(..., "--control-root"),  # noqa: B008
        composition_attestation_json: str = typer.Option(..., "--composition-attestation-json"),
        requested_at: str = typer.Option(..., "--requested-at"),
        expires_at: str = typer.Option(..., "--expires-at"),
    ) -> None:
        """Construct the sole fixed profile and render only immutable receipt-backed facts."""
        try:
            composition = RuntimeCompositionAttestation.from_payload(
                json.loads(composition_attestation_json)
            )
            submission = FixedProfilePresentationSubmission(
                submission_id=submission_id,
                selected_profile_token=profile,
                requested_at=datetime.fromisoformat(requested_at),
                expires_at=datetime.fromisoformat(expires_at),
                custody_gate=WorkspaceCustodyGate(
                    custody_store=FileDurableWorkspaceCustodyStore(control_root=control_root)
                ),
                custody_request=WorkspaceCustodyRequest(
                    attestation_id=attestation_id,
                    execution_id=execution_id,
                    run_id=run_id,
                    workspace_id=workspace_id,
                    workspace_root=workspace_root,
                    source_repository_root=source_repository_root,
                    audit_root=audit_root,
                    control_root=control_root,
                ),
                runtime_composition_attestation=composition,
            )
        except (TypeError, ValueError, RuntimeCompositionError) as error:
            raise typer.BadParameter(str(error)) from error

        view = submit_fixed_profile_construction(submission=submission)
        typer.echo(render_fixed_profile_terminal_view(view))
        if view.disposition is not FixedProfilePresentationDisposition.RECEIPT_AVAILABLE:
            raise typer.Exit(code=1)


__all__ = ["register_fixed_profile_presentation_command"]
