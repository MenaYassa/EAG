export const MAX_MANIFEST_BYTES = 64 * 1024;

export const MANIFEST_FIELDS = Object.freeze([
  'submission_id',
  'profile',
  'requested_at',
  'expires_at',
  'attestation_id',
  'execution_id',
  'run_id',
  'workspace_id',
  'workspace_root',
  'source_repository_root',
  'audit_root',
  'control_root',
  'composition_attestation',
]);

export const IMPORT_DISPOSITIONS = Object.freeze({
  NOT_SELECTED: 'NOT_SELECTED',
  IMPORT_REFUSED: 'IMPORT_REFUSED',
  LOADED_FOR_REVIEW: 'LOADED_FOR_REVIEW',
});

const fieldLabels = {
  selected_profile: 'Profile',
  profile_version: 'Profile version',
  source_specification_digest: 'Source specification digest',
  intent_request_id: 'Intent request',
  intent_request_digest: 'Intent request digest',
  intent_assessment_id: 'Intent assessment',
  intent_assessment_digest: 'Intent assessment digest',
  work_order_id: 'Work order',
  work_order_digest: 'Work order digest',
  work_order_assessment_id: 'Work order assessment',
  work_order_assessment_digest: 'Work order assessment digest',
  work_order_expires_at: 'Work order expiry',
  authorization_id: 'Authorization',
  authorization_digest: 'Authorization digest',
  plan_digest: 'Plan digest',
  construction_disposition: 'Construction disposition',
  construction_failure: 'Construction failure',
  failure_stage: 'Failure stage',
  failure_code: 'Failure code',
};

function importRefusal(message) {
  return Object.freeze({
    disposition: IMPORT_DISPOSITIONS.IMPORT_REFUSED,
    message,
    values: null,
  });
}

function isJsonObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Parse caller-supplied manifest bytes without assessing evidence or profile meaning.
 * The declared-size gate is evaluated before the caller reads user-selected bytes.
 */
export function parseGovernedSubmissionManifest({ declaredSize, bytes }) {
  if (!Number.isSafeInteger(declaredSize) || declaredSize < 0) {
    return importRefusal('Manifest size is invalid.');
  }
  if (declaredSize > MAX_MANIFEST_BYTES) {
    return importRefusal('Manifest exceeds the local 64 KiB import limit.');
  }
  if (!(bytes instanceof Uint8Array) || bytes.byteLength !== declaredSize) {
    return importRefusal('Manifest bytes do not match the declared file size.');
  }

  let text;
  try {
    text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch (_) {
    return importRefusal('Manifest must be valid UTF-8.');
  }

  let payload;
  try {
    payload = JSON.parse(text);
  } catch (_) {
    return importRefusal('Manifest must be valid JSON.');
  }
  if (!isJsonObject(payload)) {
    return importRefusal('Manifest must be a JSON object.');
  }

  const keys = Object.keys(payload);
  if (keys.length !== MANIFEST_FIELDS.length || keys.some((key) => !MANIFEST_FIELDS.includes(key))) {
    return importRefusal('Manifest must contain exactly the supported request fields.');
  }
  for (const field of MANIFEST_FIELDS) {
    if (!(field in payload)) {
      return importRefusal('Manifest must contain exactly the supported request fields.');
    }
  }
  for (const field of MANIFEST_FIELDS.slice(0, -1)) {
    if (typeof payload[field] !== 'string') {
      return importRefusal(`Manifest field ${field} must be a string.`);
    }
  }
  if (!isJsonObject(payload.composition_attestation)) {
    return importRefusal('Manifest composition_attestation must be an object.');
  }

  return Object.freeze({
    disposition: IMPORT_DISPOSITIONS.LOADED_FOR_REVIEW,
    message: 'Manifest loaded for review. Review fields and press Create.',
    values: Object.freeze({
      ...payload,
      composition_attestation: JSON.stringify(payload.composition_attestation),
    }),
  });
}

/**
 * Apply a parsed manifest only after every representation check has succeeded.
 * This is a local form operation; it neither submits nor assesses the manifest.
 */
export function applyManifestToForm({ form, result }) {
  if (result.disposition !== IMPORT_DISPOSITIONS.LOADED_FOR_REVIEW || result.values === null) {
    return false;
  }
  for (const field of MANIFEST_FIELDS) {
    const control = form.elements.namedItem(field);
    if (!(control instanceof HTMLInputElement || control instanceof HTMLTextAreaElement)) {
      throw new Error(`Missing manifest form control: ${field}`);
    }
    control.value = result.values[field];
  }
  return true;
}

/**
 * Read user-selected local bytes only after the fixed pre-read size check.
 */
export async function importGovernedSubmissionManifest(file) {
  if (file === null) {
    return Object.freeze({
      disposition: IMPORT_DISPOSITIONS.NOT_SELECTED,
      message: 'No manifest selected.',
      values: null,
    });
  }
  if (!Number.isSafeInteger(file.size) || file.size < 0) {
    return importRefusal('Manifest size is invalid.');
  }
  if (file.size > MAX_MANIFEST_BYTES) {
    return importRefusal('Manifest exceeds the local 64 KiB import limit.');
  }

  let bytes;
  try {
    bytes = new Uint8Array(await file.arrayBuffer());
  } catch (_) {
    return importRefusal('Manifest bytes could not be read.');
  }
  return parseGovernedSubmissionManifest({ declaredSize: file.size, bytes });
}

/**
 * Encode caller-entered DOM text and reuse the existing manifest representation parser.
 * Loading text is local form preparation only; it neither submits nor assesses the values.
 */
export function loadPastedGovernedSubmissionManifest(text) {
  if (typeof text !== 'string') {
    return importRefusal('Pasted manifest text is invalid.');
  }
  const bytes = new TextEncoder().encode(text);
  return parseGovernedSubmissionManifest({ declaredSize: bytes.byteLength, bytes });
}

/**
 * Discard only browser-local caller preparation state. This neither submits nor
 * evaluates the values, and fails without changing state unless every required
 * control is present.
 */
export function discardPreparedInputs({ form, importInput, pastedManifest, importStatus }) {
  const controls = MANIFEST_FIELDS.map((field) => form.elements.namedItem(field));
  if (controls.some((control) => !(control instanceof HTMLInputElement || control instanceof HTMLTextAreaElement))
    || !(importInput instanceof HTMLInputElement)
    || !(pastedManifest instanceof HTMLTextAreaElement)
    || !(importStatus instanceof HTMLElement)) {
    return false;
  }
  for (const control of controls) {
    control.value = '';
  }
  importInput.value = '';
  pastedManifest.value = '';
  importStatus.textContent = 'Prepared local inputs discarded. No construction was submitted.';
  return true;
}

/**
 * Dismiss only an already-rendered terminal presentation. This is browser-local
 * presentation state: it neither submits nor changes prepared inputs or upstream facts.
 */
export function dismissTerminalResult({ status, facts, files, fileRows }) {
  if (!(facts instanceof HTMLElement) || !(files instanceof HTMLElement)) {
    return false;
  }
  const terminalPresentationRendered = facts.children.length > 0 || files.hidden === false;
  if (!terminalPresentationRendered) {
    return false;
  }
  if (!(status instanceof HTMLElement) || !(fileRows instanceof HTMLTableSectionElement)) {
    return false;
  }
  resetResult({ facts, fileRows, files });
  status.textContent = 'Terminal result dismissed locally. No upstream state changed.';
  return true;
}

function resetResult({ facts, fileRows, files }) {
  facts.replaceChildren();
  fileRows.replaceChildren();
  files.hidden = true;
}

function appendFact({ facts, label, value }) {
  if (value === null || value === undefined) return;
  const term = document.createElement('dt');
  term.textContent = label;
  const definition = document.createElement('dd');
  definition.textContent = value;
  facts.append(term, definition);
}

function renderResult({ facts, fileRows, files, status }, result) {
  resetResult({ facts, fileRows, files });
  status.textContent = `${result.presentation_disposition}${result.failure_code ? ` — ${result.failure_code}` : ''}`;
  Object.entries(fieldLabels).forEach(([key, label]) => appendFact({ facts, label, value: result[key] }));
  if (result.receipt_files.length) {
    result.receipt_files.forEach((item) => {
      const row = document.createElement('tr');
      [item.relative_path, String(item.byte_count), item.content_digest].forEach((value) => {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      });
      fileRows.append(row);
    });
    files.hidden = false;
  }
}

function bindVisualPage() {
  const form = document.querySelector('#construct-form');
  const status = document.querySelector('#status');
  const importInput = document.querySelector('#submission-manifest');
  const pastedManifest = document.querySelector('#pasted-manifest');
  const loadPastedManifest = document.querySelector('#load-pasted-manifest');
  const discardPreparedInputsButton = document.querySelector('#discard-prepared-inputs');
  const dismissTerminalResultButton = document.querySelector('#dismiss-terminal-result');
  const importStatus = document.querySelector('#import-status');
  const facts = document.querySelector('#facts');
  const files = document.querySelector('#files');
  const fileRows = document.querySelector('#files tbody');

  if (dismissTerminalResultButton instanceof HTMLButtonElement) {
    dismissTerminalResultButton.addEventListener('click', () => {
      dismissTerminalResult({ status, facts, files, fileRows });
    });
  }

  if (!(form instanceof HTMLFormElement)
    || !(status instanceof HTMLElement)
    || !(importInput instanceof HTMLInputElement)
    || !(pastedManifest instanceof HTMLTextAreaElement)
    || !(loadPastedManifest instanceof HTMLButtonElement)
    || !(importStatus instanceof HTMLElement)
    || !(facts instanceof HTMLElement)
    || !(files instanceof HTMLElement)
    || !(fileRows instanceof HTMLTableSectionElement)) {
    return;
  }

  importInput.addEventListener('change', async () => {
    const result = await importGovernedSubmissionManifest(importInput.files?.item(0) ?? null);
    if (result.disposition === IMPORT_DISPOSITIONS.LOADED_FOR_REVIEW) {
      applyManifestToForm({ form, result });
    }
    importStatus.textContent = result.message;
  });

  loadPastedManifest.addEventListener('click', () => {
    const result = loadPastedGovernedSubmissionManifest(pastedManifest.value);
    if (result.disposition === IMPORT_DISPOSITIONS.LOADED_FOR_REVIEW) {
      applyManifestToForm({ form, result });
    }
    importStatus.textContent = result.message;
  });

  if (discardPreparedInputsButton instanceof HTMLButtonElement) {
    discardPreparedInputsButton.addEventListener('click', () => {
      discardPreparedInputs({ form, importInput, pastedManifest, importStatus });
    });
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    if (!(button instanceof HTMLButtonElement)) return;
    button.disabled = true;
    resetResult({ facts, fileRows, files });
    status.textContent = 'Submitting governed construction request…';
    const input = new FormData(form);
    let compositionAttestation;
    try {
      compositionAttestation = JSON.parse(input.get('composition_attestation'));
    } catch (_) {
      status.textContent = 'Runtime composition attestation must be valid JSON.';
      button.disabled = false;
      return;
    }
    const payload = Object.fromEntries(input.entries());
    payload.composition_attestation = compositionAttestation;
    try {
      const response = await fetch('/api/construct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        status.textContent = result.error || 'Local visual request refused.';
        return;
      }
      renderResult({ facts, fileRows, files, status }, result);
    } catch (_) {
      status.textContent = 'The loopback visual host did not return a result.';
    } finally {
      button.disabled = false;
    }
  });
}

if (typeof document !== 'undefined') {
  bindVisualPage();
}
