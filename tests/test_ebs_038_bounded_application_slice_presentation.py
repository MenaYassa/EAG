"""EBS-038: direct receipt-backed G2.4.23 terminal presentation proof."""

from __future__ import annotations

import hashlib
from dataclasses import fields, replace
from pathlib import Path

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

from eag.governed_construction_work_order import (
    FixedConstructionIntentDisposition,
    FixedProfileConstructionIntentAssessor,
    FixedProfileConstructionIntentIssuer,
)
from eag.governed_presentation import (
    FixedProfilePresentationDisposition,
    FixedProfilePresentationFailureStage,
    continue_fixed_profile_after_handoff,
    render_fixed_profile_terminal_view,
    submit_fixed_profile_construction,
)

BENCHMARK_ID = "EBS-038"


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


def _accepted_intent(submission: object):
    issuer = FixedProfileConstructionIntentIssuer()
    intent = issuer.issue_intent_request(
        intent_request_id=f"{submission.submission_id}-ebs038-intent",
        profile=submission.selected_profile_token,
        requested_at=submission.requested_at,
    )
    assessment = FixedProfileConstructionIntentAssessor().assess(
        intent_assessment_id=f"{submission.submission_id}-ebs038-intent-assessment",
        request=intent,
        assessed_at=submission.requested_at,
    )
    assert assessment.disposition is FixedConstructionIntentDisposition.FIXED_PROFILE_CONSTRUCTION_INTENT_ATTESTED
    return issuer, intent, assessment


def test_ebs_038_exact_enum_relay_real_receipt_presentation_and_retained_descriptor_root(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs038-positive")
    submission = fixture.submission
    issuer, intent, intent_assessment = _accepted_intent(submission)
    handoff = submission.custody_gate.attest_and_acquire_root_handoff(request=submission.custody_request)
    assert handoff.attestation is not None
    assert handoff.binding is not None
    assert handoff.handle is not None

    original_root = fixture.workspace_root
    retained_root = original_root.parent / "retained-root"
    original_root.rename(retained_root)
    original_root.mkdir()
    replacement_before = _tree_state(original_root)
    retained_before = _tree_state(retained_root)

    view = continue_fixed_profile_after_handoff(
        submission=submission,
        issuer=issuer,
        intent=intent,
        intent_assessment=intent_assessment,
        handoff=handoff,
    )

    assert retained_before == ()
    assert view.disposition is FixedProfilePresentationDisposition.RECEIPT_AVAILABLE
    assert view.selected_profile == "modern_todo_static_v1"
    assert view.profile_version == "v1"
    assert view.intent_request_id == intent.intent_request_id
    assert view.intent_assessment_id == intent_assessment.intent_assessment_id
    assert view.construction_disposition is not None
    assert view.authorization_digest is not None
    assert view.plan_digest is not None
    assert tuple(item.relative_path for item in view.receipt_files) == (
        "index.html",
        "styles.css",
        "app.js",
        "README.md",
    )
    assert _tree_state(original_root) == replacement_before
    observed_file_paths = {
        path.relative_to(retained_root).as_posix()
        for path in retained_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    assert observed_file_paths == {item.relative_path for item in view.receipt_files}
    assert all(
        (retained_root / item.relative_path).read_bytes()
        for item in view.receipt_files
    )
    for item in view.receipt_files:
        actual_content = (retained_root / item.relative_path).read_bytes()
        assert len(actual_content) == item.byte_count
        assert hashlib.sha256(actual_content).hexdigest() == item.content_digest
    assert handoff.handle.is_closed is True
    assert {field.name for field in fields(view)}.isdisjoint({"handle", "descriptor", "workspace_root", "root_path"})
    rendered = render_fixed_profile_terminal_view(view)
    assert "Completed receipt-backed files:" in rendered
    assert "running" not in rendered.lower()
    assert "ready" not in rendered.lower()
    assert "deployed" not in rendered.lower()


def test_ebs_038_unsupported_token_reaches_real_g2_4_21_issuer_before_handoff_or_effect(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(
        tmp_path,
        identity="ebs038-unsupported",
        selected_profile_token="unapproved_fixed_profile",
    )
    workspace_before = _tree_state(fixture.workspace_root)
    control_before = _tree_state(fixture.control_root)

    view = submit_fixed_profile_construction(submission=fixture.submission)

    assert view.disposition is FixedProfilePresentationDisposition.UPSTREAM_REFUSED
    assert view.failure_stage is FixedProfilePresentationFailureStage.PROFILE_ISSUANCE
    assert view.failure_code == "unsupported fixed construction intent profile"
    assert view.receipt_files == ()
    assert view.construction_disposition is None
    assert _tree_state(fixture.workspace_root) == workspace_before
    assert _tree_state(fixture.control_root) == control_before


def test_ebs_038_post_handoff_refusal_exits_g2_4_10_context_without_construction(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path / "first", identity="ebs038-first")
    substituted = fixed_profile_presentation_fixture(tmp_path / "second", identity="ebs038-second")
    submission = replace(
        fixture.submission,
        runtime_composition_attestation=substituted.submission.runtime_composition_attestation,
    )
    issuer, intent, intent_assessment = _accepted_intent(submission)
    handoff = submission.custody_gate.attest_and_acquire_root_handoff(request=submission.custody_request)
    assert handoff.handle is not None
    workspace_before = _tree_state(fixture.workspace_root)

    view = continue_fixed_profile_after_handoff(
        submission=submission,
        issuer=issuer,
        intent=intent,
        intent_assessment=intent_assessment,
        handoff=handoff,
    )

    assert view.disposition is FixedProfilePresentationDisposition.UPSTREAM_REFUSED
    assert view.failure_stage is FixedProfilePresentationFailureStage.WORK_ORDER_ASSESSMENT
    assert view.receipt_files == ()
    assert view.construction_disposition is None
    assert _tree_state(fixture.workspace_root) == workspace_before
    assert handoff.handle.is_closed is True
    assert {field.name for field in fields(view)}.isdisjoint({"handle", "descriptor", "workspace_root", "root_path"})


def test_ebs_038_public_surface_has_no_forbidden_operational_capability() -> None:
    import eag.governed_presentation as presentation

    for name in (
        "browser",
        "build",
        "command",
        "deploy",
        "network",
        "publish",
        "retry",
        "rollback",
        "run",
        "server",
        "session",
    ):
        assert not hasattr(presentation, name)
