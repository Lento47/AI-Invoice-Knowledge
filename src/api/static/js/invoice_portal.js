class ApiError extends Error {
  constructor(status, message, payload) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

const STORAGE_KEY = 'ai-invoice-portal.credentials';

const elements = {
  apiKey: document.getElementById('api-key'),
  licenseToken: document.getElementById('license-token'),
  rememberSecrets: document.getElementById('remember-secrets'),
  extract: {
    form: document.getElementById('extract-form'),
    fileInput: document.getElementById('extract-file'),
    fileName: document.getElementById('extract-file-name'),
    trigger: document.getElementById('extract-file-button'),
    dropZone: document.getElementById('extract-drop-zone'),
    submit: document.getElementById('extract-submit'),
    loading: document.getElementById('extract-loading'),
    result: document.getElementById('extract-result'),
  },
  classify: {
    form: document.getElementById('classify-form'),
    text: document.getElementById('classify-text'),
    submit: document.getElementById('classify-submit'),
    loading: document.getElementById('classify-loading'),
    result: document.getElementById('classify-result'),
  },
  predict: {
    form: document.getElementById('predict-form'),
    tableBody: document.getElementById('feature-rows'),
    template: document.getElementById('feature-row-template'),
    addRow: document.getElementById('add-feature-row'),
    endpoint: document.getElementById('predict-endpoint'),
    submit: document.getElementById('predict-submit'),
    loading: document.getElementById('predict-loading'),
    result: document.getElementById('predict-result'),
  },
  tica: {
    form: document.getElementById('tica-form'),
    tableBody: document.getElementById('tica-rows'),
    template: document.getElementById('tica-row-template'),
    addItem: document.getElementById('add-tica-item'),
    submit: document.getElementById('tica-submit'),
    loading: document.getElementById('tica-loading'),
    result: document.getElementById('tica-result'),
  },
};

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function muted(text = '—') {
  return `<span class="muted">${escapeHtml(text)}</span>`;
}

function normaliseErrorDetail(detail) {
  if (detail == null) return 'Unexpected error.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => normaliseErrorDetail(item)).filter(Boolean).join('\n');
  }
  if (typeof detail === 'object') {
    if (Object.prototype.hasOwnProperty.call(detail, 'detail')) {
      return normaliseErrorDetail(detail.detail);
    }
    if (Object.prototype.hasOwnProperty.call(detail, 'message')) {
      return normaliseErrorDetail(detail.message);
    }
    if (Object.prototype.hasOwnProperty.call(detail, 'msg')) {
      const prefix = Array.isArray(detail.loc) ? `${detail.loc.join('.')}: ` : '';
      return `${prefix}${detail.msg}`;
    }
    try {
      return JSON.stringify(detail, null, 2);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

async function sendRequest(
  url,
  { method = 'GET', headers = new Headers(), body = undefined, responseType = 'auto' } = {},
) {
  const response = await fetch(url, { method, headers, body });

  // Handle non-2xx with best-effort body parsing for detail
  if (!response.ok) {
    let parsed;
    try {
      const text = await response.text();
      if (text) {
        try {
          parsed = JSON.parse(text);
        } catch {
          parsed = text;
        }
      } else {
        parsed = '';
      }
    } catch {
      parsed = '';
    }
    const detail = normaliseErrorDetail(parsed);
    throw new ApiError(response.status, detail, parsed);
  }

  // Success: honor explicit response type
  if (responseType === 'binary') {
    return await response.blob();
  }
  if (responseType === 'text') {
    try {
      return await response.text();
    } catch {
      return '';
    }
  }

  // Auto-detect
  const contentType = response.headers.get('Content-Type') || '';
  if (contentType.includes('application/json')) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  try {
    return await response.text();
  } catch {
    return '';
  }
}

function readCredentials() {
  return {
    apiKey: elements.apiKey?.value.trim() ?? '',
    licenseToken: elements.licenseToken?.value.trim() ?? '',
  };
}

function buildHeaders(additional = {}) {
  const headers = new Headers();
  Object.entries(additional).forEach(([key, value]) => {
    if (value != null) headers.set(key, value);
  });
  const { apiKey, licenseToken } = readCredentials();
  if (apiKey) headers.set('X-API-Key', apiKey);
  if (licenseToken) headers.set('X-License-Token', licenseToken);
  return headers;
}

function safeStorage(action, key, value) {
  try {
    if (!window.localStorage) return null;
  } catch {
    return null;
  }

  try {
    if (action === 'get') return window.localStorage.getItem(key);
    if (action === 'set') window.localStorage.setItem(key, value ?? '');
    if (action === 'remove') window.localStorage.removeItem(key);
  } catch (error) {
    console.warn('Unable to access localStorage', error);
  }
  return null;
}

function persistCredentialsIfNeeded() {
  if (!elements.rememberSecrets) return;
  if (!elements.rememberSecrets.checked) {
    safeStorage('remove', STORAGE_KEY);
    return;
  }
  const credentials = readCredentials();
  const serialised = JSON.stringify(credentials);
  safeStorage('set', STORAGE_KEY, serialised);
}

function restoreCredentials() {
  const stored = safeStorage('get', STORAGE_KEY);
  if (!stored) return;
  try {
    const credentials = JSON.parse(stored);
    if (credentials.apiKey && elements.apiKey) {
      elements.apiKey.value = credentials.apiKey;
    }
    if (credentials.licenseToken && elements.licenseToken) {
      elements.licenseToken.value = credentials.licenseToken;
    }
    if (elements.rememberSecrets) {
      elements.rememberSecrets.checked = true;
    }
  } catch (error) {
    console.warn('Stored credentials could not be parsed', error);
  }
}

function setLoading(button, indicator, busy) {
  if (!button || !indicator) return;
  button.disabled = busy;
  indicator.hidden = !busy;
  button.setAttribute('aria-busy', String(busy));
}

function clearResult(container) {
  if (!container) return;
  container.innerHTML = '';
  container.classList.remove('has-error');
}

function setResult(container, html, isError = false) {
  if (!container) return;
  container.innerHTML = html;
  container.classList.toggle('has-error', isError);
}

function renderError(container, message, status) {
  const statusLabel = status ? `Request failed (HTTP ${status})` : 'Request failed';
  const detail = escapeHtml(message);
  setResult(
    container,
    `<div class="error-banner"><span>${statusLabel}</span><span class="error-banner__detail">${detail}</span></div>`,
    true,
  );
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') return muted();
  if (typeof value === 'number') {
    return escapeHtml(value.toLocaleString(undefined, { maximumFractionDigits: 4 }));
  }
  return escapeHtml(String(value));
}

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return muted();
  const number = Number(value);
  return escapeHtml(
    number.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }),
  );
}

function formatProbability(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return muted();
  const number = Number(value);
  const percent = number * 100;
  return escapeHtml(
    percent.toLocaleString(undefined, {
      minimumFractionDigits: 1,
      maximumFractionDigits: 2,
    }) + '%',
  );
}

function normaliseString(value) {
  if (value === null || value === undefined) return '';
  return String(value).trim();
}

function parseDecimalInput(value) {
  const trimmed = normaliseString(value);
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isNaN(parsed) ? null : parsed;
}

function renderExtraction(result) {
  const container = elements.extract.result;
  const fields = [
    ['Supplier name', result.supplier_name],
    ['Supplier tax ID', result.supplier_tax_id],
    ['Invoice number', result.invoice_number],
    ['Invoice date', result.invoice_date],
    ['Due date', result.due_date],
    ['Buyer name', result.buyer_name],
    ['Buyer tax ID', result.buyer_tax_id],
    ['Currency', result.currency],
    ['Subtotal', result.subtotal],
    ['Tax', result.tax],
    ['Total', result.total],
  ];

  let html = '<div class="result-card">';
  html += '<h3>Extracted fields</h3>';
  html += '<dl class="result-grid">';
  fields.forEach(([label, value]) => {
    html += `<dt>${escapeHtml(label)}</dt><dd>${formatValue(value)}</dd>`;
  });
  html += '</dl>';

  if (Array.isArray(result.items) && result.items.length > 0) {
    html += '<h4>Line items</h4>';
    html += '<table class="result-table"><thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Total</th></tr></thead><tbody>';
    result.items.forEach((item) => {
      html += '<tr>';
      html += `<td>${formatValue(item.description)}</td>`;
      html += `<td>${formatValue(item.quantity)}</td>`;
      html += `<td>${formatValue(item.unit_price)}</td>`;
      html += `<td>${formatValue(item.total)}</td>`;
      html += '</tr>';
    });
    html += '</tbody></table>';
  }

  if (result.raw_text) {
    html += `<details class="result-meta" open><summary>Raw text</summary><pre>${escapeHtml(result.raw_text)}</pre></details>`;
  }

  html += '</div>';
  setResult(container, html);
}

function renderClassification(result) {
  const container = elements.classify.result;
  const html = `
    <div class="result-card">
      <h3>Classification result</h3>
      <dl class="result-grid">
        <dt>Label</dt><dd>${formatValue(result.label)}</dd>
        <dt>Probability</dt><dd>${formatProbability(result.proba)}</dd>
      </dl>
    </div>
  `;
  setResult(container, html);
}

function renderPrediction(result) {
  const container = elements.predict.result;
  const html = `
    <div class="result-card">
      <h3>Predicted payment</h3>
      <dl class="result-grid">
        <dt>Expected days to pay</dt><dd>${formatNumber(result.predicted_payment_days, 1)}</dd>
        <dt>Projected payment date</dt><dd>${formatValue(result.predicted_payment_date)}</dd>
        <dt>Risk score</dt><dd>${formatNumber(result.risk_score, 3)}</dd>
        <dt>Confidence</dt><dd>${formatProbability(result.confidence)}</dd>
      </dl>
    </div>
  `;
  setResult(container, html);
}

function parseFeatureValue(value) {
  if (value === null || value === undefined) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (trimmed.toLowerCase() === 'true') return true;
  if (trimmed.toLowerCase() === 'false') return false;
  const numeric = Number(trimmed);
  if (!Number.isNaN(numeric)) return numeric;
  return value;
}

function collectFeatures() {
  const rows = Array.from(elements.predict.tableBody?.querySelectorAll('.feature-row') ?? []);
  const features = {};
  let hasError = false;

  rows.forEach((row) => {
    row.classList.remove('has-error');
    const keyInput = row.querySelector('.feature-key');
    const valueInput = row.querySelector('.feature-value');
    const key = keyInput?.value.trim() ?? '';
    const value = valueInput?.value ?? '';

    if (!key && !value) return; // skip empty rows
    if (!key) {
      row.classList.add('has-error');
      hasError = true;
      return;
    }
    features[key] = parseFeatureValue(value);
  });

  return { features, hasError };
}

function ensureMinimumRows() {
  const rows = elements.predict.tableBody?.querySelectorAll('.feature-row');
  if (!rows || rows.length > 0) return;
  addFeatureRow();
}

function addFeatureRow(key = '', value = '') {
  const template = elements.predict.template;
  const tbody = elements.predict.tableBody;
  if (!template || !tbody) return;
  const prototypeRow = template.content.firstElementChild;
  if (!prototypeRow) return;
  const fragment = prototypeRow.cloneNode(true);
  const keyInput = fragment.querySelector('.feature-key');
  const valueInput = fragment.querySelector('.feature-value');
  const removeButton = fragment.querySelector('.remove-feature');

  if (keyInput) keyInput.value = key;
  if (valueInput) valueInput.value = value;
  if (removeButton) {
    removeButton.addEventListener('click', () => {
      fragment.remove();
      ensureMinimumRows();
    });
  }

  tbody.appendChild(fragment);
}

function triggerDownload(blob, filename) {
  if (!(blob instanceof Blob)) return;
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function collectTicaItems() {
  const rows = Array.from(elements.tica.tableBody?.querySelectorAll('.tica-row') ?? []);
  const items = [];
  let hasError = false;

  rows.forEach((row) => {
    row.classList.remove('has-error');
    const descriptionField = row.querySelector('.tica-description');
    const hsField = row.querySelector('.tica-hs');
    const originField = row.querySelector('.tica-origin');
    const quantityField = row.querySelector('.tica-quantity');
    const unitField = row.querySelector('.tica-unit-value');
    const totalField = row.querySelector('.tica-total-value');

    const description = normaliseString(descriptionField?.value);
    const hs = normaliseString(hsField?.value);
    const origin = normaliseString(originField?.value);
    const quantityRaw = quantityField?.value;
    const unitRaw = unitField?.value;
    const totalRaw = totalField?.value;

    const isEmpty =
      !description &&
      !normaliseString(quantityRaw) &&
      !normaliseString(unitRaw) &&
      !normaliseString(totalRaw) &&
      !hs &&
      !origin;

    if (isEmpty) return;

    const quantity = parseDecimalInput(quantityRaw);
    const unitValue = parseDecimalInput(unitRaw);
    const totalValue = parseDecimalInput(totalRaw);

    if (!description || quantity === null || unitValue === null) {
      row.classList.add('has-error');
      hasError = true;
      return;
    }

    const item = {
      description,
      quantity,
      unit_value: unitValue,
    };

    if (totalValue !== null) item.total_value = totalValue;
    if (hs) item.hs_code = hs;
    if (origin) item.country_of_origin = origin;

    items.push(item);
  });

  return { items, hasError };
}

function ensureTicaRows() {
  const rows = elements.tica.tableBody?.querySelectorAll('.tica-row');
  if (!rows || rows.length > 0) return;
  addTicaRow();
}

function addTicaRow(data = {}) {
  const template = elements.tica.template;
  const tbody = elements.tica.tableBody;
  if (!template || !tbody) return;

  const prototypeRow = template.content.firstElementChild;
  if (!prototypeRow) return;

  const row = prototypeRow.cloneNode(true);
  const description = row.querySelector('.tica-description');
  const hs = row.querySelector('.tica-hs');
  const origin = row.querySelector('.tica-origin');
  const quantity = row.querySelector('.tica-quantity');
  const unitValue = row.querySelector('.tica-unit-value');
  const totalValue = row.querySelector('.tica-total-value');
  const removeButton = row.querySelector('.remove-tica-item');

  if (description) description.value = data.description ?? '';
  if (hs) hs.value = data.hs_code ?? '';
  if (origin) origin.value = data.country_of_origin ?? '';
  if (quantity) quantity.value = data.quantity ?? '';
  if (unitValue) unitValue.value = data.unit_value ?? '';
  if (totalValue) totalValue.value = data.total_value ?? '';

  if (removeButton) {
    removeButton.addEventListener('click', () => {
      row.remove();
      ensureTicaRows();
    });
  }

  tbody.appendChild(row);
}

function updateFileNameLabel() {
  const { fileInput, fileName } = elements.extract;
  if (!fileInput || !fileName) return;
  const file = fileInput.files && fileInput.files[0];
  fileName.textContent = file ? file.name : 'No file selected';
}

function setupDropZone() {
  const { dropZone, fileInput } = elements.extract;
  if (!dropZone || !fileInput) return;
  dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropZone.classList.add('is-dragover');
  });
  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('is-dragover');
  });
  dropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    dropZone.classList.remove('is-dragover');
    const files = event.dataTransfer?.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    let assigned = false;
    if (typeof DataTransfer !== 'undefined') {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      fileInput.files = dataTransfer.files;
      assigned = true;
    }
    if (!assigned) {
      try {
        fileInput.files = files;
        assigned = true;
      } catch (error) {
        console.warn('Unable to populate file input from drop event', error);
      }
    }
    if (!assigned) {
      fileInput.value = '';
    }
    updateFileNameLabel();
  });
}

function bindCredentialPersistence() {
  if (!elements.rememberSecrets) return;
  elements.rememberSecrets.addEventListener('change', () => {
    if (!elements.rememberSecrets.checked) {
      safeStorage('remove', STORAGE_KEY);
    } else {
      persistCredentialsIfNeeded();
    }
  });
  [elements.apiKey, elements.licenseToken].forEach((input) => {
    if (!input) return;
    input.addEventListener('input', () => {
      if (elements.rememberSecrets?.checked) {
        persistCredentialsIfNeeded();
      }
    });
  });
}

function bindExtractForm() {
  const { form, submit, loading, result, fileInput, trigger } = elements.extract;
  if (!form || !submit || !loading || !result || !fileInput) return;

  if (trigger) {
    trigger.addEventListener('click', () => fileInput.click());
  }

  fileInput.addEventListener('change', updateFileNameLabel);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearResult(result);

    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      renderError(result, 'Select an invoice file before submitting.', 400);
      return;
    }

    persistCredentialsIfNeeded();
    setLoading(submit, loading, true);
    const headers = buildHeaders();
    const formData = new FormData();
    formData.append('file', file);

    try {
      const payload = await sendRequest('/invoices/extract', {
        method: 'POST',
        headers,
        body: formData,
      });
      renderExtraction(payload);
    } catch (error) {
      if (error instanceof ApiError) {
        renderError(result, error.message, error.status);
      } else {
        renderError(result, error?.message ?? 'Unexpected network error.', undefined);
      }
    } finally {
      setLoading(submit, loading, false);
    }
  });
}

function bindClassifyForm() {
  const { form, submit, loading, result, text } = elements.classify;
  if (!form || !submit || !loading || !result || !text) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearResult(result);

    const content = text.value.trim();
    if (!content) {
      renderError(result, 'Provide text to classify.', 400);
      return;
    }

    persistCredentialsIfNeeded();
    setLoading(submit, loading, true);
    const headers = buildHeaders({ 'Content-Type': 'application/json' });

    try {
      const payload = await sendRequest('/invoices/classify', {
        method: 'POST',
        headers,
        body: JSON.stringify({ text: content }),
      });
      renderClassification(payload);
    } catch (error) {
      if (error instanceof ApiError) {
        renderError(result, error.message, error.status);
      } else {
        renderError(result, error?.message ?? 'Unexpected network error.', undefined);
      }
    } finally {
      setLoading(submit, loading, false);
    }
  });
}

function bindPredictForm() {
  const { form, submit, loading, result, addRow, endpoint } = elements.predict;
  if (!form || !submit || !loading || !result || !addRow || !endpoint) return;

  addRow.addEventListener('click', () => addFeatureRow());

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearResult(result);

    const { features, hasError } = collectFeatures();
    if (hasError) {
      renderError(result, 'Each populated row must include a feature key.', 400);
      return;
    }
    if (Object.keys(features).length === 0) {
      renderError(result, 'Add at least one feature before scoring.', 400);
      return;
    }

    persistCredentialsIfNeeded();
    setLoading(submit, loading, true);
    const headers = buildHeaders({ 'Content-Type': 'application/json' });
    const target = endpoint.value || '/invoices/predict';

    try {
      const payload = await sendRequest(target, {
        method: 'POST',
        headers,
        body: JSON.stringify({ features }),
      });
      renderPrediction(payload);
    } catch (error) {
      if (error instanceof ApiError) {
        renderError(result, error.message, error.status);
      } else {
        renderError(result, error?.message ?? 'Unexpected network error.', undefined);
      }
    } finally {
      setLoading(submit, loading, false);
    }
  });
}

function initialisePredictTable() {
  const sampleRows = [
    ['amount', '950'],
    ['customer_age_days', '400'],
    ['prior_invoices', '12'],
    ['late_ratio', '0.2'],
  ];
  sampleRows.forEach(([key, value]) => addFeatureRow(key, value));
}

function bindTicaForm() {
  const { form, submit, loading, result, addItem } = elements.tica;
  if (!form || !submit || !loading || !result || !addItem) return;

  addItem.addEventListener('click', () => addTicaRow());

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearResult(result);

    const formData = new FormData(form);
    const invoiceNumber = normaliseString(formData.get('invoice_number'));
    const issueDate = normaliseString(formData.get('issue_date'));
    const exporterName = normaliseString(formData.get('exporter_name'));
    const exporterId = normaliseString(formData.get('exporter_id'));
    const importerName = normaliseString(formData.get('importer_name'));
    const importerId = normaliseString(formData.get('importer_id'));
    const currency = normaliseString(formData.get('currency'));
    const subtotal = parseDecimalInput(formData.get('subtotal'));
    const tax = parseDecimalInput(formData.get('tax'));
    const total = parseDecimalInput(formData.get('total'));

    if (!invoiceNumber) {
      renderError(result, 'Invoice number is required for the TICA document.', 400);
      return;
    }
    if (!issueDate) {
      renderError(result, 'Provide an issue date (YYYY-MM-DD).', 400);
      return;
    }
    if (!exporterName || !exporterId) {
      renderError(result, 'Exporter name and identification are required.', 400);
      return;
    }
    if (!importerName || !importerId) {
      renderError(result, 'Importer name and identification are required.', 400);
      return;
    }
    if (!currency) {
      renderError(result, 'Specify the currency code.', 400);
      return;
    }
    if (subtotal === null || tax === null || total === null) {
      renderError(result, 'Subtotal, tax, and total must be numeric values.', 400);
      return;
    }

    const { items, hasError } = collectTicaItems();
    if (hasError) {
      renderError(result, 'Each goods line must include a description, quantity, and unit value.', 400);
      return;
    }
    if (items.length === 0) {
      renderError(result, 'Add at least one goods line before generating the PDF.', 400);
      return;
    }

    const payload = {
      invoice_number: invoiceNumber,
      issue_date: issueDate,
      exporter_name: exporterName,
      exporter_id: exporterId,
      importer_name: importerName,
      importer_id: importerId,
      currency,
      subtotal,
      tax,
      total,
      items,
    };

    const optionalFields = {
      exporter_address: normaliseString(formData.get('exporter_address')),
      importer_address: normaliseString(formData.get('importer_address')),
      customs_reference: normaliseString(formData.get('customs_reference')),
      regime: normaliseString(formData.get('regime')),
      incoterm: normaliseString(formData.get('incoterm')),
      transport_mode: normaliseString(formData.get('transport_mode')),
      destination_port: normaliseString(formData.get('destination_port')),
      notes: normaliseString(formData.get('notes')),
    };

    Object.entries(optionalFields).forEach(([key, value]) => {
      if (value) payload[key] = value;
    });

    persistCredentialsIfNeeded();
    setLoading(submit, loading, true);
    const headers = buildHeaders({ 'Content-Type': 'application/json' });
    const filename = `tica_invoice_${invoiceNumber}.pdf`;

    try {
      const blob = await sendRequest('/invoices/tica-pdf', {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        responseType: 'binary',
      });
      triggerDownload(blob, filename);
      const html = `
        <div class="result-card">
          <h3>PDF generated</h3>
          <p>The customs document was downloaded as <strong>${escapeHtml(filename)}</strong>.</p>
        </div>
      `;
      setResult(result, html);
    } catch (error) {
      if (error instanceof ApiError) {
        renderError(result, error.message, error.status);
      } else {
        renderError(result, error?.message ?? 'Unexpected network error.', undefined);
      }
    } finally {
      setLoading(submit, loading, false);
    }
  });
}

function initialiseTicaTable() {
  const sampleItems = [
    {
      description: 'Equipo de oficina',
      hs_code: '8471.30',
      country_of_origin: 'CN',
      quantity: '10',
      unit_value: '150',
    },
  ];
  sampleItems.forEach((item) => addTicaRow(item));
  ensureTicaRows();

  const issueDate = document.getElementById('tica-issue-date');
  if (issueDate && !issueDate.value) {
    const now = new Date();
    const iso = now.toISOString().slice(0, 10);
    issueDate.value = iso;
  }
}

function init() {
  restoreCredentials();
  bindCredentialPersistence();
  bindExtractForm();
  bindClassifyForm();
  bindPredictForm();
  bindTicaForm();
  setupDropZone();
  initialisePredictTable();
  initialiseTicaTable();
}

init();
