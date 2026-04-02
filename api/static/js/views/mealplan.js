/**
 * MealPlan View – Week View, Create/Delete Entries
 */
const MealPlanView = (() => {
  let entries = [];
  let weekStart = getMonday(new Date());
  let showForm = false;

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
    container.innerHTML = `
      <a class="view-back" href="#/dashboard"><span class="material-symbols-outlined mi-sm">arrow_back</span> Dashboard</a>
      <div class="section-header"><span class="section-icon material-symbols-outlined">restaurant</span> Wochenplan</div>
      <div class="week-nav">
        <button class="btn btn-sm btn-secondary" onclick="MealPlanView.prevWeek()">&#8592; Vorherige</button>
        <span id="week-label" class="week-label">KW ${getWeekNumber(weekStart)}</span>
        <button class="btn btn-sm btn-secondary" onclick="MealPlanView.nextWeek()">Nächste &#8594;</button>
      </div>
      <div class="flex-between mb-8">
        <div></div>
        <button class="btn btn-sm btn-primary" onclick="MealPlanView.toggleForm()">+ Mahlzeit</button>
      </div>
      <div id="mealplan-form-area"></div>
      <div id="mealplan-content"><div class="loading"><div class="spinner"></div> Laden…</div></div>
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
    if (el) el.innerHTML = '<div class="loading"><div class="spinner"></div> Laden…</div>';

    try {
      entries = await Api.getMealPlanWeek(formatDateISO(weekStart));
      renderWeek();
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
            html += `
              <div class="meal-card">
                <div class="meal-type">${MEAL_TYPES[type]}</div>
                <div class="meal-title">${escapeHtml(m.recipe_title)}</div>
                ${m.servings ? `<div class="meal-meta">${m.servings} Portionen</div>` : ''}
                ${m.notes ? `<div class="meal-meta">${escapeHtml(m.notes)}</div>` : ''}
                <button class="item-delete" onclick="MealPlanView.deleteEntry(${m.id})" title="Löschen"><span class="material-symbols-outlined">delete</span></button>
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
    const el = document.getElementById('mealplan-form-area');
    if (!el) return;
    if (!showForm) { el.innerHTML = ''; return; }

    const today = formatDateISO(new Date());
    el.innerHTML = `
      <div class="card event-create-form">
        <input type="text" id="meal-title" placeholder="Rezeptname" class="mb-8">
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
          <button class="btn btn-sm btn-primary" onclick="MealPlanView.createEntry()">Hinzufügen</button>
        </div>
      </div>
    `;
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

    try {
      const entry = await Api.createMealPlan(data);
      entries.push(entry);
      showForm = false;
      document.getElementById('mealplan-form-area').innerHTML = '';
      renderWeek();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  async function deleteEntry(id) {
    if (!confirm('Mahlzeit löschen?')) return;
    try {
      await Api.deleteMealPlan(id);
      entries = entries.filter(e => e.id !== id);
      renderWeek();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  return { render, prevWeek, nextWeek, toggleForm, createEntry, deleteEntry };
})();
