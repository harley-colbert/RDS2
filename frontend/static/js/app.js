const CONFIG_ROWS = [
  { label: 'Infeed Orientation', priceKey: 'J18', defaultOption: 'Centered' },
  { label: 'Spare Parts Package', priceKey: 'J38', quantityCell: 'C3' },
  { label: 'Spare Saw Blades', priceKey: 'J39', quantityCell: 'C4' },
  { label: 'Spare Foam Pads', priceKey: 'J40', quantityCell: 'C5' },
  { label: 'Guarding', priceKey: 'J32', defaultOption: 'Standard' },
  { label: 'Feeding USL/Badger', priceKey: 'J19', defaultOption: 'Included' },
  { label: 'Training', priceKey: 'J47', defaultOption: 'English' },
];

const quoteNumberInput = document.getElementById('quote-number');
const customerInput = document.getElementById('customer-name');
const configTextarea = document.getElementById('config-json');
const configTableBody = document.getElementById('config-table-body');
const baseCostEl = document.getElementById('quote-base-cost');
const marginEl = document.getElementById('quote-margin');
const sellPriceEl = document.getElementById('quote-sell-price');
const optionsEl = document.getElementById('quote-options');
const marginDialog = document.getElementById('margin-dialog');
let currentQuote = quoteNumberInput?.value || 'Q12345';

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
  if (!cell) return null;
  const sheet3 = inputs?.Sheet3;
  if (!sheet3) return null;
  if (!(cell in sheet3)) return null;
  const quantity = sheet3[cell];
  if (quantity === null || quantity === undefined) return null;
  return quantity;
}

function optionDisplayValue(row, inputs, summary) {
  const quantity = getQuantity(inputs, row.quantityCell);
  if (quantity !== null && quantity !== undefined) {
    return String(quantity);
  }

  if (typeof row.getValue === 'function') {
    return row.getValue(inputs, summary);
  }

  return row.defaultOption ?? '';
}

async function fetchQuote() {
  const response = await fetch(`/api/quote/${currentQuote}`);
  const data = await response.json();
  renderQuote(data);
}

function computeOptionsTotal(totals) {
  const base = Number(totals?.base_total ?? 0);
  const sell = Number(totals?.sell_price ?? 0);
  if (!Number.isNaN(base) && !Number.isNaN(sell) && sell >= base) {
    return sell - base;
  }

  return CONFIG_ROWS.reduce((sum, row) => sum + Number(totals?.[row.priceKey] ?? 0), 0);
}

function renderConfigRows(inputs, summary) {
  const totals = summary?.totals || {};
  configTableBody.innerHTML = '';

  CONFIG_ROWS.forEach((row) => {
    const tr = document.createElement('tr');

    const descriptionCell = document.createElement('th');
    descriptionCell.scope = 'row';
    descriptionCell.textContent = row.label;

    const optionCell = document.createElement('td');
    optionCell.className = 'option-cell';
    optionCell.textContent = optionDisplayValue(row, inputs, summary);

    const priceCell = document.createElement('td');
    priceCell.className = 'price-cell';
    priceCell.textContent = formatCurrency(totals[row.priceKey]);

    tr.appendChild(descriptionCell);
    tr.appendChild(optionCell);
    tr.appendChild(priceCell);

    configTableBody.appendChild(tr);
  });
}

function renderQuote(data) {
  currentQuote = data.quote_number;
  if (quoteNumberInput) quoteNumberInput.value = data.quote_number;
  if (customerInput) customerInput.value = data.customer || '';
  if (configTextarea) configTextarea.value = JSON.stringify(data.inputs ?? {}, null, 2);

  const pricing = data.pricing || {};
  const totals = data.summary?.totals || {};

  baseCostEl.textContent = formatCurrency(pricing.base_total ?? totals.base_total);
  sellPriceEl.textContent = formatCurrency(pricing.sell_price ?? totals.sell_price);
  marginEl.textContent = formatMargin(pricing.margin ?? totals.margin ?? 0);
  marginEl.dataset.margin = String(pricing.margin ?? totals.margin ?? 0);

  const optionTotal = computeOptionsTotal({
    base_total: pricing.base_total ?? totals.base_total,
    sell_price: pricing.sell_price ?? totals.sell_price,
    ...totals,
  });
  optionsEl.textContent = formatCurrency(optionTotal);

  renderConfigRows(data.inputs || {}, data.summary);
}

if (quoteNumberInput) {
  fetchQuote();
}

document.getElementById('btn-margin').addEventListener('click', () => {
  const currentMargin = parseFloat(marginEl.dataset.margin || '0');
  const marginInput = document.getElementById('margin-input');
  if (marginInput) {
    marginInput.value = Number.isNaN(currentMargin) ? '0.20' : currentMargin.toFixed(2);
  }
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

document.getElementById('btn-generate-quote').addEventListener('click', async () => {
  const response = await fetch(`/api/quote/${currentQuote}/generate`, { method: 'POST' });
  const result = await response.json();
  alert(`Generated quote files:\nCosting Workbook: ${result.costing}\nProposal Document: ${result.proposal_docx}`);
});

document.getElementById('btn-generate-layout').addEventListener('click', async () => {
  const response = await fetch(`/api/quote/${currentQuote}/generate`, { method: 'POST' });
  const result = await response.json();
  alert(`Layout export ready at:\n${result.proposal_pdf}`);
});

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
