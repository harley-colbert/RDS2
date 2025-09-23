const CONFIG_ROWS = [
  { label: 'Front USL Guarding', priceKey: 'J18', toggle: 'H18', quantityCell: 'C8' },
  { label: 'Side USL Guarding', priceKey: 'J19', toggle: 'H19', quantityCell: 'C9' },
  { label: 'Side Badger Guarding', priceKey: 'J20', toggle: 'H20', quantityCell: 'C10' },
  { label: 'Tall Guarding', priceKey: 'J32', toggle: 'H32', quantityCell: 'C6' },
  { label: 'Net Guarding', priceKey: 'J33', toggle: 'H33', quantityCell: 'C7' },
  { label: 'Spare Parts Package', priceKey: 'J38', toggle: 'H38', quantityCell: 'C3' },
  { label: 'Spare Saw Blades', priceKey: 'J39', toggle: 'H39', quantityCell: 'C4' },
  { label: 'Spare Foam Pads', priceKey: 'J40', toggle: 'H40', quantityCell: 'C5' },
  { label: 'Canadian Electrical', priceKey: 'J45', toggle: 'H45', quantityCell: 'C11' },
  { label: 'Step Platform', priceKey: 'J46', toggle: 'H46', quantityCell: 'C12' },
  { label: 'Operator Training', priceKey: 'J47', toggle: 'H47', quantityCell: 'C13' },
];

const quoteNumberInput = document.getElementById('quote-number');
const customerInput = document.getElementById('customer-name');
const configTextarea = document.getElementById('config-json');
const configTableBody = document.getElementById('config-table-body');
const baseCostEl = document.getElementById('quote-base-cost');
const marginEl = document.getElementById('quote-margin');
const sellPriceEl = document.getElementById('quote-sell-price');
const layoutPreview = document.getElementById('layout-preview');
const marginDialog = document.getElementById('margin-dialog');
let currentQuote = quoteNumberInput.value || 'Q12345';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
});

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '$0.00';
  }
  return currencyFormatter.format(Number(value));
}

function formatMargin(value) {
  const numeric = Number(value ?? 0);
  return `${(numeric * 100).toFixed(2)}%`;
}

function getQuantity(inputs, cell) {
  const sheet3 = inputs?.Sheet3;
  if (!sheet3) return null;
  if (!(cell in sheet3)) return null;
  return sheet3[cell];
}

async function fetchQuote() {
  const response = await fetch(`/api/quote/${currentQuote}`);
  const data = await response.json();
  renderQuote(data);
}

function renderLayoutPreview(inputs) {
  const layout = inputs?.layout_image || inputs?.layout;
  if (!layout) {
    layoutPreview.innerHTML = '<p class="max-w-[16rem] text-sm">Upload a layout image via the configuration JSON to mirror the proposal workbook.</p>';
    layoutPreview.classList.remove('bg-white');
    layoutPreview.classList.add('bg-slate-50');
    return;
  }

  const image = document.createElement('img');
  image.alt = 'System layout preview';
  image.className = 'max-h-full max-w-full object-contain rounded';

  if (typeof layout === 'string' && layout.startsWith('data:image/')) {
    image.src = layout;
  } else if (typeof layout === 'string') {
    image.src = layout;
  } else {
    layoutPreview.innerHTML = '<p class="text-sm text-slate-500">Unsupported layout format.</p>';
    return;
  }

  layoutPreview.innerHTML = '';
  layoutPreview.classList.add('bg-white');
  layoutPreview.appendChild(image);
}

function renderConfigRows(inputs, summary) {
  const totals = summary?.totals || {};
  const toggles = summary?.toggles || {};
  configTableBody.innerHTML = '';

  CONFIG_ROWS.forEach((row) => {
    const tr = document.createElement('tr');
    tr.className = 'odd:bg-white even:bg-slate-50';

    const descriptionCell = document.createElement('th');
    descriptionCell.scope = 'row';
    descriptionCell.className = 'px-4 py-3 font-medium text-slate-800';
    descriptionCell.textContent = row.label;

    const optionCell = document.createElement('td');
    optionCell.className = 'px-4 py-3 text-slate-700 space-y-1';

    const quantity = getQuantity(inputs, row.quantityCell);
    if (quantity !== null && quantity !== undefined) {
      const quantitySpan = document.createElement('span');
      quantitySpan.className = 'block text-xs uppercase tracking-wide text-slate-500';
      quantitySpan.textContent = `Qty: ${quantity}`;
      optionCell.appendChild(quantitySpan);
    }

    if (row.toggle) {
      const toggleLabel = document.createElement('label');
      toggleLabel.className = 'inline-flex items-center gap-2 text-sm';
      const toggleInput = document.createElement('input');
      toggleInput.type = 'checkbox';
      toggleInput.dataset.cell = row.toggle;
      toggleInput.className = 'toggle-checkbox h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500';
      toggleInput.checked = Boolean(toggles[row.toggle]);
      const toggleText = document.createElement('span');
      toggleText.textContent = toggleInput.checked ? 'Included' : 'Optional';
      toggleLabel.appendChild(toggleInput);
      toggleLabel.appendChild(toggleText);
      optionCell.appendChild(toggleLabel);
    }

    const priceCell = document.createElement('td');
    priceCell.className = 'px-4 py-3 text-right font-mono text-slate-800';
    priceCell.textContent = formatCurrency(totals[row.priceKey]);

    tr.appendChild(descriptionCell);
    tr.appendChild(optionCell);
    tr.appendChild(priceCell);

    configTableBody.appendChild(tr);
  });
}

function renderQuote(data) {
  currentQuote = data.quote_number;
  quoteNumberInput.value = data.quote_number;
  customerInput.value = data.customer || '';
  configTextarea.value = JSON.stringify(data.inputs ?? {}, null, 2);

  const pricing = data.pricing || {};
  const totals = data.summary?.totals || {};

  baseCostEl.textContent = formatCurrency(pricing.base_total ?? totals.base_total);
  sellPriceEl.textContent = formatCurrency(pricing.sell_price ?? totals.sell_price);
  marginEl.textContent = formatMargin(pricing.margin ?? totals.margin ?? 0);
  marginEl.dataset.margin = String(pricing.margin ?? totals.margin ?? 0);

  renderConfigRows(data.inputs || {}, data.summary);
  renderLayoutPreview(data.inputs || {});
}

fetchQuote();

document.getElementById('save-inputs').addEventListener('click', async () => {
  const quoteNumber = quoteNumberInput.value.trim();
  if (!quoteNumber) {
    alert('Quote number is required');
    return;
  }
  currentQuote = quoteNumber;

  const customer = customerInput.value;
  let parsed;
  try {
    parsed = JSON.parse(configTextarea.value || '{}');
  } catch (error) {
    alert('Configuration JSON is invalid');
    return;
  }

  const response = await fetch(`/api/quote/${quoteNumber}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: parsed, customer }),
  });
  const data = await response.json();
  renderQuote(data);
});

document.getElementById('btn-margin').addEventListener('click', () => {
  const currentMargin = parseFloat(marginEl.dataset.margin || '0');
  const marginInput = document.getElementById('margin-input');
  marginInput.value = Number.isNaN(currentMargin) ? '0.2' : currentMargin.toFixed(2);
  marginDialog.showModal();
});

marginDialog.addEventListener('close', async () => {
  if (marginDialog.returnValue !== 'confirm') return;
  const marginValue = parseFloat(document.getElementById('margin-input').value);
  if (Number.isNaN(marginValue)) {
    alert('Enter a valid margin value');
    return;
  }
  await fetch(`/api/quote/${currentQuote}/margin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ margin: marginValue }),
  });
  fetchQuote();
});

document.getElementById('btn-reset-margin').addEventListener('click', async () => {
  await fetch(`/api/quote/${currentQuote}/margin/reset`, { method: 'POST' });
  fetchQuote();
});

configTableBody.addEventListener('change', async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement) || target.type !== 'checkbox') {
    return;
  }
  const cell = target.dataset.cell;
  if (!cell) return;
  await fetch(`/api/quote/${currentQuote}/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cell, value: target.checked ? 1 : 0 }),
  });
  fetchQuote();
});

document.getElementById('btn-generate').addEventListener('click', async () => {
  const response = await fetch(`/api/quote/${currentQuote}/generate`, { method: 'POST' });
  const result = await response.json();
  alert(`Generated files:\nCosting: ${result.costing}\nProposal: ${result.proposal_docx}`);
});
