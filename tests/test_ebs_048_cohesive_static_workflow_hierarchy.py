from __future__ import annotations

from json import loads
from pathlib import Path
from subprocess import run

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"


def _run_grouped_workflow(tmp_path: Path) -> dict[str, object]:
    runner_path = tmp_path / "ebs_048_grouped_workflow_runner.mjs"
    runner_path.write_text(
        """import { pathToFileURL } from 'node:url';

const [clientPath] = process.argv.slice(2);

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
  append(...children) { this.children.push(...children); }
}
class BenchmarkInputElement extends BenchmarkElement { constructor(value = '', type = 'text') { super(value); this.type = type; this.files = null; } }
class BenchmarkTextAreaElement extends BenchmarkElement {}
class BenchmarkButtonElement extends BenchmarkElement { constructor() { super(); this.disabled = false; } }
class BenchmarkTableSectionElement extends BenchmarkElement {}
class BenchmarkFormElement extends BenchmarkElement {
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
class BenchmarkFormData {
  constructor(form) { this.form = form; }
  get(field) { return this.form.controls.get(field)?.value ?? null; }
  *entries() { for (const [field, control] of this.form.controls.entries()) yield [field, control.value]; }
}
class WorkflowGroup extends BenchmarkElement { constructor(label) { super(); this.label = label; } }

globalThis.HTMLElement = BenchmarkElement;
globalThis.HTMLInputElement = BenchmarkInputElement;
globalThis.HTMLTextAreaElement = BenchmarkTextAreaElement;
globalThis.HTMLButtonElement = BenchmarkButtonElement;
globalThis.HTMLTableSectionElement = BenchmarkTableSectionElement;
globalThis.HTMLFormElement = BenchmarkFormElement;
globalThis.FormData = BenchmarkFormData;

const validManifest = JSON.stringify({
  submission_id: 'grouped-submission', profile: 'modern_todo_static_v1', requested_at: '2026-01-01T00:00:00Z',
  expires_at: '2026-01-01T01:00:00Z', attestation_id: 'grouped-attestation', execution_id: 'grouped-execution',
  run_id: 'grouped-run', workspace_id: 'grouped-workspace', workspace_root: '/tmp/grouped-workspace',
  source_repository_root: '/tmp/grouped-source', audit_root: '/tmp/grouped-audit', control_root: '/tmp/grouped-control',
  composition_attestation: { runtime: 'browser-local' },
});
const validBytes = new TextEncoder().encode(validManifest);
const localFile = { size: validBytes.byteLength, arrayBuffer: async () => validBytes.buffer };
const controls = new Map([
  ['submission_id', new BenchmarkInputElement('seed-submission')],
  ['profile', new BenchmarkInputElement('modern_todo_static_v1')],
  ['requested_at', new BenchmarkInputElement('seed-requested-at')],
  ['expires_at', new BenchmarkInputElement('seed-expires-at')],
  ['attestation_id', new BenchmarkInputElement('seed-attestation')],
  ['execution_id', new BenchmarkInputElement('seed-execution')],
  ['run_id', new BenchmarkInputElement('seed-run')],
  ['workspace_id', new BenchmarkInputElement('seed-workspace')],
  ['workspace_root', new BenchmarkInputElement('seed-workspace-root')],
  ['source_repository_root', new BenchmarkInputElement('seed-source-root')],
  ['audit_root', new BenchmarkInputElement('seed-audit-root')],
  ['control_root', new BenchmarkInputElement('seed-control-root')],
  ['composition_attestation', new BenchmarkTextAreaElement('seed-composition')],
]);
const createButton = new BenchmarkButtonElement();
const form = new BenchmarkFormElement(controls, createButton);
const importInput = new BenchmarkInputElement('grouped-manifest.json', 'file');
importInput.files = { item: (index) => index === 0 ? localFile : null };
const pastedManifest = new BenchmarkTextAreaElement(validManifest);
const importStatus = new BenchmarkElement(); importStatus.textContent = 'No manifest imported.';
const status = new BenchmarkElement(); status.textContent = 'No construction submitted.';
const facts = new BenchmarkElement();
const files = new BenchmarkElement(); files.hidden = true;
const fileRows = new BenchmarkTableSectionElement();
const clearSelectedButton = new BenchmarkButtonElement();
const clearPastedButton = new BenchmarkButtonElement();
const loadButton = new BenchmarkButtonElement();
const discardButton = new BenchmarkButtonElement();
const dismissResultButton = new BenchmarkButtonElement();
const dismissImportButton = new BenchmarkButtonElement();

const groups = {
  local: new WorkflowGroup('Prepare locally'), review: new WorkflowGroup('Review prepared inputs'),
  submit: new WorkflowGroup('Explicitly submit governed construction'), result: new WorkflowGroup('Review terminal result'),
};
groups.local.append(importInput, clearSelectedButton, pastedManifest, clearPastedButton, loadButton, importStatus, dismissImportButton, discardButton);
groups.review.append(...controls.values());
groups.submit.append(createButton);
groups.result.append(status, dismissResultButton, facts, files, fileRows);

const elements = new Map([
  ['#construct-form', form], ['#status', status], ['#submission-manifest', importInput],
  ['#clear-selected-manifest', clearSelectedButton], ['#pasted-manifest', pastedManifest],
  ['#clear-pasted-manifest', clearPastedButton], ['#load-pasted-manifest', loadButton],
  ['#discard-prepared-inputs', discardButton], ['#dismiss-terminal-result', dismissResultButton],
  ['#dismiss-import-status', dismissImportButton], ['#import-status', importStatus],
  ['#facts', facts], ['#files', files], ['#files tbody', fileRows],
]);
globalThis.document = {
  querySelector: (selector) => elements.get(selector) ?? null,
  createElement: () => new BenchmarkElement(),
};
let requestCount = 0;
let request = null;
let responseMode = 'success';
globalThis.fetch = async (url, init) => {
  requestCount += 1;
  request = { url, method: init.method, contentType: init.headers['Content-Type'], payload: JSON.parse(init.body) };
  const response = responseMode === 'refusal'
    ? {
        presentation_disposition: 'UPSTREAM_REFUSED', selected_profile: 'not_a_fixed_profile',
        failure_stage: 'g2_4_21_profile_issuance', failure_code: 'unsupported profile', receipt_files: [],
      }
    : {
        presentation_disposition: 'CONSTRUCTION_COMPLETED', selected_profile: 'modern_todo_static_v1', profile_version: 'v1',
        receipt_files: [{ relative_path: 'index.html', byte_count: 11, content_digest: 'a'.repeat(64) }],
      };
  return { ok: true, json: async () => response };
};

const client = await import(pathToFileURL(clientPath).href);
const listener = (button) => button.listeners.get('click');
const importListener = importInput.listeners.get('change');
const pastedLoadListener = listener(loadButton);
const clearSelectedListener = listener(clearSelectedButton);
const clearPastedListener = listener(clearPastedButton);
const discardListener = listener(discardButton);
const dismissImportListener = listener(dismissImportButton);
const submitListener = form.listeners.get('submit');
const dismissResultListener = listener(dismissResultButton);
const listeners = {
  import: typeof importListener === 'function', pastedLoad: typeof pastedLoadListener === 'function',
  selectedClear: typeof clearSelectedListener === 'function', pastedClear: typeof clearPastedListener === 'function',
  discard: typeof discardListener === 'function', dismissImport: typeof dismissImportListener === 'function',
  create: typeof submitListener === 'function', dismissResult: typeof dismissResultListener === 'function',
};
const initialTerminal = { status: status.textContent, facts: facts.children.length, filesHidden: files.hidden, rows: fileRows.children.length };
await importListener();
const afterFileLoad = { importStatus: importStatus.textContent, profile: controls.get('profile').value };
discardListener();
const afterDiscard = { clearedFieldCount: [...controls.values()].filter((control) => control.value === '').length, requestCount, createInvocations: form.createInvocations };
pastedManifest.value = validManifest;
pastedLoadListener();
const afterPastedLoad = { importStatus: importStatus.textContent, profile: controls.get('profile').value, submissionId: controls.get('submission_id').value };
importInput.value = 'clear-after-load.json';
clearSelectedListener();
const afterSelectedClear = { importInput: importInput.value, importStatus: importStatus.textContent, requestCount, createInvocations: form.createInvocations };
clearPastedListener();
const afterPastedClear = { pastedManifest: pastedManifest.value, importStatus: importStatus.textContent, requestCount, createInvocations: form.createInvocations };
pastedManifest.value = validManifest;
pastedLoadListener();
dismissImportListener();
const beforeSubmit = {
  importStatus: importStatus.textContent, terminal: { status: status.textContent, facts: facts.children.length, filesHidden: files.hidden, rows: fileRows.children.length },
  requestCount, createInvocations: form.createInvocations,
};
let preventDefaultCount = 0;
await submitListener({ preventDefault: () => { preventDefaultCount += 1; } });
const afterSubmit = {
  requestCount, createInvocations: form.createInvocations, preventDefaultCount, request,
  terminal: { status: status.textContent, facts: facts.children.length, filesHidden: files.hidden, rows: fileRows.children.length },
};
dismissResultListener();
const afterTerminalDismissal = { status: status.textContent, facts: facts.children.length, filesHidden: files.hidden, rows: fileRows.children.length, requestCount, createInvocations: form.createInvocations };
controls.get('profile').value = 'not_a_fixed_profile';
responseMode = 'refusal';
const refusalPreparedBefore = [...controls.entries()].map(([field, control]) => [field, control.value]);
const refusalBeforeSubmit = { importStatus: importStatus.textContent, prepared: refusalPreparedBefore, requestCount, createInvocations: form.createInvocations };
await submitListener({ preventDefault: () => { preventDefaultCount += 1; } });
const refusalAfterSubmit = {
  requestCount, createInvocations: form.createInvocations, request,
  terminal: { status: status.textContent, facts: facts.children.length, filesHidden: files.hidden, rows: fileRows.children.length },
};
const refusalBeforeDismissal = {
  status: status.textContent, facts: facts.children.length, filesHidden: files.hidden, rows: fileRows.children.length,
  prepared: [...controls.entries()].map(([field, control]) => [field, control.value]), importStatus: importStatus.textContent,
  requestCount, createInvocations: form.createInvocations,
};
dismissResultListener();
const afterRefusalDismissal = {
  status: status.textContent, facts: facts.children.length, filesHidden: files.hidden, rows: fileRows.children.length,
  prepared: [...controls.entries()].map(([field, control]) => [field, control.value]), importStatus: importStatus.textContent,
  requestCount, createInvocations: form.createInvocations,
};
process.stdout.write(JSON.stringify({
  fields: client.MANIFEST_FIELDS, groups: Object.fromEntries(Object.entries(groups).map(([name, group]) => [name, group.children.length])),
  listeners, initialTerminal, afterFileLoad, afterDiscard, afterPastedLoad, afterSelectedClear, afterPastedClear,
  beforeSubmit, afterSubmit, afterTerminalDismissal, refusalPreparedBefore, refusalBeforeSubmit, refusalAfterSubmit,
  refusalBeforeDismissal, afterRefusalDismissal,
}));
""",
        encoding="utf-8",
    )
    completed = run(["node", str(runner_path), str(_STATIC_CLIENT)], check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    return loads(completed.stdout)


def test_ebs_048_grouped_page_preserves_real_local_submit_and_terminal_workflow(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="ebs-048-workflow")
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    result = _run_grouped_workflow(tmp_path)
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace

    assert result["fields"] == [
        "submission_id", "profile", "requested_at", "expires_at", "attestation_id", "execution_id", "run_id",
        "workspace_id", "workspace_root", "source_repository_root", "audit_root", "control_root", "composition_attestation",
    ]
    assert result["groups"] == {"local": 8, "review": 13, "submit": 1, "result": 5}
    assert result["listeners"] == {
        "import": True, "pastedLoad": True, "selectedClear": True, "pastedClear": True,
        "discard": True, "dismissImport": True, "create": True, "dismissResult": True,
    }
    assert result["initialTerminal"] == {"status": "No construction submitted.", "facts": 0, "filesHidden": True, "rows": 0}
    assert result["afterFileLoad"] == {
        "importStatus": "Manifest loaded for review. Review fields and press Create.", "profile": "modern_todo_static_v1",
    }
    assert result["afterDiscard"] == {"clearedFieldCount": 13, "requestCount": 0, "createInvocations": 0}
    assert result["afterPastedLoad"] == {
        "importStatus": "Manifest loaded for review. Review fields and press Create.",
        "profile": "modern_todo_static_v1", "submissionId": "grouped-submission",
    }
    assert result["afterSelectedClear"] == {
        "importInput": "", "importStatus": "Selected local manifest cleared. Prepared inputs unchanged.",
        "requestCount": 0, "createInvocations": 0,
    }
    assert result["afterPastedClear"] == {
        "pastedManifest": "", "importStatus": "Pasted manifest cleared locally. Prepared inputs unchanged.",
        "requestCount": 0, "createInvocations": 0,
    }
    assert result["beforeSubmit"] == {
        "importStatus": "", "terminal": {"status": "No construction submitted.", "facts": 0, "filesHidden": True, "rows": 0},
        "requestCount": 0, "createInvocations": 0,
    }
    assert result["afterSubmit"]["requestCount"] == 1
    assert result["afterSubmit"]["createInvocations"] == 1
    assert result["afterSubmit"]["preventDefaultCount"] == 1
    assert result["afterSubmit"]["request"] == {
        "url": "/api/construct", "method": "POST", "contentType": "application/json",
        "payload": {
            "submission_id": "grouped-submission", "profile": "modern_todo_static_v1", "requested_at": "2026-01-01T00:00:00Z",
            "expires_at": "2026-01-01T01:00:00Z", "attestation_id": "grouped-attestation", "execution_id": "grouped-execution",
            "run_id": "grouped-run", "workspace_id": "grouped-workspace", "workspace_root": "/tmp/grouped-workspace",
            "source_repository_root": "/tmp/grouped-source", "audit_root": "/tmp/grouped-audit", "control_root": "/tmp/grouped-control",
            "composition_attestation": {"runtime": "browser-local"},
        },
    }
    assert result["afterSubmit"]["terminal"] == {
        "status": "CONSTRUCTION_COMPLETED", "facts": 4, "filesHidden": False, "rows": 1,
    }
    assert result["afterTerminalDismissal"] == {
        "status": "Terminal result dismissed locally. No upstream state changed.", "facts": 0, "filesHidden": True, "rows": 0,
        "requestCount": 1, "createInvocations": 1,
    }

    assert result["refusalPreparedBefore"] == result["refusalBeforeSubmit"]["prepared"]
    assert result["refusalBeforeSubmit"]["requestCount"] == 1
    assert result["refusalBeforeSubmit"]["createInvocations"] == 1
    assert result["refusalAfterSubmit"]["requestCount"] == 2
    assert result["refusalAfterSubmit"]["createInvocations"] == 2
    assert result["refusalAfterSubmit"]["request"] == {
        "url": "/api/construct", "method": "POST", "contentType": "application/json",
        "payload": {
            "submission_id": "grouped-submission", "profile": "not_a_fixed_profile", "requested_at": "2026-01-01T00:00:00Z",
            "expires_at": "2026-01-01T01:00:00Z", "attestation_id": "grouped-attestation", "execution_id": "grouped-execution",
            "run_id": "grouped-run", "workspace_id": "grouped-workspace", "workspace_root": "/tmp/grouped-workspace",
            "source_repository_root": "/tmp/grouped-source", "audit_root": "/tmp/grouped-audit", "control_root": "/tmp/grouped-control",
            "composition_attestation": {"runtime": "browser-local"},
        },
    }
    assert result["refusalAfterSubmit"]["terminal"]["status"].startswith("UPSTREAM_REFUSED")
    assert result["refusalAfterSubmit"]["terminal"]["facts"] > 0
    assert result["refusalAfterSubmit"]["terminal"]["filesHidden"] is True
    assert result["refusalAfterSubmit"]["terminal"]["rows"] == 0
    assert result["refusalBeforeDismissal"]["prepared"] == result["afterRefusalDismissal"]["prepared"]
    assert result["refusalBeforeDismissal"]["importStatus"] == result["afterRefusalDismissal"]["importStatus"]
    assert result["afterRefusalDismissal"] == {
        "status": "Terminal result dismissed locally. No upstream state changed.", "facts": 0, "filesHidden": True, "rows": 0,
        "prepared": result["refusalBeforeDismissal"]["prepared"], "importStatus": "", "requestCount": 2, "createInvocations": 2,
    }


def test_ebs_048_hierarchy_delta_does_not_add_client_behavior_or_test_seams() -> None:
    client = _STATIC_CLIENT.read_text(encoding="utf-8")
    benchmark = Path(__file__).read_text(encoding="utf-8")

    assert "workflow-stage" not in client
    assert "primary-submit-area" not in client
    assert "source-grid" not in client
    for forbidden in (
        "monkey" + "patch",
        "unittest" + ".mock",
        "Magic" + "Mock",
        "Mock" + "(",
        "ob" + "server",
        "ho" + "ok",
        "call" + "back",
    ):
        assert forbidden not in benchmark
