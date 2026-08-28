from __future__ import annotations

from json import loads
from pathlib import Path
from subprocess import run

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"
_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"


def _run_real_import_status_dismissal_listener(tmp_path: Path, scenario: str) -> dict[str, object]:
    runner_path = tmp_path / "ebs_047_import_status_dismissal_runner.mjs"
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
  addEventListener(type, listener) { this.listeners.set(type, listener); }
  replaceChildren(...children) { this.children = [...children]; this.textContent = ''; }
}
class BenchmarkInputElement extends BenchmarkElement { constructor(value = '', type = 'text') { super(value); this.type = type; } }
class BenchmarkTextAreaElement extends BenchmarkElement {}
class BenchmarkButtonElement extends BenchmarkElement {}
class BenchmarkTableSectionElement extends BenchmarkElement {}
class BenchmarkNonHTMLElementElement {
  constructor(value = '') { this.value = value; this.textContent = ''; this.hidden = false; this.children = []; }
  replaceChildren(...children) { this.children = [...children]; this.textContent = ''; }
}
class BenchmarkForm extends BenchmarkElement {
  constructor(controls, createButton) {
    super(); this.controls = controls; this.createButton = createButton; this.createListenerInvocations = 0;
    this.elements = { namedItem: (field) => this.controls.get(field) ?? null };
  }
  addEventListener(type, listener) {
    if (type === 'submit') {
      super.addEventListener(type, (...args) => { this.createListenerInvocations += 1; return listener(...args); });
      return;
    }
    super.addEventListener(type, listener);
  }
  querySelector(selector) { return selector === 'button[type="submit"]' ? this.createButton : null; }
}

globalThis.HTMLElement = BenchmarkElement;
globalThis.HTMLInputElement = BenchmarkInputElement;
globalThis.HTMLTextAreaElement = BenchmarkTextAreaElement;
globalThis.HTMLButtonElement = BenchmarkButtonElement;
globalThis.HTMLTableSectionElement = BenchmarkTableSectionElement;
globalThis.HTMLFormElement = BenchmarkForm;
let requestCount = 0;
globalThis.fetch = () => { requestCount += 1; throw new Error('EBS-047 dismissal must not issue a request'); };

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
const importInput = new BenchmarkInputElement('selected-local-manifest.json', 'file');
const validManifest = JSON.stringify({
  submission_id: 'loaded-submission', profile: 'modern_todo_static_v1', requested_at: '2026-01-01T00:00:00Z',
  expires_at: '2026-01-01T01:00:00Z', attestation_id: 'loaded-attestation', execution_id: 'loaded-execution',
  run_id: 'loaded-run', workspace_id: 'loaded-workspace', workspace_root: '/tmp/loaded-workspace',
  source_repository_root: '/tmp/loaded-source', audit_root: '/tmp/loaded-audit', control_root: '/tmp/loaded-control',
  composition_attestation: { runtime: 'browser-local' },
});
const pastedManifest = new BenchmarkTextAreaElement(
  scenario === 'loaded' ? validManifest : scenario === 'refused' ? '{' : '{"local":true}',
);
const importStatus = scenario === 'wrong-status' ? new BenchmarkNonHTMLElementElement() : new BenchmarkElement();
importStatus.textContent = scenario === 'empty-status' ? '' : scenario === 'loaded' || scenario === 'refused' || scenario === 'local-clearance' ? '' : 'opaque initial status';
const clearSelectedButton = new BenchmarkButtonElement();
const clearPastedButton = new BenchmarkButtonElement();
const loadButton = new BenchmarkButtonElement();
const discardButton = new BenchmarkButtonElement();
const dismissResultButton = new BenchmarkButtonElement();
const dismissImportButton = scenario === 'missing-control' ? null : scenario === 'wrong-control' ? new BenchmarkElement() : new BenchmarkButtonElement();
const status = new BenchmarkElement(); status.textContent = 'terminal-result';
const facts = new BenchmarkElement(); facts.children = [{ node: 'dt' }, { node: 'dd' }]; facts.textContent = 'rendered-terminal-facts';
const files = new BenchmarkElement(); files.hidden = false;
const fileRows = new BenchmarkTableSectionElement(); fileRows.children = [{ node: 'tr' }]; fileRows.textContent = 'rendered-receipt-row';
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
const importStatusTarget = elements.get('#import-status') ?? null;
const producer = scenario === 'loaded' || scenario === 'refused' ? loadButton.listeners.get('click')
  : scenario === 'local-clearance' ? clearPastedButton.listeners.get('click') : null;
let producerInvocations = 0;
if (typeof producer === 'function') { producerInvocations += 1; producer(); }
const beforeDismissal = {
  controls: Object.fromEntries([...controls.entries()].map(([field, control]) => [field, control.value])),
  importInput: snapshot(importInput), pastedManifest: snapshot(pastedManifest), importStatus: snapshot(importStatusTarget),
  terminal: { status: snapshot(status), facts: snapshot(facts), files: snapshot(files), fileRows: snapshot(fileRows) },
};
const dismissListener = dismissImportButton?.listeners.get('click');
const listeners = {
  dismissImport: typeof dismissListener === 'function', selectedClear: typeof clearSelectedButton.listeners.get('click') === 'function',
  pastedClear: typeof clearPastedButton.listeners.get('click') === 'function', import: typeof importInput.listeners.get('change') === 'function',
  pastedLoad: typeof loadButton.listeners.get('click') === 'function', discard: typeof discardButton.listeners.get('click') === 'function',
  dismissResult: typeof dismissResultButton.listeners.get('click') === 'function', create: typeof form.listeners.get('submit') === 'function',
};
let dismissInvocations = 0;
if (typeof dismissListener === 'function') { dismissInvocations += 1; dismissListener(); }
process.stdout.write(JSON.stringify({
  fields: client.MANIFEST_FIELDS, scenario, beforeDismissal,
  afterDismissal: {
    controls: Object.fromEntries([...controls.entries()].map(([field, control]) => [field, control.value])),
    importInput: snapshot(importInput), pastedManifest: snapshot(pastedManifest), importStatus: snapshot(importStatusTarget),
    terminal: { status: snapshot(status), facts: snapshot(facts), files: snapshot(files), fileRows: snapshot(fileRows) },
  },
  listeners, producerInvocations, dismissInvocations, createListenerInvocations: form.createListenerInvocations, requestCount,
}));
""",
        encoding="utf-8",
    )
    completed = run(["node", str(runner_path), str(_STATIC_CLIENT), scenario], check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    return loads(completed.stdout)


def _run_with_unchanged_workspace(tmp_path: Path, *, identity: str, scenario: str) -> dict[str, object]:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity=identity)
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    result = _run_real_import_status_dismissal_listener(tmp_path, scenario)
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace
    return result


def _assert_unrelated_state_is_unchanged(result: dict[str, object]) -> None:
    fields = result["fields"]
    assert isinstance(fields, list)
    assert len(fields) == 13
    assert result["afterDismissal"]["controls"] == result["beforeDismissal"]["controls"]
    assert result["afterDismissal"]["importInput"] == result["beforeDismissal"]["importInput"]
    assert result["afterDismissal"]["pastedManifest"] == result["beforeDismissal"]["pastedManifest"]
    assert result["afterDismissal"]["terminal"] == result["beforeDismissal"]["terminal"]
    assert result["createListenerInvocations"] == 0
    assert result["requestCount"] == 0


def test_ebs_047_dismisses_each_real_opaque_nonempty_import_status_form_locally(tmp_path: Path) -> None:
    for scenario in ("loaded", "refused", "local-clearance"):
        result = _run_with_unchanged_workspace(tmp_path, identity=f"ebs-047-{scenario}", scenario=scenario)

        assert result["listeners"] == {
            "dismissImport": True, "selectedClear": True, "pastedClear": True, "import": True, "pastedLoad": True,
            "discard": True, "dismissResult": True, "create": True,
        }
        assert result["producerInvocations"] == 1
        assert result["dismissInvocations"] == 1
        _assert_unrelated_state_is_unchanged(result)
        assert result["beforeDismissal"]["importStatus"]["textContent"] != ""
        assert result["afterDismissal"]["importStatus"]["textContent"] == ""


def test_ebs_047_empty_import_status_is_a_real_listener_strict_local_no_op(tmp_path: Path) -> None:
    result = _run_with_unchanged_workspace(tmp_path, identity="ebs-047-empty", scenario="empty-status")

    assert result["listeners"]["dismissImport"] is True
    assert result["producerInvocations"] == 0
    assert result["dismissInvocations"] == 1
    _assert_unrelated_state_is_unchanged(result)
    assert result["afterDismissal"] == result["beforeDismissal"]


def test_ebs_047_missing_or_wrong_type_import_status_fails_closed_before_mutation(tmp_path: Path) -> None:
    for scenario in ("missing-status", "wrong-status"):
        result = _run_with_unchanged_workspace(tmp_path, identity=f"ebs-047-{scenario}", scenario=scenario)

        assert result["listeners"]["dismissImport"] is True
        assert result["producerInvocations"] == 0
        assert result["dismissInvocations"] == 1
        _assert_unrelated_state_is_unchanged(result)
        assert result["afterDismissal"] == result["beforeDismissal"]


def test_ebs_047_missing_or_wrong_type_dismiss_control_preserves_all_existing_bindings(tmp_path: Path) -> None:
    for scenario in ("missing-control", "wrong-control"):
        result = _run_with_unchanged_workspace(tmp_path, identity=f"ebs-047-{scenario}", scenario=scenario)

        assert result["listeners"] == {
            "dismissImport": False, "selectedClear": True, "pastedClear": True, "import": True, "pastedLoad": True,
            "discard": True, "dismissResult": True, "create": True,
        }
        assert result["producerInvocations"] == 0
        assert result["dismissInvocations"] == 0
        _assert_unrelated_state_is_unchanged(result)
        assert result["afterDismissal"] == result["beforeDismissal"]


def test_ebs_047_import_status_dismissal_delta_has_no_prohibited_browser_or_submission_capability() -> None:
    client = _STATIC_CLIENT.read_text(encoding="utf-8")
    routine = client[client.index("export function dismissImportStatus") : client.index("export function dismissTerminalResult")]
    binding = client[
        client.index("if (dismissImportStatusButton instanceof HTMLButtonElement)") : client.index(
            "if (!(form instanceof HTMLFormElement)"
        )
    ]

    for forbidden in (
        "fetch(", "TextEncoder", "TextDecoder", "arrayBuffer", ".files", "navigator.clipboard", "localStorage",
        "sessionStorage", "indexedDB", "http://", "https://", "/api/construct",
    ):
        assert forbidden not in routine
        assert forbidden not in binding
