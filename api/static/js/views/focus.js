/**
 * Focus View – Kompakte Tagesansicht mit priorisierten Items
 *
 * Zeigt max. 5 priorisierte Tagesaktionen:
 * 1. Naechster Termin (zeitlich sortiert)
 * 2. Wichtigste offene Aufgabe (Prioritaet + Faelligkeit)
 * 3. Schicht heute (falls vorhanden)
 * 4. Einkaufsstatus (falls offene Items)
 * 5. Wochenplan heute (falls Mahlzeiten geplant)
 */
const FocusView = (() => {
  function getGreeting() {
    const h = new Date().getHours();
    if (h < 12) return 'Guten Morgen';
    if (h < 18) return 'Guten Tag';
    return 'Guten Abend';
  }

  function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
  }

  function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }

  async function render(container) {
    const user = capitalize(Api.getUserKey());
    container.innerHTML = `
      <div class="focus-container">
        <div class="greeting">${getGreeting()}, ${user}</div>
        <div class="greeting-sub">Dein Fokus fuer heute</div>
        <div id="focus-content">
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
        </div>
        <div class="focus-toggle">
          <a href="#/dashboard"><span class="material-symbols-outlined mi-sm">dashboard</span> Vollstaendiges Dashboard</a>
        </div>
      </div>
    `;

    try {
      const data = await Api.getDashboard();
      renderFocusItems(data);
    } catch (err) {
      document.getElementById('focus-content').innerHTML = `
        <div class="error-state">
          <p>${escapeHtml(err.message)}</p>
          <button class="btn btn-secondary" onclick="FocusView.render(document.getElementById('view-container'))">
            Erneut versuchen
          </button>
        </div>
      `;
    }
  }

  function renderFocusItems(data) {
    const el = document.getElementById('focus-content');
    if (!el) return;

    const items = [];

    // 1. Naechster Termin
    const nextEvent = getNextEvent(data.events_today || []);
    if (nextEvent) {
      items.push(renderEventCard(nextEvent));
    }

    // 2. Wichtigste Aufgabe
    const topTask = getTopTask(data.open_tasks || []);
    if (topTask) {
      items.push(renderTaskCard(topTask));
    }

    // 3. Schicht heute
    const shift = (data.shifts_today || [])[0];
    if (shift) {
      items.push(renderShiftCard(shift));
    }

    // 4. Einkaufsstatus
    const shop = data.shopping_preview || {};
    if ((shop.pending || 0) > 0) {
      items.push(renderShoppingCard(shop));
    }

    // 5. Ungelesene E-Mails
    if ((data.unread_emails || 0) > 0) {
      items.push(renderEmailCard(data.unread_emails));
    }

    if (items.length === 0) {
      el.innerHTML = `
        <div class="focus-empty">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--success)">check_circle</span>
          <p>Nichts Wichtiges heute – alles erledigt!</p>
        </div>
      `;
    } else {
      el.innerHTML = items.slice(0, 5).join('');
    }

    // Async: Wochenplan heute laden
    loadTodayMeals(el, items.length);
  }

  function getNextEvent(events) {
    if (events.length === 0) return null;
    const now = new Date();
    // Sortiere nach Startzeit, finde den naechsten zukuenftigen
    const sorted = [...events].sort((a, b) => new Date(a.start) - new Date(b.start));
    const upcoming = sorted.find(e => new Date(e.end || e.start) > now);
    return upcoming || sorted[0]; // Fallback: erster Termin des Tages
  }

  function getTopTask(tasks) {
    if (tasks.length === 0) return null;
    const prioOrder = { high: 0, medium: 1, low: 2 };
    const sorted = [...tasks].sort((a, b) => {
      const pa = prioOrder[a.priority] ?? 1;
      const pb = prioOrder[b.priority] ?? 1;
      if (pa !== pb) return pa - pb;
      // Bei gleicher Prioritaet: frueheres Faelligkeitsdatum zuerst
      if (a.due_date && b.due_date) return new Date(a.due_date) - new Date(b.due_date);
      if (a.due_date) return -1;
      if (b.due_date) return 1;
      return 0;
    });
    return sorted[0];
  }

  function renderEventCard(e) {
    const time = formatTime(e.start);
    const endTime = e.end ? ' – ' + formatTime(e.end) : '';
    return `
      <a class="focus-card" href="#/calendar">
        <div class="focus-card-icon"><span class="material-symbols-outlined">calendar_month</span></div>
        <div class="focus-card-content">
          <div class="focus-card-label">Naechster Termin</div>
          <div class="focus-card-title">${escapeHtml(e.summary || '')}</div>
          ${e.location ? `<div class="focus-card-sub">${escapeHtml(e.location)}</div>` : ''}
        </div>
        <div class="focus-card-meta">${time}${endTime}</div>
      </a>
    `;
  }

  function renderTaskCard(t) {
    const prioMap = { high: 'badge-error', medium: 'badge-warning', low: 'badge-success' };
    const prioLabel = { high: 'Hoch', medium: 'Mittel', low: 'Niedrig' };
    return `
      <a class="focus-card" href="#/tasks">
        <div class="focus-card-icon"><span class="material-symbols-outlined">check_circle</span></div>
        <div class="focus-card-content">
          <div class="focus-card-label">Wichtigste Aufgabe</div>
          <div class="focus-card-title">${escapeHtml(t.title)}</div>
          ${t.description ? `<div class="focus-card-sub">${escapeHtml(t.description)}</div>` : ''}
        </div>
        <div class="focus-card-meta"><span class="badge ${prioMap[t.priority] || 'badge-accent'}">${prioLabel[t.priority] || t.priority}</span></div>
      </a>
    `;
  }

  function renderShiftCard(s) {
    const color = s.shift_color || 'var(--accent)';
    return `
      <a class="focus-card" href="#/shifts">
        <div class="focus-card-icon" style="color:${color}"><span class="material-symbols-outlined">work</span></div>
        <div class="focus-card-content">
          <div class="focus-card-label">Dienst heute</div>
          <div class="focus-card-title">${escapeHtml(s.summary || s.shift_short_name || '')}</div>
        </div>
        <div class="focus-card-meta">${formatTime(s.start)}${s.end ? ' – ' + formatTime(s.end) : ''}</div>
      </a>
    `;
  }

  function renderShoppingCard(shop) {
    const pending = shop.pending || 0;
    const total = shop.total || 0;
    const pct = total > 0 ? Math.round(((total - pending) / total) * 100) : 0;
    return `
      <a class="focus-card" href="#/shopping">
        <div class="focus-card-icon"><span class="material-symbols-outlined">shopping_cart</span></div>
        <div class="focus-card-content">
          <div class="focus-card-label">Einkaufsliste</div>
          <div class="focus-card-title">${pending} offene Artikel</div>
          <div class="progress-bar" style="margin-top:4px"><div class="progress-fill" style="width:${pct}%"></div></div>
        </div>
        <div class="focus-card-meta">${pct}%</div>
      </a>
    `;
  }

  function renderEmailCard(count) {
    return `
      <a class="focus-card" href="#/dashboard">
        <div class="focus-card-icon"><span class="material-symbols-outlined">mail</span></div>
        <div class="focus-card-content">
          <div class="focus-card-label">E-Mails</div>
          <div class="focus-card-title">${count} ungelesene E-Mail${count > 1 ? 's' : ''}</div>
        </div>
        <div class="focus-card-meta"><span class="badge badge-accent">${count}</span></div>
      </a>
    `;
  }

  async function loadTodayMeals(container, currentCount) {
    if (currentCount >= 5) return; // Max 5 Items
    try {
      const meals = await Api.getMealPlanWeek();
      const today = new Date().toISOString().slice(0, 10);
      const todayMeals = meals.filter(m => m.planned_date === today);
      if (todayMeals.length === 0) return;

      const typeLabels = { breakfast: 'Fruehstueck', lunch: 'Mittagessen', dinner: 'Abendessen' };
      const mealSummary = todayMeals.map(m => typeLabels[m.meal_type] || m.meal_type).join(', ');
      const titles = todayMeals.map(m => escapeHtml(m.recipe_title)).join(', ');

      const html = `
        <a class="focus-card" href="#/mealplan">
          <div class="focus-card-icon"><span class="material-symbols-outlined">restaurant</span></div>
          <div class="focus-card-content">
            <div class="focus-card-label">Wochenplan heute</div>
            <div class="focus-card-title">${titles}</div>
            <div class="focus-card-sub">${mealSummary}</div>
          </div>
          <div class="focus-card-meta">${todayMeals.length}</div>
        </a>
      `;
      container.insertAdjacentHTML('beforeend', html);
    } catch {
      // Silently skip meal plan if unavailable
    }
  }

  return { render };
})();
