/**
 * Dashboard View – Configurable widget-based layout.
 *
 * Widgets werden aus den User-Preferences geladen.
 * Jedes Widget hat eine eigene Render-Funktion.
 */
const DashboardView = (() => {
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

  function priorityBadge(p) {
    const map = { high: 'badge-error', medium: 'badge-warning', low: 'badge-success' };
    return `<span class="badge ${map[p] || 'badge-accent'} task-priority">${p || 'normal'}</span>`;
  }

  function formatDate() {
    return new Date().toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' });
  }

  function buildSummaryLine(data) {
    const parts = [];
    const events = (data.events_today || []).length + (data.shifts_today || []).length;
    if (events > 0) parts.push(`${events} Termin${events > 1 ? 'e' : ''}`);
    const tasks = data.task_count || (data.open_tasks || []).length;
    if (tasks > 0) parts.push(`${tasks} offene Aufgabe${tasks > 1 ? 'n' : ''}`);
    const pending = (data.shopping_preview || {}).pending || 0;
    if (pending > 0) parts.push(`${pending}\u00d7 Einkauf offen`);
    if (parts.length === 0) return 'Dein Tag ist frei \u2014 genie\u00df ihn!';
    return parts.join(' \u00b7 ');
  }

  function renderQuickActions() {
    return `
      <div class="quick-actions">
        <a href="#/tasks" class="quick-action-btn"><span class="material-symbols-outlined">add_task</span> Aufgabe</a>
        <a href="#/shopping" class="quick-action-btn"><span class="material-symbols-outlined">add_shopping_cart</span> Einkauf</a>
        <a href="#/calendar" class="quick-action-btn"><span class="material-symbols-outlined">event</span> Termin</a>
        <a href="#/chat" class="quick-action-btn"><span class="material-symbols-outlined">chat</span> Fragen</a>
      </div>
    `;
  }

  // ── Widget Renderers ──
  // Each returns an HTML string (or empty string to skip)

  function renderEmailsWidget(data) {
    const emails = data.unread_emails || 0;
    if (emails <= 0) return '';
    return `<div class="mb-16"><span class="badge badge-accent email-badge"><span class="material-symbols-outlined mi-sm">mail</span> ${emails} ungelesene E-Mail${emails > 1 ? 's' : ''}</span></div>`;
  }

  function renderShiftsWidget(data) {
    const shifts = (data.shifts_today || []).slice(0, 3);
    if (shifts.length === 0) return '';
    let html = `<a class="section-header section-link" href="#/shifts"><span class="section-icon material-symbols-outlined">work</span> Deine Schichten <span class="section-arrow">Verwalten &#8594;</span></a>`;
    shifts.forEach(s => {
      const color = s.shift_color || 'var(--accent)';
      html += `
        <div class="card" style="border-left:4px solid ${color}">
          <div class="event-time">${formatTime(s.start)}${s.end ? ' – ' + formatTime(s.end) : ''}</div>
          <div class="card-title"><span class="shift-badge" style="background:${color}22;color:${color}">${escapeHtml(s.shift_short_name || '')}</span> ${escapeHtml(s.summary || '')}</div>
          ${s.description ? `<div class="card-subtitle">${escapeHtml(s.description)}</div>` : ''}
        </div>
      `;
    });
    return html;
  }

  function renderEventsWidget(data) {
    const events = (data.events_today || []).slice(0, 3);
    let html = `<a class="section-header section-link" href="#/calendar"><span class="section-icon material-symbols-outlined">calendar_month</span> Deine Termine <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
    if (events.length === 0) {
      html += `<div class="empty-state"><span class="material-symbols-outlined empty-state-icon">calendar_month</span><div class="empty-state-text">Heute keine Termine</div><a href="#/calendar" class="empty-state-cta">Termin erstellen \u2192</a></div>`;
    } else {
      events.forEach(e => {
        html += `
          <div class="card">
            <div class="event-time">${formatTime(e.start)}${e.end ? ' – ' + formatTime(e.end) : ''}</div>
            <div class="card-title">${escapeHtml(e.summary)}</div>
            ${e.location ? `<div class="card-subtitle">${escapeHtml(e.location)}</div>` : ''}
          </div>
        `;
      });
    }
    return html;
  }

  function renderTasksWidget(data) {
    const tasks = (data.open_tasks || []).slice(0, 3);
    let html = `<a class="section-header section-link" href="#/tasks"><span class="section-icon material-symbols-outlined">check_circle</span> Zu erledigen <span class="badge badge-accent">${data.task_count || tasks.length}</span> <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
    if (tasks.length === 0) {
      html += `<div class="empty-state"><span class="material-symbols-outlined empty-state-icon">check_circle</span><div class="empty-state-text">Alles erledigt \u2014 gut gemacht!</div><a href="#/tasks" class="empty-state-cta">Neue Aufgabe \u2192</a></div>`;
    } else {
      tasks.forEach(t => {
        html += `
          <div class="card">
            <div class="flex-between">
              <div class="card-title">${escapeHtml(t.title)}</div>
              ${priorityBadge(t.priority)}
            </div>
            ${t.description ? `<div class="card-subtitle">${escapeHtml(t.description)}</div>` : ''}
          </div>
        `;
      });
    }
    return html;
  }

  function renderShoppingWidget(data) {
    const shop = data.shopping_preview || {};
    const total = shop.total || 0;
    const checked = shop.checked || 0;
    const pending = shop.pending || (total - checked);
    const pct = total > 0 ? Math.round((checked / total) * 100) : 0;

    let html = `<a class="section-header section-link" href="#/shopping"><span class="section-icon material-symbols-outlined">shopping_cart</span> Einkauf <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
    if (total === 0) {
      html += `<div class="empty-state"><span class="material-symbols-outlined empty-state-icon">shopping_cart</span><div class="empty-state-text">Einkaufsliste ist leer</div><a href="#/shopping" class="empty-state-cta">Etwas hinzuf\u00fcgen \u2192</a></div>`;
    } else {
      html += `
        <div class="card card-clickable" onclick="Router.navigate('#/shopping')">
          <div class="flex-between mb-8">
            <span>${pending} offen</span>
            <span class="card-subtitle">${checked}/${total} erledigt</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div class="progress-text">${pct}%</div>
        </div>
      `;
    }
    return html;
  }

  // Widget registry: maps widget ID to render function
  const WIDGET_RENDERERS = {
    emails: renderEmailsWidget,
    shifts: renderShiftsWidget,
    events: renderEventsWidget,
    tasks: renderTasksWidget,
    shopping: renderShoppingWidget,
  };

  // Async widget renderers (loaded after initial render)
  const ASYNC_WIDGET_RENDERERS = {
    mealplan: renderMealplanWidget,
    drive: renderDriveWidget,
  };

  async function render(container) {
    const user = capitalize(Api.getUserKey());
    container.innerHTML = `
      <div class="greeting-date">${formatDate()}</div>
      <div class="greeting">${getGreeting()}, ${user}</div>
      <div class="greeting-sub" id="greeting-summary">Dein Tages\u00fcberblick wird geladen\u2026</div>
      <div id="proactive-suggestions"></div>
      ${renderQuickActions()}
      <div id="dashboard-content">
        <div class="skeleton skeleton-section-header"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-section-header"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-section-header"></div>
        <div class="skeleton skeleton-card"></div>
      </div>
    `;

    try {
      const data = await Api.getDashboard();
      renderContent(data);
      // Proaktive Vorschlaege im Hintergrund laden
      loadProactiveSuggestions();
    } catch (err) {
      document.getElementById('dashboard-content').innerHTML = `
        <div class="error-state">
          <p>${err.message}</p>
          <button class="btn btn-secondary" onclick="DashboardView.render(document.getElementById('view-container'))">
            Erneut versuchen
          </button>
        </div>
      `;
    }
  }

  function getWidgetConfig() {
    const prefs = window.AppPreferences ? window.AppPreferences.getCached() : null;
    if (prefs && prefs.dashboard && prefs.dashboard.widgets) {
      return prefs.dashboard.widgets
        .filter(w => w.enabled !== false)
        .sort((a, b) => (a.order || 0) - (b.order || 0));
    }
    // Default widget order
    return [
      { id: 'emails', enabled: true, order: 0 },
      { id: 'shifts', enabled: true, order: 1 },
      { id: 'events', enabled: true, order: 2 },
      { id: 'tasks', enabled: true, order: 3 },
      { id: 'shopping', enabled: true, order: 4 },
      { id: 'mealplan', enabled: true, order: 5 },
      { id: 'drive', enabled: true, order: 6 },
    ];
  }

  function renderContent(data) {
    const el = document.getElementById('dashboard-content');
    if (!el) return;

    // Update summary line with real data
    const subEl = document.getElementById('greeting-summary');
    if (subEl) subEl.textContent = buildSummaryLine(data);

    const widgets = getWidgetConfig();
    let html = '';

    // Zone A: "Dein Tag" — Shifts + Events (priority zone)
    const zoneShifts = WIDGET_RENDERERS.shifts ? renderShiftsWidget(data) : '';
    const zoneEvents = WIDGET_RENDERERS.events ? renderEventsWidget(data) : '';
    const zoneAContent = zoneShifts + zoneEvents;
    if (zoneAContent.trim()) {
      html += `<div class="dashboard-zone zone-today"><div class="zone-label">Dein Tag</div>${zoneAContent}</div>`;
    } else {
      html += zoneAContent;
    }

    // Zone B: Tasks + Shopping (planning)
    html += renderTasksWidget(data);
    html += renderShoppingWidget(data);

    // Render remaining sync widgets not covered by zones
    for (const widget of widgets) {
      if (['shifts', 'events', 'tasks', 'shopping'].includes(widget.id)) continue;
      const renderer = WIDGET_RENDERERS[widget.id];
      if (renderer) {
        html += renderer(data);
      }
    }

    el.innerHTML = html;

    // Load async widgets (MealPlan, Drive) without blocking
    loadAsyncWidgets(el, widgets, data);
  }

  async function loadAsyncWidgets(container, widgets, _data) {
    const asyncWidgets = widgets.filter(w => ASYNC_WIDGET_RENDERERS[w.id]);
    if (asyncWidgets.length === 0) return;

    const promises = asyncWidgets.map(async (w) => {
      const renderer = ASYNC_WIDGET_RENDERERS[w.id];
      if (!renderer) return '';
      try {
        return await renderer();
      } catch {
        return '';
      }
    });

    const results = await Promise.allSettled(promises);
    let extraHtml = '';
    for (const result of results) {
      if (result.status === 'fulfilled' && result.value) {
        extraHtml += result.value;
      }
    }

    if (extraHtml) {
      container.insertAdjacentHTML('beforeend', extraHtml);
    }
  }

  async function renderMealplanWidget() {
    const meals = await Api.getMealPlanWeek();
    const today = new Date().toISOString().slice(0, 10);
    const todayMeals = meals.filter(m => m.planned_date === today);

    let html = `<a class="section-header section-link" href="#/mealplan"><span class="section-icon material-symbols-outlined">restaurant</span> Heute auf dem Tisch <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
    if (todayMeals.length === 0) {
      html += `<div class="empty-state"><span class="material-symbols-outlined empty-state-icon">restaurant</span><div class="empty-state-text">Noch nichts geplant f\u00fcr heute</div><a href="#/mealplan" class="empty-state-cta">Woche planen \u2192</a></div>`;
    } else {
      const typeLabels = { breakfast: 'Fruehstueck', lunch: 'Mittagessen', dinner: 'Abendessen' };
      todayMeals.forEach(m => {
        html += `
          <div class="card card-clickable" onclick="Router.navigate('#/mealplan')">
            <div class="card-subtitle">${typeLabels[m.meal_type] || m.meal_type}</div>
            <div class="card-title">${escapeHtml(m.recipe_title)}</div>
          </div>
        `;
      });
    }
    return html;
  }

  async function renderDriveWidget() {
    const driveData = await Api.getDriveFiles(null, 2);
    let html = `<a class="section-header section-link" href="#/drive"><span class="section-icon material-symbols-outlined">folder</span> Letzte Dateien <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
    if (driveData.connected === false) {
      html += `<div class="empty-state"><span class="material-symbols-outlined empty-state-icon">cloud_off</span><div class="empty-state-text">Drive noch nicht verbunden</div><a href="#/drive" class="empty-state-cta">Verbinden \u2192</a></div>`;
    } else if ((driveData.files || []).length === 0) {
      html += `<div class="empty-state"><span class="material-symbols-outlined empty-state-icon">folder_open</span><div class="empty-state-text">Keine Dateien</div></div>`;
    } else {
      driveData.files.forEach(f => {
        html += `
          <div class="card card-clickable" onclick="Router.navigate('#/drive')">
            <div class="card-title">${escapeHtml(f.name)}</div>
            ${f.modified_time ? `<div class="card-subtitle">${new Date(f.modified_time).toLocaleDateString('de-DE', { day: 'numeric', month: 'short' })}</div>` : ''}
          </div>
        `;
      });
    }
    return html;
  }

  // ── Proaktive Vorschlaege ──

  function _getDismissed() {
    try {
      const raw = localStorage.getItem('dm_dismissed_suggestions');
      if (!raw) return {};
      const data = JSON.parse(raw);
      const now = Date.now();
      // Abgelaufene Eintraege entfernen (24h TTL)
      const cleaned = {};
      for (const [k, v] of Object.entries(data)) {
        if (now - v < 86400000) cleaned[k] = v;
      }
      return cleaned;
    } catch { return {}; }
  }

  function _dismissSuggestion(id) {
    const dismissed = _getDismissed();
    dismissed[id] = Date.now();
    localStorage.setItem('dm_dismissed_suggestions', JSON.stringify(dismissed));
    const card = document.querySelector(`.suggestion-card[data-id="${id}"]`);
    if (card) {
      card.style.opacity = '0';
      card.style.transform = 'translateX(20px)';
      setTimeout(() => {
        card.remove();
        // Container ausblenden wenn leer
        const container = document.getElementById('proactive-suggestions');
        if (container && container.querySelectorAll('.suggestion-card').length === 0) {
          container.innerHTML = '';
        }
      }, 200);
    }
  }

  async function loadProactiveSuggestions() {
    // Pruefen ob Feature aktiviert ist
    const prefs = window.AppPreferences ? window.AppPreferences.getCached() : null;
    if (prefs && prefs.proactive_suggestions === false) return;

    const el = document.getElementById('proactive-suggestions');
    if (!el) return;

    try {
      const suggestions = await Api.getProactiveSuggestions();
      if (!suggestions || suggestions.length === 0) return;

      const dismissed = _getDismissed();
      const visible = suggestions.filter(s => !dismissed[s.id]);
      if (visible.length === 0) return;

      const ICONS = {
        tasks: 'check_circle',
        calendar: 'event',
        shopping: 'shopping_cart',
        email: 'mail',
      };

      el.innerHTML = visible.map(s => {
        const icon = ICONS[s.type] || 'lightbulb';
        return `
          <div class="suggestion-card card" data-id="${escapeHtml(s.id)}">
            <div class="suggestion-card-body">
              <span class="material-symbols-outlined suggestion-card-icon">${icon}</span>
              <div class="suggestion-card-content">
                <div class="suggestion-card-title">${escapeHtml(s.title)}</div>
                <div class="suggestion-card-text">${escapeHtml(s.body)}</div>
              </div>
              ${s.dismissible ? `<button class="btn btn-icon suggestion-card-dismiss" onclick="DashboardView.dismissSuggestion('${escapeHtml(s.id)}')" title="Ausblenden"><span class="material-symbols-outlined mi-sm">close</span></button>` : ''}
            </div>
            ${s.action_route ? `<a href="${escapeHtml(s.action_route)}" class="suggestion-card-action">${escapeHtml(s.action_label || 'Oeffnen')} <span class="material-symbols-outlined mi-sm">arrow_forward</span></a>` : ''}
          </div>
        `;
      }).join('');
    } catch {
      // Fehler ignorieren – Vorschlaege sind optional
    }
  }

  return { render, dismissSuggestion: _dismissSuggestion };
})();
