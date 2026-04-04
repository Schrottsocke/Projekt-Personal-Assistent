/**
 * Invoices View – Rechnungen erstellen (Kleinunternehmer / Regelbesteuerung)
 */
const InvoicesView = (() => {
  let invoices = [];
  let currentInvoice = null; // Editing state
  let viewMode = 'list'; // list | form | preview

  // ── Helpers ──

  function esc(str) {
    return typeof Utils !== 'undefined' ? Utils.escapeHtml(String(str || '')) : String(str || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  }

  function currency(n) {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n || 0);
  }

  function showToast(msg, type) {
    if (typeof Toast !== 'undefined') Toast.show(msg, type);
  }

  function statusBadge(status) {
    const map = {
      draft: { label: 'Entwurf', cls: 'badge-muted' },
      sent: { label: 'Versendet', cls: 'badge-accent' },
      paid: { label: 'Bezahlt', cls: 'badge-success' },
      cancelled: { label: 'Storniert', cls: 'badge-error' },
    };
    const s = map[status] || map.draft;
    return `<span class="badge ${s.cls}">${s.label}</span>`;
  }

  function typeBadge(type) {
    if (type === 'kleinunternehmer') return '<span class="badge badge-warning">Kleinunternehmer</span>';
    return '<span class="badge badge-accent">Regelbesteuerung</span>';
  }

  // ── Render Entry ──

  async function render(container) {
    viewMode = 'list';
    currentInvoice = null;
    container.innerHTML = `
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">receipt_long</span>
        Rechnungen
      </div>
      <div id="invoice-content">
        <div class="skeleton skeleton-card"></div>
      </div>
    `;
    await loadInvoices();
  }

  // ── Load & List ──

  async function loadInvoices() {
    try {
      invoices = await Api.getInvoices();
    } catch (err) {
      if (!err.isOffline) showToast('Rechnungen konnten nicht geladen werden', 'error');
      invoices = [];
    }
    renderList();
  }

  function renderList() {
    const el = document.getElementById('invoice-content');
    if (!el) return;

    el.innerHTML = `
      <div class="invoice-toolbar">
        <button class="btn btn-primary" onclick="InvoicesView.showForm()">
          <span class="material-symbols-outlined">add</span> Neue Rechnung
        </button>
      </div>
      ${invoices.length === 0
        ? `<div class="empty-state">
            <span class="material-symbols-outlined">receipt_long</span>
            <p>Noch keine Rechnungen</p>
            <button class="btn btn-primary" onclick="InvoicesView.showForm()">Erste Rechnung erstellen</button>
          </div>`
        : `<div class="invoice-list">${invoices.map(renderInvoiceCard).join('')}</div>`
      }
    `;
  }

  function renderInvoiceCard(inv) {
    return `
      <div class="card invoice-card" onclick="InvoicesView.openPreview('${inv.id}')">
        <div class="invoice-card-header">
          <strong>${esc(inv.invoice_number)}</strong>
          <div>${statusBadge(inv.status)} ${typeBadge(inv.invoice_type)}</div>
        </div>
        <div class="invoice-card-body">
          <div class="invoice-card-recipient">${esc(inv.recipient_name) || 'Kein Empfaenger'}</div>
          <div class="invoice-card-date">${esc(inv.invoice_date)}</div>
        </div>
        <div class="invoice-card-footer">
          <span class="invoice-card-total">${currency(inv.total)}</span>
          <div class="invoice-card-actions">
            <button class="btn btn-sm btn-icon" onclick="event.stopPropagation(); InvoicesView.editInvoice('${inv.id}')" title="Bearbeiten">
              <span class="material-symbols-outlined">edit</span>
            </button>
            <button class="btn btn-sm btn-icon" onclick="event.stopPropagation(); InvoicesView.duplicateInvoice('${inv.id}')" title="Duplizieren">
              <span class="material-symbols-outlined">content_copy</span>
            </button>
            <button class="btn btn-sm btn-icon btn-danger" onclick="event.stopPropagation(); InvoicesView.confirmDelete('${inv.id}')" title="Loeschen">
              <span class="material-symbols-outlined">delete</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // ── Form ──

  function showForm(invoice) {
    viewMode = 'form';
    currentInvoice = invoice || {
      invoice_type: 'kleinunternehmer',
      status: 'draft',
      sender_name: '', sender_address: '', sender_tax_id: '', sender_vat_id: '', sender_bank: '',
      recipient_name: '', recipient_address: '',
      invoice_date: new Date().toISOString().slice(0, 10),
      delivery_date: '', delivery_period: '',
      payment_terms: '14 Tage netto',
      items: [{ description: '', quantity: 1, unit_price: 0, tax_rate: 19 }],
      notes: '',
    };
    renderForm();
  }

  function renderForm() {
    const el = document.getElementById('invoice-content');
    if (!el) return;
    const inv = currentInvoice;
    const isKU = inv.invoice_type === 'kleinunternehmer';
    const isEdit = !!inv.id;

    el.innerHTML = `
      <div class="invoice-form">
        <div class="invoice-form-header">
          <button class="btn btn-secondary btn-sm" onclick="InvoicesView.backToList()">
            <span class="material-symbols-outlined">arrow_back</span> Zurueck
          </button>
          <h3>${isEdit ? 'Rechnung bearbeiten' : 'Neue Rechnung'}</h3>
        </div>

        <!-- Rechnungstyp -->
        <div class="invoice-type-toggle">
          <button class="btn ${isKU ? 'btn-primary' : 'btn-secondary'}" onclick="InvoicesView.setType('kleinunternehmer')">
            <span class="material-symbols-outlined">storefront</span> Kleinunternehmer
          </button>
          <button class="btn ${!isKU ? 'btn-primary' : 'btn-secondary'}" onclick="InvoicesView.setType('regelbesteuerung')">
            <span class="material-symbols-outlined">account_balance</span> Regelbesteuerung
          </button>
        </div>

        ${isKU ? `<div class="invoice-hint invoice-hint-info">
          <span class="material-symbols-outlined">info</span>
          Kleinunternehmerregelung nach &sect; 19 UStG: Keine Umsatzsteuer wird ausgewiesen.
        </div>` : `<div class="invoice-hint invoice-hint-accent">
          <span class="material-symbols-outlined">info</span>
          Regelbesteuerung: Nettobetrag, Steuersatz, USt und Brutto werden ausgewiesen.
        </div>`}

        <!-- Absender -->
        <fieldset class="invoice-fieldset">
          <legend>Rechnungssteller</legend>
          <div class="form-group">
            <label>Name / Firma *</label>
            <input class="input" id="inv-sender-name" value="${esc(inv.sender_name)}" placeholder="Max Mustermann">
          </div>
          <div class="form-group">
            <label>Anschrift *</label>
            <textarea class="input" id="inv-sender-address" rows="2" placeholder="Musterstr. 1, 12345 Berlin">${esc(inv.sender_address)}</textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Steuernummer</label>
              <input class="input" id="inv-sender-tax-id" value="${esc(inv.sender_tax_id)}" placeholder="12/345/67890">
            </div>
            <div class="form-group">
              <label>USt-IdNr.</label>
              <input class="input" id="inv-sender-vat-id" value="${esc(inv.sender_vat_id)}" placeholder="DE123456789">
            </div>
          </div>
          <div class="form-group">
            <label>Bankverbindung</label>
            <textarea class="input" id="inv-sender-bank" rows="2" placeholder="IBAN: DE89... / BIC: ... / Bank: ...">${esc(inv.sender_bank)}</textarea>
          </div>
        </fieldset>

        <!-- Empfaenger -->
        <fieldset class="invoice-fieldset">
          <legend>Empfaenger</legend>
          <div class="form-group">
            <label>Name / Firma *</label>
            <input class="input" id="inv-recipient-name" value="${esc(inv.recipient_name)}" placeholder="Firma XY GmbH">
          </div>
          <div class="form-group">
            <label>Anschrift *</label>
            <textarea class="input" id="inv-recipient-address" rows="2" placeholder="Beispielweg 5, 54321 Koeln">${esc(inv.recipient_address)}</textarea>
          </div>
        </fieldset>

        <!-- Rechnungsdaten -->
        <fieldset class="invoice-fieldset">
          <legend>Rechnungsdaten</legend>
          <div class="form-row">
            <div class="form-group">
              <label>Rechnungsdatum *</label>
              <input class="input" type="date" id="inv-date" value="${esc(inv.invoice_date)}">
            </div>
            <div class="form-group">
              <label>Rechnungsnr.</label>
              <input class="input" id="inv-number" value="${esc(inv.invoice_number || '')}" placeholder="Wird automatisch vergeben">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Leistungsdatum</label>
              <input class="input" type="date" id="inv-delivery-date" value="${esc(inv.delivery_date || '')}">
            </div>
            <div class="form-group">
              <label>Leistungszeitraum</label>
              <input class="input" id="inv-delivery-period" value="${esc(inv.delivery_period || '')}" placeholder="z.B. 01.03. – 31.03.2026">
            </div>
          </div>
          <div class="form-group">
            <label>Zahlungsziel</label>
            <input class="input" id="inv-payment-terms" value="${esc(inv.payment_terms)}" placeholder="14 Tage netto">
          </div>
          <div class="form-group">
            <label>Status</label>
            <select class="input" id="inv-status">
              <option value="draft" ${inv.status === 'draft' ? 'selected' : ''}>Entwurf</option>
              <option value="sent" ${inv.status === 'sent' ? 'selected' : ''}>Versendet</option>
              <option value="paid" ${inv.status === 'paid' ? 'selected' : ''}>Bezahlt</option>
              <option value="cancelled" ${inv.status === 'cancelled' ? 'selected' : ''}>Storniert</option>
            </select>
          </div>
        </fieldset>

        <!-- Positionen -->
        <fieldset class="invoice-fieldset">
          <legend>Positionen</legend>
          <div id="inv-items-list">
            ${(inv.items || []).map((item, idx) => renderItemRow(item, idx, isKU)).join('')}
          </div>
          <button class="btn btn-secondary btn-sm" onclick="InvoicesView.addItem()">
            <span class="material-symbols-outlined">add</span> Position hinzufuegen
          </button>
          <div class="invoice-totals" id="inv-totals">
            ${renderTotals(inv)}
          </div>
        </fieldset>

        <!-- Notizen -->
        <fieldset class="invoice-fieldset">
          <legend>Anmerkungen</legend>
          <div class="form-group">
            <textarea class="input" id="inv-notes" rows="3" placeholder="Optionale Hinweise auf der Rechnung">${esc(inv.notes)}</textarea>
          </div>
        </fieldset>

        <!-- Actions -->
        <div class="invoice-form-actions">
          <button class="btn btn-secondary" onclick="InvoicesView.backToList()">Abbrechen</button>
          <button class="btn btn-accent" onclick="InvoicesView.previewFromForm()">
            <span class="material-symbols-outlined">preview</span> Vorschau
          </button>
          <button class="btn btn-primary" onclick="InvoicesView.saveInvoice()">
            <span class="material-symbols-outlined">save</span> Speichern
          </button>
        </div>
      </div>
    `;

    recalcTotals();
  }

  function renderItemRow(item, idx, isKU) {
    return `
      <div class="invoice-item-row" data-idx="${idx}">
        <div class="form-group invoice-item-desc">
          <label>Beschreibung</label>
          <input class="input" data-field="description" value="${esc(item.description)}" placeholder="Leistung / Produkt" oninput="InvoicesView.updateItem(${idx}, this)">
        </div>
        <div class="invoice-item-numbers">
          <div class="form-group">
            <label>Menge</label>
            <input class="input" type="number" data-field="quantity" value="${item.quantity || 1}" min="0.01" step="0.01" oninput="InvoicesView.updateItem(${idx}, this)">
          </div>
          <div class="form-group">
            <label>Einzelpreis</label>
            <input class="input" type="number" data-field="unit_price" value="${item.unit_price || 0}" min="0" step="0.01" oninput="InvoicesView.updateItem(${idx}, this)">
          </div>
          ${!isKU ? `<div class="form-group">
            <label>USt %</label>
            <select class="input" data-field="tax_rate" onchange="InvoicesView.updateItem(${idx}, this)">
              <option value="19" ${(item.tax_rate || 19) == 19 ? 'selected' : ''}>19%</option>
              <option value="7" ${item.tax_rate == 7 ? 'selected' : ''}>7%</option>
            </select>
          </div>` : ''}
          <div class="form-group">
            <label>Netto</label>
            <div class="invoice-item-computed">${currency((item.quantity || 1) * (item.unit_price || 0))}</div>
          </div>
        </div>
        <button class="btn btn-icon btn-danger btn-sm invoice-item-remove" onclick="InvoicesView.removeItem(${idx})" title="Entfernen">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    `;
  }

  function renderTotals(inv) {
    const isKU = inv.invoice_type === 'kleinunternehmer';
    const subtotal = (inv.items || []).reduce((s, i) => s + (i.quantity || 1) * (i.unit_price || 0), 0);

    if (isKU) {
      return `
        <div class="invoice-total-row">
          <span>Gesamtbetrag</span>
          <strong>${currency(subtotal)}</strong>
        </div>
        <div class="invoice-total-hint">Kein Ausweis der Umsatzsteuer gem&auml;&szlig; &sect; 19 UStG</div>
      `;
    }

    // Regelbesteuerung: nach Steuersatz gruppieren
    const taxGroups = {};
    for (const item of (inv.items || [])) {
      const rate = item.tax_rate || 19;
      const net = (item.quantity || 1) * (item.unit_price || 0);
      if (!taxGroups[rate]) taxGroups[rate] = { net: 0, tax: 0 };
      taxGroups[rate].net += net;
      taxGroups[rate].tax += net * rate / 100;
    }

    let taxRows = '';
    let totalTax = 0;
    for (const [rate, g] of Object.entries(taxGroups)) {
      taxRows += `<div class="invoice-total-row"><span>USt ${rate}% auf ${currency(g.net)}</span><span>${currency(g.tax)}</span></div>`;
      totalTax += g.tax;
    }

    return `
      <div class="invoice-total-row"><span>Netto</span><span>${currency(subtotal)}</span></div>
      ${taxRows}
      <div class="invoice-total-row invoice-total-grand"><span>Brutto</span><strong>${currency(subtotal + totalTax)}</strong></div>
    `;
  }

  // ── Item Management ──

  function addItem() {
    if (!currentInvoice) return;
    const isKU = currentInvoice.invoice_type === 'kleinunternehmer';
    currentInvoice.items.push({
      description: '', quantity: 1, unit_price: 0,
      tax_rate: isKU ? 0 : 19,
    });
    renderForm();
  }

  function removeItem(idx) {
    if (!currentInvoice) return;
    currentInvoice.items.splice(idx, 1);
    renderForm();
  }

  function updateItem(idx, inputEl) {
    if (!currentInvoice || !currentInvoice.items[idx]) return;
    const field = inputEl.dataset.field;
    let val = inputEl.value;
    if (field !== 'description') val = parseFloat(val) || 0;
    currentInvoice.items[idx][field] = val;
    recalcTotals();
  }

  function recalcTotals() {
    if (!currentInvoice) return;
    // Update computed net per row
    document.querySelectorAll('.invoice-item-row').forEach((row) => {
      const idx = parseInt(row.dataset.idx);
      const item = currentInvoice.items[idx];
      if (!item) return;
      const net = (item.quantity || 1) * (item.unit_price || 0);
      const comp = row.querySelector('.invoice-item-computed');
      if (comp) comp.textContent = currency(net);
    });
    // Update totals block
    const totalsEl = document.getElementById('inv-totals');
    if (totalsEl) totalsEl.innerHTML = renderTotals(currentInvoice);
  }

  function setType(type) {
    if (!currentInvoice) return;
    currentInvoice.invoice_type = type;
    // Reset tax rates
    for (const item of currentInvoice.items) {
      item.tax_rate = type === 'kleinunternehmer' ? 0 : 19;
    }
    renderForm();
  }

  // ── Collect Form Data ──

  function collectFormData() {
    const inv = currentInvoice;
    inv.sender_name = document.getElementById('inv-sender-name')?.value || '';
    inv.sender_address = document.getElementById('inv-sender-address')?.value || '';
    inv.sender_tax_id = document.getElementById('inv-sender-tax-id')?.value || '';
    inv.sender_vat_id = document.getElementById('inv-sender-vat-id')?.value || '';
    inv.sender_bank = document.getElementById('inv-sender-bank')?.value || '';
    inv.recipient_name = document.getElementById('inv-recipient-name')?.value || '';
    inv.recipient_address = document.getElementById('inv-recipient-address')?.value || '';
    inv.invoice_date = document.getElementById('inv-date')?.value || '';
    inv.invoice_number = document.getElementById('inv-number')?.value || '';
    inv.delivery_date = document.getElementById('inv-delivery-date')?.value || '';
    inv.delivery_period = document.getElementById('inv-delivery-period')?.value || '';
    inv.payment_terms = document.getElementById('inv-payment-terms')?.value || '14 Tage netto';
    inv.status = document.getElementById('inv-status')?.value || 'draft';
    inv.notes = document.getElementById('inv-notes')?.value || '';
    return inv;
  }

  // ── Save ──

  async function saveInvoice() {
    const data = collectFormData();

    // Client-side validation
    if (!data.sender_name) { showToast('Rechnungssteller-Name fehlt', 'error'); return; }
    if (!data.recipient_name) { showToast('Empfaenger-Name fehlt', 'error'); return; }
    if (!data.invoice_date) { showToast('Rechnungsdatum fehlt', 'error'); return; }
    if (!data.items || data.items.length === 0) { showToast('Mindestens eine Position noetig', 'error'); return; }

    try {
      let result;
      if (data.id) {
        result = await Api.updateInvoice(data.id, data);
        showToast('Rechnung aktualisiert', 'success');
      } else {
        result = await Api.createInvoice(data);
        showToast('Rechnung erstellt', 'success');
      }
      currentInvoice = null;
      viewMode = 'list';
      await loadInvoices();
    } catch (err) {
      showToast(err.message || 'Fehler beim Speichern', 'error');
    }
  }

  // ── Edit / Duplicate / Delete ──

  async function editInvoice(id) {
    try {
      const inv = await Api.getInvoice(id);
      showForm(inv);
    } catch (err) {
      showToast('Rechnung konnte nicht geladen werden', 'error');
    }
  }

  async function duplicateInvoice(id) {
    try {
      const inv = await Api.getInvoice(id);
      delete inv.id;
      inv.invoice_number = '';
      inv.status = 'draft';
      inv.invoice_date = new Date().toISOString().slice(0, 10);
      showForm(inv);
      showToast('Rechnung dupliziert – bitte anpassen und speichern', 'info');
    } catch (err) {
      showToast('Fehler beim Duplizieren', 'error');
    }
  }

  async function confirmDelete(id) {
    if (!confirm('Rechnung wirklich loeschen?')) return;
    try {
      await Api.deleteInvoice(id);
      showToast('Rechnung geloescht', 'success');
      await loadInvoices();
    } catch (err) {
      showToast('Fehler beim Loeschen', 'error');
    }
  }

  // ── Preview ──

  function previewFromForm() {
    const data = collectFormData();
    openPreviewDirect(data);
  }

  async function openPreview(id) {
    try {
      const inv = await Api.getInvoice(id);
      openPreviewDirect(inv);
    } catch (err) {
      showToast('Vorschau konnte nicht geladen werden', 'error');
    }
  }

  function openPreviewDirect(inv) {
    viewMode = 'preview';
    const el = document.getElementById('invoice-content');
    if (!el) return;

    const isKU = inv.invoice_type === 'kleinunternehmer';
    const subtotal = (inv.items || []).reduce((s, i) => s + (i.quantity || 1) * (i.unit_price || 0), 0);

    // Tax calculation
    let taxGroups = {};
    let totalTax = 0;
    if (!isKU) {
      for (const item of (inv.items || [])) {
        const rate = item.tax_rate || 19;
        const net = (item.quantity || 1) * (item.unit_price || 0);
        if (!taxGroups[rate]) taxGroups[rate] = { net: 0, tax: 0 };
        taxGroups[rate].net += net;
        taxGroups[rate].tax += net * rate / 100;
      }
      totalTax = Object.values(taxGroups).reduce((s, g) => s + g.tax, 0);
    }

    el.innerHTML = `
      <div class="invoice-preview-toolbar">
        <button class="btn btn-secondary btn-sm" onclick="InvoicesView.backToList()">
          <span class="material-symbols-outlined">arrow_back</span> Zurueck
        </button>
        ${inv.id ? `<button class="btn btn-secondary btn-sm" onclick="InvoicesView.editInvoice('${inv.id}')">
          <span class="material-symbols-outlined">edit</span> Bearbeiten
        </button>` : ''}
        <button class="btn btn-primary btn-sm" onclick="InvoicesView.printPreview()">
          <span class="material-symbols-outlined">print</span> Drucken / PDF
        </button>
      </div>
      <div class="invoice-preview" id="invoice-printable">
        <div class="inv-prev-header">
          <div class="inv-prev-sender">
            <div class="inv-prev-sender-name">${esc(inv.sender_name)}</div>
            <div class="inv-prev-sender-addr">${esc(inv.sender_address).replace(/\n/g, '<br>')}</div>
          </div>
          <div class="inv-prev-meta">
            <div class="inv-prev-title">RECHNUNG</div>
            <table class="inv-prev-meta-table">
              <tr><td>Rechnungsnr.:</td><td>${esc(inv.invoice_number || '–')}</td></tr>
              <tr><td>Datum:</td><td>${esc(inv.invoice_date)}</td></tr>
              ${inv.delivery_date ? `<tr><td>Leistungsdatum:</td><td>${esc(inv.delivery_date)}</td></tr>` : ''}
              ${inv.delivery_period ? `<tr><td>Leistungszeitraum:</td><td>${esc(inv.delivery_period)}</td></tr>` : ''}
            </table>
          </div>
        </div>

        <div class="inv-prev-recipient">
          <div class="inv-prev-recipient-label">An:</div>
          <div>${esc(inv.recipient_name)}</div>
          <div>${esc(inv.recipient_address).replace(/\n/g, '<br>')}</div>
        </div>

        <table class="inv-prev-items">
          <thead>
            <tr>
              <th>Pos.</th>
              <th>Beschreibung</th>
              <th class="right">Menge</th>
              <th class="right">Einzelpreis</th>
              ${!isKU ? '<th class="right">USt</th>' : ''}
              <th class="right">Netto</th>
            </tr>
          </thead>
          <tbody>
            ${(inv.items || []).map((item, i) => {
              const net = (item.quantity || 1) * (item.unit_price || 0);
              return `<tr>
                <td>${i + 1}</td>
                <td>${esc(item.description)}</td>
                <td class="right">${item.quantity}</td>
                <td class="right">${currency(item.unit_price)}</td>
                ${!isKU ? `<td class="right">${item.tax_rate}%</td>` : ''}
                <td class="right">${currency(net)}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>

        <div class="inv-prev-totals">
          ${isKU ? `
            <div class="inv-prev-total-row inv-prev-total-grand">
              <span>Gesamtbetrag:</span>
              <strong>${currency(subtotal)}</strong>
            </div>
            <div class="inv-prev-kleinunternehmer-hinweis">
              Kein Ausweis der Umsatzsteuer gem&auml;&szlig; &sect; 19 UStG.
            </div>
          ` : `
            <div class="inv-prev-total-row">
              <span>Nettobetrag:</span><span>${currency(subtotal)}</span>
            </div>
            ${Object.entries(taxGroups).map(([rate, g]) =>
              `<div class="inv-prev-total-row"><span>zzgl. ${rate}% USt auf ${currency(g.net)}:</span><span>${currency(g.tax)}</span></div>`
            ).join('')}
            <div class="inv-prev-total-row inv-prev-total-grand">
              <span>Bruttobetrag:</span><strong>${currency(subtotal + totalTax)}</strong>
            </div>
          `}
        </div>

        ${inv.payment_terms ? `<div class="inv-prev-payment">Zahlungsziel: ${esc(inv.payment_terms)}</div>` : ''}

        ${inv.notes ? `<div class="inv-prev-notes">${esc(inv.notes).replace(/\n/g, '<br>')}</div>` : ''}

        <div class="inv-prev-footer">
          ${inv.sender_tax_id ? `<div>Steuernr.: ${esc(inv.sender_tax_id)}</div>` : ''}
          ${inv.sender_vat_id ? `<div>USt-IdNr.: ${esc(inv.sender_vat_id)}</div>` : ''}
          ${inv.sender_bank ? `<div class="inv-prev-bank">${esc(inv.sender_bank).replace(/\n/g, '<br>')}</div>` : ''}
        </div>
      </div>
    `;
  }

  function printPreview() {
    const printable = document.getElementById('invoice-printable');
    if (!printable) return;

    const win = window.open('', '_blank');
    win.document.write(`<!DOCTYPE html><html><head>
      <meta charset="UTF-8">
      <title>Rechnung</title>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
               color: #222; padding: 40px; max-width: 800px; margin: 0 auto; font-size: 14px; line-height: 1.5; }
        .inv-prev-header { display: flex; justify-content: space-between; margin-bottom: 32px; }
        .inv-prev-sender-name { font-size: 18px; font-weight: 700; }
        .inv-prev-sender-addr { color: #555; margin-top: 4px; }
        .inv-prev-title { font-size: 22px; font-weight: 800; text-align: right; margin-bottom: 8px; color: #333; }
        .inv-prev-meta-table { font-size: 13px; }
        .inv-prev-meta-table td { padding: 2px 8px; }
        .inv-prev-meta-table td:first-child { color: #666; }
        .inv-prev-recipient { margin-bottom: 28px; padding: 16px; border: 1px solid #ddd; border-radius: 4px; }
        .inv-prev-recipient-label { font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 4px; }
        .inv-prev-items { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        .inv-prev-items th { background: #f5f5f5; padding: 8px 12px; text-align: left; font-size: 12px; text-transform: uppercase; color: #555; border-bottom: 2px solid #ddd; }
        .inv-prev-items td { padding: 8px 12px; border-bottom: 1px solid #eee; }
        .inv-prev-items .right, .inv-prev-items th.right { text-align: right; }
        .inv-prev-totals { margin-left: auto; width: 300px; margin-bottom: 24px; }
        .inv-prev-total-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; }
        .inv-prev-total-grand { border-top: 2px solid #333; padding-top: 8px; margin-top: 4px; font-size: 16px; }
        .inv-prev-kleinunternehmer-hinweis { font-size: 12px; color: #666; font-style: italic; margin-top: 8px; }
        .inv-prev-payment { margin-bottom: 16px; color: #444; }
        .inv-prev-notes { margin-bottom: 16px; color: #555; font-size: 13px; padding: 12px; background: #f9f9f9; border-radius: 4px; }
        .inv-prev-footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
        .inv-prev-bank { margin-top: 4px; }
        @media print { body { padding: 20px; } }
      </style>
    </head><body>${printable.innerHTML}</body></html>`);
    win.document.close();
    setTimeout(() => win.print(), 250);
  }

  function backToList() {
    viewMode = 'list';
    currentInvoice = null;
    renderList();
  }

  // ── Public API ──
  return {
    render,
    showForm,
    setType,
    addItem,
    removeItem,
    updateItem,
    saveInvoice,
    editInvoice,
    duplicateInvoice,
    confirmDelete,
    openPreview,
    previewFromForm,
    printPreview,
    backToList,
  };
})();
