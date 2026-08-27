"""Focused direct proofs for the G2.4.25 local governed submission-manifest import."""

from __future__ import annotations

from json import dumps, loads
from pathlib import Path
from subprocess import run

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"


def _manifest(*, profile: str = "modern_todo_static_v1") -> dict[str, object]:
    return {
        "submission_id": "submission-id",
        "profile": profile,
        "requested_at": "2026-08-26T00:00:00+00:00",
        "expires_at": "2026-08-26T01:00:00+00:00",
        "attestation_id": "attestation-id",
        "execution_id": "execution-id",
        "run_id": "run-id",
        "workspace_id": "workspace-id",
        "workspace_root": "/caller/workspace",
        "source_repository_root": "/caller/source",
        "audit_root": "/caller/audit",
        "control_root": "/caller/control",
        "composition_attestation": {"caller": "supplied"},
    }


def _run_real_manifest_import(tmp_path: Path, manifest_bytes: bytes) -> dict[str, object]:
    """Exercise the real browser module with a real Node File and its arrayBuffer path."""
    input_path = tmp_path / "manifest.json"
    runner_path = tmp_path / "manifest_import_runner.mjs"
    input_path.write_bytes(manifest_bytes)
    runner_path.write_text(
        """import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { File } from 'node:buffer';

const [clientPath, manifestPath] = process.argv.slice(2);
const client = await import(pathToFileURL(clientPath).href);
const bytes = readFileSync(manifestPath);
const file = new File([bytes], 'governed-submission.json', { type: 'application/json' });
const result = await client.importGovernedSubmissionManifest(file);
process.stdout.write(JSON.stringify(result));
""",
        encoding="utf-8",
    )
    completed = run(
        ["node", str(runner_path), str(_STATIC_CLIENT), str(input_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return loads(completed.stdout)


def test_manifest_client_has_fixed_representation_boundary_before_form_application() -> None:
    static_client = _STATIC_CLIENT.read_text(encoding="utf-8")

    assert "export const MAX_MANIFEST_BYTES = 64 * 1024;" in static_client
    assert "file.size > MAX_MANIFEST_BYTES" in static_client
    assert "new TextDecoder('utf-8', { fatal: true })" in static_client
    assert "Object.keys(payload)" in static_client
    assert "MANIFEST_FIELDS.includes(key)" in static_client
    assert "typeof payload[field] !== 'string'" in static_client
    assert "isJsonObject(payload.composition_attestation)" in static_client
    assert "result.disposition === IMPORT_DISPOSITIONS.LOADED_FOR_REVIEW" in static_client
    assert "applyManifestToForm({ form, result });" in static_client
    assert "fetch('/api/construct'" in static_client
    assert static_client.index("file.size > MAX_MANIFEST_BYTES") < static_client.index(
        "await file.arrayBuffer()"
    )


def test_schema_valid_unsupported_profile_is_relayed_literally_for_review(tmp_path: Path) -> None:
    manifest = _manifest(profile="unsupported_profile_literal")
    result = _run_real_manifest_import(tmp_path, dumps(manifest).encode("utf-8"))

    assert result["disposition"] == "LOADED_FOR_REVIEW"
    assert result["message"] == "Manifest loaded for review. Review fields and press Create."
    assert result["values"]["profile"] == "unsupported_profile_literal"
    assert result["values"]["composition_attestation"] == dumps(
        manifest["composition_attestation"], separators=(",", ":")
    )


def test_oversized_malformed_utf8_and_unknown_key_manifests_are_refused_without_values(
    tmp_path: Path,
) -> None:
    oversized = _run_real_manifest_import(tmp_path, b"x" * ((64 * 1024) + 1))
    malformed_utf8 = _run_real_manifest_import(tmp_path, b"\xff")
    with_unknown_key = _manifest()
    with_unknown_key["unexpected"] = "not configuration"
    unknown_key = _run_real_manifest_import(tmp_path, dumps(with_unknown_key).encode("utf-8"))

    for result in (oversized, malformed_utf8, unknown_key):
        assert result["disposition"] == "IMPORT_REFUSED"
        assert result["values"] is None
    assert oversized["message"] == "Manifest exceeds the local 64 KiB import limit."
    assert malformed_utf8["message"] == "Manifest must be valid UTF-8."
    assert unknown_key["message"] == "Manifest must contain exactly the supported request fields."
