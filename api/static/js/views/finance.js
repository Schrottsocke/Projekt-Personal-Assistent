/**
 * Finance View – Übersicht, Transaktionen, Verträge, Budgets, Rechnungen
 */
const FinanceView = (() => {
  let currentTab = 'overview';

  // ── Helpers ──────────────────────────────────────────────────────────────

  function esc(str) {
    return String(str || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
  }

  function currency(n) {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n || 0);
  }

  function fmtDate(iso) {
    if (!iso) return '–';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function fmtDateShort(iso) {
    if (!iso) return '–';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: 'short' });
  }

  function today() {
    return new Date().toISOString().slice(0, 10);
  }

  function currentYearMonth() {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  }

  // ── Render Entry ─────────────────────────────────────────────────────────

  async function render(container) {
    container.innerHTML = `
      <a class="view-back" href="#/mehr">
        <span class="material-symbols-outlined mi-sm">arrow_back</span> Mehr
      </a>
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">account_balance_wallet</span>
        Finanzen
      </div>
      <div class="tabs" id="finance-tabs">
        <button class="tab ${currentTab === 'overview'      ? 'active' : ''}" onclick="FinanceView.switchTab('overview')">Übersicht</button>
        <button class="tab ${currentTab === 'transactions'  ? 'active' : ''}" onclick="FinanceView.switchTab('transactions')">Transaktionen</button>
        <button class="tab ${currentTab === 'contracts'     ? 'active' : ''}" onclick="FinanceView.switchTab('contracts')">Verträge</button>
        <button class="tab ${currentTab === 'budgets'       ? 'active' : ''}" onclick="FinanceView.switchTab('budgets')">Budgets</button>
        <button class="tab ${currentTab === 'invoices'      ? 'active' : ''}" onclick="FinanceView.switchTab('invoices')">Rechnungen</button>
      </div>
      <div id="finance-content">
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
      </div>
    `;
    await loadTab(currentTab);
  }

  function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('#finance-tabs .tab').forEach(btn => {
      btn.classList.toggle('active', btn.textContent.trim() === tabLabel(tab));
    });
    const content = document.getElementById('finance-content');
    content.innerHTML = '<div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div>';
    loadTab(tab);
  }

  function tabLabel(tab) {
    const labels = { overview: 'Übersicht', transactions: 'Transaktionen', contracts: 'Verträge', budgets: 'Budgets', invoices: 'Rechnungen' };
    return labels[tab] || tab;
  }

  async function loadTab(tab) {
    if (tab === 'overview')     return loadOverview();
    if (tab === 'transactions') return loadTransactions();
    if (tab === 'contracts')    return loadContracts();
    if (tab === 'budgets')      return loadBudgets();
    if (tab === 'invoices')     return loadInvoices();
  }

  // ── Tab: Übersicht ───────────────────────────────────────────────────────

  async function loadOverview() {
    const content = document.getElementById('finance-content');
    try {
      const { year, month } = currentYearMonth();
      const [summary, monthly, byCategory] = await Promise.all([
        Api.get('/finance/widget-summary'),
        Api.get(`/finance/transactions/monthly-overview?year=${year}&month=${month}`),
        Api.get(`/finance/transactions/by-category?year=${year}&month=${month}`)
      ]);
      renderOverview(content, summary, monthly, byCategory);
    } catch (err) {
      content.innerHTML = errorState(err, "FinanceView.switchTab('overview')");
    }
  }

  function renderOverview(el, summary, monthly, byCategory) {
    const nextPayment = summary.next_payment_date
      ? `${fmtDate(summary.next_payment_date)} · ${currency(summary.next_payment_amount)}`
      : '–';

    const budgetUsed = summary.budget_total > 0
      ? Math.round((summary.spending_this_month / summary.budget_total) * 100)
      : 0;

    const categoryRows = byCategory.categories && Object.keys(byCategory.categories).length > 0
      ? Object.entries(byCategory.categories)
          .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
          .map(([cat, amount]) => `
            <div class="finance-cat-row">
              <span class="finance-cat-name">${esc(cat)}</span>
              <span class="finance-cat-amount">${currency(amount)}</span>
            </div>
          `).join('')
      : '<p class="text-muted" style="font-size:0.85rem">Keine Kategoriedaten</p>';

    el.innerHTML = `
      <div class="finance-widget-grid">
        <div class="card finance-widget">
          <div class="finance-widget-label">
            <span class="material-symbols-outlined mi-sm">shopping_cart</span> Ausgaben diesen Monat
          </div>
          <div class="finance-widget-value">${currency(summary.spending_this_month)}</div>
          ${summary.budget_total > 0 ? `
            <div class="finance-progress-bar">
              <div class="finance-progress-fill ${budgetUsed > 100 ? 'finance-progress-over' : ''}"
                   style="width:${Math.min(budgetUsed, 100)}%"></div>
            </div>
            <div class="finance-widget-sub">Budget: ${currency(summary.budget_total)} (${budgetUsed}%)</div>
          ` : ''}
        </div>

        <div class="card finance-widget">
          <div class="finance-widget-label">
            <span class="material-symbols-outlined mi-sm">event_repeat</span> Nächste Zahlung
          </div>
          <div class="finance-widget-value" style="font-size:1rem">${esc(nextPayment)}</div>
        </div>

        <div class="card finance-widget">
          <div class="finance-widget-label">
            <span class="material-symbols-outlined mi-sm">receipt_long</span> Offene Rechnungen
          </div>
          <div class="finance-widget-value">${summary.open_invoices_count ?? 0}</div>
        </div>
      </div>

      <div class="card" style="margin-top:16px">
        <div class="finance-section-title">
          <span class="material-symbols-outlined mi-sm">bar_chart</span>
          Monatsübersicht – ${monthName(monthly.month)} ${monthly.year}
        </div>
        <div class="finance-monthly-row">
          <div class="finance-monthly-item">
            <div class="finance-monthly-label">Einnahmen</div>
            <div class="finance-monthly-value finance-income">${currency(monthly.total_income)}</div>
          </div>
          <div class="finance-monthly-item">
            <div class="finance-monthly-label">Ausgaben</div>
            <div class="finance-monthly-value finance-expense">${currency(monthly.total_expenses)}</div>
          </div>
          <div class="finance-monthly-item">
            <div class="finance-monthly-label">Saldo</div>
            <div class="finance-monthly-value ${(monthly.total_income - monthly.total_expenses) >= 0 ? 'finance-income' : 'finance-expense'}">
              ${currency(monthly.total_income - monthly.total_expenses)}
            </div>
          </div>
        </div>
      </div>

      <div class="card" style="margin-top:16px">
        <div class="finance-section-title">
          <span class="material-symbols-outlined mi-sm">category</span>
          Nach Kategorie
        </div>
        <div class="finance-cat-list">${categoryRows}</div>
      </div>
    `;
  }

  function monthName(m) {
    const names = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
    return names[(m - 1)] || m;
  }

  // ── Tab: Transaktionen ───────────────────────────────────────────────────

  let transactions = [];
  let txCategoryFilter = '';
  let showTxForm = false;

  async function loadTransactions() {
    const content = document.getElementById('finance-content');
    try {
      const url = txCategoryFilter ? `/finance/transactions?category=${encodeURIComponent(txCategoryFilter)}` : '/finance/transactions';
      transactions = await Api.get(url);
      renderTransactions(content);
    } catch (err) {
      content.innerHTML = errorState(err, "FinanceView.switchTab('transactions')");
    }
  }

  function renderTransactions(el) {
    const listHtml = transactions.length === 0
      ? `<div class="empty-state">
           <span class="material-symbols-outlined">receipt</span>
           <p>Keine Transaktionen gefunden</p>
         </div>`
      : transactions.map(tx => `
          <div class="card finance-tx-card">
            <div class="finance-tx-row">
              <div class="finance-tx-left">
                <div class="finance-tx-desc">${esc(tx.description || '–')}</div>
                <div class="finance-tx-meta">${fmtDate(tx.date)} · <span class="badge badge-muted">${esc(tx.category || '–')}</span></div>
                ${tx.source ? `<div class="finance-tx-source text-muted" style="font-size:0.75rem">${esc(tx.source)}</div>` : ''}
              </div>
              <div class="finance-tx-amount ${tx.amount >= 0 ? 'finance-income' : 'finance-expense'}">
                ${currency(tx.amount)}
              </div>
            </div>
            <div class="finance-tx-actions">
              <button class="btn btn-sm btn-danger" onclick="FinanceView.deleteTx('${esc(tx.id)}')">
                <span class="material-symbols-outlined mi-sm">delete</span>
              </button>
            </div>
          </div>
        `).join('');

    el.innerHTML = `
      <div class="finance-toolbar">
        <div class="form-row" style="margin-bottom:8px">
          <input class="input" id="tx-cat-filter" placeholder="Kategorie filtern…" value="${esc(txCategoryFilter)}"
                 onkeydown="if(event.key==='Enter') FinanceView.applyTxFilter()">
          <button class="btn btn-secondary btn-sm" onclick="FinanceView.applyTxFilter()">Filter</button>
          ${txCategoryFilter ? `<button class="btn btn-secondary btn-sm" onclick="FinanceView.clearTxFilter()">✕</button>` : ''}
        </div>
        <div class="finance-toolbar-actions">
          <button class="btn btn-primary btn-sm" onclick="FinanceView.toggleTxForm()">
            <span class="material-symbols-outlined mi-sm">add</span> Transaktion
          </button>
          <button class="btn btn-secondary btn-sm" onclick="FinanceView.openCsvUpload()">
            <span class="material-symbols-outlined mi-sm">upload_file</span> CSV
          </button>
        </div>
      </div>

      <div id="tx-form-area"></div>
      <input type="file" id="tx-csv-input" accept=".csv" style="display:none" onchange="FinanceView.uploadCsv(this)">

      ${showTxForm ? renderTxForm() : ''}
      <div id="tx-list">${listHtml}</div>
    `;

    if (showTxForm) {
      document.getElementById('tx-form-new')?.addEventListener('submit', submitTxForm);
    }
  }

  function renderTxForm() {
    return `
      <div class="card" style="margin-bottom:12px" id="tx-form-area">
        <div class="finance-section-title">Transaktion erfassen</div>
        <form id="tx-form-new">
          <div class="form-row">
            <div class="form-group">
              <label>Datum</label>
              <input class="input" type="date" name="date" value="${today()}" required>
            </div>
            <div class="form-group">
              <label>Betrag (€)</label>
              <input class="input" type="number" name="amount" step="0.01" placeholder="–12.50" required>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Kategorie</label>
              <input class="input" type="text" name="category" placeholder="z.B. Lebensmittel">
            </div>
            <div class="form-group">
              <label>Quelle</label>
              <input class="input" type="text" name="source" placeholder="z.B. DKB">
            </div>
          </div>
          <div class="form-group">
            <label>Beschreibung</label>
            <input class="input" type="text" name="description" placeholder="Buchungstext" required>
          </div>
          <div class="form-row" style="justify-content:flex-end;gap:8px">
            <button type="button" class="btn btn-secondary" onclick="FinanceView.toggleTxForm()">Abbrechen</button>
            <button type="submit" class="btn btn-primary">Speichern</button>
          </div>
        </form>
      </div>
    `;
  }

  async function submitTxForm(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = {
      date: fd.get('date'),
      amount: parseFloat(fd.get('amount')),
      currency: 'EUR',
      category: fd.get('category') || '',
      description: fd.get('description'),
      source: fd.get('source') || ''
    };
    try {
      await Api.post('/finance/transactions', payload);
      Toast.show('Transaktion gespeichert', 'success');
      showTxForm = false;
      txCategoryFilter = '';
      await loadTransactions();
    } catch (err) {
      Toast.show('Fehler beim Speichern: ' + err.message, 'error');
    }
  }

  function toggleTxForm() {
    showTxForm = !showTxForm;
    const content = document.getElementById('finance-content');
    if (content) renderTransactions(content);
    if (showTxForm) {
      document.getElementById('tx-form-new')?.addEventListener('submit', submitTxForm);
    }
  }

  function applyTxFilter() {
    const val = document.getElementById('tx-cat-filter')?.value.trim() || '';
    txCategoryFilter = val;
    loadTransactions();
  }

  function clearTxFilter() {
    txCategoryFilter = '';
    loadTransactions();
  }

  function openCsvUpload() {
    document.getElementById('tx-csv-input')?.click();
  }

  async function uploadCsv(input) {
    if (!input.files || !input.files[0]) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);
    try {
      const result = await Api.post('/finance/transactions/csv?skip_duplicates=true', formData, { rawBody: true });
      Toast.show(`CSV importiert: ${result.imported} neu, ${result.skipped_duplicates} Duplikate übersprungen`, 'success');
      input.value = '';
      await loadTransactions();
    } catch (err) {
      Toast.show('CSV-Import fehlgeschlagen: ' + err.message, 'error');
      input.value = '';
    }
  }

  async function deleteTx(id) {
    if (!confirm('Transaktion wirklich löschen?')) return;
    try {
      await Api.delete(`/finance/transactions/${id}`);
      Toast.show('Transaktion gelöscht', 'success');
      await loadTransactions();
    } catch (err) {
      Toast.show('Fehler beim Löschen: ' + err.message, 'error');
    }
  }

  // ── Tab: Verträge ────────────────────────────────────────────────────────

  let contracts = [];
  let contractSummary = null;
  let expiringContracts = [];
  let contractSheet = null; // null | 'new' | contract-object

  async function loadContracts() {
    const content = document.getElementById('finance-content');
    try {
      const [list, summary, expiring] = await Promise.all([
        Api.get('/finance/contracts'),
        Api.get('/finance/contracts/summary'),
        Api.get('/finance/contracts/expiring?days=30')
      ]);
      contracts = list;
      contractSummary = summary;
      expiringContracts = expiring;
      renderContracts(content);
    } catch (err) {
      content.innerHTML = errorState(err, "FinanceView.switchTab('contracts')");
    }
  }

  function renderContracts(el) {
    const summaryHtml = contractSummary ? `
      <div class="card finance-summary-banner">
        <div class="finance-summary-item">
          <span class="finance-summary-label">Monatliche Kosten</span>
          <span class="finance-summary-value">${currency(contractSummary.total_monthly_cost)}</span>
        </div>
        <div class="finance-summary-item">
          <span class="finance-summary-label">Aktive Verträge</span>
          <span class="finance-summary-value">${contractSummary.active_count ?? 0}</span>
        </div>
        ${contractSummary.expiring_soon > 0 ? `
          <div class="finance-summary-item">
            <span class="finance-summary-label">Bald auslaufend</span>
            <span class="finance-summary-value finance-expense">${contractSummary.expiring_soon}</span>
          </div>
        ` : ''}
      </div>
    ` : '';

    const expiringAlert = expiringContracts.length > 0 ? `
      <div class="card finance-alert-banner" style="border-left:3px solid var(--warning)">
        <span class="material-symbols-outlined mi-sm" style="color:var(--warning)">warning</span>
        <strong>${expiringContracts.length} Vertrag${expiringContracts.length > 1 ? 'e' : ''} läuft bald aus</strong>
      </div>
    ` : '';

    const listHtml = contracts.length === 0
      ? `<div class="empty-state">
           <span class="material-symbols-outlined">description</span>
           <p>Keine Verträge hinterlegt</p>
         </div>`
      : contracts.map(c => renderContractCard(c)).join('');

    const sheetHtml = contractSheet !== null ? renderContractSheet() : '';

    el.innerHTML = `
      ${summaryHtml}
      ${expiringAlert}
      <div class="finance-toolbar">
        <button class="btn btn-primary btn-sm" onclick="FinanceView.openContractSheet(null)">
          <span class="material-symbols-outlined mi-sm">add</span> Vertrag
        </button>
        <button class="btn btn-secondary btn-sm" onclick="FinanceView.detectContracts()">
          <span class="material-symbols-outlined mi-sm">auto_awesome</span> Erkennung
        </button>
      </div>
      ${listHtml}
      ${sheetHtml}
    `;
  }

  function renderContractCard(c) {
    const interval = { monthly: 'Monatlich', yearly: 'Jährlich', weekly: 'Wöchentlich', quarterly: 'Quartalsweise' };
    const isExpiring = expiringContracts.some(e => e.id === c.id);
    const expBadge = isExpiring
      ? `<span class="badge badge-warning">Läuft aus</span>`
      : '';

    return `
      <div class="card finance-contract-card">
        <div class="finance-tx-row">
          <div class="finance-tx-left">
            <div class="finance-tx-desc">${esc(c.name)}</div>
            <div class="finance-tx-meta">
              ${esc(c.provider || '–')} · <span class="badge badge-muted">${esc(c.category || '–')}</span>
              ${expBadge}
            </div>
            <div class="finance-tx-meta">${interval[c.interval] || esc(c.interval || '–')} · Start: ${fmtDate(c.start_date)}</div>
            ${c.end_date ? `<div class="finance-tx-meta text-muted">Ende: ${fmtDate(c.end_date)}</div>` : ''}
          </div>
          <div class="finance-tx-amount finance-expense">${currency(c.amount)}</div>
        </div>
        <div class="finance-tx-actions">
          <button class="btn btn-sm btn-secondary" onclick="FinanceView.openContractSheet(${JSON.stringify(c).replace(/"/g, '&quot;')})">
            <span class="material-symbols-outlined mi-sm">edit</span>
          </button>
          <button class="btn btn-sm btn-danger" onclick="FinanceView.deleteContract('${esc(c.id)}')">
            <span class="material-symbols-outlined mi-sm">delete</span>
          </button>
        </div>
      </div>
    `;
  }

  function renderContractSheet() {
    const c = contractSheet === 'new' ? null : contractSheet;
    const title = c ? 'Vertrag bearbeiten' : 'Neuer Vertrag';
    return `
      <div class="finance-sheet-backdrop" onclick="FinanceView.closeContractSheet()"></div>
      <div class="finance-bottom-sheet">
        <div class="finance-sheet-handle"></div>
        <div class="finance-section-title">${title}</div>
        <form id="contract-form" onsubmit="FinanceView.submitContractForm(event)">
          <div class="form-row">
            <div class="form-group">
              <label>Name *</label>
              <input class="input" type="text" name="name" value="${esc(c?.name || '')}" required>
            </div>
            <div class="form-group">
              <label>Anbieter</label>
              <input class="input" type="text" name="provider" value="${esc(c?.provider || '')}">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Betrag (€) *</label>
              <input class="input" type="number" name="amount" step="0.01" value="${esc(c?.amount ?? '')}" required>
            </div>
            <div class="form-group">
              <label>Intervall *</label>
              <select class="input" name="interval" required>
                ${['monthly','quarterly','yearly','weekly'].map(v =>
                  `<option value="${v}" ${c?.interval === v ? 'selected' : ''}>${{ monthly:'Monatlich', quarterly:'Quartalsweise', yearly:'Jährlich', weekly:'Wöchentlich' }[v]}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Startdatum *</label>
              <input class="input" type="date" name="start_date" value="${esc(c?.start_date || today())}" required>
            </div>
            <div class="form-group">
              <label>Enddatum</label>
              <input class="input" type="date" name="end_date" value="${esc(c?.end_date || '')}">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Kategorie</label>
              <input class="input" type="text" name="category" value="${esc(c?.category || '')}">
            </div>
            <div class="form-group">
              <label>Kündigungsfrist (Tage)</label>
              <input class="input" type="number" name="cancellation_days" value="${esc(c?.cancellation_days ?? '')}">
            </div>
          </div>
          <div class="form-group">
            <label>Notizen</label>
            <input class="input" type="text" name="notes" value="${esc(c?.notes || '')}">
          </div>
          ${c ? `<input type="hidden" name="_id" value="${esc(c.id)}">` : ''}
          <div class="form-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
            <button type="button" class="btn btn-secondary" onclick="FinanceView.closeContractSheet()">Abbrechen</button>
            <button type="submit" class="btn btn-primary">Speichern</button>
          </div>
        </form>
      </div>
    `;
  }

  function openContractSheet(c) {
    contractSheet = c || 'new';
    const content = document.getElementById('finance-content');
    if (content) renderContracts(content);
  }

  function closeContractSheet() {
    contractSheet = null;
    const content = document.getElementById('finance-content');
    if (content) renderContracts(content);
  }

  async function submitContractForm(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const id = fd.get('_id');
    const payload = {
      name: fd.get('name'),
      amount: parseFloat(fd.get('amount')),
      interval: fd.get('interval'),
      start_date: fd.get('start_date'),
      provider: fd.get('provider') || '',
      category: fd.get('category') || '',
      end_date: fd.get('end_date') || null,
      cancellation_days: fd.get('cancellation_days') ? parseInt(fd.get('cancellation_days')) : null,
      notes: fd.get('notes') || ''
    };
    try {
      if (id) {
        await Api.patch(`/finance/contracts/${id}`, payload);
        Toast.show('Vertrag aktualisiert', 'success');
      } else {
        await Api.post('/finance/contracts', payload);
        Toast.show('Vertrag gespeichert', 'success');
      }
      contractSheet = null;
      await loadContracts();
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function deleteContract(id) {
    if (!confirm('Vertrag wirklich löschen?')) return;
    try {
      await Api.delete(`/finance/contracts/${id}`);
      Toast.show('Vertrag gelöscht', 'success');
      await loadContracts();
    } catch (err) {
      Toast.show('Fehler beim Löschen: ' + err.message, 'error');
    }
  }

  async function detectContracts() {
    try {
      const result = await Api.get('/finance/contracts/detect-from-transactions?min_occurrences=3');
      const detected = Array.isArray(result) ? result : (result.contracts || []);
      if (detected.length === 0) {
        Toast.show('Keine neuen Verträge erkannt', 'info');
      } else {
        Toast.show(`${detected.length} potenzielle Vertrag${detected.length > 1 ? 'e' : ''} erkannt`, 'success');
        await loadContracts();
      }
    } catch (err) {
      Toast.show('Erkennung fehlgeschlagen: ' + err.message, 'error');
    }
  }

  // ── Tab: Budgets ─────────────────────────────────────────────────────────

  let budgets = [];
  let budgetAlerts = [];
  let showBudgetForm = false;

  async function loadBudgets() {
    const content = document.getElementById('finance-content');
    try {
      const [list, alerts] = await Promise.all([
        Api.get('/finance/budgets'),
        Api.get('/finance/budgets/alerts')
      ]);
      budgets = list;
      budgetAlerts = alerts;
      renderBudgets(content);
    } catch (err) {
      content.innerHTML = errorState(err, "FinanceView.switchTab('budgets')");
    }
  }

  function renderBudgets(el) {
    const overBudget = budgetAlerts.filter(a => a.over_limit);
    const alertBanner = overBudget.length > 0 ? `
      <div class="card finance-alert-banner" style="border-left:3px solid var(--error)">
        <span class="material-symbols-outlined mi-sm" style="color:var(--error)">error</span>
        <strong>${overBudget.length} Budget${overBudget.length > 1 ? 's' : ''} überschritten:</strong>
        ${overBudget.map(a => esc(a.category)).join(', ')}
      </div>
    ` : '';

    // Build an alert map for quick lookup
    const alertMap = {};
    budgetAlerts.forEach(a => { alertMap[a.category] = a; });

    const budgetCards = budgets.length === 0
      ? `<div class="empty-state">
           <span class="material-symbols-outlined">pie_chart</span>
           <p>Keine Budgets definiert</p>
         </div>`
      : budgets.map(b => {
          const alert = alertMap[b.category];
          const pct = alert ? Math.round(alert.percentage) : 0;
          const spent = alert ? alert.spent : 0;
          const over = alert ? alert.over_limit : false;
          return `
            <div class="card finance-budget-card">
              <div class="finance-tx-row">
                <div class="finance-tx-left">
                  <div class="finance-tx-desc">${esc(b.category)}</div>
                  <div class="finance-tx-meta">Limit: ${currency(b.monthly_limit)} · Alarm ab ${b.alert_threshold}%</div>
                </div>
                <div class="finance-tx-amount ${over ? 'finance-expense' : ''}">
                  ${currency(spent)} / ${currency(b.monthly_limit)}
                </div>
              </div>
              <div class="finance-progress-bar" style="margin-top:8px">
                <div class="finance-progress-fill ${over ? 'finance-progress-over' : ''}"
                     style="width:${Math.min(pct, 100)}%"></div>
              </div>
              <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">${pct}% genutzt</div>
              <div class="finance-tx-actions">
                <button class="btn btn-sm btn-danger" onclick="FinanceView.deleteBudget('${esc(b.id)}')">
                  <span class="material-symbols-outlined mi-sm">delete</span>
                </button>
              </div>
            </div>
          `;
        }).join('');

    el.innerHTML = `
      ${alertBanner}
      <div class="finance-toolbar">
        <button class="btn btn-primary btn-sm" onclick="FinanceView.toggleBudgetForm()">
          <span class="material-symbols-outlined mi-sm">add</span> Budget
        </button>
      </div>
      ${showBudgetForm ? renderBudgetForm() : ''}
      ${budgetCards}
    `;

    if (showBudgetForm) {
      document.getElementById('budget-form-new')?.addEventListener('submit', submitBudgetForm);
    }
  }

  function renderBudgetForm() {
    return `
      <div class="card" style="margin-bottom:12px">
        <div class="finance-section-title">Neues Budget</div>
        <form id="budget-form-new">
          <div class="form-row">
            <div class="form-group">
              <label>Kategorie *</label>
              <input class="input" type="text" name="category" placeholder="z.B. Lebensmittel" required>
            </div>
            <div class="form-group">
              <label>Monatliches Limit (€) *</label>
              <input class="input" type="number" name="monthly_limit" step="0.01" required>
            </div>
          </div>
          <div class="form-group">
            <label>Alarmschwelle (%)</label>
            <input class="input" type="number" name="alert_threshold" value="80" min="1" max="200">
          </div>
          <div class="form-row" style="justify-content:flex-end;gap:8px">
            <button type="button" class="btn btn-secondary" onclick="FinanceView.toggleBudgetForm()">Abbrechen</button>
            <button type="submit" class="btn btn-primary">Speichern</button>
          </div>
        </form>
      </div>
    `;
  }

  async function submitBudgetForm(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = {
      category: fd.get('category'),
      monthly_limit: parseFloat(fd.get('monthly_limit')),
      alert_threshold: parseInt(fd.get('alert_threshold') || '80')
    };
    try {
      await Api.post('/finance/budgets', payload);
      Toast.show('Budget gespeichert', 'success');
      showBudgetForm = false;
      await loadBudgets();
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  function toggleBudgetForm() {
    showBudgetForm = !showBudgetForm;
    const content = document.getElementById('finance-content');
    if (content) renderBudgets(content);
    if (showBudgetForm) {
      document.getElementById('budget-form-new')?.addEventListener('submit', submitBudgetForm);
    }
  }

  async function deleteBudget(id) {
    if (!confirm('Budget wirklich löschen?')) return;
    try {
      await Api.delete(`/finance/budgets/${id}`);
      Toast.show('Budget gelöscht', 'success');
      await loadBudgets();
    } catch (err) {
      Toast.show('Fehler beim Löschen: ' + err.message, 'error');
    }
  }

  // ── Tab: Rechnungen ──────────────────────────────────────────────────────

  let invoices = [];
  let invoiceStats = null;
  let invoiceStatusFilter = '';
  let invoiceSheet = null; // null | 'new' | invoice-object

  async function loadInvoices() {
    const content = document.getElementById('finance-content');
    try {
      const url = invoiceStatusFilter ? `/finance/invoices?status=${encodeURIComponent(invoiceStatusFilter)}` : '/finance/invoices';
      const [list, stats] = await Promise.all([
        Api.get(url),
        Api.get('/finance/invoices/stats')
      ]);
      invoices = list;
      invoiceStats = stats;
      renderInvoices(content);
    } catch (err) {
      content.innerHTML = errorState(err, "FinanceView.switchTab('invoices')");
    }
  }

  function invoiceStatusBadge(status) {
    const map = {
      open:     { label: 'Offen',      cls: 'badge-accent' },
      paid:     { label: 'Bezahlt',    cls: 'badge-success' },
      overdue:  { label: 'Überfällig', cls: 'badge-error' },
      draft:    { label: 'Entwurf',    cls: 'badge-muted' }
    };
    const s = map[status] || map.draft;
    return `<span class="badge ${s.cls}">${s.label}</span>`;
  }

  function renderInvoices(el) {
    const statsHtml = invoiceStats ? `
      <div class="finance-widget-grid" style="margin-bottom:12px">
        ${['open','paid','overdue','draft'].map(k => {
          const s = invoiceStats[k] || { count: 0, total: 0 };
          const badge = invoiceStatusBadge(k);
          return `
            <div class="card finance-invoice-stat">
              ${badge}
              <div class="finance-widget-value" style="font-size:1rem">${currency(s.total)}</div>
              <div class="finance-widget-sub">${s.count} Rechnung${s.count !== 1 ? 'en' : ''}</div>
            </div>
          `;
        }).join('')}
      </div>
    ` : '';

    const filterButtons = ['', 'open', 'paid', 'overdue', 'draft'].map(v => {
      const labels = { '': 'Alle', open: 'Offen', paid: 'Bezahlt', overdue: 'Überfällig', draft: 'Entwurf' };
      const active = invoiceStatusFilter === v;
      return `<button class="filter-btn ${active ? 'active' : ''}" onclick="FinanceView.setInvoiceFilter('${v}')">${labels[v]}</button>`;
    }).join('');

    const listHtml = invoices.length === 0
      ? `<div class="empty-state">
           <span class="material-symbols-outlined">receipt_long</span>
           <p>Keine Rechnungen gefunden</p>
         </div>`
      : invoices.map(inv => `
          <div class="card finance-invoice-card">
            <div class="finance-tx-row">
              <div class="finance-tx-left">
                <div class="finance-tx-desc">${esc(inv.invoice_number || '–')} · ${esc(inv.recipient || '–')}</div>
                <div class="finance-tx-meta">
                  ${invoiceStatusBadge(inv.status)}
                  Fällig: ${fmtDate(inv.due_date)}
                </div>
                ${inv.notes ? `<div class="finance-tx-meta text-muted" style="font-size:0.75rem">${esc(inv.notes)}</div>` : ''}
              </div>
              <div class="finance-tx-amount">${currency(inv.total)}</div>
            </div>
            <div class="finance-tx-actions">
              ${inv.status !== 'paid' ? `
                <button class="btn btn-sm btn-secondary" onclick="FinanceView.markInvoicePaid('${esc(inv.id)}')">
                  <span class="material-symbols-outlined mi-sm">check_circle</span> Bezahlt
                </button>
              ` : ''}
              <button class="btn btn-sm btn-secondary" onclick="FinanceView.openInvoiceSheet(${JSON.stringify(inv).replace(/"/g, '&quot;')})">
                <span class="material-symbols-outlined mi-sm">edit</span>
              </button>
              <button class="btn btn-sm btn-danger" onclick="FinanceView.deleteInvoice('${esc(inv.id)}')">
                <span class="material-symbols-outlined mi-sm">delete</span>
              </button>
            </div>
          </div>
        `).join('');

    const sheetHtml = invoiceSheet !== null ? renderInvoiceSheet() : '';

    el.innerHTML = `
      ${statsHtml}
      <div class="finance-toolbar">
        <div class="filter-group" style="flex-wrap:wrap;gap:4px;margin-bottom:8px">${filterButtons}</div>
        <button class="btn btn-primary btn-sm" onclick="FinanceView.openInvoiceSheet(null)">
          <span class="material-symbols-outlined mi-sm">add</span> Rechnung
        </button>
      </div>
      ${listHtml}
      ${sheetHtml}
    `;
  }

  function renderInvoiceSheet() {
    const inv = invoiceSheet === 'new' ? null : invoiceSheet;
    const title = inv ? 'Rechnung bearbeiten' : 'Neue Rechnung';
    return `
      <div class="finance-sheet-backdrop" onclick="FinanceView.closeInvoiceSheet()"></div>
      <div class="finance-bottom-sheet">
        <div class="finance-sheet-handle"></div>
        <div class="finance-section-title">${title}</div>
        <form id="invoice-form" onsubmit="FinanceView.submitInvoiceForm(event)">
          <div class="form-row">
            <div class="form-group">
              <label>Empfänger *</label>
              <input class="input" type="text" name="recipient" value="${esc(inv?.recipient || '')}" required>
            </div>
            <div class="form-group">
              <label>Rechnungsnummer</label>
              <input class="input" type="text" name="invoice_number" value="${esc(inv?.invoice_number || '')}">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Gesamtbetrag (€) *</label>
              <input class="input" type="number" name="total" step="0.01" value="${esc(inv?.total ?? '')}" required>
            </div>
            <div class="form-group">
              <label>MwSt. (%)</label>
              <input class="input" type="number" name="tax_rate" step="0.1" value="${esc(inv?.tax_rate ?? 19)}">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Ausstellungsdatum</label>
              <input class="input" type="date" name="issue_date" value="${esc(inv?.issue_date || today())}">
            </div>
            <div class="form-group">
              <label>Fälligkeitsdatum *</label>
              <input class="input" type="date" name="due_date" value="${esc(inv?.due_date || '')}" required>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Status</label>
              <select class="input" name="status">
                ${['draft','open','paid','overdue'].map(s =>
                  `<option value="${s}" ${(inv?.status || 'draft') === s ? 'selected' : ''}>${{ draft:'Entwurf', open:'Offen', paid:'Bezahlt', overdue:'Überfällig' }[s]}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>Empfängeradresse</label>
            <input class="input" type="text" name="recipient_address" value="${esc(inv?.recipient_address || '')}">
          </div>
          <div class="form-group">
            <label>Notizen</label>
            <input class="input" type="text" name="notes" value="${esc(inv?.notes || '')}">
          </div>
          ${inv ? `<input type="hidden" name="_id" value="${esc(inv.id)}">` : ''}
          <div class="form-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
            <button type="button" class="btn btn-secondary" onclick="FinanceView.closeInvoiceSheet()">Abbrechen</button>
            <button type="submit" class="btn btn-primary">Speichern</button>
          </div>
        </form>
      </div>
    `;
  }

  function openInvoiceSheet(inv) {
    invoiceSheet = inv || 'new';
    const content = document.getElementById('finance-content');
    if (content) renderInvoices(content);
  }

  function closeInvoiceSheet() {
    invoiceSheet = null;
    const content = document.getElementById('finance-content');
    if (content) renderInvoices(content);
  }

  async function submitInvoiceForm(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const id = fd.get('_id');
    const payload = {
      recipient: fd.get('recipient'),
      total: parseFloat(fd.get('total')),
      due_date: fd.get('due_date'),
      status: fd.get('status') || 'draft',
      invoice_number: fd.get('invoice_number') || '',
      recipient_address: fd.get('recipient_address') || '',
      issue_date: fd.get('issue_date') || null,
      tax_rate: parseFloat(fd.get('tax_rate') || '19'),
      notes: fd.get('notes') || ''
    };
    try {
      if (id) {
        await Api.patch(`/finance/invoices/${id}`, payload);
        Toast.show('Rechnung aktualisiert', 'success');
      } else {
        await Api.post('/finance/invoices', payload);
        Toast.show('Rechnung erstellt', 'success');
      }
      invoiceSheet = null;
      await loadInvoices();
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  function setInvoiceFilter(status) {
    invoiceStatusFilter = status;
    loadInvoices();
  }

  async function markInvoicePaid(id) {
    try {
      await Api.post(`/finance/invoices/${id}/mark-paid`, {});
      Toast.show('Rechnung als bezahlt markiert', 'success');
      await loadInvoices();
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function deleteInvoice(id) {
    if (!confirm('Rechnung wirklich löschen?')) return;
    try {
      await Api.delete(`/finance/invoices/${id}`);
      Toast.show('Rechnung gelöscht', 'success');
      await loadInvoices();
    } catch (err) {
      Toast.show('Fehler beim Löschen: ' + err.message, 'error');
    }
  }

  // ── Shared Helpers ───────────────────────────────────────────────────────

  function errorState(err, reloadCall) {
    return `
      <div class="error-state">
        <span class="material-symbols-outlined">error_outline</span>
        <p>${esc(err.message || 'Unbekannter Fehler')}</p>
        <button class="btn btn-secondary" onclick="${reloadCall}">Erneut versuchen</button>
      </div>
    `;
  }

  // ── Public API ───────────────────────────────────────────────────────────

  return {
    render,
    switchTab,
    // Transactions
    toggleTxForm,
    applyTxFilter,
    clearTxFilter,
    openCsvUpload,
    uploadCsv,
    deleteTx,
    // Contracts
    openContractSheet,
    closeContractSheet,
    submitContractForm,
    deleteContract,
    detectContracts,
    // Budgets
    toggleBudgetForm,
    deleteBudget,
    // Invoices
    openInvoiceSheet,
    closeInvoiceSheet,
    submitInvoiceForm,
    setInvoiceFilter,
    markInvoicePaid,
    deleteInvoice
  };
})();
