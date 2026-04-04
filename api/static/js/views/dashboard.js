/**
 * Dashboard View – Configurable widget-based layout with Focus Mode.
 *
 * Widgets werden aus den User-Preferences geladen.
 * Jedes Widget hat eine eigene Render-Funktion.
 * Focus Mode zeigt nur die wichtigsten Tagespunkte.
 */
const DashboardView = (() => {
  const getGreeting = Utils.getGreeting;
  const capitalize = Utils.capitalize;
  const formatTime = Utils.formatClockTime;

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

  // ── Helper: Drive file icon (from drive.js) ──
  function fileIcon(mimeType) {
    const mi = (name) => `<span class="material-symbols-outlined">${name}</span>`;
    if (!mimeType) return mi('draft');
    if (mimeType.startsWith('image/')) return mi('image');
    if (mimeType.startsWith('video/')) return mi('videocam');
    if (mimeType.startsWith('audio/')) return mi('audio_file');
    if (mimeType.includes('pdf')) return mi('picture_as_pdf');
    if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return mi('table_chart');
    if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return mi('slideshow');
    if (mimeType.includes('document') || mimeType.includes('word')) return mi('description');
    if (mimeType.includes('folder')) return mi('folder');
    return mi('draft');
  }

  function formatFileSize(bytes) {
    if (!bytes) return '';
    const num = parseInt(bytes);
    if (isNaN(num)) return bytes;
    if (num < 1024) return num + ' B';
    if (num < 1048576) return (num / 1024).toFixed(1) + ' KB';
    return (num / 1048576).toFixed(1) + ' MB';
  }

  // ── Helper: Weather icon (from weather.js) ──
  function weatherIcon(desc) {
    const d = (desc || '').toLowerCase();
    if (d.includes('regen') || d.includes('rain')) return 'rainy';
    if (d.includes('schnee') || d.includes('snow')) return 'ac_unit';
    if (d.includes('wolke') || d.includes('cloud') || d.includes('bewölkt')) return 'cloud';
    if (d.includes('sonne') || d.includes('klar') || d.includes('sunny') || d.includes('clear')) return 'wb_sunny';
    if (d.includes('gewitter') || d.includes('thunder')) return 'thunderstorm';
    if (d.includes('nebel') || d.includes('fog')) return 'foggy';
    return 'thermostat';
  }

  function getWeatherHint(temp, desc) {
    const d = (desc || '').toLowerCase();
    if ((d.includes('regen') || d.includes('rain')) && temp < 10) return 'Regenjacke und warme Schuhe einpacken';
    if (d.includes('regen') || d.includes('rain')) return 'Regenschirm nicht vergessen';
    if (d.includes('schnee') || d.includes('snow')) return 'Warm anziehen \u2013 es schneit!';
    if (d.includes('gewitter') || d.includes('thunder')) return 'Gewitter erwartet \u2013 lieber drinnen bleiben';
    if (temp >= 30) return 'Viel trinken und Sonnencreme nicht vergessen';
    if (temp >= 25 && (d.includes('sonne') || d.includes('klar') || d.includes('sunny') || d.includes('clear'))) return 'Sonnencreme nicht vergessen';
    if (temp <= 0) return 'Vorsicht Glatteis \u2013 warm anziehen!';
    if (temp <= 5) return 'Dick einpacken, es ist kalt drau\u00dfen';
    if (d.includes('nebel') || d.includes('fog')) return 'Vorsicht im Verkehr \u2013 Nebel';
    return null;
  }

  function renderQuickActions() {
    return `
      <div class="quick-actions">
        <a href="#/tasks" class="quick-action-btn"><span class="material-symbols-outlined">add_task</span> Aufgabe</a>
        <a href="#/shopping" class="quick-action-btn"><span class="material-symbols-outlined">add_shopping_cart</span> Einkauf</a>
        <a href="#/calendar" class="quick-action-btn"><span class="material-symbols-outlined">event</span> Termin</a>
        <a href="#/chat" class="quick-action-btn"><span class="material-symbols-outlined">chat</span> Chat</a>
      </div>
    `;
  }

  function renderBriefingTrigger() {
    return `
      <div class="card card-clickable briefing-trigger" onclick="DashboardView.showBriefing()" style="margin-bottom:16px">
        <div class="flex-between">
          <div style="display:flex;align-items:center;gap:8px">
            <span class="material-symbols-outlined" style="color:var(--accent)">wb_sunny</span>
            <span class="card-title" style="margin:0">Tagesbriefing</span>
          </div>
          <span class="material-symbols-outlined" style="color:var(--text-muted)">arrow_forward</span>
        </div>
      </div>
    `;
  }

  async function showBriefing() {
    // Show modal overlay with loading state
    let overlay = document.getElementById('briefing-overlay');
    if (overlay) overlay.remove();

    overlay = document.createElement('div');
    overlay.id = 'briefing-overlay';
    overlay.className = 'assistant-overlay open';
    overlay.innerHTML = `
      <div class="assistant-sheet" style="max-height:85vh">
        <div class="assistant-sheet-handle"></div>
        <div class="assistant-sheet-header">
          <span class="assistant-sheet-title"><span class="material-symbols-outlined" style="font-size:20px;vertical-align:-4px;margin-right:4px">wb_sunny</span> Tagesbriefing</span>
          <button class="btn btn-icon" onclick="document.getElementById('briefing-overlay').remove()"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div id="briefing-content" style="padding:16px;overflow-y:auto;max-height:calc(85vh - 80px)">
          <div style="text-align:center;padding:32px 0">
            <span class="typing-dots"><span></span><span></span><span></span></span>
            <div class="card-subtitle" style="margin-top:8px">Briefing wird erstellt…</div>
          </div>
        </div>
      </div>
    `;
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.remove();
    });
    document.body.appendChild(overlay);

    try {
      const data = await Api.get('/dashboard/briefing');
      const contentEl = document.getElementById('briefing-content');
      if (!contentEl) return;

      if (!data.sections || data.sections.length === 0) {
        contentEl.innerHTML = `
          <div class="empty-state">
            <span class="material-symbols-outlined empty-state-icon">wb_sunny</span>
            <div class="empty-state-text">Heute steht nichts an — genieß den Tag!</div>
          </div>
        `;
        return;
      }

      let html = '';
      for (const section of data.sections) {
        html += `<div class="section-header" style="margin-top:12px"><span class="section-icon material-symbols-outlined">${section.icon || 'info'}</span> ${escapeHtml(section.title)}</div>`;
        for (const item of section.items || []) {
          html += `<div class="card" style="margin-bottom:8px"><div class="card-title">${escapeHtml(item.text)}</div>${item.detail ? `<div class="card-subtitle">${escapeHtml(item.detail)}</div>` : ''}</div>`;
        }
      }
      contentEl.innerHTML = html;
    } catch (err) {
      const contentEl = document.getElementById('briefing-content');
      if (contentEl) {
        contentEl.innerHTML = `<div class="error-state"><p>${escapeHtml(err.message || 'Fehler beim Laden')}</p><button class="btn btn-secondary" onclick="DashboardView.showBriefing()">Erneut versuchen</button></div>`;
      }
    }
  }

  // ── Widget Renderers ──

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
    if (data.calendar_connected === false) {
      html += `<div class="card calendar-disconnected-hint"><span class="material-symbols-outlined mi-sm" style="color:var(--warning);vertical-align:-3px">warning</span> Kalender nicht verbunden \u2013 Termine werden nicht synchronisiert. <a href="#/profile">Zum Profil</a></div>`;
    }
    if (events.length === 0 && data.calendar_connected !== false) {
      html += `<div class="empty-state"><span class="material-symbols-outlined empty-state-icon">calendar_month</span><div class="empty-state-text">Heute keine Termine</div><a href="#/calendar" class="empty-state-cta">Termin erstellen \u2192</a></div>`;
    } else if (events.length === 0) {
      // Calendar disconnected hint already shown above, skip empty state
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
        const recur = t.recurrence ? `<span class="badge badge-accent recurrence-badge"><span class="material-symbols-outlined mi-sm">repeat</span></span>` : '';
        html += `
          <div class="card">
            <div class="flex-between">
              <div class="card-title">${escapeHtml(t.title)}</div>
              <div class="task-badges">${recur}${priorityBadge(t.priority)}</div>
            </div>
            ${t.description ? `<div class="card-subtitle">${escapeHtml(t.description)}</div>` : ''}
          </div>
        `;
      });
    }
    return html;
  }

  function renderNotificationsWidget(data) {
    const unread = data.notifications_unread || 0;
    const latest = data.notifications_latest || [];
    if (unread <= 0 && latest.length === 0) return '';

    const TYPE_ICONS = {
      reminder: 'schedule', follow_up: 'reply', document: 'description',
      inbox: 'inbox', weather: 'cloud', system: 'info',
    };

    function relTime(dateStr) {
      const diff = Date.now() - new Date(dateStr).getTime();
      if (diff < 60000) return 'Gerade eben';
      if (diff < 3600000) return `vor ${Math.floor(diff / 60000)} Min.`;
      if (diff < 86400000) return `vor ${Math.floor(diff / 3600000)} Std.`;
      return 'Gestern';
    }

    let html = `<a class="section-header section-link" href="#/inbox"><span class="section-icon material-symbols-outlined">notifications</span> Benachrichtigungen <span class="badge badge-accent">${unread}</span> <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;

    if (latest.length === 0) {
      html += `<div class="card card-clickable" onclick="Router.navigate('#/inbox')"><div class="card-subtitle">${unread} ungelesene Benachrichtigung${unread > 1 ? 'en' : ''}</div></div>`;
    } else {
      latest.forEach(n => {
        const icon = TYPE_ICONS[n.type] || 'info';
        html += `
          <div class="card card-clickable dashboard-notification-item" onclick="Router.navigate('${n.link || '#/inbox'}')">
            <div class="flex-between">
              <div class="card-title"><span class="material-symbols-outlined mi-sm" style="vertical-align:-3px;margin-right:4px;color:var(--accent)">${icon}</span>${escapeHtml(n.title)}</div>
              <span class="card-subtitle">${relTime(n.created_at)}</span>
            </div>
            ${n.message ? `<div class="card-subtitle notification-preview">${escapeHtml(n.message.length > 80 ? n.message.slice(0, 80) + '\u2026' : n.message)}</div>` : ''}
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

  // Widget registry
  const WIDGET_RENDERERS = {
    notifications: renderNotificationsWidget,
    emails: renderEmailsWidget,
    shifts: renderShiftsWidget,
    events: renderEventsWidget,
    tasks: renderTasksWidget,
    shopping: renderShoppingWidget,
  };

  const ASYNC_WIDGET_RENDERERS = {
    mealplan: renderMealplanWidget,
    weather: renderWeatherWidget,
    drive: renderDriveWidget,
    weeklyreview: renderWeeklyReviewWidget,
    finance: renderFinanceWidget,
    inventory: renderInventoryWidget,
    family: renderFamilyWidget,
  };

  // ── Main Render ──

  async function render(container) {
    const user = capitalize(Api.getUserKey());
    container.innerHTML = `
      <div class="greeting-date">${formatDate()}</div>
      <div class="greeting-row">
        <div class="greeting">${getGreeting()}, ${user}</div>
      </div>
      <div class="greeting-sub" id="greeting-summary">Dein Tages\u00fcberblick wird geladen\u2026</div>
      <div id="proactive-suggestions"></div>
      ${renderBriefingTrigger()}
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
    return [
      { id: 'notifications', enabled: true, order: 0 },
      { id: 'emails', enabled: true, order: 1 },
      { id: 'shifts', enabled: true, order: 2 },
      { id: 'events', enabled: true, order: 3 },
      { id: 'tasks', enabled: true, order: 4 },
      { id: 'shopping', enabled: true, order: 5 },
      { id: 'mealplan', enabled: true, order: 6 },
      { id: 'weather', enabled: true, order: 7 },
      { id: 'drive', enabled: true, order: 8 },
      { id: 'weeklyreview', enabled: true, order: 9 },
      { id: 'finance', enabled: false, order: 10 },
      { id: 'inventory', enabled: false, order: 11 },
      { id: 'family', enabled: false, order: 12 },
    ];
  }

  function renderContent(data) {
    const el = document.getElementById('dashboard-content');
    if (!el) return;

    const subEl = document.getElementById('greeting-summary');
    if (subEl) subEl.textContent = buildSummaryLine(data);

    const widgets = getWidgetConfig();
    let html = '';

    // Notifications widget (above all zones)
    const notifWidget = widgets.find(w => w.id === 'notifications');
    if (notifWidget && notifWidget.enabled !== false) {
      html += renderNotificationsWidget(data);
    }

    // Zone A: "Dein Tag" — Shifts + Events
    const zoneShifts = WIDGET_RENDERERS.shifts ? renderShiftsWidget(data) : '';
    const zoneEvents = WIDGET_RENDERERS.events ? renderEventsWidget(data) : '';
    const zoneAContent = zoneShifts + zoneEvents;
    if (zoneAContent.trim()) {
      html += `<div class="dashboard-zone zone-today"><div class="zone-label">Dein Tag</div>${zoneAContent}</div>`;
    } else {
      html += zoneAContent;
    }

    // Zone B: Tasks + Shopping
    html += renderTasksWidget(data);
    html += renderShoppingWidget(data);

    // Remaining sync widgets
    for (const widget of widgets) {
      if (['notifications', 'shifts', 'events', 'tasks', 'shopping'].includes(widget.id)) continue;
      const renderer = WIDGET_RENDERERS[widget.id];
      if (renderer) {
        html += renderer(data);
      }
    }

    el.innerHTML = html;
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
        const size = formatFileSize(f.size);
        const date = f.modified_time ? new Date(f.modified_time).toLocaleDateString('de-DE', { day: 'numeric', month: 'short' }) : '';
        const meta = [size, date].filter(Boolean).join(' \u00b7 ');
        html += `
          <div class="card card-clickable" onclick="Router.navigate('#/drive')">
            <div class="drive-widget-file">
              <span class="drive-widget-icon">${fileIcon(f.mime_type)}</span>
              <div class="drive-widget-info">
                <div class="card-title">${escapeHtml(f.name)}</div>
                ${meta ? `<div class="card-subtitle">${meta}</div>` : ''}
              </div>
            </div>
          </div>
        `;
      });
    }
    return html;
  }

  async function renderWeatherWidget() {
    try {
      const data = await Api.get('/weather/current?location=Schwerin');
      const c = data.current;
      if (!c) return '';

      const icon = weatherIcon(c.description);
      const hint = getWeatherHint(c.temp_c, c.description);

      let html = `<a class="section-header section-link" href="#/weather"><span class="section-icon material-symbols-outlined">cloud</span> Wetter <span class="section-arrow">Details &#8594;</span></a>`;
      html += `<div class="card card-clickable" onclick="Router.navigate('#/weather')">`;
      html += `<div class="weather-widget-main">`;
      html += `<span class="material-symbols-outlined weather-widget-icon">${icon}</span>`;
      html += `<div class="weather-widget-temp">${c.temp_c}\u00b0C</div>`;
      html += `<div class="weather-widget-desc">${escapeHtml(c.description)}</div>`;
      html += `</div>`;
      if (hint) {
        html += `<div class="weather-widget-hint"><span class="material-symbols-outlined mi-sm">tips_and_updates</span> ${escapeHtml(hint)}</div>`;
      }
      html += `</div>`;
      return html;
    } catch {
      return '';
    }
  }

  async function renderWeeklyReviewWidget() {
    const review = await Api.getWeeklyReview();
    const ct = review.completed_tasks || 0;
    const ev = review.events_attended || 0;
    const sh = review.items_shopped || 0;

    if (ct === 0 && ev === 0 && sh === 0) {
      return `
        <div class="section-header"><span class="section-icon material-symbols-outlined">bar_chart</span> Wochenr\u00fcckblick</div>
        <div class="empty-state"><span class="material-symbols-outlined empty-state-icon">bar_chart</span><div class="empty-state-text">Noch keine Aktivit\u00e4t diese Woche</div></div>
      `;
    }

    let html = `<div class="section-header"><span class="section-icon material-symbols-outlined">bar_chart</span> Wochenr\u00fcckblick</div>`;
    html += `<div class="weekly-review-card">`;
    html += `<div class="weekly-review-stats">`;
    if (ct > 0) html += `<div class="weekly-review-stat"><span class="weekly-review-num">${ct}</span><span class="weekly-review-label">Aufgabe${ct > 1 ? 'n' : ''} erledigt</span></div>`;
    if (ev > 0) html += `<div class="weekly-review-stat"><span class="weekly-review-num">${ev}</span><span class="weekly-review-label">Termin${ev > 1 ? 'e' : ''}</span></div>`;
    if (sh > 0) html += `<div class="weekly-review-stat"><span class="weekly-review-num">${sh}</span><span class="weekly-review-label">Eink\u00e4ufe</span></div>`;
    html += `</div>`;

    // Highlights
    const highlights = review.highlights || [];
    if (highlights.length > 0) {
      html += `<div class="weekly-review-highlights">`;
      highlights.slice(0, 3).forEach(h => {
        html += `<div class="weekly-review-highlight"><span class="material-symbols-outlined mi-sm">check</span> ${escapeHtml(h)}</div>`;
      });
      html += `</div>`;
    }

    html += `</div>`;
    return html;
  }

  // ── Produktlinien-Widgets ──

  async function renderFinanceWidget() {
    try {
      const data = await Api.get('/finance/widget-summary');
      let html = `<a class="section-header section-link" href="#/finance"><span class="section-icon material-symbols-outlined">account_balance</span> Finanzhub <span class="section-arrow">Details &#8594;</span></a>`;
      html += `<div class="card card-clickable" onclick="Router.navigate('#/finance')">`;
      html += `<div class="card-title">Ausgaben diesen Monat</div>`;
      const pct = data.budget_total > 0 ? Math.min(100, Math.round(data.spending_this_month / data.budget_total * 100)) : 0;
      html += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">`;
      html += `<span style="font-size:1.3em;font-weight:600">${data.spending_this_month.toFixed(2)} \u20ac</span>`;
      if (data.budget_total > 0) {
        html += `<span class="card-subtitle">/ ${data.budget_total.toFixed(2)} \u20ac Budget (${pct}%)</span>`;
      }
      html += `</div>`;
      if (data.budget_total > 0) {
        html += `<div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>`;
      }
      if (data.next_payment_date) {
        html += `<div class="card-subtitle" style="margin-top:8px">N\u00e4chste Zahlung: ${new Date(data.next_payment_date).toLocaleDateString('de-DE')} \u2013 ${data.next_payment_amount.toFixed(2)} \u20ac</div>`;
      }
      if (data.open_invoices_count > 0) {
        html += `<div class="card-subtitle">${data.open_invoices_count} offene Rechnung${data.open_invoices_count > 1 ? 'en' : ''}</div>`;
      }
      html += `</div>`;
      return html;
    } catch {
      return '';
    }
  }

  async function renderInventoryWidget() {
    try {
      const data = await Api.get('/inventory/widget-summary');
      let html = `<a class="section-header section-link" href="#/inventory"><span class="section-icon material-symbols-outlined">inventory_2</span> Haushaltsordner <span class="section-arrow">Details &#8594;</span></a>`;
      html += `<div class="card card-clickable" onclick="Router.navigate('#/inventory')">`;
      const items = [];
      if (data.expiring_warranties_count > 0) {
        items.push(`${data.expiring_warranties_count} Garantie${data.expiring_warranties_count > 1 ? 'n' : ''} laufen bald ab`);
      }
      if (data.unprocessed_documents_count > 0) {
        items.push(`${data.unprocessed_documents_count} unbearbeitete${data.unprocessed_documents_count > 1 ? '' : 's'} Dokument${data.unprocessed_documents_count > 1 ? 'e' : ''}`);
      }
      if (data.next_deadline) {
        items.push(`N\u00e4chste Frist: ${new Date(data.next_deadline).toLocaleDateString('de-DE')}${data.next_deadline_doc ? ' (' + escapeHtml(data.next_deadline_doc) + ')' : ''}`);
      }
      if (items.length === 0) {
        html += `<div class="card-subtitle">Alles im gr\u00fcnen Bereich</div>`;
      } else {
        items.forEach(item => {
          html += `<div class="card-subtitle" style="margin-bottom:4px">${item}</div>`;
        });
      }
      html += `</div>`;
      return html;
    } catch {
      return '';
    }
  }

  async function renderFamilyWidget() {
    try {
      const data = await Api.get('/family/widget-summary');
      let html = `<a class="section-header section-link" href="#/family"><span class="section-icon material-symbols-outlined">family_restroom</span> Familien-Hub <span class="section-arrow">Details &#8594;</span></a>`;
      html += `<div class="card card-clickable" onclick="Router.navigate('#/family')">`;
      if (data.todays_routines && data.todays_routines.length > 0) {
        html += `<div class="card-title">Deine Aufgaben heute</div>`;
        data.todays_routines.forEach(r => {
          html += `<div class="card-subtitle" style="margin-bottom:4px"><span class="material-symbols-outlined mi-sm">task_alt</span> ${escapeHtml(r.name)}</div>`;
        });
      } else {
        html += `<div class="card-subtitle">Keine Aufgaben f\u00fcr heute</div>`;
      }
      if (data.workspace_count > 0) {
        html += `<div class="card-subtitle" style="margin-top:4px">${data.workspace_count} Workspace${data.workspace_count > 1 ? 's' : ''}</div>`;
      }
      html += `</div>`;
      return html;
    } catch {
      return '';
    }
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

  return { render, dismissSuggestion: _dismissSuggestion, showBriefing };
})();
