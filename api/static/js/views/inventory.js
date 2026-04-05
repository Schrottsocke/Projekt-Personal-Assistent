/**
 * DualMind Inventory View – Haushaltsinventar, Garantien, Dokumente
 */
const InventoryView = (() => {
  let activeTab = 'inventar';
  let container = null;

  // ── Inventar state
  let items = [];
  let rooms = [];
  let roomFilter = '';
  let valueSummary = null;
  let showItemForm = false;
  let editingItem = null;

  // ── Garantien state
  let warranties = [];
  let warrantyFilter = 'active'; // active | expired | all
  let expiringWarranties = [];
  let showWarrantyForm = false;
  let editingWarranty = null;

  // ── Dokumente state
  let documents = [];
  let docSearchQuery = '';
  let classifyResults = {}; // docId -> result

  // ── Helpers ─────────────────────────────────────────────────

  function esc(str) {
    return String(str || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[c]);
  }

  function currency(n) {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(n || 0);
  }

  function showToast(msg, type) {
    if (typeof Toast !== 'undefined') Toast.show(msg, type);
  }

  function formatDate(dateStr) {
    if (!dateStr) return '–';
    const d = new Date(dateStr);
    if (isNaN(d)) return dateStr;
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function daysUntil(dateStr) {
    if (!dateStr) return null;
    const d = new Date(dateStr);
    if (isNaN(d)) return null;
    return Math.ceil((d - Date.now()) / 86400000);
  }

  function warrantyStatusBadge(warranty) {
    const days = daysUntil(warranty.warranty_end);
    if (days === null) return '<span class="badge">Unbekannt</span>';
    if (days < 0) return '<span class="badge badge-error">Abgelaufen</span>';
    if (days <= 30) return `<span class="badge badge-warning">Läuft ab in ${days}d</span>`;
    return '<span class="badge badge-success">Aktiv</span>';
  }

  function actionBadge(actionType) {
    const map = {
      expense:  { label: 'Ausgabe',   cls: 'badge-warning' },
      warranty: { label: 'Garantie',  cls: 'badge-success' },
      contract: { label: 'Vertrag',   cls: 'badge-accent'  },
      task:     { label: 'Aufgabe',   cls: 'badge-error'   },
    };
    const m = map[actionType] || { label: esc(actionType), cls: '' };
    return `<span class="badge ${m.cls}">${m.label}</span>`;
  }

  // ── Render Entry ─────────────────────────────────────────────

  async function render(el) {
    container = el;
    activeTab = 'inventar';
    container.innerHTML = `
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">inventory_2</span>
        Inventar
      </div>
      <div class="tabs mb-8" id="inventory-tabs">
        <button class="tab active" data-tab="inventar" onclick="InventoryView.switchTab('inventar')">Inventar</button>
        <button class="tab" data-tab="garantien" onclick="InventoryView.switchTab('garantien')">Garantien</button>
        <button class="tab" data-tab="dokumente" onclick="InventoryView.switchTab('dokumente')">Dokumente</button>
      </div>
      <div id="inventory-content"><div class="skeleton skeleton-card"></div></div>
    `;
    await loadAndRenderTab();
  }

  async function switchTab(tab) {
    activeTab = tab;
    updateTabButtons();
    const el = document.getElementById('inventory-content');
    if (el) el.innerHTML = '<div class="skeleton skeleton-card"></div>';
    await loadAndRenderTab();
  }

  function updateTabButtons() {
    document.querySelectorAll('#inventory-tabs .tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === activeTab);
    });
  }

  async function loadAndRenderTab() {
    if (activeTab === 'inventar') await loadInventarTab();
    else if (activeTab === 'garantien') await loadGarantienTab();
    else if (activeTab === 'dokumente') await loadDokumenteTab();
  }

  // ════════════════════════════════════════════════════════════
  // TAB 1: INVENTAR
  // ════════════════════════════════════════════════════════════

  async function loadInventarTab() {
    try {
      [items, rooms, valueSummary] = await Promise.all([
        Api.get(`/inventory/items${roomFilter ? `?room=${encodeURIComponent(roomFilter)}` : ''}`),
        Api.get('/inventory/rooms').then(r => r.rooms || []),
        Api.get('/inventory/items/value-summary'),
      ]);
    } catch (err) {
      if (!err?.isOffline) showToast('Inventar konnte nicht geladen werden', 'error');
      items = []; rooms = []; valueSummary = null;
    }
    renderInventarTab();
  }

  function renderInventarTab() {
    const el = document.getElementById('inventory-content');
    if (!el) return;

    el.innerHTML = `
      ${renderValueBanner()}
      <div class="inventory-toolbar" style="display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
        <select class="input" id="inv-room-filter" style="flex:1;min-width:140px;max-width:220px" onchange="InventoryView.applyRoomFilter(this.value)">
          <option value="">Alle Räume</option>
          ${rooms.map(r => `<option value="${esc(r)}" ${roomFilter === r ? 'selected' : ''}>${esc(r)}</option>`).join('')}
        </select>
        <button class="btn btn-primary" onclick="InventoryView.openItemForm()">
          <span class="material-symbols-outlined">add</span> Artikel
        </button>
      </div>
      ${showItemForm ? renderItemForm() : ''}
      ${items.length === 0
        ? `<div class="empty-state">
            <span class="material-symbols-outlined">inventory_2</span>
            <p>Keine Artikel gefunden</p>
            <button class="btn btn-primary" onclick="InventoryView.openItemForm()">Ersten Artikel anlegen</button>
          </div>`
        : `<div class="inventory-grid">${items.map(renderItemCard).join('')}</div>`
      }
    `;
  }

  function renderValueBanner() {
    if (!valueSummary) return '';
    const { total_value, item_count } = valueSummary;
    return `
      <div class="card" style="background:var(--surface-2,var(--card-bg));margin-bottom:12px;display:flex;align-items:center;gap:16px;padding:14px 16px">
        <span class="material-symbols-outlined" style="font-size:32px;color:var(--accent)">account_balance_wallet</span>
        <div>
          <div style="font-size:20px;font-weight:700">${currency(total_value)}</div>
          <div style="color:var(--text-secondary);font-size:13px">${item_count || 0} Artikel im Inventar</div>
        </div>
      </div>
    `;
  }

  function renderItemCard(item) {
    const hasPhoto = !!item.photo_url;
    return `
      <div class="card inventory-item-card" style="position:relative">
        ${hasPhoto
          ? `<img src="${esc(item.photo_url)}" alt="${esc(item.name)}" style="width:100%;height:140px;object-fit:cover;border-radius:8px 8px 0 0;margin:-16px -16px 12px -16px;width:calc(100% + 32px)">`
          : `<div style="display:flex;justify-content:center;margin-bottom:12px">
              <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-secondary)">inventory_2</span>
            </div>`
        }
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;margin-bottom:4px">${esc(item.name)}</div>
            ${item.room ? `<span class="badge" style="margin-bottom:6px">${esc(item.room)}</span>` : ''}
            ${item.description ? `<div style="font-size:13px;color:var(--text-secondary);margin-bottom:4px">${esc(item.description)}</div>` : ''}
            ${item.serial_number ? `<div style="font-size:12px;color:var(--text-secondary)">S/N: ${esc(item.serial_number)}</div>` : ''}
            ${item.box_label ? `<div style="font-size:12px;color:var(--text-secondary)">Box: ${esc(item.box_label)}</div>` : ''}
            ${item.purchase_date ? `<div style="font-size:12px;color:var(--text-secondary)">Gekauft: ${formatDate(item.purchase_date)}</div>` : ''}
          </div>
          <div style="text-align:right;flex-shrink:0">
            ${item.value ? `<div style="font-weight:700;color:var(--accent)">${currency(item.value)}</div>` : ''}
          </div>
        </div>
        <div style="display:flex;gap:6px;margin-top:10px;justify-content:flex-end">
          <label class="btn btn-secondary btn-sm" title="Foto hochladen" style="cursor:pointer">
            <span class="material-symbols-outlined">photo_camera</span>
            <input type="file" accept="image/*" hidden onchange="InventoryView.uploadPhoto('${esc(item.id)}', this)">
          </label>
          <button class="btn btn-secondary btn-sm" onclick="InventoryView.openItemForm('${esc(item.id)}')" title="Bearbeiten">
            <span class="material-symbols-outlined">edit</span>
          </button>
          <button class="btn btn-danger btn-sm" onclick="InventoryView.deleteItem('${esc(item.id)}')" title="Löschen">
            <span class="material-symbols-outlined">delete</span>
          </button>
        </div>
      </div>
    `;
  }

  function renderItemForm() {
    const item = editingItem || {};
    const isEdit = !!item.id;
    return `
      <div class="card" style="margin-bottom:16px;border:2px solid var(--accent,#6c63ff)">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <strong>${isEdit ? 'Artikel bearbeiten' : 'Neuer Artikel'}</strong>
          <button class="btn btn-secondary btn-sm" onclick="InventoryView.closeItemForm()">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Name *</label>
            <input class="input" id="item-name" value="${esc(item.name)}" placeholder="z.B. Kaffeemaschine">
          </div>
          <div class="form-group">
            <label>Raum</label>
            <select class="input" id="item-room">
              <option value="">– kein Raum –</option>
              ${rooms.map(r => `<option value="${esc(r)}" ${item.room === r ? 'selected' : ''}>${esc(r)}</option>`).join('')}
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>Beschreibung</label>
          <textarea class="input" id="item-description" rows="2" placeholder="Kurze Beschreibung">${esc(item.description)}</textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Wert (€)</label>
            <input class="input" type="number" id="item-value" value="${item.value || ''}" placeholder="0.00" step="0.01" min="0">
          </div>
          <div class="form-group">
            <label>Kaufdatum</label>
            <input class="input" type="date" id="item-purchase-date" value="${esc(item.purchase_date || '')}">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Seriennummer</label>
            <input class="input" id="item-serial" value="${esc(item.serial_number)}" placeholder="Optional">
          </div>
          <div class="form-group">
            <label>Box-Label</label>
            <input class="input" id="item-box" value="${esc(item.box_label)}" placeholder="z.B. Kiste A3">
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px">
          <button class="btn btn-primary" onclick="InventoryView.saveItem()">
            <span class="material-symbols-outlined">save</span> Speichern
          </button>
          <button class="btn btn-secondary" onclick="InventoryView.closeItemForm()">Abbrechen</button>
        </div>
      </div>
    `;
  }

  function openItemForm(id) {
    showItemForm = true;
    editingItem = id ? (items.find(i => String(i.id) === String(id)) || {}) : {};
    renderInventarTab();
    const el = document.getElementById('item-name');
    if (el) el.focus();
  }

  function closeItemForm() {
    showItemForm = false;
    editingItem = null;
    renderInventarTab();
  }

  async function saveItem() {
    const name = document.getElementById('item-name')?.value?.trim();
    if (!name) { showToast('Name ist erforderlich', 'error'); return; }

    const payload = {
      name,
      room: document.getElementById('item-room')?.value || '',
      description: document.getElementById('item-description')?.value || '',
      value: parseFloat(document.getElementById('item-value')?.value) || null,
      purchase_date: document.getElementById('item-purchase-date')?.value || null,
      serial_number: document.getElementById('item-serial')?.value || '',
      box_label: document.getElementById('item-box')?.value || '',
    };

    try {
      if (editingItem?.id) {
        await Api.patch(`/inventory/items/${editingItem.id}`, payload);
        showToast('Artikel aktualisiert', 'success');
      } else {
        await Api.post('/inventory/items', payload);
        showToast('Artikel angelegt', 'success');
      }
      showItemForm = false;
      editingItem = null;
      await loadInventarTab();
    } catch (err) {
      showToast(err?.message || 'Fehler beim Speichern', 'error');
    }
  }

  async function deleteItem(id) {
    if (!confirm('Artikel wirklich löschen?')) return;
    try {
      await Api.delete(`/inventory/items/${id}`);
      showToast('Artikel gelöscht', 'success');
      await loadInventarTab();
    } catch (err) {
      showToast(err?.message || 'Fehler beim Löschen', 'error');
    }
  }

  async function uploadPhoto(itemId, inputEl) {
    const file = inputEl.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('photo', file);
    try {
      await Api.post(`/inventory/items/${itemId}/photo`, fd, { formData: true });
      showToast('Foto hochgeladen', 'success');
      await loadInventarTab();
    } catch (err) {
      showToast(err?.message || 'Foto-Upload fehlgeschlagen', 'error');
    }
    inputEl.value = '';
  }

  async function applyRoomFilter(room) {
    roomFilter = room;
    const el = document.getElementById('inventory-content');
    if (el) el.innerHTML = '<div class="skeleton skeleton-card"></div>';
    await loadInventarTab();
  }

  // ════════════════════════════════════════════════════════════
  // TAB 2: GARANTIEN
  // ════════════════════════════════════════════════════════════

  async function loadGarantienTab() {
    try {
      const params = warrantyFilter !== 'all' ? `?status=${warrantyFilter}` : '';
      [warranties, expiringWarranties] = await Promise.all([
        Api.get(`/inventory/warranties${params}`),
        Api.get('/inventory/warranties/expiring?days=30'),
      ]);
    } catch (err) {
      if (!err?.isOffline) showToast('Garantien konnten nicht geladen werden', 'error');
      warranties = []; expiringWarranties = [];
    }
    renderGarantienTab();
  }

  function renderGarantienTab() {
    const el = document.getElementById('inventory-content');
    if (!el) return;

    const expiringBanner = expiringWarranties.length > 0 ? `
      <div class="card" style="border-left:4px solid var(--warning,#f59e0b);margin-bottom:12px;display:flex;align-items:center;gap:12px;padding:12px 16px">
        <span class="material-symbols-outlined" style="color:var(--warning,#f59e0b)">warning</span>
        <div>
          <strong>${expiringWarranties.length} Garantie${expiringWarranties.length !== 1 ? 'n' : ''} läuft bald ab</strong>
          <div style="font-size:13px;color:var(--text-secondary)">
            ${expiringWarranties.slice(0, 3).map(w => `${esc(w.product_name)} (${formatDate(w.warranty_end)})`).join(', ')}
            ${expiringWarranties.length > 3 ? ` und ${expiringWarranties.length - 3} weitere` : ''}
          </div>
        </div>
      </div>
    ` : '';

    el.innerHTML = `
      ${expiringBanner}
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
        <div class="notification-filter-row" style="flex:1">
          <button class="filter-chip ${warrantyFilter === 'active' ? 'active' : ''}" onclick="InventoryView.setWarrantyFilter('active')">Aktiv</button>
          <button class="filter-chip ${warrantyFilter === 'expired' ? 'active' : ''}" onclick="InventoryView.setWarrantyFilter('expired')">Abgelaufen</button>
          <button class="filter-chip ${warrantyFilter === 'all' ? 'active' : ''}" onclick="InventoryView.setWarrantyFilter('all')">Alle</button>
        </div>
        <button class="btn btn-primary btn-sm" onclick="InventoryView.openWarrantyForm()">
          <span class="material-symbols-outlined">add</span> Garantie
        </button>
      </div>
      ${showWarrantyForm ? renderWarrantyForm() : ''}
      ${warranties.length === 0
        ? `<div class="empty-state">
            <span class="material-symbols-outlined">verified_user</span>
            <p>Keine Garantien gefunden</p>
            <button class="btn btn-primary" onclick="InventoryView.openWarrantyForm()">Erste Garantie anlegen</button>
          </div>`
        : warranties.map(renderWarrantyCard).join('')
      }
    `;
  }

  function renderWarrantyCard(w) {
    return `
      <div class="card" style="margin-bottom:8px">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">
              <strong>${esc(w.product_name)}</strong>
              ${warrantyStatusBadge(w)}
            </div>
            ${w.store ? `<div style="font-size:13px;color:var(--text-secondary)"><span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">store</span> ${esc(w.store)}</div>` : ''}
            <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">
              Kaufdatum: ${formatDate(w.purchase_date)} · Garantie bis: ${formatDate(w.warranty_end)}
            </div>
            ${w.notes ? `<div style="font-size:13px;color:var(--text-secondary);margin-top:4px">${esc(w.notes)}</div>` : ''}
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0">
            <button class="btn btn-secondary btn-sm" onclick="InventoryView.openWarrantyForm('${esc(w.id)}')" title="Bearbeiten">
              <span class="material-symbols-outlined">edit</span>
            </button>
            <button class="btn btn-danger btn-sm" onclick="InventoryView.deleteWarranty('${esc(w.id)}')" title="Löschen">
              <span class="material-symbols-outlined">delete</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function renderWarrantyForm() {
    const w = editingWarranty || {};
    const isEdit = !!w.id;
    return `
      <div class="card" style="margin-bottom:16px;border:2px solid var(--accent,#6c63ff)">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <strong>${isEdit ? 'Garantie bearbeiten' : 'Neue Garantie'}</strong>
          <button class="btn btn-secondary btn-sm" onclick="InventoryView.closeWarrantyForm()">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Produktname *</label>
            <input class="input" id="war-product" value="${esc(w.product_name)}" placeholder="z.B. Waschmaschine">
          </div>
          <div class="form-group">
            <label>Artikel verknüpfen</label>
            <select class="input" id="war-item">
              <option value="">– kein Artikel –</option>
              ${items.map(i => `<option value="${esc(i.id)}" ${w.item_id && String(w.item_id) === String(i.id) ? 'selected' : ''}>${esc(i.name)}</option>`).join('')}
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Kaufdatum</label>
            <input class="input" type="date" id="war-purchase" value="${esc(w.purchase_date || '')}">
          </div>
          <div class="form-group">
            <label>Garantie bis *</label>
            <input class="input" type="date" id="war-end" value="${esc(w.warranty_end || '')}">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Händler / Geschäft</label>
            <input class="input" id="war-store" value="${esc(w.store)}" placeholder="z.B. MediaMarkt">
          </div>
          <div class="form-group">
            <label>Beleg-URL</label>
            <input class="input" id="war-receipt" value="${esc(w.receipt_url)}" placeholder="https://...">
          </div>
        </div>
        <div class="form-group">
          <label>Notizen</label>
          <textarea class="input" id="war-notes" rows="2" placeholder="Optional">${esc(w.notes)}</textarea>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px">
          <button class="btn btn-primary" onclick="InventoryView.saveWarranty()">
            <span class="material-symbols-outlined">save</span> Speichern
          </button>
          <button class="btn btn-secondary" onclick="InventoryView.closeWarrantyForm()">Abbrechen</button>
        </div>
      </div>
    `;
  }

  function openWarrantyForm(id) {
    showWarrantyForm = true;
    editingWarranty = id ? (warranties.find(w => String(w.id) === String(id)) || {}) : {};
    renderGarantienTab();
    const el = document.getElementById('war-product');
    if (el) el.focus();
  }

  function closeWarrantyForm() {
    showWarrantyForm = false;
    editingWarranty = null;
    renderGarantienTab();
  }

  async function saveWarranty() {
    const product_name = document.getElementById('war-product')?.value?.trim();
    const warranty_end = document.getElementById('war-end')?.value;
    if (!product_name) { showToast('Produktname ist erforderlich', 'error'); return; }
    if (!warranty_end) { showToast('Garantiedatum ist erforderlich', 'error'); return; }

    const payload = {
      product_name,
      item_id: document.getElementById('war-item')?.value || null,
      purchase_date: document.getElementById('war-purchase')?.value || null,
      warranty_end,
      store: document.getElementById('war-store')?.value || '',
      receipt_url: document.getElementById('war-receipt')?.value || '',
      notes: document.getElementById('war-notes')?.value || '',
    };
    if (!payload.item_id) delete payload.item_id;

    try {
      if (editingWarranty?.id) {
        await Api.patch(`/inventory/warranties/${editingWarranty.id}`, payload);
        showToast('Garantie aktualisiert', 'success');
      } else {
        await Api.post('/inventory/warranties', payload);
        showToast('Garantie angelegt', 'success');
      }
      showWarrantyForm = false;
      editingWarranty = null;
      await loadGarantienTab();
    } catch (err) {
      showToast(err?.message || 'Fehler beim Speichern', 'error');
    }
  }

  async function deleteWarranty(id) {
    if (!confirm('Garantie wirklich löschen?')) return;
    try {
      await Api.delete(`/inventory/warranties/${id}`);
      showToast('Garantie gelöscht', 'success');
      await loadGarantienTab();
    } catch (err) {
      showToast(err?.message || 'Fehler beim Löschen', 'error');
    }
  }

  async function setWarrantyFilter(filter) {
    warrantyFilter = filter;
    const el = document.getElementById('inventory-content');
    if (el) el.innerHTML = '<div class="skeleton skeleton-card"></div>';
    await loadGarantienTab();
  }

  // ════════════════════════════════════════════════════════════
  // TAB 3: DOKUMENTE
  // ════════════════════════════════════════════════════════════

  async function loadDokumenteTab() {
    try {
      const qs = docSearchQuery ? `?q=${encodeURIComponent(docSearchQuery)}` : '';
      documents = await Api.get(`/inventory/documents/search${qs}`);
    } catch (err) {
      if (!err?.isOffline) showToast('Dokumente konnten nicht geladen werden', 'error');
      documents = [];
    }
    renderDokumenteTab();
  }

  function renderDokumenteTab() {
    const el = document.getElementById('inventory-content');
    if (!el) return;

    el.innerHTML = `
      <div style="margin-bottom:12px">
        <div style="display:flex;gap:8px">
          <input class="input" id="doc-search-input" placeholder="Dokumente durchsuchen..." value="${esc(docSearchQuery)}" style="flex:1"
                 oninput="InventoryView.handleDocSearch(this.value)">
          <button class="btn btn-secondary btn-sm" onclick="InventoryView.handleDocSearch('')" title="Suche zurücksetzen">
            <span class="material-symbols-outlined">clear</span>
          </button>
        </div>
      </div>
      ${documents.length === 0
        ? `<div class="empty-state">
            <span class="material-symbols-outlined">folder_open</span>
            <p>Keine Dokumente gefunden</p>
            <p style="font-size:13px;color:var(--text-secondary)">Dokumente werden über den Dokumenten-Scanner hinzugefügt.</p>
          </div>`
        : documents.map(renderDocumentCard).join('')
      }
    `;
  }

  function renderDocumentCard(doc) {
    const result = classifyResults[doc.id];
    const resultHtml = result ? `
      <div style="margin-top:8px;padding:8px;background:var(--surface-2,rgba(255,255,255,0.05));border-radius:6px;font-size:13px">
        ${result.action_type ? actionBadge(result.action_type) : ''}
        ${result.category ? `<span class="badge">${esc(result.category)}</span>` : ''}
        ${result.confidence != null ? `<span style="color:var(--text-secondary);margin-left:6px">${Math.round(result.confidence * 100)}% Konfidenz</span>` : ''}
        ${result.message ? `<div style="margin-top:4px;color:var(--text-secondary)">${esc(result.message)}</div>` : ''}
        ${result.suggested_action ? `<div style="margin-top:4px">${esc(result.suggested_action)}</div>` : ''}
        ${result.extracted_data ? `<div style="margin-top:4px;font-size:12px;color:var(--text-secondary)">${esc(JSON.stringify(result.extracted_data))}</div>` : ''}
      </div>
    ` : '';

    return `
      <div class="card" style="margin-bottom:8px" data-doc-id="${esc(doc.id)}">
        <div style="display:flex;align-items:flex-start;gap:12px">
          <span class="material-symbols-outlined" style="font-size:32px;color:var(--accent);flex-shrink:0">description</span>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;margin-bottom:2px">${esc(doc.filename || doc.title || 'Dokument')}</div>
            ${doc.summary ? `<div style="font-size:13px;color:var(--text-secondary);margin-bottom:4px">${esc(doc.summary)}</div>` : ''}
            ${doc.doc_type ? `<span class="badge" style="margin-right:4px">${esc(doc.doc_type)}</span>` : ''}
            ${doc.created_at ? `<span style="font-size:12px;color:var(--text-secondary)">${formatDate(doc.created_at)}</span>` : ''}
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
          <button class="btn btn-secondary btn-sm" onclick="InventoryView.classifyDocument('${esc(doc.id)}')" id="classify-btn-${esc(doc.id)}">
            <span class="material-symbols-outlined">auto_fix_high</span> Klassifizieren
          </button>
          <button class="btn btn-secondary btn-sm" onclick="InventoryView.scanToAction('${esc(doc.id)}')" id="scan-btn-${esc(doc.id)}">
            <span class="material-symbols-outlined">document_scanner</span> Scan → Aktion
          </button>
        </div>
        ${resultHtml}
      </div>
    `;
  }

  let docSearchDebounce = null;
  function handleDocSearch(value) {
    docSearchQuery = value.trim();
    const input = document.getElementById('doc-search-input');
    if (input && input.value !== value) input.value = value;
    clearTimeout(docSearchDebounce);
    docSearchDebounce = setTimeout(() => loadDokumenteTab(), 350);
  }

  async function classifyDocument(docId) {
    const btn = document.getElementById(`classify-btn-${docId}`);
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="material-symbols-outlined">hourglass_empty</span> Läuft...'; }
    try {
      const result = await Api.post('/inventory/documents/classify', { document_id: docId });
      classifyResults[docId] = result;
      showToast('Klassifizierung abgeschlossen', 'success');
      renderDokumenteTab();
    } catch (err) {
      showToast(err?.message || 'Klassifizierung fehlgeschlagen', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = '<span class="material-symbols-outlined">auto_fix_high</span> Klassifizieren'; }
    }
  }

  async function scanToAction(docId) {
    const btn = document.getElementById(`scan-btn-${docId}`);
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="material-symbols-outlined">hourglass_empty</span> Läuft...'; }
    try {
      const result = await Api.post('/inventory/documents/scan-to-action', { document_id: docId });
      classifyResults[docId] = { ...classifyResults[docId], ...result };
      showToast(result.message || 'Aktion erkannt', 'success');
      renderDokumenteTab();
    } catch (err) {
      showToast(err?.message || 'Scan-to-Aktion fehlgeschlagen', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = '<span class="material-symbols-outlined">document_scanner</span> Scan → Aktion'; }
    }
  }

  // ── Public API ───────────────────────────────────────────────

  return {
    render,
    switchTab,
    // Inventar
    openItemForm,
    closeItemForm,
    saveItem,
    deleteItem,
    uploadPhoto,
    applyRoomFilter,
    // Garantien
    openWarrantyForm,
    closeWarrantyForm,
    saveWarranty,
    deleteWarranty,
    setWarrantyFilter,
    // Dokumente
    handleDocSearch,
    classifyDocument,
    scanToAction,
  };
})();
