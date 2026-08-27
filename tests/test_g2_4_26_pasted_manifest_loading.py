"""Focused direct proofs for G2.4.26 pasted governed submission-manifest loading."""

from __future__ import annotations

from json import dumps, loads
from pathlib import Path
from subprocess import run

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"
_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"


def _manifest(*, profile: str = "modern_todo_static_v1") -> dict[str, object]:
    return {
        "submission_id": "submission-id",
        "profile": profile,
        "requested_at": "2026-08-27T00:00:00+00:00",
        "expires_at": "2026-08-27T01:00:00+00:00",
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


def _load_pasted_manifest(tmp_path: Path, text: str) -> dict[str, object]:
    runner_path = tmp_path / "g2_4_26_pasted_manifest_runner.mjs"
    runner_path.write_text(
        """import { pathToFileURL } from 'node:url';

const [clientPath, pastedText] = process.argv.slice(2);

class PastedTextControl {
  constructor(value) {
    this.value = value;
  }
}

globalThis.HTMLInputElement = PastedTextControl;
globalThis.HTMLTextAreaElement = PastedTextControl;

const client = await import(pathToFileURL(clientPath).href);
const controls = new Map(
  client.MANIFEST_FIELDS.map((field, index) => [
    field,
    new PastedTextControl(`initial-${index}-${field}`),
  ]),
);
const form = {
  elements: {
    namedItem(field) {
      return controls.get(field) ?? null;
    },
  },
};
const beforeFormValues = Object.fromEntries(
  client.MANIFEST_FIELDS.map((field) => [field, controls.get(field).value]),
);
const result = client.loadPastedGovernedSubmissionManifest(pastedText);
const formApplied = client.applyManifestToForm({ form, result });
const afterFormValues = Object.fromEntries(
  client.MANIFEST_FIELDS.map((field) => [field, controls.get(field).value]),
);
process.stdout.write(JSON.stringify({
  result,
  form_state_proof: { formApplied, beforeFormValues, afterFormValues },
}));
""",
        encoding="utf-8",
    )
    completed = run(
        ["node", str(runner_path), str(_STATIC_CLIENT), text],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return loads(completed.stdout)


def test_pasted_manifest_page_has_an_explicit_non_submit_load_control() -> None:
    page = _STATIC_PAGE.read_text(encoding="utf-8")
    client = _STATIC_CLIENT.read_text(encoding="utf-8")

    assert 'id="pasted-manifest"' in page
    assert 'id="load-pasted-manifest" type="button"' in page
    assert "Load pasted manifest for review" in page
    assert "export function loadPastedGovernedSubmissionManifest(text)" in client
    assert "new TextEncoder().encode(text)" in client
    assert "parseGovernedSubmissionManifest({ declaredSize: bytes.byteLength, bytes })" in client
    assert "loadPastedManifest.addEventListener('click'" in client
    assert "navigator.clipboard" not in client
    assert "localStorage" not in client
    assert "sessionStorage" not in client
    assert "indexedDB" not in client


def test_pasted_manifest_loads_literal_values_for_review_without_submission(tmp_path: Path) -> None:
    manifest = _manifest(profile="unsupported_pasted_profile_literal")
    loaded = _load_pasted_manifest(tmp_path, dumps(manifest))

    result = loaded["result"]
    assert result["disposition"] == "LOADED_FOR_REVIEW"
    assert result["message"] == "Manifest loaded for review. Review fields and press Create."
    assert result["values"]["profile"] == "unsupported_pasted_profile_literal"
    assert loads(result["values"]["composition_attestation"]) == manifest["composition_attestation"]
    form_state = loaded["form_state_proof"]
    assert form_state["formApplied"] is True
    assert len(form_state["afterFormValues"]) == 13
    assert form_state["afterFormValues"] == result["values"]


def test_pasted_oversized_and_schema_invalid_text_refuse_without_form_mutation(tmp_path: Path) -> None:
    oversized = _load_pasted_manifest(tmp_path, "é" * ((64 * 1024 // 2) + 1))
    schema_invalid = _load_pasted_manifest(tmp_path, dumps({"unexpected": "value"}))

    for loaded in (oversized, schema_invalid):
        result = loaded["result"]
        assert result["disposition"] == "IMPORT_REFUSED"
        assert result["values"] is None
        form_state = loaded["form_state_proof"]
        assert form_state["formApplied"] is False
        assert len(form_state["beforeFormValues"]) == 13
        assert form_state["afterFormValues"] == form_state["beforeFormValues"]
    assert oversized["result"]["message"] == "Manifest exceeds the local 64 KiB import limit."
    assert schema_invalid["result"]["message"] == "Manifest must contain exactly the supported request fields."
