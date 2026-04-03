/**
 * MealPlan View – Week View, Create/Delete Entries, Recipe Import, Shopping Transfer
 */
const MealPlanView = (() => {
  let entries = [];
  let weekStart = getMonday(new Date());
  let showForm = false;
  let recipeSearchResults = [];
  let recipeSearchTimer = null;
  let selectedRecipe = null;
  let savedRecipesCache = [];

  const MEAL_TYPES = { breakfast: 'Fruehstueck', lunch: 'Mittagessen', dinner: 'Abendessen' };
  const WEEKDAYS = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];

  function getMonday(d) {
    const date = new Date(d);
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1);
    date.setDate(diff);
    date.setHours(0, 0, 0, 0);
    return date;
  }

  function formatDateISO(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function getWeekNumber(d) {
    const date = new Date(d);
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
    const week1 = new Date(date.getFullYear(), 0, 4);
    return 1 + Math.round(((date - week1) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7);
  }

  async function render(container) {
    showForm = false;
    selectedRecipe = null;
    recipeSearchResults = [];
    container.innerHTML = `
      <a class="view-back" href="#/dashboard"><span class="material-symbols-outlined mi-sm">arrow_back</span> Dashboard</a>
      <div class="section-header"><span class="section-icon material-symbols-outlined">restaurant</span> Wochenplan</div>
      <div class="week-nav">
        <button class="btn btn-sm btn-secondary" onclick="MealPlanView.prevWeek()">&#8592; Vorherige</button>
        <span id="week-label" class="week-label">KW ${getWeekNumber(weekStart)}</span>
        <button class="btn btn-sm btn-secondary" onclick="MealPlanView.nextWeek()">Nächste &#8594;</button>
      </div>
      <div class="flex-between mb-8">
        <button class="btn btn-sm btn-secondary" id="week-shopping-btn" onclick="MealPlanView.weekToShopping()" style="display:none">
          <span class="material-symbols-outlined mi-sm">shopping_cart</span> Wocheneinkauf
        </button>
        <button class="btn btn-sm btn-primary" onclick="MealPlanView.toggleForm()">+ Mahlzeit</button>
      </div>
      <div id="mealplan-form-area"></div>
      <div id="mealplan-content">
        <div class="week-grid">
          ${Array.from({length: 7}, () => '<div class="day-column"><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card" style="height:40px"></div></div>').join('')}
        </div>
      </div>
    `;
    await loadWeek();
  }

  async function prevWeek() {
    weekStart = new Date(weekStart.getTime() - 7 * 86400000);
    updateWeekLabel();
    await loadWeek();
  }

  async function nextWeek() {
    weekStart = new Date(weekStart.getTime() + 7 * 86400000);
    updateWeekLabel();
    await loadWeek();
  }

  function updateWeekLabel() {
    const el = document.getElementById('week-label');
    if (el) el.textContent = `KW ${getWeekNumber(weekStart)}`;
  }

  async function loadWeek() {
    const el = document.getElementById('mealplan-content');
    if (el) el.innerHTML = `<div class="week-grid">
      ${Array.from({length: 7}, () => '<div class="day-column"><div class="skeleton skeleton-card"></div></div>').join('')}
    </div>`;

    try {
      entries = await Api.getMealPlanWeek(formatDateISO(weekStart));
      renderWeek();
      _updateWeekShoppingBtn();
    } catch (err) {
      if (el) el.innerHTML = `
        <div class="error-state"><p>${escapeHtml(err.message)}</p>
          <button class="btn btn-secondary" onclick="MealPlanView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

  function renderWeek() {
    const el = document.getElementById('mealplan-content');
    if (!el) return;

    let html = '';
    for (let i = 0; i < 7; i++) {
      const date = new Date(weekStart.getTime() + i * 86400000);
      const dateStr = formatDateISO(date);
      const dayEntries = entries.filter(e => e.planned_date === dateStr);
      const isToday = formatDateISO(new Date()) === dateStr;

      html += `<div class="day-column ${isToday ? 'day-today' : ''}">`;
      html += `<div class="day-title">${WEEKDAYS[i]}<span class="day-date">${date.toLocaleDateString('de-DE', { day: 'numeric', month: 'short' })}</span></div>`;

      if (dayEntries.length === 0) {
        html += '<div class="meal-empty">Kein Plan</div>';
      } else {
        Object.keys(MEAL_TYPES).forEach(type => {
          const meals = dayEntries.filter(e => e.meal_type === type);
          meals.forEach(m => {
            const hasRecipe = !!m.recipe_chefkoch_id;
            const imgHtml = m.recipe_image_url
              ? `<img class="meal-card-image" src="${escapeHtml(m.recipe_image_url)}" alt="" onerror="this.style.display='none'">`
              : '';
            html += `
              <div class="meal-card">
                ${imgHtml}
                <div class="meal-type">${MEAL_TYPES[type]}</div>
                <div class="meal-title">${escapeHtml(m.recipe_title)}</div>
                ${m.servings ? `<div class="meal-meta">${m.servings} Portionen</div>` : ''}
                ${m.notes ? `<div class="meal-meta">${escapeHtml(m.notes)}</div>` : ''}
                <div class="meal-card-actions">
                  ${hasRecipe ? `<button class="btn btn-sm btn-secondary" onclick="MealPlanView.toShopping(${m.id}, '${escapeHtml(m.recipe_chefkoch_id)}', ${m.servings || 4})" title="Zutaten einkaufen"><span class="material-symbols-outlined mi-sm">shopping_cart</span></button>` : ''}
                  <button class="item-delete" onclick="MealPlanView.deleteEntry(${m.id})" title="Löschen"><span class="material-symbols-outlined">delete</span></button>
                </div>
              </div>
            `;
          });
        });
      }
      html += '</div>';
    }

    el.innerHTML = `<div class="week-grid">${html}</div>`;
  }

  function toggleForm() {
    showForm = !showForm;
    selectedRecipe = null;
    recipeSearchResults = [];
    const el = document.getElementById('mealplan-form-area');
    if (!el) return;
    if (!showForm) { el.innerHTML = ''; return; }

    // Gespeicherte Rezepte im Hintergrund laden
    Api.getSavedRecipes().then(r => { savedRecipesCache = r || []; }).catch(() => {});

    const today = formatDateISO(new Date());
    el.innerHTML = `
      <div class="card event-create-form">
        <div class="mb-8" style="position:relative">
          <input type="text" id="meal-title" placeholder="Rezeptname eingeben oder suchen…" class="mb-4" oninput="MealPlanView.onTitleInput(this.value)">
          <div id="recipe-search-dropdown" class="recipe-search-results"></div>
          <div id="selected-recipe-info"></div>
        </div>
        <div class="input-group mb-8">
          <input type="date" id="meal-date" value="${today}" style="flex:1">
          <select id="meal-type" style="flex:1">
            <option value="breakfast">Fruehstueck</option>
            <option value="lunch">Mittagessen</option>
            <option value="dinner" selected>Abendessen</option>
          </select>
        </div>
        <div class="input-group mb-8">
          <input type="number" id="meal-servings" value="4" min="1" max="20" placeholder="Portionen" style="flex:1">
          <input type="text" id="meal-notes" placeholder="Notizen (optional)" style="flex:2">
        </div>
        <div class="flex-between">
          <button class="btn btn-sm btn-secondary" onclick="MealPlanView.toggleForm()">Abbrechen</button>
          <button class="btn btn-sm btn-primary" onclick="MealPlanView.createEntry()">Hinzufuegen</button>
        </div>
      </div>
    `;
  }

  function onTitleInput(value) {
    if (recipeSearchTimer) clearTimeout(recipeSearchTimer);
    selectedRecipe = null;
    updateSelectedRecipeInfo();

    if (value.trim().length < 2) {
      document.getElementById('recipe-search-dropdown').innerHTML = '';
      recipeSearchResults = [];
      return;
    }

    recipeSearchTimer = setTimeout(() => searchRecipes(value.trim()), 400);
  }

  async function searchRecipes(query) {
    const dropdown = document.getElementById('recipe-search-dropdown');
    if (!dropdown) return;

    const queryLower = query.toLowerCase();

    // Gespeicherte Rezepte client-seitig filtern
    const savedMatches = savedRecipesCache.filter(r =>
      r.title && r.title.toLowerCase().includes(queryLower)
    ).slice(0, 3);

    try {
      recipeSearchResults = await Api.searchRecipes(query, 5);
    } catch {
      recipeSearchResults = [];
    }

    if (savedMatches.length === 0 && recipeSearchResults.length === 0) {
      dropdown.innerHTML = '<div class="recipe-search-item recipe-search-empty">Keine Rezepte gefunden</div>';
      return;
    }

    let html = '';

    // Gespeicherte Rezepte Sektion
    if (savedMatches.length > 0) {
      html += '<div class="recipe-dropdown-section">Gespeicherte Rezepte</div>';
      html += savedMatches.map((r, i) => `
        <div class="recipe-search-item" onclick="MealPlanView.selectSavedRecipe(${i}, '${escapeHtml(queryLower)}')">
          ${r.image_url ? `<img src="${escapeHtml(r.image_url)}" alt="" class="recipe-search-thumb">` : ''}
          <div class="recipe-search-info">
            <div class="recipe-search-name">${escapeHtml(r.title)}</div>
            <div class="recipe-search-meta"><span class="material-symbols-outlined mi-sm" style="font-size:12px">bookmark</span> Gespeichert${r.difficulty ? ' · ' + escapeHtml(r.difficulty) : ''}</div>
          </div>
        </div>
      `).join('');
    }

    // Chefkoch-Suche Sektion
    if (recipeSearchResults.length > 0) {
      if (savedMatches.length > 0) {
        html += '<div class="recipe-dropdown-section">Chefkoch-Suche</div>';
      }
      html += recipeSearchResults.map((r, i) => `
        <div class="recipe-search-item" onclick="MealPlanView.selectRecipe(${i})">
          ${r.image_url ? `<img src="${escapeHtml(r.image_url)}" alt="" class="recipe-search-thumb">` : ''}
          <div class="recipe-search-info">
            <div class="recipe-search-name">${escapeHtml(r.title)}</div>
            <div class="recipe-search-meta">${r.prep_time ? r.prep_time + ' Min.' : ''} ${r.difficulty ? '· ' + escapeHtml(r.difficulty) : ''}</div>
          </div>
        </div>
      `).join('');
    }

    dropdown.innerHTML = html;
  }

  function selectSavedRecipe(index, queryLower) {
    const matches = savedRecipesCache.filter(r =>
      r.title && r.title.toLowerCase().includes(queryLower)
    ).slice(0, 3);
    const r = matches[index];
    if (!r) return;

    // ingredients_json parsen falls vorhanden
    let ingredients = [];
    if (r.ingredients_json) {
      try { ingredients = JSON.parse(r.ingredients_json); } catch { /* ignore */ }
    }

    selectedRecipe = {
      chefkoch_id: r.chefkoch_id,
      title: r.title,
      image_url: r.image_url,
      servings: r.servings || 4,
      prep_time: r.prep_time,
      difficulty: r.difficulty,
      ingredients,
    };

    const titleInput = document.getElementById('meal-title');
    if (titleInput) titleInput.value = r.title;

    const servingsInput = document.getElementById('meal-servings');
    if (servingsInput && r.servings) servingsInput.value = r.servings;

    document.getElementById('recipe-search-dropdown').innerHTML = '';
    updateSelectedRecipeInfo();
  }

  function selectRecipe(index) {
    const r = recipeSearchResults[index];
    if (!r) return;

    selectedRecipe = r;
    const titleInput = document.getElementById('meal-title');
    if (titleInput) titleInput.value = r.title;

    const servingsInput = document.getElementById('meal-servings');
    if (servingsInput && r.servings) servingsInput.value = r.servings;

    document.getElementById('recipe-search-dropdown').innerHTML = '';
    updateSelectedRecipeInfo();
  }

  function updateSelectedRecipeInfo() {
    const el = document.getElementById('selected-recipe-info');
    if (!el) return;
    if (!selectedRecipe) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = `
      <div class="recipe-selected-badge">
        <span class="material-symbols-outlined mi-sm">check_circle</span>
        Rezept: ${escapeHtml(selectedRecipe.title)}
        <button class="btn-inline" onclick="MealPlanView.clearRecipe()">&#10005;</button>
      </div>
    `;
  }

  function clearRecipe() {
    selectedRecipe = null;
    updateSelectedRecipeInfo();
  }

  async function createEntry() {
    const title = document.getElementById('meal-title').value.trim();
    if (!title) { alert('Bitte Rezeptname angeben.'); return; }

    const data = {
      recipe_title: title,
      planned_date: document.getElementById('meal-date').value,
      meal_type: document.getElementById('meal-type').value,
      servings: parseInt(document.getElementById('meal-servings').value) || 4,
    };
    const notes = document.getElementById('meal-notes').value.trim();
    if (notes) data.notes = notes;

    if (selectedRecipe) {
      data.recipe_chefkoch_id = selectedRecipe.chefkoch_id;
      data.recipe_image_url = selectedRecipe.image_url || null;
    }

    try {
      const entry = await Api.createMealPlan(data);
      entries.push(entry);
      showForm = false;
      selectedRecipe = null;
      document.getElementById('mealplan-form-area').innerHTML = '';
      renderWeek();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  function toShopping(entryId, chefkochId, servings) {
    if (!chefkochId) return;
    // Rezeptname aus den Entries finden
    const entry = entries.find(e => e.id === entryId);
    IngredientPreview.show({
      title: entry ? entry.recipe_title : 'Rezept',
      chefkochId,
      ingredients: null, // Werden via API nachgeladen
      baseServings: servings || 4,
      currentServings: servings || 4,
      onConfirm: async (items) => {
        try {
          const result = await Api.addIngredientsToShopping(items);
          const msg = result.merged > 0
            ? `${result.added} Zutaten hinzugefuegt, ${result.merged} zusammengefuehrt`
            : `${result.added} Zutaten zur Einkaufsliste hinzugefuegt`;
          Toast.show(msg, 'info');
        } catch (err) {
          Toast.show('Fehler: ' + err.message, 'error');
        }
      }
    });
  }

  async function deleteEntry(id) {
    if (!confirm('Mahlzeit loeschen?')) return;
    try {
      await Api.deleteMealPlan(id);
      entries = entries.filter(e => e.id !== id);
      renderWeek();
      _updateWeekShoppingBtn();
    } catch (err) {
      alert('Fehler beim Loeschen: ' + err.message);
    }
  }

  function _updateWeekShoppingBtn() {
    const btn = document.getElementById('week-shopping-btn');
    if (!btn) return;
    const hasRecipes = entries.some(e => !!e.recipe_chefkoch_id);
    btn.style.display = hasRecipes ? '' : 'none';
  }

  async function weekToShopping() {
    const recipeCount = entries.filter(e => !!e.recipe_chefkoch_id).length;
    if (recipeCount === 0) return;
    if (!confirm(`Zutaten von ${recipeCount} Rezept${recipeCount > 1 ? 'en' : ''} zur Einkaufsliste hinzufuegen?`)) return;

    try {
      const result = await Api.addWeekToShopping(formatDateISO(weekStart));
      const parts = [];
      if (result.added > 0) parts.push(`${result.added} hinzugefuegt`);
      if (result.merged > 0) parts.push(`${result.merged} zusammengefuehrt`);
      if (result.skipped > 0) parts.push(`${result.skipped} uebersprungen`);
      Toast.show(
        parts.length > 0
          ? `Wocheneinkauf: ${parts.join(', ')}`
          : 'Keine Zutaten gefunden',
        parts.length > 0 ? 'info' : 'warning'
      );
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  return { render, prevWeek, nextWeek, toggleForm, createEntry, deleteEntry, onTitleInput, selectRecipe, selectSavedRecipe, clearRecipe, toShopping, weekToShopping };
})();
