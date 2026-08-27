"""Focused direct proofs for G2.4.28 browser-local terminal-result dismissal."""

from __future__ import annotations

from json import loads
from pathlib import Path
from subprocess import run

from test_support.g2_4_23_presentation_fixture import fixed_profile_presentation_fixture

_STATIC_CLIENT = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/app.js"
_STATIC_PAGE = Path(__file__).parents[1] / "src/eag/governed_visual_presentation/static/index.html"


def _run_dismissal_listener(tmp_path: Path, scenario: str) -> dict[str, object]:
    runner_path = tmp_path / "g2_4_28_dismissal_runner.mjs"
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
const createButton = new BenchmarkButtonElement();
const form = new BenchmarkForm(controls, createButton);
const importInput = new BenchmarkInputElement('prepared-manifest.json');
const pastedManifest = new BenchmarkTextAreaElement('{"prepared":true}');
const loadPastedManifest = new BenchmarkButtonElement();
const discardPreparedInputsButton = new BenchmarkButtonElement();
const importStatus = new BenchmarkElement();
importStatus.textContent = 'Manifest loaded for review. Review fields and press Create.';
const status = new BenchmarkElement();
status.textContent = scenario === 'no-rendered-result' ? 'No construction submitted.' : 'terminal-result';
const facts = new BenchmarkElement();
const files = new BenchmarkElement();
const fileRows = new BenchmarkTableSectionElement();

if (scenario === 'no-rendered-result') {
  facts.textContent = 'preserved-no-rendered-facts-text';
  fileRows.textContent = 'preserved-no-rendered-row-text';
  files.hidden = true;
} else {
  facts.children = [{ node: 'dt' }, { node: 'dd' }];
  facts.textContent = 'rendered-terminal-facts';
  if (scenario === 'refusal-like') {
    files.hidden = true;
  } else {
    files.hidden = false;
    fileRows.children = [{ node: 'tr' }];
    fileRows.textContent = 'rendered-receipt-row';
  }
}

const dismissalControl = scenario === 'missing-dismissal-control'
  ? null
  : scenario === 'wrong-type-dismissal-control'
    ? new BenchmarkElement()
    : new BenchmarkButtonElement();
const elementsBySelector = new Map([
  ['#construct-form', form],
  ['#status', status],
  ['#submission-manifest', importInput],
  ['#pasted-manifest', pastedManifest],
  ['#load-pasted-manifest', loadPastedManifest],
  ['#discard-prepared-inputs', discardPreparedInputsButton],
  ['#dismiss-terminal-result', dismissalControl],
  ['#import-status', importStatus],
  ['#facts', facts],
  ['#files', files],
  ['#files tbody', fileRows],
]);
if (scenario === 'missing-file-rows') elementsBySelector.delete('#files tbody');
if (scenario === 'wrong-type-file-rows') elementsBySelector.set('#files tbody', new BenchmarkElement());
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
  factsText: facts.textContent,
  factsChildren: facts.children.length,
  filesHidden: files.hidden,
  fileRowsText: fileRows.textContent,
  fileRowsChildren: fileRows.children.length,
};
const dismissalListener = dismissalControl?.listeners.get('click');
const fileImportListener = importInput.listeners.get('change');
const pastedLoadListener = loadPastedManifest.listeners.get('click');
const discardListener = discardPreparedInputsButton.listeners.get('click');
const createListener = form.listeners.get('submit');
let dismissalListenerInvocations = 0;
if (typeof dismissalListener === 'function') {
  dismissalListenerInvocations += 1;
  dismissalListener();
}
process.stdout.write(JSON.stringify({
  fields: client.MANIFEST_FIELDS,
  beforeControls,
  afterControls: Object.fromEntries(
    [...controls.entries()].map(([field, control]) => [field, control.value]),
  ),
  beforeLocalInputs,
  afterLocalInputs: {
    importInput: importInput.value,
    pastedManifest: pastedManifest.value,
    importStatus: importStatus.textContent,
  },
  beforeTerminal,
  afterTerminal: {
    status: status.textContent,
    factsText: facts.textContent,
    factsChildren: facts.children.length,
    filesHidden: files.hidden,
    fileRowsText: fileRows.textContent,
    fileRowsChildren: fileRows.children.length,
  },
  interaction: {
    dismissalListenerInstalled: typeof dismissalListener === 'function',
    dismissalListenerInvocations,
    fileImportListenerInstalled: typeof fileImportListener === 'function',
    pastedLoadListenerInstalled: typeof pastedLoadListener === 'function',
    discardListenerInstalled: typeof discardListener === 'function',
    createListenerInstalled: typeof createListener === 'function',
    createListenerInvocations: form.createListenerInvocations,
  },
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


def _assert_prepared_state_is_unchanged(result: dict[str, object]) -> None:
    assert result["afterControls"] == result["beforeControls"]
    assert result["afterLocalInputs"] == result["beforeLocalInputs"]
    fields = result["fields"]
    assert isinstance(fields, list)
    assert len(fields) == 13
    assert set(result["beforeControls"]) == set(fields)


def test_terminal_dismissal_control_and_binding_are_explicit_and_local() -> None:
    page = _STATIC_PAGE.read_text(encoding="utf-8")
    client = _STATIC_CLIENT.read_text(encoding="utf-8")
    routine = client[
        client.index("export function dismissTerminalResult") : client.index("function resetResult")
    ]
    binding = client[
        client.index("if (dismissTerminalResultButton instanceof HTMLButtonElement)") : client.index(
            "if (!(form instanceof HTMLFormElement)"
        )
    ]

    assert 'id="dismiss-terminal-result" type="button"' in page
    assert "Dismiss terminal result" in page
    assert "facts.children.length > 0 || files.hidden === false" in routine
    assert "fetch(" not in routine
    assert "resetResult({ facts, fileRows, files });" in routine
    assert "Terminal result dismissed locally. No upstream state changed." in routine
    assert "dismissTerminalResultButton.addEventListener('click'" in binding
    assert "fetch(" not in binding


def test_receipt_backed_terminal_result_is_dismissed_without_preparation_or_workspace_change(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="g2-4-28-receipt")
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    result = _run_dismissal_listener(tmp_path, "receipt-backed")

    interaction = result["interaction"]
    assert interaction["dismissalListenerInstalled"] is True
    assert interaction["dismissalListenerInvocations"] == 1
    assert interaction["fileImportListenerInstalled"] is True
    assert interaction["pastedLoadListenerInstalled"] is True
    assert interaction["discardListenerInstalled"] is True
    assert interaction["createListenerInstalled"] is True
    assert interaction["createListenerInvocations"] == 0
    _assert_prepared_state_is_unchanged(result)
    assert result["afterTerminal"] == {
        "status": "Terminal result dismissed locally. No upstream state changed.",
        "factsText": "",
        "factsChildren": 0,
        "filesHidden": True,
        "fileRowsText": "",
        "fileRowsChildren": 0,
    }
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace


def test_refusal_like_zero_receipt_result_dismisses_because_rendered_facts_are_present(
    tmp_path: Path,
) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="g2-4-28-refusal")
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    result = _run_dismissal_listener(tmp_path, "refusal-like")

    assert result["beforeTerminal"]["factsChildren"] == 2
    assert result["beforeTerminal"]["fileRowsChildren"] == 0
    assert result["beforeTerminal"]["filesHidden"] is True
    assert result["interaction"]["dismissalListenerInstalled"] is True
    assert result["interaction"]["dismissalListenerInvocations"] == 1
    assert result["interaction"]["createListenerInvocations"] == 0
    _assert_prepared_state_is_unchanged(result)
    assert result["afterTerminal"] == {
        "status": "Terminal result dismissed locally. No upstream state changed.",
        "factsText": "",
        "factsChildren": 0,
        "filesHidden": True,
        "fileRowsText": "",
        "fileRowsChildren": 0,
    }
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace


def test_no_rendered_terminal_result_is_a_strict_local_no_op(tmp_path: Path) -> None:
    fixture = fixed_profile_presentation_fixture(tmp_path, identity="g2-4-28-no-result")
    before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
    result = _run_dismissal_listener(tmp_path, "no-rendered-result")

    assert result["beforeTerminal"]["factsChildren"] == 0
    assert result["beforeTerminal"]["filesHidden"] is True
    assert result["interaction"]["dismissalListenerInstalled"] is True
    assert result["interaction"]["dismissalListenerInvocations"] == 1
    assert result["interaction"]["createListenerInvocations"] == 0
    _assert_prepared_state_is_unchanged(result)
    assert result["afterTerminal"] == result["beforeTerminal"]
    assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace


def test_missing_or_wrong_type_result_target_fails_closed_without_partial_mutation(
    tmp_path: Path,
) -> None:
    for scenario in ("missing-file-rows", "wrong-type-file-rows"):
        fixture = fixed_profile_presentation_fixture(tmp_path, identity=f"g2-4-28-{scenario}")
        before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
        result = _run_dismissal_listener(tmp_path, scenario)

        assert result["beforeTerminal"]["factsChildren"] == 2
        assert result["beforeTerminal"]["filesHidden"] is False
        assert result["interaction"]["dismissalListenerInstalled"] is True
        assert result["interaction"]["dismissalListenerInvocations"] == 1
        assert result["interaction"]["createListenerInvocations"] == 0
        _assert_prepared_state_is_unchanged(result)
        assert result["afterTerminal"] == result["beforeTerminal"]
        assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace


def test_missing_or_wrong_type_dismissal_control_preserves_existing_bindings_and_state(
    tmp_path: Path,
) -> None:
    for scenario in ("missing-dismissal-control", "wrong-type-dismissal-control"):
        fixture = fixed_profile_presentation_fixture(tmp_path, identity=f"g2-4-28-{scenario}")
        before_workspace = tuple(sorted(path.name for path in fixture.workspace_root.iterdir()))
        result = _run_dismissal_listener(tmp_path, scenario)

        interaction = result["interaction"]
        assert interaction["dismissalListenerInstalled"] is False
        assert interaction["dismissalListenerInvocations"] == 0
        assert interaction["fileImportListenerInstalled"] is True
        assert interaction["pastedLoadListenerInstalled"] is True
        assert interaction["discardListenerInstalled"] is True
        assert interaction["createListenerInstalled"] is True
        assert interaction["createListenerInvocations"] == 0
        _assert_prepared_state_is_unchanged(result)
        assert result["afterTerminal"] == result["beforeTerminal"]
        assert tuple(sorted(path.name for path in fixture.workspace_root.iterdir())) == before_workspace
