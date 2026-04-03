/**
 * Recipes View – Search, Saved, Detail Modal
 */
const RecipesView = (() => {
  const SEARCH_STORAGE_KEY = 'recipes_search_state';
  const SEARCH_TTL_MS = 30 * 60 * 1000; // 30 minutes
  const PLACEHOLDER_SVG = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect fill='%23262626' width='400' height='300'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23555' font-family='sans-serif' font-size='48'%3E🍽%3C/text%3E%3C/svg%3E`;

  let activeTab = 'search';
  let searchResults = [];
  let savedRecipes = [];
  let searchTimer = null;
  let currentServings = 4;

  function handleImgError(img) {
    img.onerror = null;
    img.src = PLACEHOLDER_SVG;
  }

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

  function renderSearch() {
    const el = document.getElementById('recipes-content');
    const saved = loadSearchState();
    el.innerHTML = `
      <div class="input-group mb-16">
        <input type="search" id="recipe-search" placeholder="Rezept suchen…"
               oninput="RecipesView.onSearch(this.value)" value="${saved ? escapeHtml(saved.query) : ''}">
      </div>
      <div id="recipe-results">
        <div class="empty-state">Suchbegriff eingeben, um Rezepte zu finden</div>
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
      document.getElementById('recipe-results').innerHTML =
        '<div class="empty-state">Suchbegriff eingeben, um Rezepte zu finden</div>';
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
        el.innerHTML = '<div class="empty-state">Keine Rezepte gefunden</div>';
        return;
      }
      renderRecipeGrid(el, searchResults, false);
      saveSearchState(query, searchResults);
    } catch (err) {
      el.innerHTML = `<div class="error-state"><p>${err.message}</p></div>`;
    }
  }

  async function renderSaved() {
    const el = document.getElementById('recipes-content');
    el.innerHTML = '<div class="loading"><div class="spinner"></div> Laden…</div>';

    try {
      savedRecipes = await Api.getSavedRecipes();
      if (savedRecipes.length === 0) {
        el.innerHTML = '<div class="empty-state">Keine gespeicherten Rezepte</div>';
        return;
      }
      renderRecipeGrid(el, savedRecipes, true);
    } catch (err) {
      el.innerHTML = `<div class="error-state"><p>${err.message}</p></div>`;
    }
  }

  function renderRecipeGrid(el, recipes, isSaved) {
    let html = '<div class="recipe-grid">';
    recipes.forEach((r, idx) => {
      const imgSrc = r.image_url || '';
      const time = (r.prep_time || 0) + (r.cook_time || 0);
      html += `
        <div class="recipe-card" onclick="RecipesView.showDetail(${idx}, ${isSaved})">
          ${imgSrc ? `<img class="recipe-img" src="${escapeHtml(imgSrc)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='${PLACEHOLDER_SVG}'">` : '<div class="recipe-img"></div>'}
          <div class="recipe-info">
            <div class="recipe-title">${escapeHtml(r.title)}</div>
            <div class="recipe-meta">
              ${time > 0 ? `<span><span class="material-symbols-outlined mi-sm">schedule</span> ${time} Min.</span>` : ''}
              ${r.difficulty ? `<span>${escapeHtml(r.difficulty)}</span>` : ''}
              ${isSaved ? `<button class="btn-icon" onclick="event.stopPropagation();RecipesView.toggleFavorite(${idx})" title="${r.is_favorite ? 'Favorit entfernen' : 'Als Favorit markieren'}" style="margin-left:auto">
                <span class="material-symbols-outlined" style="color:${r.is_favorite ? 'var(--error)' : 'var(--text-secondary)'};font-size:20px">${r.is_favorite ? 'favorite' : 'favorite_border'}</span>
              </button>` : ''}
            </div>
          </div>
        </div>
      `;
    });
    html += '</div>';
    el.innerHTML = html;
  }

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

    overlay.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h2 style="font-size:1.1rem;font-weight:600">${escapeHtml(r.title)}</h2>
          <button class="modal-close" onclick="this.closest('.modal-overlay').remove()"><span class="material-symbols-outlined">close</span></button>
        </div>
        ${r.image_url ? `<img class="modal-img" src="${escapeHtml(r.image_url)}" alt="" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='${PLACEHOLDER_SVG}'">` : ''}
        <div class="recipe-meta mb-16">
          ${r.prep_time ? `<span><span class="material-symbols-outlined mi-sm">schedule</span> ${r.prep_time} Min. Vorbereitung</span>` : ''}
          ${r.cook_time ? `<span><span class="material-symbols-outlined mi-sm">skillet</span> ${r.cook_time} Min. Kochen</span>` : ''}
          ${r.difficulty ? `<span class="badge badge-accent">${escapeHtml(r.difficulty)}</span>` : ''}
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
          ${!isSaved ? `<button class="btn btn-primary" onclick="RecipesView.saveRecipe(${idx})">Speichern</button>` : ''}
          ${ingredients.length > 0 ? `<button class="btn btn-secondary" onclick="RecipesView.addToShopping('${escapeHtml(r.chefkoch_id || '')}')">Zur Einkaufsliste</button>` : ''}
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
  }

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
      return `<li><span>${escapeHtml(ing.name)}</span><span class="ingredient-amount">${escapeHtml(amount)}</span></li>`;
    }).join('');
  }

  function updateServings(val, baseServings) {
    currentServings = parseInt(val);
    document.getElementById('servings-display').textContent = currentServings;
    const list = document.getElementById('ingredient-list');
    // Re-read ingredients from current modal context
    const overlay = document.querySelector('.modal-overlay');
    if (!overlay) return;
    // Find the recipe via data attributes instead of DOM text matching
    const idx = parseInt(overlay.dataset.recipeIdx, 10);
    const isSaved = overlay.dataset.isSaved === 'true';
    const recipes = isSaved ? savedRecipes : searchResults;
    const recipe = recipes[idx];
    if (recipe && list) {
      list.innerHTML = renderIngredients(recipe.ingredients || [], currentServings, baseServings);
    }
  }

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
      alert(`${result.added} Zutaten zur Einkaufsliste hinzugefuegt`);
      document.querySelector('.modal-overlay')?.remove();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  return { render, switchTab, onSearch, showDetail, updateServings, saveRecipe, addToShopping, toggleFavorite };
})();
