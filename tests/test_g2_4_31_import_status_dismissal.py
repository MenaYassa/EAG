from __future__ import annotations

from json import loads
from pathlib import Path
from subprocess import run

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"
_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"


def _run_real_import_status_dismissal_listener(tmp_path: Path, scenario: str) -> dict[str, object]:
    runner_path = tmp_path / "g2_4_31_import_status_dismissal_runner.mjs"
    runner_path.write_text(
        """import { pathToFileURL } from 'node:url';

const [clientPath, scenario] = process.argv.slice(2);

class TestElement {
  constructor(value = '') {
    this.value = value;
    this.textContent = '';
    this.hidden = false;
    this.children = [];
    this.listeners = new Map();
  }
  addEventListener(type, listener) { this.listeners.set(type, listener); }
  replaceChildren(...children) { this.children = [...children]; this.textContent = ''; }
}
class TestInputElement extends TestElement { constructor(value = '', type = 'text') { super(value); this.type = type; } }
class TestTextAreaElement extends TestElement {}
class TestButtonElement extends TestElement {}
class TestTableSectionElement extends TestElement {}
class TestNonHTMLElement { constructor(value = '') { this.value = value; this.textContent = ''; this.hidden = false; this.children = []; } }
class TestFormElement extends TestElement {
  constructor(controls, createButton) {
    super(); this.controls = controls; this.createButton = createButton; this.createInvocations = 0;
    this.elements = { namedItem: (field) => this.controls.get(field) ?? null };
  }
  addEventListener(type, listener) {
    if (type === 'submit') {
      super.addEventListener(type, (...args) => { this.createInvocations += 1; return listener(...args); });
      return;
    }
    super.addEventListener(type, listener);
  }
  querySelector(selector) { return selector === 'button[type="submit"]' ? this.createButton : null; }
}

globalThis.HTMLElement = TestElement;
globalThis.HTMLInputElement = TestInputElement;
globalThis.HTMLTextAreaElement = TestTextAreaElement;
globalThis.HTMLButtonElement = TestButtonElement;
globalThis.HTMLTableSectionElement = TestTableSectionElement;
globalThis.HTMLFormElement = TestFormElement;
let requestCount = 0;
globalThis.fetch = () => { requestCount += 1; throw new Error('G2.4.31 dismissal must not request'); };

const controls = new Map([
  ['submission_id', new TestInputElement('prepared-submission_id')],
  ['profile', new TestInputElement('prepared-profile')],
  ['requested_at', new TestInputElement('prepared-requested_at')],
  ['expires_at', new TestInputElement('prepared-expires_at')],
  ['attestation_id', new TestInputElement('prepared-attestation_id')],
  ['execution_id', new TestInputElement('prepared-execution_id')],
  ['run_id', new TestInputElement('prepared-run_id')],
  ['workspace_id', new TestInputElement('prepared-workspace_id')],
  ['workspace_root', new TestInputElement('prepared-workspace_root')],
  ['source_repository_root', new TestInputElement('prepared-source_repository_root')],
  ['audit_root', new TestInputElement('prepared-audit_root')],
  ['control_root', new TestInputElement('prepared-control_root')],
  ['composition_attestation', new TestTextAreaElement('prepared-composition_attestation')],
]);
const createButton = new TestButtonElement();
const form = new TestFormElement(controls, createButton);
const importInput = new TestInputElement('selected-local-manifest.json', 'file');
const pastedManifest = new TestTextAreaElement('{"prepared":true}');
const importStatus = scenario === 'wrong-status' ? new TestNonHTMLElement() : new TestElement();
importStatus.textContent = scenario === 'empty-status' ? '' : 'opaque existing local status';
const clearSelectedButton = new TestButtonElement();
const clearPastedButton = new TestButtonElement();
const loadButton = new TestButtonElement();
const discardButton = new TestButtonElement();
const dismissResultButton = new TestButtonElement();
const dismissImportButton = scenario === 'missing-control' ? null : scenario === 'wrong-control' ? new TestElement() : new TestButtonElement();
const status = new TestElement(); status.textContent = 'terminal-result';
const facts = new TestElement(); facts.children = [{ node: 'dt' }];
const files = new TestElement(); files.hidden = false;
const fileRows = new TestTableSectionElement(); fileRows.children = [{ node: 'tr' }];
const elements = new Map([
  ['#construct-form', form], ['#status', status], ['#submission-manifest', importInput],
  ['#clear-selected-manifest', clearSelectedButton], ['#pasted-manifest', pastedManifest],
  ['#clear-pasted-manifest', clearPastedButton], ['#load-pasted-manifest', loadButton],
  ['#discard-prepared-inputs', discardButton], ['#dismiss-terminal-result', dismissResultButton],
  ['#dismiss-import-status', dismissImportButton], ['#import-status', importStatus],
  ['#facts', facts], ['#files', files], ['#files tbody', fileRows],
]);
if (scenario === 'missing-status') elements.delete('#import-status');
globalThis.document = { querySelector: (selector) => elements.get(selector) ?? null };

const client = await import(pathToFileURL(clientPath).href);
const snapshot = (target) => target === null ? null : {
  value: target.value, textContent: target.textContent, hidden: target.hidden, children: target.children.length,
};
const statusTarget = elements.get('#import-status') ?? null;
const before = {
  controls: Object.fromEntries([...controls.entries()].map(([field, control]) => [field, control.value])),
  importInput: snapshot(importInput), pastedManifest: snapshot(pastedManifest), importStatus: snapshot(statusTarget),
  terminal: { status: snapshot(status), facts: snapshot(facts), files: snapshot(files), fileRows: snapshot(fileRows) },
};
const dismissListener = dismissImportButton?.listeners.get('click');
let dismissInvocations = 0;
if (typeof dismissListener === 'function') { dismissInvocations += 1; dismissListener(); }
process.stdout.write(JSON.stringify({
  fields: client.MANIFEST_FIELDS,
  before,
  after: {
    controls: Object.fromEntries([...controls.entries()].map(([field, control]) => [field, control.value])),
    importInput: snapshot(importInput), pastedManifest: snapshot(pastedManifest), importStatus: snapshot(statusTarget),
    terminal: { status: snapshot(status), facts: snapshot(facts), files: snapshot(files), fileRows: snapshot(fileRows) },
  },
  listeners: {
    dismissImport: typeof dismissListener === 'function', selectedClear: typeof clearSelectedButton.listeners.get('click') === 'function',
    pastedClear: typeof clearPastedButton.listeners.get('click') === 'function', import: typeof importInput.listeners.get('change') === 'function',
    pastedLoad: typeof loadButton.listeners.get('click') === 'function', discard: typeof discardButton.listeners.get('click') === 'function',
    dismissResult: typeof dismissResultButton.listeners.get('click') === 'function', create: typeof form.listeners.get('submit') === 'function',
  },
  dismissInvocations, createInvocations: form.createInvocations, requestCount,
}));
""",
        encoding="utf-8",
    )
    completed = run(["node", str(runner_path), str(_STATIC_CLIENT), scenario], check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    return loads(completed.stdout)


def _run_with_unchanged_workspace(tmp_path: Path, *, identity: str, scenario: str) -> dict[str, object]:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity=identity)
    before = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    result = _run_real_import_status_dismissal_listener(tmp_path, scenario)
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before
    return result


def _assert_unrelated_state_is_unchanged(result: dict[str, object]) -> None:
    assert isinstance(result["fields"], list)
    assert len(result["fields"]) == 13
    assert result["after"]["controls"] == result["before"]["controls"]
    assert result["after"]["importInput"] == result["before"]["importInput"]
    assert result["after"]["pastedManifest"] == result["before"]["pastedManifest"]
    assert result["after"]["terminal"] == result["before"]["terminal"]
    assert result["createInvocations"] == 0
    assert result["requestCount"] == 0


def test_import_status_dismissal_is_explicit_non_submit_and_local() -> None:
    page = _STATIC_PAGE.read_text(encoding="utf-8")
    client = _STATIC_CLIENT.read_text(encoding="utf-8")
    routine = client[client.index("export function dismissImportStatus") : client.index("export function dismissTerminalResult")]

    assert 'id="dismiss-import-status" type="button"' in page
    assert "importStatus instanceof HTMLElement" in routine
    assert "importStatus.textContent === ''" in routine
    assert "importStatus.textContent = '';" in routine
    for forbidden in ("fetch(", "TextEncoder", "TextDecoder", "arrayBuffer", ".files", "navigator.clipboard", "localStorage"):
        assert forbidden not in routine


def test_nonempty_import_status_is_cleared_by_the_real_bound_listener(tmp_path: Path) -> None:
    result = _run_with_unchanged_workspace(tmp_path, identity="g2-4-31-nonempty", scenario="nonempty-status")

    assert result["listeners"] == {
        "dismissImport": True, "selectedClear": True, "pastedClear": True, "import": True, "pastedLoad": True,
        "discard": True, "dismissResult": True, "create": True,
    }
    assert result["dismissInvocations"] == 1
    _assert_unrelated_state_is_unchanged(result)
    assert result["before"]["importStatus"]["textContent"] != ""
    assert result["after"]["importStatus"]["textContent"] == ""


def test_empty_missing_or_wrong_type_import_status_fails_closed_without_partial_mutation(tmp_path: Path) -> None:
    for scenario in ("empty-status", "missing-status", "wrong-status"):
        result = _run_with_unchanged_workspace(tmp_path, identity=f"g2-4-31-{scenario}", scenario=scenario)

        assert result["listeners"]["dismissImport"] is True
        assert result["dismissInvocations"] == 1
        _assert_unrelated_state_is_unchanged(result)
        assert result["after"] == result["before"]


def test_missing_or_wrong_type_dismiss_control_preserves_existing_bindings(tmp_path: Path) -> None:
    for scenario in ("missing-control", "wrong-control"):
        result = _run_with_unchanged_workspace(tmp_path, identity=f"g2-4-31-{scenario}", scenario=scenario)

        assert result["listeners"] == {
            "dismissImport": False, "selectedClear": True, "pastedClear": True, "import": True, "pastedLoad": True,
            "discard": True, "dismissResult": True, "create": True,
        }
        assert result["dismissInvocations"] == 0
        _assert_unrelated_state_is_unchanged(result)
        assert result["after"] == result["before"]
