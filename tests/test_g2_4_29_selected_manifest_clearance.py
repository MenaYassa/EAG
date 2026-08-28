"""Focused direct proofs for G2.4.29 browser-local selected-manifest clearance."""

from __future__ import annotations

from json import loads
from pathlib import Path
from subprocess import run

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"
_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"


def _run_clearance_listener(tmp_path: Path, scenario: str) -> dict[str, object]:
    runner_path = tmp_path / "g2_4_29_clearance_runner.mjs"
    runner_path.write_text(
        """import { pathToFileURL } from 'node:url';

const [clientPath, scenario] = process.argv.slice(2);

class BenchmarkElement {
  constructor(value = '') {
    this.value = value;
    this.textContent = '';
    this.hidden = false;
    this.children = [];
    this.listeners = new Map();
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  replaceChildren(...children) {
    this.children = [...children];
    this.textContent = '';
  }
}

class BenchmarkInputElement extends BenchmarkElement {
  constructor(value = '', type = 'text') {
    super(value);
    this.type = type;
  }
}
class BenchmarkTextAreaElement extends BenchmarkElement {}
class BenchmarkButtonElement extends BenchmarkElement {}
class BenchmarkTableSectionElement extends BenchmarkElement {}
class BenchmarkNonHTMLElementElement {
  constructor(value = '', type = 'text') {
    this.value = value;
    this.type = type;
    this.textContent = '';
    this.hidden = false;
    this.children = [];
  }

  replaceChildren(...children) {
    this.children = [...children];
    this.textContent = '';
  }
}
class BenchmarkForm extends BenchmarkElement {
  constructor(controls, createButton) {
    super();
    this.controls = controls;
    this.createButton = createButton;
    this.createListenerInvocations = 0;
    this.elements = { namedItem: (field) => this.controls.get(field) ?? null };
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

globalThis.HTMLElement = BenchmarkElement;
globalThis.HTMLInputElement = BenchmarkInputElement;
globalThis.HTMLTextAreaElement = BenchmarkTextAreaElement;
globalThis.HTMLButtonElement = BenchmarkButtonElement;
globalThis.HTMLTableSectionElement = BenchmarkTableSectionElement;
globalThis.HTMLFormElement = BenchmarkForm;
let requestCount = 0;
globalThis.fetch = () => {
  requestCount += 1;
  throw new Error('selected-manifest clearance must not issue a request');
};

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
const createButton = new BenchmarkButtonElement();
const form = new BenchmarkForm(controls, createButton);
const importInput = new BenchmarkInputElement(
  scenario === 'empty-selection' ? '' : 'selected-local-manifest.json',
  'file',
);
const importStatus = new BenchmarkElement();
importStatus.textContent = 'Manifest loaded for review. Review fields and press Create.';
const pastedManifest = new BenchmarkTextAreaElement('{"prepared":true}');
const loadPastedManifest = new BenchmarkButtonElement();
const discardPreparedInputsButton = new BenchmarkButtonElement();
const dismissTerminalResultButton = new BenchmarkButtonElement();
const status = new BenchmarkElement();
status.textContent = 'terminal-result';
const facts = new BenchmarkElement();
facts.children = [{ node: 'dt' }, { node: 'dd' }];
facts.textContent = 'rendered-terminal-facts';
const files = new BenchmarkElement();
files.hidden = false;
const fileRows = new BenchmarkTableSectionElement();
fileRows.children = [{ node: 'tr' }];
fileRows.textContent = 'rendered-receipt-row';
const clearControl = scenario === 'missing-clear-control'
  ? null
  : scenario === 'wrong-type-clear-control'
    ? new BenchmarkElement()
    : new BenchmarkButtonElement();
const elementsBySelector = new Map([
  ['#construct-form', form],
  ['#status', status],
  ['#submission-manifest', importInput],
  ['#clear-selected-manifest', clearControl],
  ['#pasted-manifest', pastedManifest],
  ['#load-pasted-manifest', loadPastedManifest],
  ['#discard-prepared-inputs', discardPreparedInputsButton],
  ['#dismiss-terminal-result', dismissTerminalResultButton],
  ['#import-status', importStatus],
  ['#facts', facts],
  ['#files', files],
  ['#files tbody', fileRows],
]);
if (scenario === 'missing-import-input') elementsBySelector.delete('#submission-manifest');
if (scenario === 'wrong-type-import-input') {
  elementsBySelector.set('#submission-manifest', new BenchmarkElement('wrong-input'));
}
if (scenario === 'non-file-import-input') {
  elementsBySelector.set('#submission-manifest', new BenchmarkInputElement('selected-local-manifest.json', 'text'));
}
if (scenario === 'missing-import-status') elementsBySelector.delete('#import-status');
if (scenario === 'wrong-type-import-status') {
  elementsBySelector.set('#import-status', new BenchmarkNonHTMLElementElement('wrong-status'));
}
globalThis.document = { querySelector: (selector) => elementsBySelector.get(selector) ?? null };

const client = await import(pathToFileURL(clientPath).href);
const snapshot = (selector) => {
  const target = elementsBySelector.get(selector) ?? null;
  return target === null ? null : {
    value: target.value,
    type: target.type,
    textContent: target.textContent,
    hidden: target.hidden,
    children: target.children.length,
  };
};
const beforeControls = Object.fromEntries(
  [...controls.entries()].map(([field, control]) => [field, control.value]),
);
const beforePreparation = {
  importInput: snapshot('#submission-manifest'),
  importStatus: snapshot('#import-status'),
  pastedManifest: pastedManifest.value,
};
const beforeTerminal = {
  status: snapshot('#status'),
  facts: snapshot('#facts'),
  files: snapshot('#files'),
  fileRows: snapshot('#files tbody'),
};
const clearListener = clearControl?.listeners.get('click');
const listeners = {
  clear: typeof clearListener === 'function',
  import: typeof importInput.listeners.get('change') === 'function',
  pastedLoad: typeof loadPastedManifest.listeners.get('click') === 'function',
  discard: typeof discardPreparedInputsButton.listeners.get('click') === 'function',
  dismiss: typeof dismissTerminalResultButton.listeners.get('click') === 'function',
  create: typeof form.listeners.get('submit') === 'function',
};
let clearListenerInvocations = 0;
if (typeof clearListener === 'function') {
  clearListenerInvocations += 1;
  clearListener();
}
process.stdout.write(JSON.stringify({
  fields: client.MANIFEST_FIELDS,
  beforeControls,
  afterControls: Object.fromEntries(
    [...controls.entries()].map(([field, control]) => [field, control.value]),
  ),
  beforePreparation,
  afterPreparation: {
    importInput: snapshot('#submission-manifest'),
    importStatus: snapshot('#import-status'),
    pastedManifest: pastedManifest.value,
  },
  beforeTerminal,
  afterTerminal: {
    status: snapshot('#status'),
    facts: snapshot('#facts'),
    files: snapshot('#files'),
    fileRows: snapshot('#files tbody'),
  },
  listeners,
  clearListenerInvocations,
  createListenerInvocations: form.createListenerInvocations,
  requestCount,
}));
""",
        encoding="utf-8",
    )
    completed = run(
        ["node", str(runner_path), str(_STATIC_CLIENT), scenario],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return loads(completed.stdout)


def _workspace_unchanged(tmp_path: Path, *, identity: str, scenario: str) -> dict[str, object]:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity=identity)
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    result = _run_clearance_listener(tmp_path, scenario)
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before
    return result


def _assert_unrelated_state_is_unchanged(result: dict[str, object]) -> None:
    fields = result["fields"]
    assert isinstance(fields, list)
    assert len(fields) == 13
    assert set(result["beforeControls"]) == set(fields)
    assert result["afterControls"] == result["beforeControls"]
    assert result["afterPreparation"]["pastedManifest"] == result["beforePreparation"]["pastedManifest"]
    assert result["afterTerminal"] == result["beforeTerminal"]
    assert result["createListenerInvocations"] == 0
    assert result["requestCount"] == 0


def test_selected_manifest_clearance_is_explicit_non_submit_and_local() -> None:
    page = _STATIC_PAGE.read_text(encoding="utf-8")
    client = _STATIC_CLIENT.read_text(encoding="utf-8")
    routine = client[
        client.index("export function clearSelectedGovernedSubmissionManifest") : client.index(
            "export function dismissTerminalResult"
        )
    ]

    assert 'id="clear-selected-manifest" type="button"' in page
    assert "Clear selected local manifest" in page
    assert "importInput.type !== 'file'" in routine
    assert "importInput.value === ''" in routine
    assert "Selected local manifest cleared. Prepared inputs unchanged." in routine
    for forbidden in ("fetch(", "arrayBuffer", "files", "navigator.clipboard", "localStorage"):
        assert forbidden not in routine


def test_selected_manifest_is_cleared_without_changing_prepared_or_terminal_state(tmp_path: Path) -> None:
    result = _workspace_unchanged(tmp_path, identity="g2-4-29-success", scenario="selected")

    assert result["listeners"] == {
        "clear": True,
        "import": True,
        "pastedLoad": True,
        "discard": True,
        "dismiss": True,
        "create": True,
    }
    assert result["clearListenerInvocations"] == 1
    _assert_unrelated_state_is_unchanged(result)
    assert result["afterPreparation"]["importInput"]["value"] == ""
    assert result["afterPreparation"]["importStatus"]["textContent"] == (
        "Selected local manifest cleared. Prepared inputs unchanged."
    )


def test_empty_selected_manifest_is_a_strict_local_no_op(tmp_path: Path) -> None:
    result = _workspace_unchanged(tmp_path, identity="g2-4-29-empty", scenario="empty-selection")

    assert result["listeners"]["clear"] is True
    assert result["clearListenerInvocations"] == 1
    _assert_unrelated_state_is_unchanged(result)
    assert result["afterPreparation"] == result["beforePreparation"]


def test_invalid_clearance_targets_fail_closed_without_partial_mutation(tmp_path: Path) -> None:
    for scenario in (
        "missing-import-input",
        "wrong-type-import-input",
        "non-file-import-input",
        "missing-import-status",
        "wrong-type-import-status",
    ):
        result = _workspace_unchanged(tmp_path, identity=f"g2-4-29-{scenario}", scenario=scenario)

        assert result["listeners"]["clear"] is True
        assert result["clearListenerInvocations"] == 1
        _assert_unrelated_state_is_unchanged(result)
        assert result["afterPreparation"] == result["beforePreparation"]


def test_missing_or_wrong_type_clear_control_preserves_existing_bindings(tmp_path: Path) -> None:
    for scenario in ("missing-clear-control", "wrong-type-clear-control"):
        result = _workspace_unchanged(tmp_path, identity=f"g2-4-29-{scenario}", scenario=scenario)

        assert result["listeners"] == {
            "clear": False,
            "import": True,
            "pastedLoad": True,
            "discard": True,
            "dismiss": True,
            "create": True,
        }
        assert result["clearListenerInvocations"] == 0
        _assert_unrelated_state_is_unchanged(result)
        assert result["afterPreparation"] == result["beforePreparation"]
