"""Deterministic, redaction-safe fingerprints for repository context snapshots."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from eag.context.models import (
    CONTEXT_CONTRACT_VERSION,
    ContextBudget,
    ContextFingerprint,
    RepositorySnapshotFingerprint,
    RepositoryStateEvidence,
    SelectedRepositoryContext,
    SourceArtifactRecord,
)
from eag.repository.models import RepositoryProfile


def repository_snapshot_fingerprint(
    *,
    profile: RepositoryProfile,
    state: RepositoryStateEvidence,
    artifacts: tuple[SourceArtifactRecord, ...],
    policy_version: str,
    analyzer_versions: Mapping[str, str] | None = None,
) -> RepositorySnapshotFingerprint:
    """Fingerprint stable repository evidence without scanner timestamps or host paths."""
    payload = {
        "contract_version": CONTEXT_CONTRACT_VERSION,
        "policy_version": policy_version,
        "repository": {
            "name": profile.identity.name,
            "kind": profile.kind.value,
            "layout": profile.layout.value,
            "statistics": {
                "files": profile.statistics.files,
                "directories": profile.statistics.directories,
                "packages": profile.statistics.packages,
                "tests": profile.statistics.tests,
                "documentation": profile.statistics.documentation,
                "total_bytes": profile.statistics.total_bytes,
                "python_files": profile.statistics.python_files,
                "markdown_files": profile.statistics.markdown_files,
                "config_files": profile.statistics.config_files,
                "languages": [
                    {
                        "language": item.language,
                        "file_count": item.file_count,
                        "line_count": item.line_count,
                        "percentage": item.percentage,
                    }
                    for item in sorted(profile.statistics.languages, key=lambda item: item.language)
                ],
            },
            "capabilities": asdict(profile.capabilities),
            "facts": [
                {"kind": fact.kind, "value": fact.value, "confidence": fact.confidence}
                for fact in sorted(profile.facts, key=lambda item: (item.kind, item.value, item.confidence))
            ],
        },
        "state": {
            "available": state.available,
            "branch": state.branch,
            "head": state.head,
            "is_detached": state.is_detached,
            "changed_paths": sorted(state.changed_paths),
            "state_fingerprint": state.state_fingerprint,
        },
        "artifacts": [
            {
                "repository_path": item.repository_path,
                "fingerprint": item.fingerprint,
                "language": item.language,
                "byte_size": item.byte_size,
                "sensitivity_action": item.sensitivity_action,
                "analysis_status": _analysis_status(item),
            }
            for item in sorted(artifacts, key=lambda item: item.repository_path)
        ],
        "analyzer_versions": dict(sorted((analyzer_versions or {}).items())),
    }
    return RepositorySnapshotFingerprint(value=_sha256(payload))


def context_fingerprint(
    *,
    selected: SelectedRepositoryContext | None = None,
    repository_snapshot: RepositorySnapshotFingerprint,
    budget: ContextBudget,
    projection: Mapping[str, Any] | None = None,
) -> ContextFingerprint:
    """Fingerprint only the selected/redacted projection plus governing versions and budget."""
    if selected is None and projection is None:
        raise ValueError("selected or projection must be supplied")
    selected_projection: Mapping[str, Any]
    if projection is not None:
        selected_projection = projection
    else:
        assert selected is not None
        selected_projection = {
            "repository_summary": selected.repository_summary,
            "source_findings": selected.source_findings,
            "files": [asdict(item) for item in selected.files],
            "symbols": [asdict(item) for item in selected.symbols],
            "dependencies": [asdict(item) for item in selected.dependencies],
            "excerpts": [
                {
                    "repository_path": item.repository_path,
                    "line_start": item.line_start,
                    "line_end": item.line_end,
                    "content": item.content,
                    "fingerprint": item.fingerprint,
                    "provenance_id": item.provenance_id,
                }
                for item in selected.excerpts
            ],
            "provenance": [
                {
                    "provenance_id": item.provenance_id,
                    "kind": item.kind,
                    "subject": item.subject,
                    "source_fingerprint": item.source_fingerprint,
                    "selection_reason": item.selection_reason,
                    "location_path": item.location_path,
                    "line_start": item.line_start,
                    "line_end": item.line_end,
                    "derivation": item.derivation,
                    "resolution_confidence": item.resolution_confidence,
                    "sensitivity_action": item.sensitivity_action,
                    "metadata": dict(item.metadata),
                }
                for item in selected.provenance
            ],
            "truncation": {
                "configured_limits": dict(selected.truncation.configured_limits),
                "actual_usage": dict(selected.truncation.actual_usage),
                "omitted_counts": dict(selected.truncation.omitted_counts),
                "omission_reasons": dict(selected.truncation.omission_reasons),
                "truncated": selected.truncation.truncated,
                "insufficient": selected.truncation.insufficient,
            },
        }
    payload = {
        "contract_version": CONTEXT_CONTRACT_VERSION,
        "snapshot_fingerprint": repository_snapshot.value,
        "budget": asdict(budget),
        "projection": selected_projection,
    }
    return ContextFingerprint(value=_sha256(payload))


def _analysis_status(artifact: SourceArtifactRecord) -> str:
    if artifact.analysis.diagnostics:
        return "diagnostics"
    return "ok"


def _sha256(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
