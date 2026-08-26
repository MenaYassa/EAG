const form = document.querySelector('#construct-form');
const status = document.querySelector('#status');
const facts = document.querySelector('#facts');
const files = document.querySelector('#files');
const fileRows = document.querySelector('#files tbody');

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

function resetResult() {
  facts.replaceChildren();
  fileRows.replaceChildren();
  files.hidden = true;
}

function appendFact(label, value) {
  if (value === null || value === undefined) return;
  const term = document.createElement('dt');
  term.textContent = label;
  const definition = document.createElement('dd');
  definition.textContent = value;
  facts.append(term, definition);
}

function renderResult(result) {
  resetResult();
  status.textContent = `${result.presentation_disposition}${result.failure_code ? ` — ${result.failure_code}` : ''}`;
  Object.entries(fieldLabels).forEach(([key, label]) => appendFact(label, result[key]));
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

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = form.querySelector('button');
  button.disabled = true;
  resetResult();
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
  payload.profile = document.querySelector('#profile').value;
  payload.composition_attestation = compositionAttestation;
  delete payload.composition_attestation;
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
    renderResult(result);
  } catch (_) {
    status.textContent = 'The loopback visual host did not return a result.';
  } finally {
    button.disabled = false;
  }
});
