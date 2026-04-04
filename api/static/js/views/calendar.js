/**
 * Calendar View – Today/Week, Create/Edit/Delete Events
 */
const CalendarView = (() => {
  let activeTab = 'today';
  let events = [];
  let showForm = false;
  let editingEvent = null;  // null = create mode, object = edit mode
  let detailEvent = null;   // event shown in detail modal

  const formatTime = Utils.formatClockTime;

  function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' });
  }

  function formatDateShort(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  async function render(container) {
    showForm = false;
    editingEvent = null;
    detailEvent = null;
    container.innerHTML = `
      <a class="view-back" href="#/dashboard"><span class="material-symbols-outlined mi-sm">arrow_back</span> Dashboard</a>
      <div class="section-header"><span class="section-icon material-symbols-outlined">calendar_month</span> Kalender</div>
      <div class="tabs">
        <button class="tab ${activeTab === 'today' ? 'active' : ''}" data-tab="today" onclick="CalendarView.switchTab('today')">Heute</button>
        <button class="tab ${activeTab === 'week' ? 'active' : ''}" data-tab="week" onclick="CalendarView.switchTab('week')">Woche</button>
      </div>
      <div id="calendar-toolbar"></div>
      <div id="calendar-content">
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
      </div>
      <div id="calendar-detail-modal"></div>
    `;
    await loadData();
  }

  function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    showForm = false;
    editingEvent = null;
    detailEvent = null;
    document.getElementById('calendar-content').innerHTML = '<div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div>';
    loadData();
  }

  const CACHE_KEY = 'dm_cache_calendar';

  function _cacheKey() { return CACHE_KEY + '_' + activeTab; }

  async function loadData() {
    // Stale-while-revalidate: show cached data immediately, then refresh
    const cached = OfflineQueue.loadCache(_cacheKey());
    if (cached && cached.data) {
      events = cached.data.events || [];
      renderToolbar(cached.data.connected);
      renderEvents();
    }

    try {
      const data = activeTab === 'today' ? await Api.getCalendarToday() : await Api.getCalendarWeek();
      events = data.events || [];
      OfflineQueue.saveCache(_cacheKey(), data);
      renderToolbar(data.connected);
      renderEvents();
      // Remove offline banner if present
      const offBanner = document.getElementById('calendar-offline-banner');
      if (offBanner) offBanner.remove();
    } catch (err) {
      // If we already showed cached data, just add offline indicator
      if (cached && cached.data) {
        const el = document.getElementById('calendar-content');
        if (el && !document.getElementById('calendar-offline-banner')) {
          const ts = new Date(cached.ts).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
          el.insertAdjacentHTML('afterbegin',
            `<div id="calendar-offline-banner" class="offline-cache-banner">
              <span class="material-symbols-outlined mi-sm">cloud_off</span>
              Offline \u2014 zuletzt aktualisiert: ${ts}
            </div>`);
        }
        return;
      }
      document.getElementById('calendar-content').innerHTML = `
        <div class="error-state"><p>${escapeHtml(err.message)}</p>
          <button class="btn btn-secondary" onclick="CalendarView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

  function renderToolbar(connected) {
    const el = document.getElementById('calendar-toolbar');
    if (!el) return;
    el.innerHTML = `
      <div class="flex-between mb-8">
        <span class="card-subtitle">${connected === false ? '<span class="material-symbols-outlined mi-sm">warning</span> Kalender nicht verbunden' : ''}</span>
        <div style="display:flex;gap:8px">
          <a href="#/shifts" class="btn btn-sm btn-secondary"><span class="mi-sm material-symbols-outlined">work</span> Dienstplan</a>
          <button class="btn btn-sm btn-primary" onclick="CalendarView.toggleForm()" ${connected === false ? 'disabled title="Kalender nicht verbunden"' : ''}>+ Termin</button>
        </div>
      </div>
      <div id="calendar-form-area"></div>
    `;
    if (showForm) renderForm();
  }

  function toggleForm() {
    showForm = !showForm;
    editingEvent = null;
    if (showForm) renderForm();
    else {
      const el = document.getElementById('calendar-form-area');
      if (el) el.innerHTML = '';
    }
  }

  function openEditForm(evt) {
    editingEvent = evt;
    showForm = true;
    detailEvent = null;
    const modal = document.getElementById('calendar-detail-modal');
    if (modal) modal.innerHTML = '';
    renderForm();
  }

  function renderForm() {
    const el = document.getElementById('calendar-form-area');
    if (!el) return;
    const isEdit = !!editingEvent;
    const now = new Date();
    const later = new Date(now.getTime() + 3600000);
    const fmt = d => {
      if (!d) return '';
      const dt = new Date(d);
      return isNaN(dt.getTime()) ? '' : dt.toISOString().slice(0, 16);
    };
    const startVal = isEdit ? fmt(editingEvent.start) : fmt(now);
    const endVal = isEdit ? fmt(editingEvent.end) : fmt(later);
    el.innerHTML = `
      <div class="card event-create-form">
        <h4 style="margin-bottom:8px">${isEdit ? 'Termin bearbeiten' : 'Neuer Termin'}</h4>
        <input type="text" id="event-summary" placeholder="Titel" class="mb-8" value="${isEdit ? escapeHtml(editingEvent.summary || '') : ''}">
        <div class="input-group mb-8">
          <input type="datetime-local" id="event-start" value="${startVal}">
          <input type="datetime-local" id="event-end" value="${endVal}">
        </div>
        <input type="text" id="event-location" placeholder="Ort (optional)" class="mb-8" value="${isEdit ? escapeHtml(editingEvent.location || '') : ''}">
        <textarea id="event-description" placeholder="Beschreibung (optional)" class="mb-8" rows="2">${isEdit ? escapeHtml(editingEvent.description || '') : ''}</textarea>
        <div class="flex-between">
          <button class="btn btn-sm btn-secondary" onclick="CalendarView.toggleForm()">Abbrechen</button>
          <button class="btn btn-sm btn-primary" onclick="${isEdit ? 'CalendarView.saveEdit()' : 'CalendarView.createEvent()'}">
            ${isEdit ? 'Speichern' : 'Erstellen'}
          </button>
        </div>
      </div>
    `;
  }

  async function createEvent() {
    const summary = document.getElementById('event-summary').value.trim();
    const start = document.getElementById('event-start').value;
    const end = document.getElementById('event-end').value;
    const location = document.getElementById('event-location').value.trim();

    if (!summary || !start || !end) {
      if (!summary) document.getElementById('event-summary').classList.add('input-error');
      if (!start) document.getElementById('event-start').classList.add('input-error');
      if (!end) document.getElementById('event-end').classList.add('input-error');
      return;
    }

    const eventData = {
      summary,
      start: new Date(start).toISOString(),
      end: new Date(end).toISOString(),
      location: location || undefined,
    };

    try {
      await Api.createCalendarEvent(eventData);
      showForm = false;
      editingEvent = null;
      Toast.show('Termin erstellt', 'success');
      await loadData();
    } catch (err) {
      if (err.isOffline || (typeof OfflineQueue !== 'undefined' && !OfflineQueue.isOnline())) {
        OfflineQueue.enqueueCalendarCreate(eventData);
        showForm = false;
        editingEvent = null;
        Toast.show('Termin wird erstellt wenn online', 'warning');
      } else {
        Toast.show('Fehler: ' + err.message, 'error');
      }
    }
  }

  async function saveEdit() {
    if (!editingEvent || !editingEvent.id) return;

    const summary = document.getElementById('event-summary').value.trim();
    const start = document.getElementById('event-start').value;
    const end = document.getElementById('event-end').value;
    const location = document.getElementById('event-location').value.trim();
    const description = document.getElementById('event-description').value.trim();

    if (!summary || !start || !end) {
      if (!summary) document.getElementById('event-summary').classList.add('input-error');
      if (!start) document.getElementById('event-start').classList.add('input-error');
      if (!end) document.getElementById('event-end').classList.add('input-error');
      return;
    }

    try {
      await Api.request(`/calendar/events/${editingEvent.id}`, {
        method: 'PATCH',
        body: {
          summary,
          start: new Date(start).toISOString(),
          end: new Date(end).toISOString(),
          location,
          description,
        },
      });
      showForm = false;
      editingEvent = null;
      Toast.show('Termin aktualisiert', 'success');
      await loadData();
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function deleteEvent(eventId) {
    if (!eventId) return;
    try {
      await Api.request(`/calendar/events/${eventId}`, { method: 'DELETE' });
      detailEvent = null;
      const modal = document.getElementById('calendar-detail-modal');
      if (modal) modal.innerHTML = '';
      Toast.show('Termin geloescht', 'success');
      await loadData();
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  function showDetail(eventId) {
    const evt = events.find(e => e.id === eventId);
    if (!evt) return;
    detailEvent = evt;
    renderDetailModal();
  }

  function closeDetail() {
    detailEvent = null;
    const modal = document.getElementById('calendar-detail-modal');
    if (modal) modal.innerHTML = '';
  }

  function renderDetailModal() {
    const modal = document.getElementById('calendar-detail-modal');
    if (!modal || !detailEvent) return;
    const e = detailEvent;
    const isGoogle = e.source === 'google';
    modal.innerHTML = `
      <div class="modal-overlay" onclick="CalendarView.closeDetail()">
        <div class="card modal-content" onclick="event.stopPropagation()" style="max-width:480px;margin:auto;margin-top:10vh">
          <h3 style="margin-bottom:8px">${escapeHtml(e.summary || 'Kein Titel')}</h3>
          <div class="card-subtitle mb-8">
            <span class="material-symbols-outlined mi-sm">schedule</span>
            ${formatTime(e.start)}${e.end ? ' – ' + formatTime(e.end) : ''}
            ${e.start ? ' · ' + formatDate(e.start) : ''}
          </div>
          ${e.location ? `<div class="card-subtitle mb-8"><span class="material-symbols-outlined mi-sm">location_on</span> ${escapeHtml(e.location)}</div>` : ''}
          ${e.description ? `<div class="card-subtitle mb-8"><span class="material-symbols-outlined mi-sm">notes</span> ${escapeHtml(e.description)}</div>` : ''}
          <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end">
            <button class="btn btn-sm btn-secondary" onclick="CalendarView.closeDetail()">Schliessen</button>
            ${isGoogle ? `
              <button class="btn btn-sm btn-secondary" onclick="CalendarView.openEditForm(CalendarView._getDetailEvent())">
                <span class="material-symbols-outlined mi-sm">edit</span> Bearbeiten
              </button>
              <button class="btn btn-sm btn-danger" onclick="CalendarView.confirmDelete('${e.id}')">
                <span class="material-symbols-outlined mi-sm">delete</span> Loeschen
              </button>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }

  function confirmDelete(eventId) {
    const modal = document.getElementById('calendar-detail-modal');
    if (!modal) return;
    modal.innerHTML = `
      <div class="modal-overlay" onclick="CalendarView.closeDetail()">
        <div class="card modal-content" onclick="event.stopPropagation()" style="max-width:400px;margin:auto;margin-top:15vh;text-align:center">
          <span class="material-symbols-outlined" style="font-size:40px;color:var(--error);margin-bottom:8px">warning</span>
          <h3 style="margin-bottom:8px">Termin loeschen?</h3>
          <p class="card-subtitle mb-8">Diese Aktion kann nicht rueckgaengig gemacht werden.</p>
          <div style="display:flex;gap:8px;justify-content:center;margin-top:16px">
            <button class="btn btn-sm btn-secondary" onclick="CalendarView.closeDetail()">Abbrechen</button>
            <button class="btn btn-sm btn-danger" onclick="CalendarView.deleteEvent('${eventId}')">Loeschen</button>
          </div>
        </div>
      </div>
    `;
  }

  function _getDetailEvent() {
    return detailEvent;
  }

  function renderEvents() {
    const el = document.getElementById('calendar-content');
    if (!el) return;

    if (events.length === 0) {
      el.innerHTML = `<div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted);display:block;margin-bottom:8px">calendar_month</span>
        Keine Termine ${activeTab === 'today' ? 'heute' : 'diese Woche'}
        <br><button class="btn btn-sm btn-primary mt-8" onclick="CalendarView.toggleForm()">+ Termin erstellen</button>
      </div>`;
      return;
    }

    if (activeTab === 'today') {
      el.innerHTML = events.map(e => renderEventCard(e)).join('');
    } else {
      // Group by date
      const groups = {};
      events.forEach(e => {
        const day = e.start ? e.start.slice(0, 10) : 'unknown';
        if (!groups[day]) groups[day] = [];
        groups[day].push(e);
      });

      let html = '';
      Object.keys(groups).sort().forEach(day => {
        html += `<div class="day-label">${formatDate(day)}</div>`;
        html += groups[day].map(e => renderEventCard(e)).join('');
      });
      el.innerHTML = html;
    }
  }

  function renderEventCard(e) {
    const isShift = e.source === 'shift';
    const borderStyle = isShift ? `border-left:4px solid ${e.shift_color || 'var(--accent)'}` : '';
    const catBadge = isShift
      ? `<span class="shift-badge" style="background:${e.shift_color || 'var(--accent)'}22;color:${e.shift_color || 'var(--accent)'}">${escapeHtml(e.shift_short_name || '')}</span> `
      : '';
    const clickable = e.id ? `onclick="CalendarView.showDetail('${e.id}')" style="cursor:pointer;${borderStyle}"` : `style="${borderStyle}"`;
    return `
      <div class="card" ${clickable}>
        <div class="event-time">${formatTime(e.start)}${e.end ? ' – ' + formatTime(e.end) : ''}</div>
        <div class="card-title">${catBadge}${escapeHtml(e.summary || '')}</div>
        ${e.location ? `<div class="card-subtitle">${escapeHtml(e.location)}</div>` : ''}
        ${e.description ? `<div class="card-subtitle mt-8">${escapeHtml(e.description)}</div>` : ''}
      </div>
    `;
  }

  return { render, switchTab, toggleForm, createEvent, saveEdit, deleteEvent, showDetail, closeDetail, openEditForm, confirmDelete, _getDetailEvent };
})();
