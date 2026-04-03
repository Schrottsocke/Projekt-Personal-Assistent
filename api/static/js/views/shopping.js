/**
 * Shopping View – Modern shopping list with smart input, categories, inline editing,
 * undo delete, progress tracking, swipe gestures, animations.
 */
const ShoppingView = (() => {
  let showChecked = true;
  let items = [];
  let editingId = null;
  let collapsedCats = {};

  // Undo state
  let pendingDeletes = {}; // id -> { item, timer }

  // Swipe state
  let swipeStartX = 0;
  let swipeCurrentX = 0;
  let swipingEl = null;
  const SWIPE_THRESHOLD = 80;

  // Category icon mapping
  const CATEGORY_ICONS = {
    'Obst': 'nutrition',
    'Gemüse': 'eco',
    'Milchprodukte': 'water_drop',
    'Fleisch & Fisch': 'restaurant',
    'Brot & Backwaren': 'bakery_dining',
    'Getränke': 'local_cafe',
    'Gewürze & Öle': 'deployed_code',
    'Tiefkühl': 'ac_unit',
    'Konserven & Trockenware': 'inventory_2',
    'Haushalt': 'cleaning_services',
    'Sonstiges': 'category',
  };

  // ── Smart Input Parsing ──

  const UNIT_PATTERN = /^(\d+(?:[.,]\d+)?)\s*(x|kg|g|ml|l|stk|stück|pkg|packung|bund|dose|dosen|fl|flasche|flaschen|becher|beutel|glas|gläser|paar|scheiben|tüte|tüten|kasten)?\s+(.+)$/i;
  const UNIT_NOSPACE = /^(\d+(?:[.,]\d+)?)(kg|g|ml|l)\s+(.+)$/i;

  function parseItemInput(text) {
    text = text.trim();
    if (!text) return null;

    // Try "2x Milch", "3 Äpfel", "500g Mehl"
    let m = text.match(UNIT_PATTERN);
    if (m) {
      let unit = (m[2] || '').toLowerCase();
      if (unit === 'x') unit = '';
      return { quantity: m[1], unit: unit || null, name: m[3].trim() };
    }

    // Try "500g Mehl" (no space between number and unit)
    m = text.match(UNIT_NOSPACE);
    if (m) {
      return { quantity: m[1], unit: m[2].toLowerCase(), name: m[3].trim() };
    }

    return { quantity: null, unit: null, name: text };
  }

  function getCategoryIcon(cat) {
    return CATEGORY_ICONS[cat] || 'category';
  }

  // ── Render ──

  async function render(container) {
    container.innerHTML = `
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">shopping_cart</span> Einkaufsliste
      </div>
      <div class="shopping-input-area">
        <div class="shopping-input-row">
          <input type="text" id="shopping-input"
                 placeholder="z.\u202FB. 2x Milch, Brot, 500g Mehl\u2026"
                 aria-label="Artikel hinzufügen"
                 onkeydown="if(event.key==='Enter') ShoppingView.addItem()">
          <button class="btn btn-primary" onclick="ShoppingView.addItem()" aria-label="Artikel hinzufügen">
            <span class="material-symbols-outlined" style="font-size:20px">add</span>
            Hinzufügen
          </button>
        </div>
        <div class="shopping-progress-row" id="shopping-progress"></div>
      </div>
      <div class="shopping-actions" id="shopping-actions"></div>
      <div id="shopping-list">
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
      </div>
    `;

    await loadItems();
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
    const actionsEl = document.getElementById('shopping-actions');
    if (!listEl) return;

    const total = items.length;
    const checked = items.filter(i => i.checked).length;
    const unchecked = total - checked;
    const pct = total > 0 ? Math.round((checked / total) * 100) : 0;

    // Progress bar
    if (progressEl) {
      if (total === 0) {
        progressEl.innerHTML = '';
      } else {
        const isComplete = pct === 100;
        let statusText;
        if (isComplete) {
          statusText = 'Alles erledigt!';
        } else if (checked === 0) {
          statusText = `${total} Artikel auf der Liste`;
        } else {
          statusText = `${checked} von ${total} erledigt \u2013 noch ${unchecked} offen`;
        }
        progressEl.innerHTML = `
          <div class="shopping-progress-bar">
            <div class="shopping-progress-fill${isComplete ? ' complete' : ''}" style="width:${pct}%"></div>
          </div>
          <div class="shopping-progress-text">
            <span>${statusText}</span>
            <span>${pct}%</span>
          </div>
        `;
      }
    }

    // Action buttons
    if (actionsEl) {
      let actionsHtml = '';
      if (unchecked > 0) {
        actionsHtml += `<button class="btn btn-secondary" onclick="ShoppingView.checkAll()">
          <span class="material-symbols-outlined">done_all</span> Alle abhaken
        </button>`;
      }
      actionsHtml += `<button class="btn btn-secondary" onclick="ShoppingView.toggleShowChecked()" id="toggle-checked-btn">
        <span class="material-symbols-outlined">${showChecked ? 'visibility_off' : 'visibility'}</span>
        ${showChecked ? 'Erledigte ausblenden' : 'Erledigte anzeigen'}
      </button>`;
      if (checked > 0) {
        actionsHtml += `<button class="btn btn-secondary" onclick="ShoppingView.clearChecked()" style="color:var(--error)">
          <span class="material-symbols-outlined">delete_sweep</span> Erledigte löschen
        </button>`;
      }
      if (unchecked > 0) {
        actionsHtml += `<button class="btn btn-secondary" onclick="ShoppingView.saveAsTemplate()">
          <span class="material-symbols-outlined">library_add</span> Als Vorlage
        </button>`;
      }
      actionsEl.innerHTML = actionsHtml;
    }

    // Filter visible items
    const visible = showChecked ? items : items.filter(i => !i.checked);

    if (visible.length === 0) {
      const isAllDone = total > 0 && checked === total;
      const isFiltered = !showChecked && total > 0;
      let icon, title, subtitle;
      if (total === 0) {
        icon = 'shopping_cart';
        title = 'Deine Einkaufsliste ist leer';
        subtitle = 'Füge oben deinen ersten Artikel hinzu';
      } else if (isAllDone) {
        icon = 'check_circle';
        title = 'Alles eingekauft!';
        subtitle = 'Gut gemacht \u2013 deine Liste ist abgehakt';
      } else if (isFiltered) {
        icon = 'filter_list';
        title = 'Nur erledigte Artikel vorhanden';
        subtitle = 'Blende erledigte Artikel ein, um sie zu sehen';
      } else {
        icon = 'shopping_cart';
        title = 'Keine Artikel sichtbar';
        subtitle = '';
      }
      listEl.innerHTML = `<div class="shopping-empty">
        <span class="material-symbols-outlined">${icon}</span>
        <div class="empty-title">${title}</div>
        ${subtitle ? `<div class="empty-subtitle">${subtitle}</div>` : ''}
      </div>`;
      return;
    }

    // Group by category
    const groups = {};
    visible.forEach(item => {
      const cat = item.category || 'Sonstiges';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(item);
    });

    const sortedCats = Object.keys(groups).sort((a, b) => {
      if (a === 'Sonstiges') return 1;
      if (b === 'Sonstiges') return -1;
      return a.localeCompare(b, 'de');
    });

    let html = '';
    sortedCats.forEach(cat => {
      const isCollapsed = collapsedCats[cat] === true;
      const catItems = groups[cat];
      const count = catItems.length;
      const catChecked = catItems.filter(i => i.checked).length;
      const icon = getCategoryIcon(cat);

      html += `<div class="category-header" onclick="ShoppingView.toggleCategory('${escapeHtml(cat)}')">
        <span class="material-symbols-outlined category-icon">${icon}</span>
        <span class="category-name">${escapeHtml(cat)}</span>
        <span class="badge badge-accent">${catChecked > 0 ? `${catChecked}/` : ''}${count}</span>
        <span class="material-symbols-outlined category-chevron ${isCollapsed ? 'collapsed' : ''}">expand_more</span>
      </div>`;

      if (!isCollapsed) {
        catItems.forEach(item => {
          html += renderItem(item);
        });
      }
    });

    listEl.innerHTML = html;

    // Focus edit field if editing
    if (editingId) {
      const nameInput = document.getElementById(`edit-name-${editingId}`);
      if (nameInput) nameInput.focus();
    }
  }

  function renderItem(item) {
    const isEditing = editingId === item.id;
    const detail = [item.quantity, item.unit].filter(Boolean).join('\u00A0');

    if (isEditing) {
      return `
        <div class="shopping-item" data-id="${item.id}">
          <div class="shopping-edit-fields">
            <div class="shopping-edit-row">
              <input type="text" id="edit-name-${item.id}" class="edit-name-input"
                     value="${escapeHtml(item.name)}" placeholder="Artikelname"
                     aria-label="Artikelname bearbeiten"
                     onkeydown="if(event.key==='Enter') ShoppingView.saveEdit(${item.id}); if(event.key==='Escape') ShoppingView.cancelEdit()">
            </div>
            <div class="shopping-edit-row">
              <input type="text" id="edit-qty-${item.id}" class="edit-qty-input"
                     value="${escapeHtml(item.quantity || '')}" placeholder="Menge"
                     aria-label="Menge"
                     onkeydown="if(event.key==='Enter') ShoppingView.saveEdit(${item.id}); if(event.key==='Escape') ShoppingView.cancelEdit()">
              <input type="text" id="edit-unit-${item.id}" class="edit-unit-input"
                     value="${escapeHtml(item.unit || '')}" placeholder="Einheit"
                     aria-label="Einheit"
                     onkeydown="if(event.key==='Enter') ShoppingView.saveEdit(${item.id}); if(event.key==='Escape') ShoppingView.cancelEdit()">
              <div class="shopping-edit-actions">
                <button class="btn btn-sm btn-primary" onclick="ShoppingView.saveEdit(${item.id})" aria-label="Speichern">
                  <span class="material-symbols-outlined" style="font-size:18px">check</span>
                </button>
                <button class="btn btn-sm btn-secondary" onclick="ShoppingView.cancelEdit()" aria-label="Abbrechen">
                  <span class="material-symbols-outlined" style="font-size:18px">close</span>
                </button>
              </div>
            </div>
          </div>
        </div>`;
    }

    return `
      <div class="shopping-item swipe-item ${item.checked ? 'checked' : ''}" data-id="${item.id}"
           ontouchstart="ShoppingView.swipeStart(event)" ontouchmove="ShoppingView.swipeMove(event)" ontouchend="ShoppingView.swipeEnd(event)">
        <label class="shopping-item-check" aria-label="${item.checked ? 'Als offen markieren' : 'Als erledigt markieren'}">
          <input type="checkbox" ${item.checked ? 'checked' : ''}
                 onchange="ShoppingView.toggleItem(${item.id}, this.checked)">
        </label>
        <div class="shopping-item-content" onclick="ShoppingView.editItem(${item.id})">
          <div class="shopping-item-name">${escapeHtml(item.name)}</div>
          ${detail ? `<div class="shopping-item-meta">${escapeHtml(detail)}</div>` : ''}
        </div>
        <div class="shopping-item-actions">
          <button onclick="ShoppingView.editItem(${item.id})" aria-label="Bearbeiten" title="Bearbeiten">
            <span class="material-symbols-outlined">edit</span>
          </button>
          <button class="delete-btn" onclick="ShoppingView.deleteItem(${item.id})" aria-label="Löschen" title="Löschen">
            <span class="material-symbols-outlined">delete</span>
          </button>
        </div>
      </div>`;
  }

  // ── Category Toggle ──

  function toggleCategory(cat) {
    collapsedCats[cat] = !collapsedCats[cat];
    renderList();
  }

  // ── Swipe Gesture Handling ──

  function swipeStart(e) {
    const touch = e.touches[0];
    swipeStartX = touch.clientX;
    swipeCurrentX = touch.clientX;
    swipingEl = e.currentTarget;
  }

  function swipeMove(e) {
    if (!swipingEl) return;
    const touch = e.touches[0];
    swipeCurrentX = touch.clientX;
    const diff = swipeStartX - swipeCurrentX;

    if (diff > 10) {
      const shift = Math.min(diff, 120);
      swipingEl.style.transform = `translateX(-${shift}px)`;
      swipingEl.style.transition = 'none';
    }
  }

  function swipeEnd() {
    if (!swipingEl) return;
    const diff = swipeStartX - swipeCurrentX;
    const id = parseInt(swipingEl.dataset.id);

    swipingEl.style.transition = 'transform 0.2s ease';
    swipingEl.style.transform = '';

    if (diff > SWIPE_THRESHOLD && id) {
      const item = items.find(i => i.id === id);
      if (item) {
        toggleItem(id, !item.checked);
      }
    }

    swipingEl = null;
  }

  // ── CRUD Operations ──

  async function addItem() {
    const input = document.getElementById('shopping-input');
    const raw = input.value.trim();
    if (!raw) return;

    const parsed = parseItemInput(raw);
    if (!parsed) return;

    input.value = '';

    try {
      const body = { name: parsed.name };
      if (parsed.quantity) body.quantity = parsed.quantity;
      if (parsed.unit) body.unit = parsed.unit;
      const newItem = await Api.addShoppingItem(parsed.name);
      // If we parsed quantity/unit, update right away
      if (parsed.quantity || parsed.unit) {
        const updated = await Api.updateShoppingItem(newItem.id, {
          quantity: parsed.quantity,
          unit: parsed.unit,
        });
        items.unshift(updated);
      } else {
        items.unshift(newItem);
      }
      renderList();
    } catch (err) {
      showToast('Fehler beim Hinzufügen: ' + err.message, 'error');
    }
    input.focus();
  }

  function editItem(id) {
    editingId = id;
    renderList();
  }

  function cancelEdit() {
    editingId = null;
    renderList();
  }

  async function saveEdit(id) {
    const nameInput = document.getElementById(`edit-name-${id}`);
    const qtyInput = document.getElementById(`edit-qty-${id}`);
    const unitInput = document.getElementById(`edit-unit-${id}`);
    if (!nameInput) return;

    const name = nameInput.value.trim();
    if (!name) {
      nameInput.classList.add('input-error');
      return;
    }

    const data = {
      name,
      quantity: qtyInput ? (qtyInput.value.trim() || null) : null,
      unit: unitInput ? (unitInput.value.trim() || null) : null,
    };

    editingId = null;

    try {
      const updated = await Api.updateShoppingItem(id, data);
      const idx = items.findIndex(i => i.id === id);
      if (idx !== -1) items[idx] = updated;
      renderList();
    } catch (err) {
      showToast('Fehler beim Speichern: ' + err.message, 'error');
      await loadItems();
    }
  }

  async function toggleItem(id, checked) {
    // Optimistic update
    const item = items.find(i => i.id === id);
    if (item) item.checked = checked;
    renderList();

    try {
      await Api.toggleShoppingItem(id, checked);
    } catch (err) {
      // Revert on error
      if (item) item.checked = !checked;
      renderList();
      showToast('Fehler: ' + err.message, 'error');
    }
  }

  async function checkAll() {
    const uncheckedItems = items.filter(i => !i.checked);
    if (uncheckedItems.length === 0) return;

    // Optimistic update
    uncheckedItems.forEach(i => { i.checked = true; });
    renderList();

    try {
      await Promise.all(uncheckedItems.map(i => Api.toggleShoppingItem(i.id, true)));
    } catch (err) {
      showToast('Fehler beim Abhaken: ' + err.message, 'error');
      await loadItems();
    }
  }

  function deleteItem(id) {
    const item = items.find(i => i.id === id);
    if (!item) return;

    // Remove from UI immediately
    const el = document.querySelector(`.shopping-item[data-id="${id}"]`);
    if (el) {
      el.classList.add('removing');
    }

    // Cancel any existing pending delete for this item
    if (pendingDeletes[id]) {
      clearTimeout(pendingDeletes[id].timer);
      delete pendingDeletes[id];
    }

    // Remove from items array after animation
    setTimeout(() => {
      items = items.filter(i => i.id !== id);
      renderList();
    }, 250);

    // Store for undo
    pendingDeletes[id] = {
      item: { ...item },
      timer: setTimeout(async () => {
        try {
          await Api.deleteShoppingItem(id);
        } catch (err) {
          // Item may already be gone
        }
        delete pendingDeletes[id];
      }, 5000),
    };

    // Show undo toast
    showUndoToast(`„${item.name}" gelöscht`, id);
  }

  function undoDelete(id) {
    const pending = pendingDeletes[id];
    if (!pending) return;

    clearTimeout(pending.timer);
    items.unshift(pending.item);
    delete pendingDeletes[id];
    renderList();

    // Remove toast
    const toastEl = document.getElementById(`undo-toast-${id}`);
    if (toastEl) toastEl.remove();
  }

  async function clearChecked() {
    const count = items.filter(i => i.checked).length;
    if (count === 0) return;
    if (!confirm(`${count} erledigte Artikel endgültig löschen?`)) return;

    try {
      await Api.clearCheckedItems();
      items = items.filter(i => !i.checked);
      renderList();
      showToast(`${count} Artikel gelöscht`, 'success');
    } catch (err) {
      showToast('Fehler beim Löschen: ' + err.message, 'error');
      await loadItems();
    }
  }

  function toggleShowChecked() {
    showChecked = !showChecked;
    renderList();
  }

  // ── Toast Helpers ──

  function showToast(message, type) {
    if (typeof Toast !== 'undefined' && Toast.show) {
      Toast.show(message, type);
    }
  }

  function showUndoToast(message, itemId) {
    const container = document.querySelector('.toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = 'toast toast-info';
    toast.id = `undo-toast-${itemId}`;
    toast.innerHTML = `<div class="toast-undo">
      <span>${escapeHtml(message)}</span>
      <button onclick="ShoppingView.undoDelete(${itemId})">Rückgängig</button>
    </div>`;
    container.appendChild(toast);

    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 5000);
  }

  function createToastContainer() {
    let c = document.querySelector('.toast-container');
    if (!c) {
      c = document.createElement('div');
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  // ── Save as Template ──

  async function saveAsTemplate() {
    const name = prompt('Name fuer die Vorlage:');
    if (!name || !name.trim()) return;
    try {
      await Api.request('/templates/from-shopping', {
        method: 'POST',
        body: { name: name.trim(), description: '' },
      });
      showToast('Vorlage gespeichert', 'success');
    } catch (err) {
      showToast(err.message || 'Fehler beim Speichern', 'error');
    }
  }

  // ── Public API ──

  return {
    render, addItem, toggleItem, deleteItem, clearChecked, toggleShowChecked,
    editItem, saveEdit, cancelEdit, toggleCategory, checkAll, undoDelete,
    swipeStart, swipeMove, swipeEnd, saveAsTemplate,
  };
})();
