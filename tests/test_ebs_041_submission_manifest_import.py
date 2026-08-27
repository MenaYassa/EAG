"""EBS-041 — local governed submission-manifest import over the published visual chain."""

from __future__ import annotations

from io import BytesIO
from json import dumps, loads
from pathlib import Path
from subprocess import run
from typing import Any
from wsgiref.util import setup_testing_defaults

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

from eag.governed_visual_presentation import create_fixed_profile_visual_application

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"


def _payload_for_fixture(fixture: object, *, profile: str | None = None) -> dict[str, object]:
    submission = fixture.submission
    custody = submission.custody_request
    return {
        "submission_id": submission.submission_id,
        "profile": submission.selected_profile_token if profile is None else profile,
        "requested_at": submission.requested_at.isoformat(),
        "expires_at": submission.expires_at.isoformat(),
        "attestation_id": custody.attestation_id,
        "execution_id": custody.execution_id,
        "run_id": custody.run_id,
        "workspace_id": custody.workspace_id,
        "workspace_root": str(custody.workspace_root),
        "source_repository_root": str(custody.source_repository_root),
        "audit_root": str(custody.audit_root),
        "control_root": str(custody.control_root),
        "composition_attestation": submission.runtime_composition_attestation.to_payload(),
    }


def _request(
    *,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> tuple[str, dict[str, str], bytes]:
    application = create_fixed_profile_visual_application()
    body = b"" if payload is None else dumps(payload).encode("utf-8")
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(
        {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "REMOTE_ADDR": "127.0.0.1",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
        }
    )
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    response_body = b"".join(application(environ, start_response))
    return captured["status"], captured["headers"], response_body  # type: ignore[return-value]


def _import_manifest(tmp_path: Path, manifest_bytes: bytes) -> dict[str, object]:
    input_path = tmp_path / "governed-submission.json"
    runner_path = tmp_path / "ebs_041_manifest_import_runner.mjs"
    input_path.write_bytes(manifest_bytes)
    runner_path.write_text(
        """import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { File } from 'node:buffer';

const [clientPath, manifestPath] = process.argv.slice(2);

class BenchmarkInputControl {
  constructor(value) {
    this.value = value;
  }
}

globalThis.HTMLInputElement = BenchmarkInputControl;
globalThis.HTMLTextAreaElement = BenchmarkInputControl;

const client = await import(pathToFileURL(clientPath).href);
const controls = new Map(
  client.MANIFEST_FIELDS.map((field, index) => [
    field,
    new BenchmarkInputControl(`initial-${index}-${field}`),
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
const bytes = readFileSync(manifestPath);
const file = new File([bytes], 'governed-submission.json', { type: 'application/json' });
const result = await client.importGovernedSubmissionManifest(file);
const formApplied = client.applyManifestToForm({ form, result });
const afterFormValues = Object.fromEntries(
  client.MANIFEST_FIELDS.map((field) => [field, controls.get(field).value]),
);
process.stdout.write(JSON.stringify({
  ...result,
  form_state_proof: { formApplied, beforeFormValues, afterFormValues },
}));
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


def test_ebs_041_manifest_import_is_bounded_literal_and_requires_explicit_create(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-041-success")
    retained_root = fixture.workspace_root
    manifest = _payload_for_fixture(fixture)
    before_import = tuple(sorted(path.name for path in retained_root.iterdir()))

    page_status, page_headers, page = _request(method="GET", path="/")
    imported = _import_manifest(tmp_path, dumps(manifest).encode("utf-8"))

    assert page_status == "200 OK"
    assert page_headers["Content-Type"] == "text/html; charset=utf-8"
    assert b'id="submission-manifest"' in page
    assert b'id="import-status"' in page
    assert b'id="profile"' in page
    assert b"readonly" in page
    assert imported["disposition"] == "LOADED_FOR_REVIEW"
    imported_values = imported["values"]
    assert isinstance(imported_values, dict)
    assert imported_values["profile"] == manifest["profile"]
    for field, value in manifest.items():
        if field == "composition_attestation":
            assert loads(imported_values[field]) == value
        else:
            assert imported_values[field] == value
    assert tuple(sorted(path.name for path in retained_root.iterdir())) == before_import

    explicit_create_payload = dict(imported_values)
    imported_composition = explicit_create_payload["composition_attestation"]
    assert isinstance(imported_composition, str)
    explicit_create_payload["composition_attestation"] = loads(imported_composition)

    status, _, body = _request(method="POST", path="/api/construct", payload=explicit_create_payload)
    response = loads(body)
    assert status == "200 OK"
    assert response["presentation_disposition"] == "receipt_available"
    assert response["selected_profile"] == imported_values["profile"]
    assert response["selected_profile"] == "modern_todo_static_v1"
    assert response["receipt_files"]


def test_ebs_041_representation_refusals_preserve_local_values_and_workspace(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-041-representation-refusal")
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    unknown_key_manifest = _payload_for_fixture(fixture)
    unknown_key_manifest["not_a_supported_field"] = "must be refused"
    missing_key_manifest = _payload_for_fixture(fixture)
    del missing_key_manifest["workspace_id"]
    wrong_type_manifest = _payload_for_fixture(fixture)
    wrong_type_manifest["workspace_id"] = 7
    non_object_composition_manifest = _payload_for_fixture(fixture)
    non_object_composition_manifest["composition_attestation"] = ["not", "an", "object"]

    oversized = _import_manifest(tmp_path, b"x" * ((64 * 1024) + 1))
    malformed_utf8 = _import_manifest(tmp_path, b"\xff")
    unknown_key = _import_manifest(tmp_path, dumps(unknown_key_manifest).encode("utf-8"))
    missing_key = _import_manifest(tmp_path, dumps(missing_key_manifest).encode("utf-8"))
    wrong_type = _import_manifest(tmp_path, dumps(wrong_type_manifest).encode("utf-8"))
    non_object_composition = _import_manifest(
        tmp_path, dumps(non_object_composition_manifest).encode("utf-8")
    )

    for result in (
        oversized,
        malformed_utf8,
        unknown_key,
        missing_key,
        wrong_type,
        non_object_composition,
    ):
        assert result["disposition"] == "IMPORT_REFUSED"
        assert result["values"] is None
        form_state_proof = result["form_state_proof"]
        assert form_state_proof["formApplied"] is False
        assert len(form_state_proof["beforeFormValues"]) == 13
        assert form_state_proof["afterFormValues"] == form_state_proof["beforeFormValues"]
        assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before
    assert oversized["message"] == "Manifest exceeds the local 64 KiB import limit."
    assert malformed_utf8["message"] == "Manifest must be valid UTF-8."
    assert unknown_key["message"] == "Manifest must contain exactly the supported request fields."
    assert missing_key["message"] == "Manifest must contain exactly the supported request fields."
    assert wrong_type["message"] == "Manifest field workspace_id must be a string."
    assert non_object_composition["message"] == "Manifest composition_attestation must be an object."

    static_client = _STATIC_CLIENT.read_text(encoding="utf-8")
    assert static_client.index("file.size > MAX_MANIFEST_BYTES") < static_client.index(
        "await file.arrayBuffer()"
    )


def test_ebs_041_unsupported_profile_loads_then_real_g2_4_21_refuses_before_effect(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-041-profile-refusal")
    unsupported_payload = _payload_for_fixture(fixture, profile="unsupported_manifest_profile")
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))

    imported = _import_manifest(tmp_path, dumps(unsupported_payload).encode("utf-8"))
    assert imported["disposition"] == "LOADED_FOR_REVIEW"
    imported_values = imported["values"]
    assert isinstance(imported_values, dict)
    assert imported_values["profile"] == "unsupported_manifest_profile"
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before

    explicit_create_payload = dict(imported_values)
    imported_composition = explicit_create_payload["composition_attestation"]
    assert isinstance(imported_composition, str)
    explicit_create_payload["composition_attestation"] = loads(imported_composition)

    status, _, body = _request(method="POST", path="/api/construct", payload=explicit_create_payload)
    response = loads(body)
    assert status == "200 OK"
    assert response["selected_profile"] == imported_values["profile"]
    assert response["selected_profile"] == "unsupported_manifest_profile"
    assert response["presentation_disposition"] == "upstream_refused"
    assert response["failure_stage"] == "g2_4_21_profile_issuance"
    assert response["receipt_files"] == []
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before
