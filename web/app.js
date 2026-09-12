const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' });
const money = n => currency.format(n);
const text = (tag, value, className = '') => {
  const node = document.createElement(tag);
  node.textContent = value;
  node.className = className;
  return node;
};

let currentInvoices = [];

function renderInvoicesTable() {
  const query = (document.querySelector('#search-input')?.value || '').trim().toLowerCase();
  const body = document.querySelector('#invoices');
  body.replaceChildren();

  const filtered = currentInvoices.filter(r => {
    if (!query) return true;
    return (
      (r.customer_name && r.customer_name.toLowerCase().includes(query)) ||
      (r.customer_id && r.customer_id.toLowerCase().includes(query)) ||
      (r.invoice_number && r.invoice_number.toLowerCase().includes(query))
    );
  });

  if (!filtered.length) {
    const tr = document.createElement('tr');
    const td = text('td', 'No matching invoices found.');
    td.colSpan = 7;
    td.style.textAlign = 'center';
    td.style.color = '#72818a';
    tr.append(td);
    body.append(tr);
    return;
  }

  filtered.forEach(r => {
    const row = document.createElement('tr');
    [r.customer_name, r.invoice_number, r.due_date].forEach(v => row.append(text('td', v)));
    [r.amount, r.paid, r.balance].forEach(v => row.append(text('td', money(v), 'number')));
    const statusTd = document.createElement('td');
    const badge = document.createElement('span');
    if (r.is_overdue) {
      badge.className = 'badge badge-overdue';
      badge.textContent = `Overdue (${r.days_overdue}d)`;
    } else if (r.status === 'open') {
      badge.className = 'badge badge-open';
      badge.textContent = 'Open';
    } else {
      badge.className = 'badge badge-paid';
      badge.textContent = 'Paid';
    }
    statusTd.append(badge);
    row.append(statusTd);
    body.append(row);
  });
}

async function refresh() {
  const status = document.querySelector('#status').value;
  const responses = await Promise.all([fetch('/api/overview'), fetch(`/api/invoices?status=${status}`)]);
  if (responses.some(r => !r.ok)) throw new Error('Could not refresh the register.');
  const [data, rows] = await Promise.all(responses.map(r => r.json()));

  document.querySelector('#invoice-count').textContent = data.summary.invoice_count;
  document.querySelector('#open-count').textContent = data.summary.open_count;
  document.querySelector('#outstanding').textContent = money(data.summary.outstanding);
  const overdueEl = document.querySelector('#overdue-metric');
  if (overdueEl) {
    overdueEl.textContent = `${data.summary.overdue_count} (${money(data.summary.overdue_amount)})`;
  }

  // Render customer breakdown
  const custBody = document.querySelector('#customers-body');
  if (custBody && data.customers) {
    custBody.replaceChildren();
    data.customers.forEach(c => {
      const tr = document.createElement('tr');
      tr.append(text('td', c.customer_id));
      tr.append(text('td', c.name));
      tr.append(text('td', money(c.total_invoiced), 'number'));
      tr.append(text('td', money(c.total_paid), 'number'));
      tr.append(text('td', money(c.outstanding), 'number'));
      tr.append(text('td', String(c.open_count), 'number'));
      custBody.append(tr);
    });
  }

  currentInvoices = rows;
  renderInvoicesTable();

  const unmatched = document.querySelector('#unmatched');
  unmatched.replaceChildren(...data.unmatched_payments.map(p => text('li', `${p.payment_id} · ${p.customer_id} / ${p.invoice_number} · ${money(p.amount)}`)));
  if (!data.unmatched_payments.length) unmatched.append(text('li', 'No unmatched payments.'));
  document.querySelector('#page-error').textContent = '';
}

async function submitImport(form) {
  const feedback = form.querySelector('.feedback');
  const button = form.querySelector('button');
  const fileInput = form.querySelector('input');
  if (!fileInput.files || !fileInput.files[0]) {
    feedback.textContent = 'Please select a CSV file first.';
    return;
  }
  button.disabled = true;
  feedback.textContent = 'Importing…';
  try {
    const csv = await fileInput.files[0].text();
    const response = await fetch(`/api/import?kind=${form.dataset.kind}`, {
      method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: csv
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      feedback.textContent = `Import failed: ${result.error || response.statusText || 'Unknown error'}`;
      return;
    }
    let msg = `Import complete: ${result.imported} imported, ${result.skipped} skipped, ${result.rejected} rejected.`;
    if (result.errors && result.errors.length > 0) {
      const errDetails = result.errors.map(e => `Line ${e.line}: ${e.reason}`).join('; ');
      msg += ` Errors: ${errDetails}`;
    }
    feedback.textContent = msg;
    await refresh();
  } catch (error) {
    feedback.textContent = `Import failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

document.querySelector('#status').addEventListener('change', () => refresh().catch(e => { document.querySelector('#page-error').textContent = e.message; }));
document.querySelector('#search-input')?.addEventListener('input', renderInvoicesTable);
document.querySelector('#btn-rematch')?.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/rematch', { method: 'POST' });
    const data = await res.json();
    alert(`Re-check complete: ${data.rematched} payment(s) successfully linked to newly available invoices.`);
    await refresh();
  } catch (e) {
    alert(`Re-check failed: ${e.message}`);
  }
});
document.querySelectorAll('form[data-kind]').forEach(form => form.addEventListener('submit', e => { e.preventDefault(); submitImport(form); }));
refresh().catch(e => { document.querySelector('#page-error').textContent = e.message; });
