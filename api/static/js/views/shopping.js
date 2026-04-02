/**
 * Shopping View – CRUD, Toggle, Categories, Inline Quantity Edit
 */
const ShoppingView = (() => {
  let showChecked = true;
  let items = [];
  let editingId = null;

  async function render(container) {
    container.innerHTML = `
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">shopping_cart</span> Einkaufsliste
      </div>
      <div class="input-group">
        <input type="text" id="shopping-input" placeholder="Neuen Artikel hinzufügen…"
               onkeydown="if(event.key==='Enter') ShoppingView.addItem()">
        <button class="btn btn-primary" onclick="ShoppingView.addItem()">+</button>
      </div>
      <div class="shopping-toolbar">
        <div id="shopping-progress"></div>
        <div>
          <button class="btn btn-sm btn-secondary" onclick="ShoppingView.toggleShowChecked()" id="toggle-checked-btn">
            Erledigte ausblenden
          </button>
          <button class="btn btn-sm btn-danger" onclick="ShoppingView.clearChecked()" id="clear-checked-btn">
            Erledigte löschen
          </button>
        </div>
      </div>
      <div id="shopping-list"><div class="loading"><div class="spinner"></div> Laden…</div></div>
    `;

    await loadItems();
    // #459: Ensure input has focus after render
    const input = document.getElementById('shopping-input');
    if (input) input.focus();
  }

  async function loadItems() {
    try {
      items = await Api.getShoppingItems(true);
      renderList();
    } catch (err) {
      document.getElementById('shopping-list').innerHTML = `
        <div class="error-state"><p>${err.message}</p>
          <button class="btn btn-secondary" onclick="ShoppingView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

  function renderList() {
    const listEl = document.getElementById('shopping-list');
    const progressEl = document.getElementById('shopping-progress');
    if (!listEl) return;

    const total = items.length;
    const checked = items.filter(i => i.checked).length;
    const pct = total > 0 ? Math.round((checked / total) * 100) : 0;

    if (progressEl) {
      progressEl.innerHTML = `
        <span style="font-size:0.85rem;color:var(--text-secondary)">${checked}/${total} erledigt (${pct}%)</span>
      `;
    }

    const visible = showChecked ? items : items.filter(i => !i.checked);

    if (visible.length === 0) {
      listEl.innerHTML = `<div class="empty-state">${total === 0 ? 'Einkaufsliste ist leer' : 'Alle Artikel erledigt'}</div>`;
      return;
    }

    // Group by category
    const groups = {};
    visible.forEach(item => {
      const cat = item.category || 'Sonstiges';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(item);
    });

    let html = '';
    const sortedCats = Object.keys(groups).sort((a, b) => {
      if (a === 'Sonstiges') return 1;
      if (b === 'Sonstiges') return -1;
      return a.localeCompare(b, 'de');
    });

    sortedCats.forEach(cat => {
      html += `<div class="category-header">${escapeHtml(cat)}</div>`;
      groups[cat].forEach(item => {
        const detail = [item.quantity, item.unit].filter(Boolean).join(' ');
        const isEditing = editingId === item.id;
        html += `
          <div class="shopping-item ${item.checked ? 'checked' : ''}">
            <input type="checkbox" class="shopping-checkbox"
                   ${item.checked ? 'checked' : ''}
                   onchange="ShoppingView.toggleItem(${item.id}, this.checked)">
            <span class="item-name">${escapeHtml(item.name)}</span>
            ${isEditing ? `
              <span class="item-detail-edit">
                <input type="text" id="edit-qty-${item.id}" value="${escapeHtml(item.quantity || '')}"
                       placeholder="Menge" size="4"
                       onkeydown="if(event.key==='Enter') ShoppingView.saveQuantity(${item.id})">
                <input type="text" id="edit-unit-${item.id}" value="${escapeHtml(item.unit || '')}"
                       placeholder="Einheit" size="5"
                       onkeydown="if(event.key==='Enter') ShoppingView.saveQuantity(${item.id})">
                <button class="btn btn-sm btn-primary" onclick="ShoppingView.saveQuantity(${item.id})">&#10003;</button>
                <button class="btn btn-sm btn-secondary" onclick="ShoppingView.cancelEdit()">&#10005;</button>
              </span>
            ` : `
              <span class="item-detail" onclick="ShoppingView.editQuantity(${item.id})" title="Menge bearbeiten" style="cursor:pointer">
                ${detail ? escapeHtml(detail) : '<span style="opacity:0.4;font-size:0.8rem">+ Menge</span>'}
              </span>
            `}
            <button class="item-delete" onclick="ShoppingView.deleteItem(${item.id})" title="Löschen"><span class="material-symbols-outlined">delete</span></button>
          </div>
        `;
      });
    });

    listEl.innerHTML = html;

    // Focus first edit input if editing
    if (editingId) {
      const qtyInput = document.getElementById(`edit-qty-${editingId}`);
      if (qtyInput) qtyInput.focus();
    }

    // Update toggle button text
    const btn = document.getElementById('toggle-checked-btn');
    if (btn) btn.textContent = showChecked ? 'Erledigte ausblenden' : 'Erledigte einblenden';
  }

  async function addItem() {
    const input = document.getElementById('shopping-input');
    const name = input.value.trim();
    if (!name) return;

    input.value = '';
    try {
      const newItem = await Api.addShoppingItem(name);
      items.unshift(newItem);
      renderList();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
    // #459: Restore focus to input after adding
    input.focus();
  }

  function editQuantity(id) {
    editingId = id;
    renderList();
  }

  function cancelEdit() {
    editingId = null;
    renderList();
  }

  async function saveQuantity(id) {
    const qtyInput = document.getElementById(`edit-qty-${id}`);
    const unitInput = document.getElementById(`edit-unit-${id}`);
    if (!qtyInput || !unitInput) return;

    const quantity = qtyInput.value.trim() || null;
    const unit = unitInput.value.trim() || null;

    editingId = null;

    try {
      const updated = await Api.updateShoppingItem(id, { quantity, unit });
      const idx = items.findIndex(i => i.id === id);
      if (idx !== -1) items[idx] = updated;
      renderList();
    } catch (err) {
      alert('Fehler beim Speichern: ' + err.message);
      await loadItems();
    }
  }

  async function toggleItem(id, checked) {
    try {
      await Api.toggleShoppingItem(id, checked);
      const item = items.find(i => i.id === id);
      if (item) item.checked = checked;
      renderList();
    } catch (err) {
      alert('Fehler: ' + err.message);
      await loadItems();
    }
  }

  async function deleteItem(id) {
    try {
      await Api.deleteShoppingItem(id);
      items = items.filter(i => i.id !== id);
      renderList();
    } catch (err) {
      alert('Fehler beim Löschen: ' + err.message);
      await loadItems();
    }
  }

  async function clearChecked() {
    const count = items.filter(i => i.checked).length;
    if (count === 0) return;
    if (!confirm(`${count} erledigte Artikel löschen?`)) return;

    try {
      await Api.clearCheckedItems();
      items = items.filter(i => !i.checked);
      renderList();
    } catch (err) {
      alert('Fehler beim Löschen: ' + err.message);
      await loadItems();
    }
  }

  function toggleShowChecked() {
    showChecked = !showChecked;
    renderList();
  }

  return { render, addItem, toggleItem, deleteItem, clearChecked, toggleShowChecked, editQuantity, saveQuantity, cancelEdit };
})();
