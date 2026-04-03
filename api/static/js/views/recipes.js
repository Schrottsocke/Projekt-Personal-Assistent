/**
 * Recipes View – Search, Saved, Detail Modal
 * Improved: robust image fallbacks, quick-filter chips, friendly empty states
 */
const RecipesView = (() => {
  const SEARCH_STORAGE_KEY = 'recipes_search_state';
  const SEARCH_TTL_MS = 30 * 60 * 1000; // 30 minutes

  const QUICK_FILTERS = [
    { label: 'Pasta', icon: 'lunch_dining' },
    { label: 'Schnell & einfach', icon: 'bolt' },
    { label: 'Vegetarisch', icon: 'eco' },
    { label: 'Salat', icon: 'nutrition' },
    { label: 'Suppe', icon: 'soup_kitchen' },
    { label: 'Backen', icon: 'bakery_dining' },
    { label: 'Frühstück', icon: 'egg_alt' },
    { label: 'Abendessen', icon: 'dinner_dining' },
  ];

  let activeTab = 'search';
  let searchResults = [];
  let savedRecipes = [];
  let searchTimer = null;
  let currentServings = 4;

  // ── Image fallback helpers ──────────────────────────

  function imgFallbackHtml(title, cssClass) {
    const cls = cssClass || 'recipe-img-fallback';
    const initial = (title || '?').charAt(0).toUpperCase();
    return `<div class="${cls}"><span>${escapeHtml(initial)}</span><span class="material-symbols-outlined">restaurant</span></div>`;
  }

  function handleImgError(img) {
    img.onerror = null;
    const title = img.dataset.title || '?';
    const isModal = img.classList.contains('modal-img');
    const fallback = document.createElement('div');
    fallback.className = isModal ? 'modal-img-fallback' : 'recipe-img-fallback';
    const initial = (title || '?').charAt(0).toUpperCase();
    fallback.innerHTML = `<span>${escapeHtml(initial)}</span><span class="material-symbols-outlined">restaurant</span>`;
    img.replaceWith(fallback);
  }

  function renderImage(imageUrl, title, cssClass) {
    if (!imageUrl) {
      if (title) console.warn('[Recipes] Rezept ohne Bild-URL:', title);
      return imgFallbackHtml(title, cssClass === 'modal-img' ? 'modal-img-fallback' : 'recipe-img-fallback');
    }
    const cls = cssClass || 'recipe-img';
    const safeTitle = escapeHtml(title || '');
    return `<img class="${cls}" src="${escapeHtml(imageUrl)}" alt="${safeTitle}" loading="lazy" referrerpolicy="no-referrer" data-title="${safeTitle}" onerror="RecipesView._handleImgError(this)">`;
  }

  // ── Search state persistence ────────────────────────

  function saveSearchState(query, results) {
    try {
      sessionStorage.setItem(SEARCH_STORAGE_KEY, JSON.stringify({
        query: query,
        results: results,
        timestamp: Date.now()
      }));
    } catch (_) { /* quota exceeded – ignore */ }
  }

  function loadSearchState() {
    try {
      const raw = sessionStorage.getItem(SEARCH_STORAGE_KEY);
      if (!raw) return null;
      const state = JSON.parse(raw);
      if (Date.now() - state.timestamp > SEARCH_TTL_MS) {
        sessionStorage.removeItem(SEARCH_STORAGE_KEY);
        return null;
      }
      return state;
    } catch (_) { return null; }
  }

  function clearSearchState() {
    sessionStorage.removeItem(SEARCH_STORAGE_KEY);
  }

  // ── Quick-filter chips ──────────────────────────────

  function renderChips() {
    return `<div class="recipe-chips">${QUICK_FILTERS.map(f =>
      `<button class="recipe-chip" onclick="RecipesView.applyChip('${escapeHtml(f.label)}')" title="${escapeHtml(f.label)}"><span class="material-symbols-outlined mi-sm">${f.icon}</span> ${escapeHtml(f.label)}</button>`
    ).join('')}</div>`;
  }

  function applyChip(label) {
    const input = document.getElementById('recipe-search');
    if (input) input.value = label;
    doSearch(label);
  }

  // ── Empty states ────────────────────────────────────

  function emptyStateHtml(icon, title, text, extras) {
    return `<div class="recipe-empty-state">
      <span class="material-symbols-outlined">${icon}</span>
      <h3>${title}</h3>
      <p>${text}</p>
      ${extras || ''}
    </div>`;
  }

  function searchEmptyState() {
    return emptyStateHtml(
      'search',
      'Entdecke neue Rezepte',
      'Tippe einen Begriff ein oder wähle einen Vorschlag.',
      renderChips()
    );
  }

  function noResultsState(query) {
    return emptyStateHtml(
      'sentiment_dissatisfied',
      `Keine Treffer für "${escapeHtml(query)}"`,
      'Versuch einen anderen Begriff oder stöbere in den Vorschlägen.',
      renderChips()
    );
  }

  function savedEmptyState() {
    return emptyStateHtml(
      'bookmark_border',
      'Noch keine Rezepte gespeichert',
      'Suche nach Rezepten und speichere deine Favoriten.'
    );
  }

  // ── Main render ─────────────────────────────────────

  async function render(container) {
    container.innerHTML = `
      <div class="section-header"><span class="section-icon material-symbols-outlined">restaurant</span> Rezepte</div>
      <div class="tabs">
        <button class="tab active" data-tab="search" onclick="RecipesView.switchTab('search')">Suche</button>
        <button class="tab" data-tab="saved" onclick="RecipesView.switchTab('saved')">Gespeichert</button>
      </div>
      <div id="recipes-content"></div>
    `;
    activeTab = 'search';
    renderTab();
  }

  function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    renderTab();
  }

  function renderTab() {
    if (activeTab === 'search') renderSearch();
    else renderSaved();
  }

  // ── Search tab ──────────────────────────────────────

  function renderSearch() {
    const el = document.getElementById('recipes-content');
    const saved = loadSearchState();
    el.innerHTML = `
      <div class="recipe-search-header">
        <h2>Was kochst du heute?</h2>
      </div>
      <div class="input-group mb-16">
        <input type="search" id="recipe-search" placeholder="Suche nach Zutaten, Gerichten oder Kategorien"
               oninput="RecipesView.onSearch(this.value)" value="${saved ? escapeHtml(saved.query) : ''}">
      </div>
      <div id="recipe-results">
        ${searchEmptyState()}
      </div>
    `;
    if (saved && saved.results && saved.results.length > 0) {
      searchResults = saved.results;
      renderRecipeGrid(document.getElementById('recipe-results'), searchResults, false);
    }
  }

  function onSearch(query) {
    clearTimeout(searchTimer);
    if (!query.trim()) {
      document.getElementById('recipe-results').innerHTML = searchEmptyState();
      return;
    }
    searchTimer = setTimeout(() => doSearch(query.trim()), 400);
  }

  async function doSearch(query) {
    const el = document.getElementById('recipe-results');
    el.innerHTML = '<div class="loading"><div class="spinner"></div> Suche…</div>';

    try {
      searchResults = await Api.searchRecipes(query);
      if (searchResults.length === 0) {
        el.innerHTML = noResultsState(query);
        return;
      }
      renderRecipeGrid(el, searchResults, false);
      saveSearchState(query, searchResults);
    } catch (err) {
      el.innerHTML = `<div class="error-state"><p>${escapeHtml(err.message)}</p></div>`;
    }
  }

  // ── Saved tab ───────────────────────────────────────

  async function renderSaved() {
    const el = document.getElementById('recipes-content');
    el.innerHTML = '<div class="loading"><div class="spinner"></div> Laden…</div>';

    try {
      savedRecipes = await Api.getSavedRecipes();

      // Update tab label with count
      const savedTab = document.querySelector('.tab[data-tab="saved"]');
      if (savedTab) {
        savedTab.textContent = savedRecipes.length > 0
          ? `Gespeichert (${savedRecipes.length})`
          : 'Gespeichert';
      }

      if (savedRecipes.length === 0) {
        el.innerHTML = savedEmptyState();
        return;
      }
      renderRecipeGrid(el, savedRecipes, true);
    } catch (err) {
      el.innerHTML = `<div class="error-state"><p>${escapeHtml(err.message)}</p></div>`;
    }
  }

  // ── Recipe grid ─────────────────────────────────────

  function renderRecipeGrid(el, recipes, isSaved) {
    let html = '<div class="recipe-grid">';
    recipes.forEach((r, idx) => {
      const time = (r.prep_time || 0) + (r.cook_time || 0);

      html += `
        <div class="recipe-card" onclick="RecipesView.showDetail(${idx}, ${isSaved})">
          ${renderImage(r.image_url, r.title, 'recipe-img')}
          <div class="recipe-info">
            <div class="recipe-title">${escapeHtml(r.title || 'Ohne Titel')}</div>
            <div class="recipe-meta">
              ${time > 0 ? `<span><span class="material-symbols-outlined mi-sm">schedule</span> ${time} Min.</span>` : ''}
              ${r.difficulty ? `<span>${escapeHtml(r.difficulty)}</span>` : ''}
              ${isSaved ? `<button class="btn-icon" onclick="event.stopPropagation();RecipesView.toggleFavorite(${idx})" title="${r.is_favorite ? 'Favorit entfernen' : 'Als Favorit markieren'}" style="margin-left:auto">
                <span class="material-symbols-outlined" style="color:${r.is_favorite ? 'var(--error)' : 'var(--text-secondary)'};font-size:20px">${r.is_favorite ? 'favorite' : 'favorite_border'}</span>
              </button>` : ''}
            </div>
            <div class="recipe-meta-detail">
              ${r.servings ? `<span class="recipe-meta-badge"><span class="material-symbols-outlined">group</span> ${r.servings} Port.</span>` : ''}
              ${r.difficulty && !time ? `<span class="recipe-meta-badge">${escapeHtml(r.difficulty)}</span>` : ''}
              ${time > 0 && r.prep_time && r.cook_time ? `<span class="recipe-meta-badge"><span class="material-symbols-outlined">skillet</span> ${r.cook_time} Min.</span>` : ''}
            </div>
          </div>
        </div>
      `;
    });
    html += '</div>';
    el.innerHTML = html;
  }

  // ── Detail modal ────────────────────────────────────

  function showDetail(idx, isSaved) {
    const recipes = isSaved ? savedRecipes : searchResults;
    const r = recipes[idx];
    if (!r) return;

    currentServings = r.servings || 4;
    const baseServings = r.servings || 4;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.dataset.recipeIdx = idx;
    overlay.dataset.isSaved = isSaved;
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const ingredients = r.ingredients || [];
    const sourceUrl = r.url || r.source_url || '';

    overlay.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h2 style="font-size:1.1rem;font-weight:600">${escapeHtml(r.title || 'Ohne Titel')}</h2>
          <button class="modal-close" onclick="this.closest('.modal-overlay').remove()"><span class="material-symbols-outlined">close</span></button>
        </div>
        ${renderImage(r.image_url, r.title, 'modal-img')}
        <div class="recipe-meta mb-16">
          ${r.prep_time ? `<span><span class="material-symbols-outlined mi-sm">schedule</span> ${r.prep_time} Min. Vorbereitung</span>` : ''}
          ${r.cook_time ? `<span><span class="material-symbols-outlined mi-sm">skillet</span> ${r.cook_time} Min. Kochen</span>` : ''}
          ${r.difficulty ? `<span class="badge badge-accent">${escapeHtml(r.difficulty)}</span>` : ''}
          ${r.servings ? `<span><span class="material-symbols-outlined mi-sm">group</span> ${r.servings} Portionen</span>` : ''}
        </div>

        ${ingredients.length > 0 ? `
          <div class="section-header"><span class="section-icon material-symbols-outlined">grocery</span> Zutaten</div>
          <div class="servings-control">
            <span>Portionen:</span>
            <input type="range" min="1" max="12" value="${currentServings}"
                   oninput="RecipesView.updateServings(this.value, ${baseServings})">
            <span id="servings-display">${currentServings}</span>
          </div>
          <ul class="ingredient-list" id="ingredient-list">
            ${renderIngredients(ingredients, currentServings, baseServings)}
          </ul>
        ` : ''}

        <div class="modal-actions">
          ${!isSaved ? `<button class="btn btn-primary" onclick="RecipesView.saveRecipe(${idx})"><span class="material-symbols-outlined mi-sm">bookmark_add</span> Speichern</button>` : ''}
          ${ingredients.length > 0 ? `<button class="btn btn-secondary" onclick="RecipesView.addToShopping('${escapeHtml(r.chefkoch_id || '')}')"><span class="material-symbols-outlined mi-sm">add_shopping_cart</span> Zur Einkaufsliste</button>` : ''}
        </div>
        ${sourceUrl ? `<div style="margin-top:12px;text-align:center"><a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--text-muted);font-size:var(--text-xs)">Quelle: Chefkoch.de</a></div>` : ''}
      </div>
    `;

    document.body.appendChild(overlay);
  }

  // ── Ingredients ─────────────────────────────────────

  function renderIngredients(ingredients, servings, baseServings) {
    const factor = servings / baseServings;
    return ingredients.map(ing => {
      let amount = '';
      if (ing.amount) {
        const scaled = (parseFloat(ing.amount) || 0) * factor;
        amount = scaled % 1 === 0 ? scaled.toString() : scaled.toFixed(1);
        if (ing.unit) amount += ' ' + ing.unit;
      } else if (ing.unit) {
        amount = ing.unit;
      }
      return `<li><span>${escapeHtml(ing.name || '')}</span><span class="ingredient-amount">${escapeHtml(amount)}</span></li>`;
    }).join('');
  }

  function updateServings(val, baseServings) {
    currentServings = parseInt(val);
    document.getElementById('servings-display').textContent = currentServings;
    const list = document.getElementById('ingredient-list');
    const overlay = document.querySelector('.modal-overlay');
    if (!overlay) return;
    const idx = parseInt(overlay.dataset.recipeIdx, 10);
    const isSaved = overlay.dataset.isSaved === 'true';
    const recipes = isSaved ? savedRecipes : searchResults;
    const recipe = recipes[idx];
    if (recipe && list) {
      list.innerHTML = renderIngredients(recipe.ingredients || [], currentServings, baseServings);
    }
  }

  // ── Actions ─────────────────────────────────────────

  async function saveRecipe(idx) {
    const r = searchResults[idx];
    if (!r) return;
    try {
      await Api.saveRecipe({
        chefkoch_id: r.chefkoch_id,
        title: r.title,
        image_url: r.image_url,
        servings: r.servings || 4,
        prep_time: r.prep_time || 0,
        cook_time: r.cook_time || 0,
        difficulty: r.difficulty,
        source_url: r.url || '',
      });
      alert('Rezept gespeichert!');
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  async function toggleFavorite(idx) {
    const r = savedRecipes[idx];
    if (!r || !r.id) return;
    try {
      const result = await Api.toggleFavorite(r.id);
      r.is_favorite = result.is_favorite;
      renderSaved();
    } catch (_) { /* Toast handles error */ }
  }

  async function addToShopping(chefkochId) {
    if (!chefkochId) return;
    try {
      const result = await Api.addRecipeToShopping(chefkochId, currentServings);
      alert(`${result.added} Zutaten zur Einkaufsliste hinzugefügt`);
      document.querySelector('.modal-overlay')?.remove();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  return {
    render, switchTab, onSearch, showDetail, updateServings,
    saveRecipe, addToShopping, toggleFavorite,
    applyChip,
    _handleImgError: handleImgError,
  };
})();
