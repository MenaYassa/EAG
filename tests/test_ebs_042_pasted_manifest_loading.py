"""EBS-042 — explicit local pasted-manifest loading over the published visual chain."""

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
_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"


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


def _request(*, payload: dict[str, object]) -> tuple[str, dict[str, str], bytes]:
    application = create_fixed_profile_visual_application()
    body = dumps(payload).encode("utf-8")
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/construct",
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


def _load_pasted_manifest(tmp_path: Path, text: str) -> dict[str, object]:
    runner_path = tmp_path / "ebs_042_pasted_manifest_runner.mjs"
    runner_path.write_text(
        """import { pathToFileURL } from 'node:url';

const [clientPath, pastedText] = process.argv.slice(2);

class BenchmarkElement {
  constructor(value = '') {
    this.value = value;
    this.textContent = '';
    this.hidden = false;
    this.listeners = new Map();
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  replaceChildren() {}
}

class BenchmarkForm extends BenchmarkElement {
  constructor(controls, createButton) {
    super();
    this.controls = controls;
    this.createButton = createButton;
    this.createListener = null;
    this.createListenerInvocations = 0;
    this.elements = {
      namedItem: (field) => this.controls.get(field) ?? null,
    };
  }

  addEventListener(type, listener) {
    if (type === 'submit') {
      this.createListener = listener;
      super.addEventListener(type, (...args) => {
        this.createListenerInvocations += 1;
        return listener(...args);
      });
      return;
    }
    super.addEventListener(type, listener);
  }

  querySelector(selector) {
    return selector === 'button[type="submit"]' ? this.createButton : null;
  }
}

class BenchmarkInputElement extends BenchmarkElement {}
class BenchmarkTextAreaElement extends BenchmarkElement {}
class BenchmarkButtonElement extends BenchmarkElement {}
class BenchmarkTableSectionElement extends BenchmarkElement {}

globalThis.HTMLElement = BenchmarkElement;
globalThis.HTMLInputElement = BenchmarkInputElement;
globalThis.HTMLTextAreaElement = BenchmarkTextAreaElement;
globalThis.HTMLButtonElement = BenchmarkButtonElement;
globalThis.HTMLTableSectionElement = BenchmarkTableSectionElement;
globalThis.HTMLFormElement = BenchmarkForm;

const controls = new Map([
  ['submission_id', new BenchmarkInputElement('initial-submission_id')],
  ['profile', new BenchmarkInputElement('initial-profile')],
  ['requested_at', new BenchmarkInputElement('initial-requested_at')],
  ['expires_at', new BenchmarkInputElement('initial-expires_at')],
  ['attestation_id', new BenchmarkInputElement('initial-attestation_id')],
  ['execution_id', new BenchmarkInputElement('initial-execution_id')],
  ['run_id', new BenchmarkInputElement('initial-run_id')],
  ['workspace_id', new BenchmarkInputElement('initial-workspace_id')],
  ['workspace_root', new BenchmarkInputElement('initial-workspace_root')],
  ['source_repository_root', new BenchmarkInputElement('initial-source_repository_root')],
  ['audit_root', new BenchmarkInputElement('initial-audit_root')],
  ['control_root', new BenchmarkInputElement('initial-control_root')],
  ['composition_attestation', new BenchmarkTextAreaElement('initial-composition_attestation')],
]);
const createButton = new BenchmarkButtonElement();
const form = new BenchmarkForm(controls, createButton);
const importInput = new BenchmarkInputElement();
const pastedManifest = new BenchmarkTextAreaElement(pastedText);
const loadPastedManifest = new BenchmarkButtonElement();
const importStatus = new BenchmarkElement();
const status = new BenchmarkElement();
const facts = new BenchmarkElement();
const files = new BenchmarkElement();
const fileRows = new BenchmarkTableSectionElement();
const elementsBySelector = new Map([
  ['#construct-form', form],
  ['#status', status],
  ['#submission-manifest', importInput],
  ['#pasted-manifest', pastedManifest],
  ['#load-pasted-manifest', loadPastedManifest],
  ['#import-status', importStatus],
  ['#facts', facts],
  ['#files', files],
  ['#files tbody', fileRows],
]);
globalThis.document = {
  querySelector(selector) {
    return elementsBySelector.get(selector) ?? null;
  },
};

const client = await import(pathToFileURL(clientPath).href);
const beforeFormValues = Object.fromEntries(
  client.MANIFEST_FIELDS.map((field) => [field, controls.get(field).value]),
);
const loadListener = loadPastedManifest.listeners.get('click');
const capturedCreateListener = form.listeners.get('submit');
if (typeof loadListener !== 'function' || typeof capturedCreateListener !== 'function') {
  throw new Error('production visual listeners were not installed');
}
let loadListenerInvocations = 0;
loadListenerInvocations += 1;
loadListener();
const listenerWrittenImportStatus = importStatus.textContent;
const afterFormValues = Object.fromEntries(
  client.MANIFEST_FIELDS.map((field) => [field, controls.get(field).value]),
);
const result = afterFormValues.profile === beforeFormValues.profile
  ? client.loadPastedGovernedSubmissionManifest(pastedText)
  : Object.freeze({
      disposition: client.IMPORT_DISPOSITIONS.LOADED_FOR_REVIEW,
      message: importStatus.textContent,
      values: Object.freeze(afterFormValues),
    });
process.stdout.write(JSON.stringify({
  result,
  form_state_proof: {
    formApplied: afterFormValues.profile !== beforeFormValues.profile,
    beforeFormValues,
    afterFormValues,
  },
  interaction_proof: {
    loadListenerInstalled: typeof loadListener === 'function',
    loadListenerInvocations,
    createListenerInstalled: typeof capturedCreateListener === 'function',
    createListenerInvocations: form.createListenerInvocations,
    importStatus: listenerWrittenImportStatus,
  },
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


def test_ebs_042_pasted_supported_text_loads_then_explicit_create_reaches_receipt_success(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-042-success")
    manifest = _payload_for_fixture(fixture)
    before_load = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))

    page = _STATIC_PAGE.read_text(encoding="utf-8")
    loaded = _load_pasted_manifest(tmp_path, dumps(manifest))

    assert 'id="pasted-manifest"' in page
    assert 'id="load-pasted-manifest" type="button"' in page
    static_client = _STATIC_CLIENT.read_text(encoding="utf-8")
    load_binding = static_client[
        static_client.index("loadPastedManifest.addEventListener('click'") : static_client.index(
            "form.addEventListener('submit'"
        )
    ]
    text_adapter = static_client[
        static_client.index("export function loadPastedGovernedSubmissionManifest") : static_client.index(
            "function resetResult"
        )
    ]
    assert "loadPastedGovernedSubmissionManifest(pastedManifest.value)" in load_binding
    assert "applyManifestToForm({ form, result })" in load_binding
    assert "fetch(" not in load_binding
    assert "new TextEncoder().encode(text)" in text_adapter
    assert "parseGovernedSubmissionManifest" in text_adapter
    assert "importGovernedSubmissionManifest" not in text_adapter
    assert "fetch(" not in text_adapter
    interaction = loaded["interaction_proof"]
    assert interaction["loadListenerInstalled"] is True
    assert interaction["loadListenerInvocations"] == 1
    assert interaction["createListenerInstalled"] is True
    assert interaction["createListenerInvocations"] == 0
    assert interaction["importStatus"] == "Manifest loaded for review. Review fields and press Create."
    assert loaded["result"]["disposition"] == "LOADED_FOR_REVIEW"
    imported_values = loaded["result"]["values"]
    assert isinstance(imported_values, dict)
    assert imported_values["profile"] == manifest["profile"]
    assert loads(imported_values["composition_attestation"]) == manifest["composition_attestation"]
    form_state = loaded["form_state_proof"]
    assert form_state["formApplied"] is True
    assert form_state["afterFormValues"] == imported_values
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_load

    explicit_create_payload = dict(imported_values)
    composition_attestation = explicit_create_payload["composition_attestation"]
    assert isinstance(composition_attestation, str)
    explicit_create_payload["composition_attestation"] = loads(composition_attestation)

    status, _, body = _request(payload=explicit_create_payload)
    response = loads(body)
    assert status == "200 OK"
    assert response["presentation_disposition"] == "receipt_available"
    assert response["selected_profile"] == imported_values["profile"]
    assert response["receipt_files"]


def test_ebs_042_pasted_unsupported_profile_stays_local_until_explicit_create_then_g2_4_21_refuses(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-042-profile-refusal")
    manifest = _payload_for_fixture(fixture, profile="unsupported_pasted_profile")
    before_load = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))

    loaded = _load_pasted_manifest(tmp_path, dumps(manifest))

    interaction = loaded["interaction_proof"]
    assert interaction["loadListenerInstalled"] is True
    assert interaction["loadListenerInvocations"] == 1
    assert interaction["createListenerInstalled"] is True
    assert interaction["createListenerInvocations"] == 0
    assert interaction["importStatus"] == "Manifest loaded for review. Review fields and press Create."
    assert loaded["result"]["disposition"] == "LOADED_FOR_REVIEW"
    imported_values = loaded["result"]["values"]
    assert isinstance(imported_values, dict)
    assert imported_values["profile"] == "unsupported_pasted_profile"
    assert loaded["form_state_proof"]["formApplied"] is True
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_load

    explicit_create_payload = dict(imported_values)
    composition_attestation = explicit_create_payload["composition_attestation"]
    assert isinstance(composition_attestation, str)
    explicit_create_payload["composition_attestation"] = loads(composition_attestation)

    status, _, body = _request(payload=explicit_create_payload)
    response = loads(body)
    assert status == "200 OK"
    assert response["selected_profile"] == imported_values["profile"]
    assert response["presentation_disposition"] == "upstream_refused"
    assert response["failure_stage"] == "g2_4_21_profile_issuance"
    assert response["receipt_files"] == []
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_load


def test_ebs_042_pasted_representation_refusals_preserve_all_form_controls_and_workspace(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-042-refusal")
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))

    oversized = _load_pasted_manifest(tmp_path, "é" * ((64 * 1024 // 2) + 1))
    malformed_json = _load_pasted_manifest(tmp_path, "{")
    schema_invalid = _load_pasted_manifest(tmp_path, dumps({"not": "the required shape"}))

    refusal_cases = (
        (oversized, "Manifest exceeds the local 64 KiB import limit."),
        (malformed_json, "Manifest must be valid JSON."),
        (schema_invalid, "Manifest must contain exactly the supported request fields."),
    )
    for loaded, expected_message in refusal_cases:
        interaction = loaded["interaction_proof"]
        assert interaction["loadListenerInstalled"] is True
        assert interaction["loadListenerInvocations"] == 1
        assert interaction["createListenerInstalled"] is True
        assert interaction["createListenerInvocations"] == 0
        assert interaction["importStatus"] == expected_message

        result = loaded["result"]
        assert result["disposition"] == "IMPORT_REFUSED"
        assert result["values"] is None
        assert result["message"] == expected_message
        form_state = loaded["form_state_proof"]
        assert form_state["formApplied"] is False
        assert len(form_state["beforeFormValues"]) == 13
        assert form_state["afterFormValues"] == form_state["beforeFormValues"]
        assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before

    static_client = _STATIC_CLIENT.read_text(encoding="utf-8")
    adapter = static_client[
        static_client.index("export function loadPastedGovernedSubmissionManifest") : static_client.index(
            "function resetResult"
        )
    ]
    assert "parseGovernedSubmissionManifest" in adapter
    assert "fetch(" not in adapter
    assert "navigator.clipboard" not in static_client
    assert "localStorage" not in static_client
    assert "sessionStorage" not in static_client
    assert "indexedDB" not in static_client
