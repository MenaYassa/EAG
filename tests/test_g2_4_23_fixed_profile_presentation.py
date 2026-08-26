"""Focused G2.4.23 proof for the thin receipt-backed terminal presentation slice."""

from __future__ import annotations

import json
from dataclasses import fields, replace
from pathlib import Path

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture
from typer.testing import CliRunner

from eag.cli import app
from eag.governed_presentation import (
    FixedProfilePresentationDisposition,
    FixedProfilePresentationFailureStage,
    render_fixed_profile_terminal_view,
    submit_fixed_profile_construction,
)


def _tree_state(root: Path) -> tuple[tuple[str, str, bytes | None], ...]:
    """Direct state proof over test-owned filesystem objects only."""
    state: list[tuple[str, str, bytes | None]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative_path = path.relative_to(root).as_posix()
        if path.is_symlink():
            state.append((relative_path, "symlink", None))
        elif path.is_dir():
            state.append((relative_path, "directory", None))
        else:
            state.append((relative_path, "file", path.read_bytes()))
    return tuple(state)


def test_receipt_backed_view_uses_the_real_fixed_profile_chain(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="focused-positive")

    view = submit_fixed_profile_construction(submission=fixture.submission)

    assert view.disposition is FixedProfilePresentationDisposition.RECEIPT_AVAILABLE
    assert view.selected_profile == "modern_todo_static_v1"
    assert view.profile_version == "v1"
    assert view.source_specification_digest is not None
    assert view.intent_request_id is not None
    assert view.intent_assessment_id is not None
    assert view.work_order_id is not None
    assert view.work_order_assessment_id is not None
    assert view.authorization_id is not None
    assert view.plan_digest is not None
    assert view.construction_disposition is not None
    assert tuple(item.relative_path for item in view.receipt_files) == (
        "index.html",
        "styles.css",
        "app.js",
        "README.md",
    )
    assert {field.name for field in fields(view)}.isdisjoint({"handle", "descriptor", "workspace_root", "root_path"})
    assert tuple(path for path, kind, _ in _tree_state(fixture.workspace_root) if kind == "file") == (
        "README.md",
        "app.js",
        "index.html",
        "styles.css",
    )
    rendered = render_fixed_profile_terminal_view(view)
    assert "Completed receipt-backed files:" in rendered
    assert "running" not in rendered.lower()
    assert "ready" not in rendered.lower()
    assert "deployed" not in rendered.lower()


def test_unsupported_token_reaches_g2_4_21_and_refuses_before_handoff_or_effect(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(
        tmp_path,
        identity="focused-unsupported",
        selected_profile_token="unsupported_fixed_profile",
    )
    workspace_before = _tree_state(fixture.workspace_root)
    control_before = _tree_state(fixture.control_root)

    view = submit_fixed_profile_construction(submission=fixture.submission)

    assert view.disposition is FixedProfilePresentationDisposition.UPSTREAM_REFUSED
    assert view.failure_stage is FixedProfilePresentationFailureStage.PROFILE_ISSUANCE
    assert view.failure_code == "unsupported fixed construction intent profile"
    assert view.construction_disposition is None
    assert view.receipt_files == ()
    assert _tree_state(fixture.workspace_root) == workspace_before
    assert _tree_state(fixture.control_root) == control_before


def test_post_handoff_invalid_work_order_refusal_preserves_workspace_and_hides_handle(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path / "first", identity="focused-first")
    substituted = fixed_profile_presentation_fixture(tmp_path / "second", identity="focused-second")
    workspace_before = _tree_state(fixture.workspace_root)
    invalid_submission = replace(
        fixture.submission,
        runtime_composition_attestation=substituted.submission.runtime_composition_attestation,
    )

    view = submit_fixed_profile_construction(submission=invalid_submission)

    assert view.disposition is FixedProfilePresentationDisposition.UPSTREAM_REFUSED
    assert view.failure_stage is FixedProfilePresentationFailureStage.WORK_ORDER_ASSESSMENT
    assert view.construction_disposition is None
    assert view.receipt_files == ()
    assert _tree_state(fixture.workspace_root) == workspace_before
    assert {field.name for field in fields(view)}.isdisjoint({"handle", "descriptor", "workspace_root", "root_path"})


def test_typer_command_renders_real_receipt_backed_terminal_result(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="focused-cli")
    submission = fixture.submission
    request = submission.custody_request
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "construct-fixed-profile",
            "modern_todo_static_v1",
            "--submission-id",
            submission.submission_id,
            "--attestation-id",
            request.attestation_id,
            "--execution-id",
            request.execution_id,
            "--run-id",
            request.run_id,
            "--workspace-id",
            request.workspace_id,
            "--workspace-root",
            str(request.workspace_root),
            "--source-repository-root",
            str(request.source_repository_root),
            "--audit-root",
            str(request.audit_root),
            "--control-root",
            str(request.control_root),
            "--composition-attestation-json",
            json.dumps(submission.runtime_composition_attestation.to_payload()),
            "--requested-at",
            submission.requested_at.isoformat(),
            "--expires-at",
            submission.expires_at.isoformat(),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Governed Fixed Profile Construction" in result.output
    assert "Profile: modern_todo_static_v1 (v1)" in result.output
    assert "Construction disposition: construction_files_created" in result.output
    assert "Completed receipt-backed files:" in result.output
    assert tuple(path for path, kind, _ in _tree_state(fixture.workspace_root) if kind == "file") == (
        "README.md",
        "app.js",
        "index.html",
        "styles.css",
    )
