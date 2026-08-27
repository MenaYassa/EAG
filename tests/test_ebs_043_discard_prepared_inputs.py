"""EBS-043 — explicit local prepared-submission discard over the published visual boundary."""

from __future__ import annotations

from json import loads
from pathlib import Path
from subprocess import run

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"
_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"


def _run_discard_listener(
    tmp_path: Path,
    *,
    missing_field: str | None = None,
    wrong_type_discard_control: bool = False,
    invalid_required_target: bool = False,
) -> dict[str, object]:
    runner_path = tmp_path / "ebs_043_discard_listener_runner.mjs"
    runner_path.write_text(
        """import { pathToFileURL } from 'node:url';

const [clientPath, missingField, wrongTypeDiscardControl, invalidRequiredTarget] = process.argv.slice(2);

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

  replaceChildren() {
    this.textContent = '';
  }
}

class BenchmarkForm extends BenchmarkElement {
  constructor(controls, createButton) {
    super();
    this.controls = controls;
    this.createButton = createButton;
    this.createListenerInvocations = 0;
    this.elements = {
      namedItem: (field) => this.controls.get(field) ?? null,
    };
  }

  addEventListener(type, listener) {
    if (type === 'submit') {
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
  ['submission_id', new BenchmarkInputElement('prepared-submission_id')],
  ['profile', new BenchmarkInputElement('prepared-profile')],
  ['requested_at', new BenchmarkInputElement('prepared-requested_at')],
  ['expires_at', new BenchmarkInputElement('prepared-expires_at')],
  ['attestation_id', new BenchmarkInputElement('prepared-attestation_id')],
  ['execution_id', new BenchmarkInputElement('prepared-execution_id')],
  ['run_id', new BenchmarkInputElement('prepared-run_id')],
  ['workspace_id', new BenchmarkInputElement('prepared-workspace_id')],
  ['workspace_root', new BenchmarkInputElement('prepared-workspace_root')],
  ['source_repository_root', new BenchmarkInputElement('prepared-source_repository_root')],
  ['audit_root', new BenchmarkInputElement('prepared-audit_root')],
  ['control_root', new BenchmarkInputElement('prepared-control_root')],
  ['composition_attestation', new BenchmarkTextAreaElement('prepared-composition_attestation')],
]);
if (missingField !== '') controls.delete(missingField);
if (invalidRequiredTarget === 'true') {
  controls.set('composition_attestation', new BenchmarkElement('invalid-composition_attestation'));
}
const createButton = new BenchmarkButtonElement();
const form = new BenchmarkForm(controls, createButton);
const importInput = new BenchmarkInputElement('prepared-manifest.json');
const pastedManifest = new BenchmarkTextAreaElement('{"prepared":true}');
const loadPastedManifest = new BenchmarkButtonElement();
const discardPreparedInputsButton = wrongTypeDiscardControl === 'true'
  ? new BenchmarkElement()
  : new BenchmarkButtonElement();
const importStatus = new BenchmarkElement();
importStatus.textContent = 'Manifest loaded for review. Review fields and press Create.';
const status = new BenchmarkElement();
status.textContent = 'receipt_available';
const facts = new BenchmarkElement();
facts.textContent = 'terminal-facts';
const files = new BenchmarkElement();
files.hidden = false;
const fileRows = new BenchmarkTableSectionElement();
fileRows.textContent = 'terminal-receipt-row';
const elementsBySelector = new Map([
  ['#construct-form', form],
  ['#status', status],
  ['#submission-manifest', importInput],
  ['#pasted-manifest', pastedManifest],
  ['#load-pasted-manifest', loadPastedManifest],
  ['#discard-prepared-inputs', discardPreparedInputsButton],
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
const beforeControls = Object.fromEntries(
  [...controls.entries()].map(([field, control]) => [field, control.value]),
);
const beforeLocalInputs = {
  importInput: importInput.value,
  pastedManifest: pastedManifest.value,
  importStatus: importStatus.textContent,
};
const beforeTerminal = {
  status: status.textContent,
  facts: facts.textContent,
  filesHidden: files.hidden,
  fileRows: fileRows.textContent,
};
const discardListener = discardPreparedInputsButton.listeners.get('click');
const fileImportListener = importInput.listeners.get('change');
const pastedLoadListener = loadPastedManifest.listeners.get('click');
const createListener = form.listeners.get('submit');
if (typeof createListener !== 'function'
  || typeof fileImportListener !== 'function'
  || typeof pastedLoadListener !== 'function') {
  throw new Error('pre-existing production visual listeners were not installed');
}
let discardListenerInvocations = 0;
if (typeof discardListener === 'function') {
  discardListenerInvocations += 1;
  discardListener();
}
const afterControls = Object.fromEntries(
  [...controls.entries()].map(([field, control]) => [field, control.value]),
);
process.stdout.write(JSON.stringify({
  fields: client.MANIFEST_FIELDS,
  beforeControls,
  afterControls,
  beforeLocalInputs,
  afterLocalInputs: {
    importInput: importInput.value,
    pastedManifest: pastedManifest.value,
    importStatus: importStatus.textContent,
  },
  beforeTerminal,
  afterTerminal: {
    status: status.textContent,
    facts: facts.textContent,
    filesHidden: files.hidden,
    fileRows: fileRows.textContent,
  },
  interaction: {
    discardListenerInstalled: typeof discardListener === 'function',
    discardListenerInvocations,
    fileImportListenerInstalled: typeof fileImportListener === 'function',
    pastedLoadListenerInstalled: typeof pastedLoadListener === 'function',
    createListenerInstalled: typeof createListener === 'function',
    createListenerInvocations: form.createListenerInvocations,
  },
}));
""",
        encoding="utf-8",
    )
    completed = run(
        [
            "node",
            str(runner_path),
            str(_STATIC_CLIENT),
            "" if missing_field is None else missing_field,
            "true" if wrong_type_discard_control else "false",
            "true" if invalid_required_target else "false",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return loads(completed.stdout)


def test_ebs_043_discard_listener_clears_only_browser_local_prepared_state(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-043-discard")
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    discarded = _run_discard_listener(tmp_path)

    page = _STATIC_PAGE.read_text(encoding="utf-8")
    assert 'id="discard-prepared-inputs" type="button"' in page

    interaction = discarded["interaction"]
    assert interaction["discardListenerInstalled"] is True
    assert interaction["discardListenerInvocations"] == 1
    assert interaction["createListenerInstalled"] is True
    assert interaction["createListenerInvocations"] == 0

    fields = discarded["fields"]
    assert isinstance(fields, list)
    assert len(fields) == 13
    assert set(discarded["beforeControls"]) == set(fields)
    assert all(value.startswith("prepared-") for value in discarded["beforeControls"].values())
    assert discarded["afterControls"] == {field: "" for field in fields}
    assert discarded["afterLocalInputs"] == {
        "importInput": "",
        "pastedManifest": "",
        "importStatus": "Prepared local inputs discarded. No construction was submitted.",
    }
    assert discarded["afterTerminal"] == discarded["beforeTerminal"]
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace


def test_ebs_043_missing_required_control_leaves_all_local_and_terminal_state_unchanged(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-043-missing-control")
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    refused = _run_discard_listener(tmp_path, missing_field="audit_root")

    interaction = refused["interaction"]
    assert interaction["discardListenerInstalled"] is True
    assert interaction["discardListenerInvocations"] == 1
    assert interaction["createListenerInstalled"] is True
    assert interaction["createListenerInvocations"] == 0
    assert "audit_root" not in refused["beforeControls"]
    assert refused["afterControls"] == refused["beforeControls"]
    assert refused["afterLocalInputs"] == refused["beforeLocalInputs"]
    assert refused["afterTerminal"] == refused["beforeTerminal"]
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace


def test_ebs_043_invalid_required_discard_target_fails_closed_without_partial_mutation(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-043-invalid-target")
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    refused = _run_discard_listener(tmp_path, invalid_required_target=True)

    interaction = refused["interaction"]
    assert interaction["discardListenerInstalled"] is True
    assert interaction["discardListenerInvocations"] == 1
    assert interaction["createListenerInstalled"] is True
    assert interaction["createListenerInvocations"] == 0
    fields = refused["fields"]
    assert isinstance(fields, list)
    assert len(fields) == 13
    assert set(refused["beforeControls"]) == set(fields)
    assert refused["beforeControls"]["composition_attestation"] == "invalid-composition_attestation"
    assert refused["afterControls"] == refused["beforeControls"]
    assert refused["afterLocalInputs"] == refused["beforeLocalInputs"]
    assert refused["afterTerminal"] == refused["beforeTerminal"]
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace


def test_ebs_043_wrong_type_discard_control_leaves_existing_bindings_and_state_unchanged(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-043-wrong-type-discard")
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    unchanged = _run_discard_listener(tmp_path, wrong_type_discard_control=True)

    interaction = unchanged["interaction"]
    assert interaction["discardListenerInstalled"] is False
    assert interaction["discardListenerInvocations"] == 0
    assert interaction["fileImportListenerInstalled"] is True
    assert interaction["pastedLoadListenerInstalled"] is True
    assert interaction["createListenerInstalled"] is True
    assert interaction["createListenerInvocations"] == 0
    assert unchanged["afterControls"] == unchanged["beforeControls"]
    assert unchanged["afterLocalInputs"] == unchanged["beforeLocalInputs"]
    assert unchanged["afterTerminal"] == unchanged["beforeTerminal"]
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace


def test_ebs_043_discard_delta_has_no_prohibited_browser_or_submission_capability() -> None:
    static_client = _STATIC_CLIENT.read_text(encoding="utf-8")
    discard_routine = static_client[
        static_client.index("export function discardPreparedInputs") : static_client.index("function resetResult")
    ]
    discard_binding = static_client[
        static_client.index("discardPreparedInputsButton.addEventListener('click'") : static_client.index(
            "form.addEventListener('submit'"
        )
    ]

    assert "MANIFEST_FIELDS" in discard_routine
    assert "fetch(" not in discard_routine
    assert "fetch(" not in discard_binding
    for forbidden in ("navigator.clipboard", "localStorage", "sessionStorage", "indexedDB", "http://", "https://"):
        assert forbidden not in discard_routine
        assert forbidden not in discard_binding
