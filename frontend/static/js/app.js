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
const excelEls = {
  form: document.getElementById('excel-open-form'),
  path: document.getElementById('excel-path'),
  refresh: document.getElementById('excel-refresh'),
  status: document.getElementById('excel-status'),
  body: document.getElementById('excel-summary-body'),
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

function setExcelStatus(message, type = 'info') {
  if (!excelEls.status) return;
  if (!message) {
    excelEls.status.textContent = '';
    delete excelEls.status.dataset.status;
    return;
  }
  excelEls.status.textContent = message;
  excelEls.status.dataset.status = type;
}

function clearExcelTable() {
  if (!excelEls.body) return;
  excelEls.body.innerHTML =
    '<tr class="placeholder"><td>No data loaded.</td></tr>';
}

function renderExcelTable(values) {
  if (!excelEls.body) return;
  if (!Array.isArray(values) || !values.length) {
    clearExcelTable();
    return;
  }
  const rows = values
    .map((row) => {
      const cells = (Array.isArray(row) ? row : [row])
        .map((cell) => {
          const text = cell === null || cell === undefined ? '' : String(cell);
          return `<td>${text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</td>`;
        })
        .join('');
      return `<tr>${cells}</tr>`;
    })
    .join('');
  excelEls.body.innerHTML = rows;
}

async function refreshExcelSummary() {
  if (!excelEls.body) return;
  setExcelStatus('Loading Summary…', 'info');
  try {
    const response = await fetch('/api/cost-sheet/summary');
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    renderExcelTable(payload.values || []);
    const rows = Array.isArray(payload.values) ? payload.values.length : 0;
    const sheet = payload.sheet || 'Summary';
    const range = payload.range || 'C4:K55';
    setExcelStatus(`Loaded ${rows} row${rows === 1 ? '' : 's'} from ${sheet}!${range}.`, 'success');
  } catch (error) {
    const message = error && error.message ? error.message : 'Failed to load Summary range.';
    setExcelStatus(message, 'error');
    clearExcelTable();
  }
}

async function openExcelWorkbook(event) {
  if (event && typeof event.preventDefault === 'function') {
    event.preventDefault();
  }
  if (!excelEls.path) {
    return;
  }
  const path = excelEls.path.value ? excelEls.path.value.trim() : '';
  if (!path) {
    setExcelStatus('Enter the full path to Costing.xlsb.', 'error');
    return;
  }
  setExcelStatus('Opening workbook…', 'info');
  try {
    const response = await fetch('/api/cost-sheet/path', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    setExcelStatus('Workbook opened. Loading grid…', 'success');
    await refreshExcelSummary();
  } catch (error) {
    const message = error && error.message ? error.message : 'Failed to open workbook.';
    setExcelStatus(message, 'error');
  }
}

function initExcelPanel() {
  if (!excelEls.body) {
    return;
  }
  if (excelEls.form) {
    excelEls.form.addEventListener('submit', openExcelWorkbook);
  }
  if (excelEls.refresh) {
    excelEls.refresh.addEventListener('click', (event) => {
      if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
      }
      refreshExcelSummary();
    });
  }
  clearExcelTable();
  refreshExcelSummary();
}

async function init() {
  await loadCatalog();
  renderPricing(null);
  schedulePricingRequest();
}

if (resetButton) {
  resetButton.addEventListener('click', resetToDefaults);
}

initExcelPanel();
init();
