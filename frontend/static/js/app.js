const STORAGE_KEY = 'rds.system-options.state';
const PRICE_DRIVING_FIELDS = new Set([
  'sys.spare_parts_qty',
  'sys.spare_saw_blades_qty',
  'sys.spare_foam_pads_qty',
  'sys.guarding',
  'sys.feeding_funneling',
  'sys.transformer',
  'sys.training_lang',
]);
const NUMERIC_FIELDS = new Set([
  'sys.spare_parts_qty',
  'sys.spare_saw_blades_qty',
  'sys.spare_foam_pads_qty',
]);
const ORIENTATION_FIELD = 'sys.infeed_orientation';
const DEBOUNCE_MS = 150;

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

function formatCurrency(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return '$0.00';
  }
  return currencyFormatter.format(numeric);
}

function formatMargin(value) {
  const numeric = Number(value ?? 0);
  return `${(numeric * 100).toFixed(2)}%`;
}

const fieldRefs = new Map();
let catalogDefaults = {};
let catalogVersion = null;
let debounceTimer = null;
let pendingController = null;
const state = {
  inputs: {},
  lastValidInputs: {},
  pricing: null,
  errors: {},
};

const liveRegion = document.getElementById('live-region');
const orientationVisual = document.getElementById('orientation-visual');
const orientationLabel = document.getElementById('orientation-label');
const formEl = document.getElementById('system-options-form');
const resetButton = document.getElementById('reset-defaults');
const pricePerQtyEls = {
  parts: document.getElementById('price-per-qty-parts'),
  blades: document.getElementById('price-per-qty-blades'),
  pads: document.getElementById('price-per-qty-pads'),
};
const totalsEls = {
  margin: document.getElementById('summary-margin'),
  base: document.getElementById('summary-base'),
  options: document.getElementById('summary-options'),
  grand: document.getElementById('summary-grand'),
};
const optionsBreakdownBody = document.getElementById('options-breakdown-body');
const costGridEls = {
  banner: document.getElementById('cost-grid-path-banner'),
  pathForm: document.getElementById('cost-grid-path-form'),
  pathInput: document.getElementById('cost-grid-path-input'),
  status: document.getElementById('cost-grid-status'),
  tableBody: document.getElementById('cost-grid-table-body'),
  metaPath: document.getElementById('cost-grid-meta-path'),
  metaUpdated: document.getElementById('cost-grid-meta-updated'),
  marginForm: document.getElementById('cost-grid-margin-form'),
  marginInput: document.getElementById('cost-grid-margin-input'),
  marginButton: document.getElementById('cost-grid-margin-button'),
};
const costGridState = {
  lastMeta: null,
  marginButtonLabel: costGridEls.marginButton ? costGridEls.marginButton.textContent : 'Apply Margin',
};

function announce(message) {
  if (!liveRegion) return;
  liveRegion.textContent = '';
  requestAnimationFrame(() => {
    liveRegion.textContent = message;
  });
}

function persistState() {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state.inputs));
  } catch (error) {
    console.warn('Unable to persist session state', error); // eslint-disable-line no-console
  }
}

function sanitizeStoredInputs(dropdowns) {
  const defaults = {};
  dropdowns.forEach((dropdown) => {
    defaults[dropdown.id] = dropdown.default;
  });

  let stored = null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      stored = JSON.parse(raw);
    }
  } catch (error) {
    stored = null;
  }

  const hydrated = { ...defaults };
  if (stored && typeof stored === 'object') {
    dropdowns.forEach((dropdown) => {
      const value = stored[dropdown.id];
      if (dropdown.options.includes(value)) {
        hydrated[dropdown.id] = value;
        return;
      }
      if (NUMERIC_FIELDS.has(dropdown.id)) {
        const numeric = Number(value);
        if (!Number.isNaN(numeric) && dropdown.options.includes(numeric)) {
          hydrated[dropdown.id] = numeric;
        }
        return;
      }
      if (typeof value === 'string') {
        const trimmed = value.trim();
        if (dropdown.options.includes(trimmed)) {
          hydrated[dropdown.id] = trimmed;
        }
      }
    });
  }

  return { defaults, hydrated };
}

function setOrientationPreview(value) {
  if (!orientationVisual || !orientationLabel) return;
  orientationVisual.classList.remove(
    'orientation-visual--left',
    'orientation-visual--centered',
    'orientation-visual--right',
  );
  const className = `orientation-visual--${value.toLowerCase()}`;
  orientationVisual.classList.add(className);
  orientationLabel.textContent = `${value} orientation`;
  orientationVisual.setAttribute('aria-label', `${value} orientation illustration`);
}

function getFieldElements(fieldId) {
  return fieldRefs.get(fieldId);
}

function setFieldError(fieldId, message) {
  const ref = getFieldElements(fieldId);
  if (!ref) return;
  if (message) {
    ref.container.dataset.error = 'true';
    ref.error.textContent = message;
  } else {
    ref.container.dataset.error = 'false';
    ref.error.textContent = '';
  }
}

function clearAllErrors() {
  state.errors = {};
  fieldRefs.forEach(({ container, error }) => {
    container.dataset.error = 'false';
    error.textContent = '';
  });
}

function normalizeValue(fieldId, value) {
  if (NUMERIC_FIELDS.has(fieldId)) {
    const numeric = Number(value);
    if (Number.isNaN(numeric)) {
      return null;
    }
    return numeric;
  }
  return value;
}

function updateSelectValue(fieldId, value) {
  const ref = getFieldElements(fieldId);
  if (!ref) return;
  ref.select.value = String(value);
}

function renderPricePerQty(derived) {
  if (!derived) return;
  Object.entries(pricePerQtyEls).forEach(([key, element]) => {
    if (!element) return;
    element.textContent = formatCurrency(derived[key]);
  });
}

function renderTotals(pricing) {
  totalsEls.margin.textContent = formatMargin(pricing?.totals?.margin ?? 0);
  totalsEls.base.textContent = formatCurrency(pricing?.base ?? 0);
  totalsEls.options.textContent = formatCurrency(pricing?.totals?.options ?? 0);
  totalsEls.grand.textContent = formatCurrency(pricing?.totals?.grand ?? 0);
}

function renderOptionsBreakdown(options = []) {
  optionsBreakdownBody.innerHTML = '';
  if (!options.length) {
    const row = document.createElement('tr');
    row.className = 'placeholder';
    const cell = document.createElement('td');
    cell.colSpan = 4;
    cell.textContent = 'No optional adders selected.';
    row.appendChild(cell);
    optionsBreakdownBody.appendChild(row);
    return;
  }

  options.forEach((option) => {
    const row = document.createElement('tr');

    const description = document.createElement('th');
    description.scope = 'row';
    description.textContent = option.label;

    const qty = document.createElement('td');
    qty.textContent = String(option.qty);

    const unit = document.createElement('td');
    unit.className = 'numeric';
    unit.textContent = formatCurrency(option.unit);
    unit.title = option.unit.toString();

    const extended = document.createElement('td');
    extended.className = 'numeric';
    extended.textContent = formatCurrency(option.extended);
    extended.title = option.extended.toString();

    row.appendChild(description);
    row.appendChild(qty);
    row.appendChild(unit);
    row.appendChild(extended);

    optionsBreakdownBody.appendChild(row);
  });
}

function renderPricing(pricing) {
  if (!pricing) return;
  renderPricePerQty(pricing.derived?.price_per_qty);
  renderTotals(pricing);
  renderOptionsBreakdown(pricing.options);
}

function schedulePricingRequest() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    requestPricing();
  }, DEBOUNCE_MS);
}

async function requestPricing() {
  if (pendingController) {
    pendingController.abort();
  }
  pendingController = new AbortController();
  const body = JSON.stringify({ inputs: state.inputs });
  try {
    const response = await fetch('/api/price', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(catalogVersion ? { 'X-Catalog-Version': catalogVersion } : {}),
      },
      body,
      signal: pendingController.signal,
    });

    if (response.status === 409) {
      const payload = await response.json().catch(() => ({}));
      if (payload.version && payload.version !== catalogVersion) {
        await loadCatalog(true);
        return requestPricing();
      }
      announce('Pricing catalog mismatch. Refreshed defaults.');
      return;
    }

    if (response.status === 400) {
      const payload = await response.json().catch(() => ({}));
      if (payload.field) {
        const fallback = state.lastValidInputs[payload.field] ?? catalogDefaults[payload.field];
        if (fallback !== undefined) {
          state.inputs[payload.field] = fallback;
          updateSelectValue(payload.field, fallback);
          if (payload.field === ORIENTATION_FIELD) {
            setOrientationPreview(String(fallback));
          }
        }
        state.errors[payload.field] = payload.error || 'Invalid value';
        setFieldError(payload.field, payload.error || 'Invalid value');
      }
      announce(payload.error || 'Unable to update pricing.');
      persistState();
      return;
    }

    if (!response.ok) {
      announce('Unable to compute pricing at this time.');
      return;
    }

    const payload = await response.json();
    catalogVersion = response.headers.get('X-Catalog-Version') || catalogVersion;
    state.pricing = payload;
    state.lastValidInputs = { ...state.inputs };
    clearAllErrors();
    persistState();
    renderPricing(payload);
  } catch (error) {
    if (error.name === 'AbortError') {
      return;
    }
    announce('Network error while requesting pricing.');
  } finally {
    pendingController = null;
  }
}

function onFieldChange(dropdown, event) {
  const rawValue = event.target.value;
  const normalized = normalizeValue(dropdown.id, rawValue);
  if (normalized === null) {
    setFieldError(dropdown.id, 'Enter a valid value.');
    updateSelectValue(dropdown.id, state.inputs[dropdown.id]);
    return;
  }

  state.inputs[dropdown.id] = normalized;
  setFieldError(dropdown.id, '');
  persistState();

  if (dropdown.id === ORIENTATION_FIELD) {
    setOrientationPreview(String(normalized));
    announce(`Infeed orientation set to ${normalized}.`);
    return;
  }

  if (!PRICE_DRIVING_FIELDS.has(dropdown.id)) {
    return;
  }

  schedulePricingRequest();
}

function buildForm(dropdowns) {
  formEl.innerHTML = '';
  fieldRefs.clear();

  dropdowns.forEach((dropdown) => {
    const container = document.createElement('div');
    container.className = 'form-field';
    container.dataset.fieldId = dropdown.id;
    container.dataset.error = 'false';

    const label = document.createElement('label');
    const inputId = `field-${dropdown.id.replace(/\./g, '-')}`;
    label.setAttribute('for', inputId);
    label.textContent = dropdown.label;

    const select = document.createElement('select');
    select.id = inputId;
    select.dataset.fieldId = dropdown.id;

    dropdown.options.forEach((option) => {
      const optionEl = document.createElement('option');
      optionEl.value = String(option);
      optionEl.textContent = typeof option === 'number' ? option.toString() : option;
      select.appendChild(optionEl);
    });

    const describedBy = [];

    if (dropdown.tooltip) {
      const help = document.createElement('p');
      help.id = `${inputId}-help`;
      help.className = 'form-field__help';
      help.textContent = dropdown.tooltip;
      container.appendChild(help);
      describedBy.push(help.id);
    }

    const error = document.createElement('p');
    error.id = `${inputId}-error`;
    error.className = 'form-field__error';
    container.appendChild(error);
    describedBy.push(error.id);

    if (describedBy.length) {
      select.setAttribute('aria-describedby', describedBy.join(' '));
    }

    select.value = String(state.inputs[dropdown.id]);
    select.addEventListener('change', onFieldChange.bind(null, dropdown));

    container.insertBefore(label, container.firstChild);
    container.insertBefore(select, container.children[1]);

    formEl.appendChild(container);

    fieldRefs.set(dropdown.id, { container, select, error });
  });
}

async function loadCatalog(force = false) {
  if (!force && catalogVersion && formEl.children.length) {
    return;
  }
  const response = await fetch('/api/dropdowns');
  const payload = await response.json();
  catalogVersion = response.headers.get('X-Catalog-Version') || payload.version || catalogVersion;

  const { defaults, hydrated } = sanitizeStoredInputs(payload.dropdowns || []);
  catalogDefaults = defaults;
  state.inputs = hydrated;
  state.lastValidInputs = { ...hydrated };

  buildForm(payload.dropdowns || []);
  setOrientationPreview(String(state.inputs[ORIENTATION_FIELD]));
  persistState();
}

function resetToDefaults() {
  state.inputs = { ...catalogDefaults };
  state.lastValidInputs = { ...catalogDefaults };
  fieldRefs.forEach((ref, fieldId) => {
    updateSelectValue(fieldId, state.inputs[fieldId]);
  });
  setOrientationPreview(String(state.inputs[ORIENTATION_FIELD]));
  clearAllErrors();
  persistState();
  schedulePricingRequest();
  announce('System options reset to defaults.');
}

function escapeHtml(text) {
  if (text === null || text === undefined) {
    return '';
  }
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatQuantity(value) {
  if (value === null || value === undefined) {
    return '';
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return '';
  }
  if (Math.abs(Math.round(numeric) - numeric) < 1e-6) {
    return String(Math.round(numeric));
  }
  return numeric.toFixed(2);
}

function formatGridMargin(value) {
  if (value === null || value === undefined) {
    return '';
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return '';
  }
  return `${(numeric * 100).toFixed(1)}%`;
}

function setCostGridStatus(message, type = 'info') {
  if (!costGridEls.status) return;
  if (!message) {
    costGridEls.status.textContent = '';
    delete costGridEls.status.dataset.status;
    return;
  }
  costGridEls.status.textContent = message;
  costGridEls.status.dataset.status = type;
}

function showCostGridBanner(show) {
  if (!costGridEls.banner) return;
  costGridEls.banner.hidden = !show;
}

function setCostGridControlsEnabled(enabled) {
  if (costGridEls.marginInput) {
    costGridEls.marginInput.disabled = !enabled;
  }
  if (costGridEls.marginButton) {
    costGridEls.marginButton.disabled = !enabled;
  }
}

function clearCostGridTable() {
  if (!costGridEls.tableBody) return;
  costGridEls.tableBody.innerHTML =
    '<tr class="placeholder"><td colspan="5">No data loaded.</td></tr>';
}

function renderCostGridTable(rows) {
  if (!costGridEls.tableBody) return;
  if (!Array.isArray(rows) || !rows.length) {
    clearCostGridTable();
    return;
  }

  const markup = rows
    .map((row) => {
      const description = escapeHtml(row?.description ?? '');
      const qty = formatQuantity(row?.qty);
      const cost = row?.cost === null || row?.cost === undefined ? '' : formatCurrency(row.cost);
      const sell =
        row?.sellPrice === null || row?.sellPrice === undefined
          ? ''
          : formatCurrency(row.sellPrice);
      const margin = formatGridMargin(row?.margin);
      return `<tr>
        <td>${description}</td>
        <td class="numeric">${qty}</td>
        <td class="numeric">${cost}</td>
        <td class="numeric">${sell}</td>
        <td class="numeric">${margin}</td>
      </tr>`;
    })
    .join('');
  costGridEls.tableBody.innerHTML = markup;
}

function updateCostGridMeta(meta) {
  costGridState.lastMeta = meta || null;
  if (costGridEls.metaPath) {
    const pathText = meta?.path ? `Path: ${meta.path}` : '';
    costGridEls.metaPath.textContent = pathText;
  }
  if (costGridEls.metaUpdated) {
    let updatedText = '';
    if (meta?.lastReadAt) {
      const ts = new Date(meta.lastReadAt);
      if (!Number.isNaN(ts.getTime())) {
        updatedText = `Last read: ${ts.toLocaleString()}`;
      }
    }
    costGridEls.metaUpdated.textContent = updatedText;
  }
}

function handleMissingCostGridPath() {
  showCostGridBanner(true);
  setCostGridControlsEnabled(false);
  updateCostGridMeta({});
  clearCostGridTable();
}

async function fetchCostGridSummary({ quiet = false } = {}) {
  if (!costGridEls.tableBody) return;
  if (!quiet) {
    setCostGridStatus('Loading Summary…', 'info');
  }
  try {
    const response = await fetch('/api/panel3/summary');
    const payload = await response.json().catch(() => ({}));
    if (response.status === 400 && payload?.error === 'COST_SHEET_PATH_MISSING') {
      handleMissingCostGridPath();
      if (!quiet) {
        setCostGridStatus('Set the cost sheet path to load the Summary grid.', 'info');
      }
      return;
    }
    if (!response.ok) {
      throw new Error(payload?.detail || `HTTP ${response.status}`);
    }

    const rows = Array.isArray(payload.rows) ? payload.rows : [];
    renderCostGridTable(rows);
    updateCostGridMeta(payload.meta || {});
    showCostGridBanner(false);
    setCostGridControlsEnabled(true);
    const count = rows.length;
    setCostGridStatus(`Loaded ${count} row${count === 1 ? '' : 's'} from Summary.`, 'success');
  } catch (error) {
    const message = error && error.message ? error.message : 'Failed to load Summary grid.';
    setCostGridStatus(message, 'error');
  }
}

async function submitCostGridPath(event) {
  if (event && typeof event.preventDefault === 'function') {
    event.preventDefault();
  }
  if (!costGridEls.pathInput) {
    return;
  }
  const value = costGridEls.pathInput.value ? costGridEls.pathInput.value.trim() : '';
  if (!value) {
    setCostGridStatus('Enter the full workbook path.', 'error');
    costGridEls.pathInput.focus();
    return;
  }

  const submitButton = costGridEls.pathForm?.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
  }
  setCostGridStatus('Saving cost sheet path…', 'info');
  try {
    const response = await fetch('/api/panel3/path', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: value }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.detail || `HTTP ${response.status}`);
    }
    await fetchCostGridSummary();
  } catch (error) {
    const message = error && error.message ? error.message : 'Failed to save cost sheet path.';
    setCostGridStatus(message, 'error');
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
    }
  }
}

async function submitCostGridMargin(event) {
  if (event && typeof event.preventDefault === 'function') {
    event.preventDefault();
  }
  if (!costGridEls.marginInput || !costGridEls.marginButton) {
    return;
  }

  const marginText = costGridEls.marginInput.value ? costGridEls.marginInput.value.trim() : '';
  if (!marginText) {
    setCostGridStatus('Enter a margin value to apply.', 'error');
    costGridEls.marginInput.focus();
    return;
  }

  let keepDisabled = false;
  const button = costGridEls.marginButton;
  const input = costGridEls.marginInput;
  button.disabled = true;
  input.disabled = true;
  button.textContent = 'Applying…';
  setCostGridStatus('Applying margin…', 'info');

  try {
    const response = await fetch('/api/panel3/margin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ marginText }),
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 400 && payload?.error === 'COST_SHEET_PATH_MISSING') {
      keepDisabled = true;
      handleMissingCostGridPath();
      setCostGridStatus('Set the cost sheet path before applying a margin.', 'error');
      return;
    }
    if (!response.ok) {
      throw new Error(payload?.detail || `HTTP ${response.status}`);
    }

    const rows = Array.isArray(payload.rows) ? payload.rows : [];
    renderCostGridTable(rows);
    updateCostGridMeta(payload.meta || {});
    showCostGridBanner(false);
    setCostGridControlsEnabled(true);
    setCostGridStatus('Margin applied.', 'success');
  } catch (error) {
    const message = error && error.message ? error.message : 'Failed to apply margin.';
    setCostGridStatus(message, 'error');
  } finally {
    button.textContent = costGridState.marginButtonLabel;
    setCostGridControlsEnabled(!keepDisabled);
    if (!keepDisabled) {
      input.focus();
    }
  }
}

function initCostGridPanel() {
  if (!costGridEls.tableBody) {
    return;
  }
  clearCostGridTable();
  setCostGridControlsEnabled(false);
  if (costGridEls.pathForm) {
    costGridEls.pathForm.addEventListener('submit', submitCostGridPath);
  }
  if (costGridEls.marginForm) {
    costGridEls.marginForm.addEventListener('submit', submitCostGridMargin);
  }
  document.addEventListener('cost-grid:refresh', () => {
    fetchCostGridSummary();
  });
  fetchCostGridSummary();
}

async function init() {
  await loadCatalog();
  renderPricing(null);
  schedulePricingRequest();
}

if (resetButton) {
  resetButton.addEventListener('click', resetToDefaults);
}

initCostGridPanel();
init();
