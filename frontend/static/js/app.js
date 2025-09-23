const tabButtons = document.querySelectorAll('.tab-button');
const tabPanels = document.querySelectorAll('.tab-panel');
let currentQuote = 'Q12345';

function switchTab(tab) {
  tabPanels.forEach((panel) => {
    panel.classList.toggle('hidden', panel.id !== `tab-${tab}`);
  });
  tabButtons.forEach((button) => {
    if (button.dataset.tab === tab) {
      button.classList.add('bg-slate-200');
    } else {
      button.classList.remove('bg-slate-200');
    }
  });
}

tabButtons.forEach((button) => {
  button.addEventListener('click', () => switchTab(button.dataset.tab));
});

switchTab('inputs');

async function fetchQuote() {
  const response = await fetch(`/api/quote/${currentQuote}`);
  const data = await response.json();
  renderQuote(data);
}

function renderQuote(data) {
  document.querySelector('input[name="quote_number"]').value = data.quote_number;
  document.querySelector('input[name="customer"]').value = data.customer || '';
  document.querySelector('textarea[name="data"]').value = JSON.stringify(data.inputs, null, 2);
  const pricing = data.pricing || {};
  document.getElementById('pricing-base').textContent = pricing.base_total?.toFixed?.(2) || pricing.base_total || '0.00';
  document.getElementById('pricing-margin').textContent = pricing.margin?.toFixed?.(2) || pricing.margin || '0.00';
  document.getElementById('pricing-total').textContent = pricing.sell_price?.toFixed?.(2) || pricing.sell_price || '0.00';
  const grid = document.getElementById('costing-grid');
  grid.innerHTML = '';
  const totals = data.summary?.totals || {};
  Object.keys(totals)
    .filter((key) => key.startsWith('J'))
    .sort()
    .forEach((key) => {
      const row = document.createElement('tr');
      row.innerHTML = `<td class="border px-2 py-1">${key}</td><td class="border px-2 py-1 text-right">${Number(totals[key]).toFixed(2)}</td>`;
      grid.appendChild(row);
    });
  const toggleList = document.getElementById('toggle-list');
  toggleList.innerHTML = '';
  const toggles = data.summary?.toggles || {};
  Object.entries(toggles).forEach(([cell, value]) => {
    const li = document.createElement('li');
    li.innerHTML = `
      <label class="flex items-center gap-2">
        <input type="checkbox" data-cell="${cell}" ${value ? 'checked' : ''} />
        <span>${cell}</span>
      </label>`;
    toggleList.appendChild(li);
  });
  document.getElementById('summary-margin').textContent = (totals.margin ?? 0).toFixed(2);
  document.getElementById('summary-sell').textContent = (totals.sell_price ?? 0).toFixed(2);
}

fetchQuote();

document.getElementById('save-inputs').addEventListener('click', async () => {
  const quoteNumber = document.querySelector('input[name="quote_number"]').value;
  currentQuote = quoteNumber;
  const customer = document.querySelector('input[name="customer"]').value;
  let data;
  try {
    data = JSON.parse(document.querySelector('textarea[name="data"]').value || '{}');
  } catch (err) {
    alert('Configuration JSON is invalid');
    return;
  }
  const response = await fetch(`/api/quote/${quoteNumber}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data, customer }),
  });
  renderQuote(await response.json());
});

const marginDialog = document.getElementById('margin-dialog');

document.getElementById('btn-margin').addEventListener('click', () => {
  marginDialog.showModal();
});

marginDialog.addEventListener('close', async () => {
  if (marginDialog.returnValue !== 'confirm') return;
  const marginValue = parseFloat(document.getElementById('margin-input').value);
  if (Number.isNaN(marginValue)) {
    alert('Enter a valid margin value');
    return;
  }
  const response = await fetch(`/api/quote/${currentQuote}/margin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ margin: marginValue }),
  });
  const data = await response.json();
  fetchQuote();
});

document.getElementById('btn-reset-margin').addEventListener('click', async () => {
  await fetch(`/api/quote/${currentQuote}/margin/reset`, { method: 'POST' });
  fetchQuote();
});

document.getElementById('toggle-list').addEventListener('change', async (event) => {
  if (event.target.matches('input[type="checkbox"]')) {
    const cell = event.target.dataset.cell;
    const value = event.target.checked ? 1 : 0;
    await fetch(`/api/quote/${currentQuote}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cell, value }),
    });
    fetchQuote();
  }
});

document.getElementById('btn-generate').addEventListener('click', async () => {
  const response = await fetch(`/api/quote/${currentQuote}/generate`, { method: 'POST' });
  const result = await response.json();
  alert(`Generated files:\nCosting: ${result.costing}\nProposal: ${result.proposal_docx}`);
});
