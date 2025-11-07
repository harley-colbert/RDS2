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
  browseButton: document.getElementById('cost-grid-browse-button'),
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
  isConnected: false,
  connectPromise: null,
};

const costGridBrowserEls = {
  overlay: document.getElementById('cost-grid-browser'),
  dialog: document.getElementById('cost-grid-browser-dialog'),
  closeControls: Array.from(document.querySelectorAll('[data-cost-grid-browser-close]')),
  cwd: document.getElementById('cost-grid-browser-cwd'),
  rootsSection: document.getElementById('cost-grid-browser-roots-section'),
  roots: document.getElementById('cost-grid-browser-roots'),
  entries: document.getElementById('cost-grid-browser-entries'),
  error: document.getElementById('cost-grid-browser-error'),
  loading: document.getElementById('cost-grid-browser-loading'),
  reset: document.getElementById('cost-grid-browser-reset'),
  up: document.getElementById('cost-grid-browser-up'),
};

const costGridBrowserState = {
  parent: null,
  cwd: '',
};

let costGridBrowserRestoreFocus = null;
let costGridBrowserRequestId = 0;

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

function setCostGridBrowserError(message) {
  if (!costGridBrowserEls.error) return;
  if (message) {
    costGridBrowserEls.error.hidden = false;
    costGridBrowserEls.error.textContent = message;
  } else {
    costGridBrowserEls.error.hidden = true;
    costGridBrowserEls.error.textContent = '';
  }
}

function setCostGridBrowserLoading(isLoading) {
  if (costGridBrowserEls.loading) {
    costGridBrowserEls.loading.hidden = !isLoading;
  }
  if (costGridBrowserEls.reset) {
    costGridBrowserEls.reset.disabled = isLoading;
  }
  if (costGridBrowserEls.roots) {
    costGridBrowserEls.roots.classList.toggle('is-loading', Boolean(isLoading));
  }
  if (costGridBrowserEls.entries) {
    costGridBrowserEls.entries.classList.toggle('is-loading', Boolean(isLoading));
  }
  if (costGridBrowserEls.up) {
    const disabled = isLoading || !costGridBrowserState.parent;
    costGridBrowserEls.up.disabled = Boolean(disabled);
  }
}

function renderCostGridBrowserRoots(roots) {
  if (!costGridBrowserEls.roots || !costGridBrowserEls.rootsSection) return;
  costGridBrowserEls.roots.innerHTML = '';
  const list = Array.isArray(roots) ? roots : [];
  if (!list.length) {
    costGridBrowserEls.rootsSection.hidden = true;
    return;
  }
  costGridBrowserEls.rootsSection.hidden = false;
  list.forEach((root) => {
    const path = root?.path ? String(root.path) : '';
    const label = root?.name ? String(root.name) : path;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'cost-grid-browser__root-button';
    button.textContent = label;
    button.setAttribute('data-path', path);
    costGridBrowserEls.roots.appendChild(button);
  });
}

function renderCostGridBrowserEntries(entries) {
  if (!costGridBrowserEls.entries) return;
  costGridBrowserEls.entries.innerHTML = '';
  const list = Array.isArray(entries) ? entries : [];
  if (!list.length) {
    const empty = document.createElement('div');
    empty.className = 'cost-grid-browser__empty';
    empty.textContent = 'No items in this folder.';
    costGridBrowserEls.entries.appendChild(empty);
    return;
  }

  list.forEach((entry) => {
    const row = document.createElement('div');
    row.className = 'cost-grid-browser__row';

    const itemButton = document.createElement('button');
    itemButton.type = 'button';
    itemButton.className = 'cost-grid-browser__item';
    const path = entry?.path ? String(entry.path) : '';
    const isDir = Boolean(entry?.isDir);
    const isExcel = Boolean(entry?.isExcel);
    itemButton.setAttribute('data-path', path);
    itemButton.setAttribute('data-action', isDir ? 'enter' : 'select');
    itemButton.setAttribute('data-is-dir', isDir ? '1' : '0');
    itemButton.setAttribute('data-is-excel', isExcel ? '1' : '0');

    const icon = document.createElement('span');
    icon.className = 'cost-grid-browser__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = isDir ? '📁' : isExcel ? '📄' : '📃';

    const label = document.createElement('span');
    label.className = 'cost-grid-browser__label';
    label.textContent = entry?.name ? String(entry.name) : path;

    itemButton.appendChild(icon);
    itemButton.appendChild(label);
    row.appendChild(itemButton);

    if (entry?.isFile) {
      const selectButton = document.createElement('button');
      selectButton.type = 'button';
      selectButton.className = 'cost-grid-browser__select';
      selectButton.textContent = 'Select';
      selectButton.setAttribute('data-path', path);
      selectButton.setAttribute('data-action', 'select');
      selectButton.setAttribute('data-is-dir', isDir ? '1' : '0');
      selectButton.setAttribute('data-is-excel', isExcel ? '1' : '0');
      if (!isExcel) {
        selectButton.disabled = true;
      }
      row.appendChild(selectButton);
    }

    costGridBrowserEls.entries.appendChild(row);
  });
}

function renderCostGridBrowser(payload) {
  costGridBrowserState.parent = payload?.parent ? String(payload.parent) : null;
  costGridBrowserState.cwd = payload?.cwd ? String(payload.cwd) : '';
  if (costGridBrowserEls.cwd) {
    const cwdText = costGridBrowserState.cwd || 'Drives';
    costGridBrowserEls.cwd.textContent = cwdText;
  }
  renderCostGridBrowserRoots(payload?.roots);
  renderCostGridBrowserEntries(payload?.entries);
  if (costGridBrowserEls.up) {
    costGridBrowserEls.up.disabled = !costGridBrowserState.parent;
  }
}

async function loadCostGridBrowser(targetPath) {
  if (!costGridBrowserEls.overlay) return;
  const requestId = ++costGridBrowserRequestId;
  setCostGridBrowserLoading(true);
  setCostGridBrowserError('');
  try {
    const query = targetPath ? `?path=${encodeURIComponent(targetPath)}` : '';
    const response = await fetch(`/api/cost-sheet/browse${query}`);
    const payload = await response.json().catch(() => ({}));
    if (requestId !== costGridBrowserRequestId) {
      return;
    }
    if (!response.ok) {
      throw new Error(payload?.detail || `HTTP ${response.status}`);
    }
    renderCostGridBrowser(payload || {});
    setCostGridBrowserError('');
  } catch (error) {
    if (requestId !== costGridBrowserRequestId) {
      return;
    }
    const message = error && error.message ? error.message : 'Failed to browse directories.';
    setCostGridBrowserError(message);
  } finally {
    if (requestId === costGridBrowserRequestId) {
      setCostGridBrowserLoading(false);
    }
  }
}

function handleCostGridBrowserKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault();
    closeCostGridBrowser();
  }
}

function openCostGridBrowser(initialPath) {
  if (!costGridBrowserEls.overlay) return;
  costGridBrowserRestoreFocus = document.activeElement;
  costGridBrowserEls.overlay.hidden = false;
  document.body.classList.add('modal-open');
  setCostGridBrowserError('');
  costGridBrowserState.parent = null;
  costGridBrowserState.cwd = '';
  if (costGridBrowserEls.up) {
    costGridBrowserEls.up.disabled = true;
  }
  if (costGridBrowserEls.dialog) {
    costGridBrowserEls.dialog.focus();
  }
  document.addEventListener('keydown', handleCostGridBrowserKeydown, true);
  const target = initialPath && typeof initialPath === 'string' && initialPath.trim() ? initialPath.trim() : '';
  loadCostGridBrowser(target);
}

function closeCostGridBrowser() {
  if (!costGridBrowserEls.overlay) return;
  costGridBrowserEls.overlay.hidden = true;
  document.body.classList.remove('modal-open');
  document.removeEventListener('keydown', handleCostGridBrowserKeydown, true);
  setCostGridBrowserError('');
  setCostGridBrowserLoading(false);
  costGridBrowserRequestId += 1;
  if (costGridBrowserRestoreFocus && typeof costGridBrowserRestoreFocus.focus === 'function') {
    costGridBrowserRestoreFocus.focus();
  }
  costGridBrowserRestoreFocus = null;
}

function selectCostGridBrowserPath(path) {
  if (!path || !costGridEls.pathInput) {
    closeCostGridBrowser();
    return;
  }
  costGridEls.pathInput.value = path;
  costGridEls.pathInput.dispatchEvent(new Event('input', { bubbles: true }));
  costGridBrowserRestoreFocus = costGridEls.pathInput;
  closeCostGridBrowser();
  setCostGridStatus('Workbook path selected. Save the path to load the Summary grid.', 'info');
}

function handleCostGridBrowserRootClick(event) {
  const button = event.target.closest('button[data-path]');
  if (!button) return;
  event.preventDefault();
  const path = button.getAttribute('data-path');
  if (path) {
    loadCostGridBrowser(path);
  }
}

function handleCostGridBrowserEntryClick(event) {
  const button = event.target.closest('button[data-path]');
  if (!button) return;
  event.preventDefault();
  const path = button.getAttribute('data-path');
  if (!path) {
    return;
  }
  const isDir = button.getAttribute('data-is-dir') === '1';
  const isExcel = button.getAttribute('data-is-excel') === '1';
  const action = button.getAttribute('data-action');
  if (isDir && action === 'enter') {
    loadCostGridBrowser(path);
    return;
  }
  if (!isExcel) {
    setCostGridBrowserError('Select an Excel workbook (.xlsm, .xlsb, .xlsx, .xls).');
    return;
  }
  selectCostGridBrowserPath(path);
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
  costGridState.isConnected = false;
  costGridState.connectPromise = null;
  showCostGridBanner(true);
  setCostGridControlsEnabled(false);
  updateCostGridMeta({});
  clearCostGridTable();
}

async function ensureCostGridConnected({ quiet = false } = {}) {
  if (costGridState.isConnected) {
    return true;
  }

  if (costGridState.connectPromise) {
    return costGridState.connectPromise;
  }

  const pending = (async () => {
    try {
      const response = await fetch('/api/panel3/connect', { method: 'POST' });
      const payload = await response.json().catch(() => ({}));
      if (response.status === 400 && payload?.error === 'COST_SHEET_PATH_MISSING') {
        handleMissingCostGridPath();
        if (!quiet) {
          setCostGridStatus('Set the cost sheet path to connect to Excel.', 'info');
        }
        return false;
      }
      if (!response.ok) {
        throw new Error(payload?.detail || `HTTP ${response.status}`);
      }
      costGridState.isConnected = true;
      return true;
    } catch (error) {
      costGridState.isConnected = false;
      const message = error && error.message ? error.message : 'Failed to connect to Excel.';
      if (!quiet) {
        setCostGridStatus(message, 'error');
      }
      return false;
    } finally {
      costGridState.connectPromise = null;
    }
  })();

  costGridState.connectPromise = pending;
  return pending;
}

async function fetchCostGridSummary({ quiet = false } = {}) {
  if (!costGridEls.tableBody) return;
  const connected = await ensureCostGridConnected({ quiet });
  if (!connected) {
    return;
  }
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
    costGridState.isConnected = false;
    costGridState.connectPromise = null;
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

  const connected = await ensureCostGridConnected({ quiet: false });
  if (!connected) {
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
  if (costGridEls.browseButton) {
    costGridEls.browseButton.addEventListener('click', () => {
      const initial = costGridEls.pathInput && costGridEls.pathInput.value ? costGridEls.pathInput.value.trim() : '';
      openCostGridBrowser(initial);
    });
  }
  if (costGridEls.marginForm) {
    costGridEls.marginForm.addEventListener('submit', submitCostGridMargin);
  }
  if (costGridBrowserEls.reset) {
    costGridBrowserEls.reset.addEventListener('click', () => {
      loadCostGridBrowser('');
    });
  }
  if (costGridBrowserEls.up) {
    costGridBrowserEls.up.addEventListener('click', () => {
      if (costGridBrowserState.parent) {
        loadCostGridBrowser(costGridBrowserState.parent);
      }
    });
  }
  if (costGridBrowserEls.roots) {
    costGridBrowserEls.roots.addEventListener('click', handleCostGridBrowserRootClick);
  }
  if (costGridBrowserEls.entries) {
    costGridBrowserEls.entries.addEventListener('click', handleCostGridBrowserEntryClick);
  }
  if (Array.isArray(costGridBrowserEls.closeControls)) {
    costGridBrowserEls.closeControls.forEach((el) => {
      if (el && typeof el.addEventListener === 'function') {
        el.addEventListener('click', closeCostGridBrowser);
      }
    });
  }
  document.addEventListener('cost-grid:refresh', () => {
    fetchCostGridSummary();
  });
  fetchCostGridSummary();
}

async function fetchJSON(url, opts = {}) {
  const response = await fetch(url, opts);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data && data.error ? data.error : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return data;
}

function getSettingsStatusElement() {
  return document.getElementById('app-settings-cost-grid-status');
}

async function loadCostGridSetting() {
  const input = document.getElementById('cost-grid-path');
  const status = getSettingsStatusElement();
  if (!input || !status) {
    return;
  }
  status.textContent = '';
  try {
    const data = await fetchJSON('/api/settings/cost-grid-path');
    input.value = data.path || '';
  } catch (error) {
    status.textContent = `Unable to load saved path: ${error.message}`;
  }
}

async function testCostGridPath() {
  const input = document.getElementById('cost-grid-path');
  const status = getSettingsStatusElement();
  if (!input || !status) {
    return;
  }
  status.textContent = 'Validating...';
  try {
    const data = await fetchJSON('/api/settings/cost-grid-path?dry_run=1', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: input.value }),
    });
    status.textContent = data.validated ? 'Path OK.' : 'Unknown validation result.';
  } catch (error) {
    status.textContent = `Invalid path: ${error.message}`;
  }
}

async function saveCostGridPath() {
  const input = document.getElementById('cost-grid-path');
  const status = getSettingsStatusElement();
  if (!input || !status) {
    return;
  }
  status.textContent = 'Saving...';
  try {
    const data = await fetchJSON('/api/settings/cost-grid-path', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: input.value }),
    });
    status.textContent = `Saved: ${data.path}`;
  } catch (error) {
    status.textContent = `Save failed: ${error.message}`;
  }
}

async function uploadCostGridFile() {
  const fileInput = document.getElementById('cost-grid-file');
  const status = getSettingsStatusElement();
  if (!fileInput || !status) {
    return;
  }
  if (!fileInput.files || fileInput.files.length === 0) {
    status.textContent = 'Select a file first.';
    return;
  }
  status.textContent = 'Uploading...';
  const form = new FormData();
  form.append('file', fileInput.files[0]);
  try {
    const data = await fetchJSON('/api/settings/cost-grid-upload', {
      method: 'POST',
      body: form,
    });
    const input = document.getElementById('cost-grid-path');
    if (input) {
      input.value = data.path || '';
    }
    status.textContent = `Uploaded and saved: ${data.path}`;
  } catch (error) {
    status.textContent = `Upload failed: ${error.message}`;
  }
}

function initSettingsUI() {
  const testButton = document.getElementById('btn-test-cost-grid');
  const saveButton = document.getElementById('btn-save-cost-grid');
  const uploadButton = document.getElementById('btn-upload-cost-grid');
  if (testButton) {
    testButton.addEventListener('click', testCostGridPath);
  }
  if (saveButton) {
    saveButton.addEventListener('click', saveCostGridPath);
  }
  if (uploadButton) {
    uploadButton.addEventListener('click', uploadCostGridFile);
  }
  loadCostGridSetting();
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
initSettingsUI();
init();
