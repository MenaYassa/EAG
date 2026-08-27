"""Focused direct proofs for G2.4.27 browser-local prepared-input discard."""

from __future__ import annotations

from json import loads
from pathlib import Path
from subprocess import run

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"
_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"


def _discard_result(tmp_path: Path, *, missing_field: str | None = None) -> dict[str, object]:
    runner_path = tmp_path / "g2_4_27_discard_runner.mjs"
    runner_path.write_text(
        """import { pathToFileURL } from 'node:url';

const [clientPath, missingField] = process.argv.slice(2);

class LocalElement {
  constructor(value = '') {
    this.value = value;
    this.textContent = '';
  }
}

class LocalInput extends LocalElement {}
class LocalTextArea extends LocalElement {}
class LocalStatus extends LocalElement {}

globalThis.HTMLElement = LocalElement;
globalThis.HTMLInputElement = LocalInput;
globalThis.HTMLTextAreaElement = LocalTextArea;

const client = await import(pathToFileURL(clientPath).href);
const controls = new Map(
  client.MANIFEST_FIELDS.map((field) => [
    field,
    field === 'composition_attestation'
      ? new LocalTextArea(`prepared-${field}`)
      : new LocalInput(`prepared-${field}`),
  ]),
);
if (missingField !== '') controls.delete(missingField);
const form = {
  elements: {
    namedItem: (field) => controls.get(field) ?? null,
  },
};
const importInput = new LocalInput('selected-governed-manifest.json');
const pastedManifest = new LocalTextArea('{"prepared":true}');
const importStatus = new LocalStatus();
importStatus.textContent = 'Manifest loaded for review. Review fields and press Create.';
const before = Object.fromEntries(
  [...controls.entries()].map(([field, control]) => [field, control.value]),
);
const beforeLocal = {
  importInput: importInput.value,
  pastedManifest: pastedManifest.value,
  importStatus: importStatus.textContent,
};
const discarded = client.discardPreparedInputs({ form, importInput, pastedManifest, importStatus });
const after = Object.fromEntries(
  [...controls.entries()].map(([field, control]) => [field, control.value]),
);
process.stdout.write(JSON.stringify({
  discarded,
  fields: client.MANIFEST_FIELDS,
  before,
  after,
  beforeLocal,
  afterLocal: {
    importInput: importInput.value,
    pastedManifest: pastedManifest.value,
    importStatus: importStatus.textContent,
  },
}));
""",
        encoding="utf-8",
    )
    completed = run(
        ["node", str(runner_path), str(_STATIC_CLIENT), "" if missing_field is None else missing_field],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return loads(completed.stdout)


def test_discard_control_is_explicit_and_non_submit() -> None:
    page = _STATIC_PAGE.read_text(encoding="utf-8")
    client = _STATIC_CLIENT.read_text(encoding="utf-8")

    assert 'id="discard-prepared-inputs" type="button"' in page
    assert "Discard prepared inputs" in page
    assert "export function discardPreparedInputs" in client
    assert "discardPreparedInputsButton.addEventListener('click'" in client
    assert "Prepared local inputs discarded. No construction was submitted." in client
    assert "fetch(" not in client[client.index("export function discardPreparedInputs") : client.index("function resetResult")]


def test_discard_clears_exact_prepared_controls_and_local_import_state(tmp_path: Path) -> None:
    discarded = _discard_result(tmp_path)

    assert discarded["discarded"] is True
    fields = discarded["fields"]
    assert isinstance(fields, list)
    assert len(fields) == 13
    assert set(discarded["before"]) == set(fields)
    assert all(value.startswith("prepared-") for value in discarded["before"].values())
    assert discarded["after"] == {field: "" for field in fields}
    assert discarded["afterLocal"] == {
        "importInput": "",
        "pastedManifest": "",
        "importStatus": "Prepared local inputs discarded. No construction was submitted.",
    }


def test_discard_missing_required_control_fails_closed_without_partial_reset(tmp_path: Path) -> None:
    refused = _discard_result(tmp_path, missing_field="audit_root")

    assert refused["discarded"] is False
    assert "audit_root" not in refused["before"]
    assert refused["after"] == refused["before"]
    assert refused["afterLocal"] == refused["beforeLocal"]
