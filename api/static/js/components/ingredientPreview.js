/**
 * IngredientPreview – Wiederverwendbares Modal zur Zutaten-Vorschau
 * mit Portionsanpassung und Abwahl einzelner Zutaten.
 */
const IngredientPreview = (() => {
  let currentServings = 4;
  let baseServings = 4;
  let ingredients = [];
  let selected = new Set();
  let onConfirmCallback = null;
  let overlay = null;

  /**
   * Zeigt die Zutaten-Vorschau an.
   * @param {Object} opts
   * @param {string} opts.title - Rezeptname
   * @param {string} [opts.chefkochId] - Zum Nachladen der Zutaten
   * @param {Array} [opts.ingredients] - Vorab geladene Zutaten [{name, amount, unit}]
   * @param {number} [opts.baseServings=4] - Original-Portionen
   * @param {number} [opts.currentServings=4] - Gewuenschte Portionen
   * @param {Function} opts.onConfirm - Callback mit (scaledIngredients[])
   */
  async function show(opts) {
    currentServings = opts.currentServings || 4;
    baseServings = opts.baseServings || 4;
    onConfirmCallback = opts.onConfirm || null;
    ingredients = [];
    selected = new Set();

    _createOverlay(opts.title || 'Zutaten', true);

    if (opts.ingredients && opts.ingredients.length > 0) {
      ingredients = opts.ingredients;
      _initSelected();
      _renderContent(opts.title);
    } else if (opts.chefkochId) {
      try {
        const recipe = await Api.request(`/recipes/${opts.chefkochId}`);
        ingredients = recipe.ingredients || [];
        baseServings = recipe.servings || 4;
        if (!opts.currentServings) currentServings = baseServings;
        _initSelected();
        _renderContent(opts.title || recipe.title);
      } catch {
        _renderError();
      }
    } else {
      _renderError();
    }
  }

  function _initSelected() {
    selected = new Set(ingredients.map((_, i) => i));
  }

  function _createOverlay(title, loading) {
    if (overlay) overlay.remove();
    overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) close(); };
    if (loading) {
      overlay.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <h2 style="font-size:1.1rem;font-weight:600">${escapeHtml(title)}</h2>
            <button class="modal-close" onclick="IngredientPreview.close()"><span class="material-symbols-outlined">close</span></button>
          </div>
          <div style="text-align:center;padding:32px"><div class="skeleton skeleton-card" style="height:120px"></div></div>
        </div>
      `;
    }
    document.body.appendChild(overlay);
  }

  function _renderContent(title) {
    if (!overlay) return;

    if (ingredients.length === 0) {
      _renderError();
      return;
    }

    const modal = overlay.querySelector('.modal-content') || overlay;
    modal.innerHTML = `
      <div class="modal-header">
        <h2 style="font-size:1.1rem;font-weight:600">${escapeHtml(title)}</h2>
        <button class="modal-close" onclick="IngredientPreview.close()"><span class="material-symbols-outlined">close</span></button>
      </div>
      <div class="servings-control">
        <span>Portionen:</span>
        <input type="range" min="1" max="12" value="${currentServings}"
               oninput="IngredientPreview.updateServings(this.value)">
        <span id="ip-servings-display">${currentServings}</span>
      </div>
      <div class="ingredient-preview-actions mb-8">
        <button class="btn btn-sm btn-secondary" onclick="IngredientPreview.toggleAll()">
          <span class="material-symbols-outlined mi-sm" id="ip-toggle-icon">deselect</span>
          <span id="ip-toggle-label">Alle abwaehlen</span>
        </button>
      </div>
      <ul class="ingredient-list" id="ip-ingredient-list">
        ${_renderIngredients()}
      </ul>
      <div class="ingredient-preview-summary" id="ip-summary">${_summaryText()}</div>
      <div class="modal-actions">
        <button class="btn btn-primary" id="ip-confirm-btn" onclick="IngredientPreview.confirm()">
          <span class="material-symbols-outlined mi-sm">add_shopping_cart</span> Zur Einkaufsliste
        </button>
      </div>
    `;
  }

  function _renderError() {
    if (!overlay) return;
    const modal = overlay.querySelector('.modal-content') || overlay;
    modal.innerHTML = `
      <div class="modal-header">
        <h2 style="font-size:1.1rem;font-weight:600">Zutaten</h2>
        <button class="modal-close" onclick="IngredientPreview.close()"><span class="material-symbols-outlined">close</span></button>
      </div>
      <div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-muted)">grocery</span>
        <p style="color:var(--text-muted)">Keine Zutaten verfuegbar. Das Rezept konnte nicht geladen werden.</p>
      </div>
    `;
  }

  function _renderIngredients() {
    const factor = currentServings / baseServings;
    return ingredients.map((ing, i) => {
      const isSelected = selected.has(i);
      let amount = '';
      if (ing.amount) {
        const scaled = (parseFloat(ing.amount) || 0) * factor;
        amount = scaled % 1 === 0 ? scaled.toString() : scaled.toFixed(1);
        if (ing.unit) amount += ' ' + ing.unit;
      } else if (ing.unit) {
        amount = ing.unit;
      }
      return `
        <li class="${isSelected ? '' : 'ingredient-deselected'}" onclick="IngredientPreview.toggleItem(${i})" style="cursor:pointer">
          <span>
            <span class="material-symbols-outlined mi-sm" style="vertical-align:middle;margin-right:4px">${isSelected ? 'check_box' : 'check_box_outline_blank'}</span>
            ${escapeHtml(ing.name || '')}
          </span>
          <span class="ingredient-amount">${escapeHtml(amount)}</span>
        </li>`;
    }).join('');
  }

  function _summaryText() {
    return `${selected.size} von ${ingredients.length} Zutaten ausgewaehlt`;
  }

  function _refresh() {
    const list = document.getElementById('ip-ingredient-list');
    if (list) list.innerHTML = _renderIngredients();
    const summary = document.getElementById('ip-summary');
    if (summary) summary.textContent = _summaryText();
    const btn = document.getElementById('ip-confirm-btn');
    if (btn) btn.disabled = selected.size === 0;
    _updateToggleButton();
  }

  function _updateToggleButton() {
    const icon = document.getElementById('ip-toggle-icon');
    const label = document.getElementById('ip-toggle-label');
    if (!icon || !label) return;
    if (selected.size === ingredients.length) {
      icon.textContent = 'deselect';
      label.textContent = 'Alle abwaehlen';
    } else {
      icon.textContent = 'select_all';
      label.textContent = 'Alle auswaehlen';
    }
  }

  function updateServings(val) {
    currentServings = parseInt(val) || 4;
    const display = document.getElementById('ip-servings-display');
    if (display) display.textContent = currentServings;
    const list = document.getElementById('ip-ingredient-list');
    if (list) list.innerHTML = _renderIngredients();
  }

  function toggleItem(index) {
    if (selected.has(index)) {
      selected.delete(index);
    } else {
      selected.add(index);
    }
    _refresh();
  }

  function toggleAll() {
    if (selected.size === ingredients.length) {
      selected.clear();
    } else {
      selected = new Set(ingredients.map((_, i) => i));
    }
    _refresh();
  }

  function confirm() {
    if (selected.size === 0 || !onConfirmCallback) return;

    const factor = currentServings / baseServings;
    const scaledItems = [];
    selected.forEach(i => {
      const ing = ingredients[i];
      if (!ing) return;
      let scaledAmount = ing.amount || '';
      if (ing.amount && factor !== 1) {
        try {
          const num = parseFloat(ing.amount) * factor;
          scaledAmount = num % 1 === 0 ? num.toString() : num.toFixed(2);
        } catch { /* keep original */ }
      }
      scaledItems.push({
        name: ing.name,
        amount: scaledAmount || null,
        unit: ing.unit || null,
      });
    });

    onConfirmCallback(scaledItems);
    close();
  }

  function close() {
    if (overlay) {
      overlay.remove();
      overlay = null;
    }
  }

  return { show, close, updateServings, toggleItem, toggleAll, confirm };
})();
