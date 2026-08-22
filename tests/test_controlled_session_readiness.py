"""Deterministic unit coverage for G2.4.13 pre-session readiness validation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from test_support.g2_4_8_replay_ledger_fixture import session_bindings

from eag.governed_session import ReadinessDisposition, ReadinessRejectionReason


def test_readiness_accepts_exact_existing_custody_and_composition_evidence(tmp_path: Path) -> None:
    bindings = session_bindings(tmp_path, identity="readiness-valid")

    admission = bindings.readiness_gate.validate_for_session(
        evidence=bindings.readiness_evidence,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        runtime_availability=bindings.runtime_availability,
    )

    assert admission.decision.disposition is ReadinessDisposition.READY
    assert admission.decision.reason is None
    assert admission.evidence is bindings.readiness_evidence
    assert not hasattr(bindings.readiness_gate, "create_session")
    assert not hasattr(bindings.readiness_gate, "issue_permit")
    assert not hasattr(bindings.readiness_gate, "execute")


def test_readiness_rejects_missing_custody_or_composition_evidence_without_authority(tmp_path: Path) -> None:
    bindings = session_bindings(tmp_path, identity="readiness-missing")
    missing_custody = replace(
        bindings.readiness_evidence,
        custody_request=None,
        custody_attestation=None,
    )
    missing_composition = replace(
        bindings.readiness_evidence,
        composition_manifest=None,
        composition_attestation=None,
    )

    custody_result = bindings.readiness_gate.validate_for_session(
        evidence=missing_custody,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        runtime_availability=bindings.runtime_availability,
    )
    composition_result = bindings.readiness_gate.validate_for_session(
        evidence=missing_composition,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        runtime_availability=bindings.runtime_availability,
    )

    assert custody_result.decision.disposition is ReadinessDisposition.REJECTED
    assert custody_result.decision.reason is ReadinessRejectionReason.MISSING_WORKSPACE_CUSTODY_EVIDENCE
    assert composition_result.decision.disposition is ReadinessDisposition.REJECTED
    assert composition_result.decision.reason is ReadinessRejectionReason.MISSING_RUNTIME_COMPOSITION_EVIDENCE
    assert custody_result.evidence is None
    assert composition_result.evidence is None


def test_readiness_rejects_altered_custody_and_composition_bindings(tmp_path: Path) -> None:
    bindings = session_bindings(tmp_path, identity="readiness-altered")
    custody_request = bindings.readiness_evidence.custody_request
    composition_manifest = bindings.readiness_evidence.composition_manifest
    assert custody_request is not None
    assert composition_manifest is not None
    altered_custody = replace(
        bindings.readiness_evidence,
        custody_request=replace(custody_request, run_id="altered-run"),
    )
    altered_composition = replace(
        bindings.readiness_evidence,
        composition_manifest=replace(composition_manifest, runtime_id="altered-runtime"),
    )

    custody_result = bindings.readiness_gate.validate_for_session(
        evidence=altered_custody,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        runtime_availability=bindings.runtime_availability,
    )
    composition_result = bindings.readiness_gate.validate_for_session(
        evidence=altered_composition,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        runtime_availability=bindings.runtime_availability,
    )

    assert custody_result.decision.reason is ReadinessRejectionReason.WORKSPACE_CUSTODY_BINDING_MISMATCH
    assert composition_result.decision.reason is ReadinessRejectionReason.RUNTIME_COMPOSITION_BINDING_MISMATCH


def test_readiness_rejects_exact_request_cross_binding_mismatch(tmp_path: Path) -> None:
    bindings = session_bindings(tmp_path, identity="readiness-cross-binding")
    changed_runtime_request = replace(bindings.runtime_request, run_id="different-run")

    result = bindings.readiness_gate.validate_for_session(
        evidence=bindings.readiness_evidence,
        activation_request=bindings.activation_request,
        runtime_request=changed_runtime_request,
        runtime_availability=bindings.runtime_availability,
    )

    assert result.decision.disposition is ReadinessDisposition.REJECTED
    assert result.decision.reason is ReadinessRejectionReason.WORKSPACE_CUSTODY_BINDING_MISMATCH
