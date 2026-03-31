/**
 * Calendar View – Today/Week, Create Events
 */
const CalendarView = (() => {
  let activeTab = 'today';
  let events = [];
  let showForm = false;

  function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }

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
    container.innerHTML = `
      <a class="view-back" href="#/dashboard">&#8592; Dashboard</a>
      <div class="section-header"><span class="section-icon">&#128197;</span> Kalender</div>
      <div class="tabs">
        <button class="tab ${activeTab === 'today' ? 'active' : ''}" data-tab="today" onclick="CalendarView.switchTab('today')">Heute</button>
        <button class="tab ${activeTab === 'week' ? 'active' : ''}" data-tab="week" onclick="CalendarView.switchTab('week')">Woche</button>
      </div>
      <div id="calendar-toolbar"></div>
      <div id="calendar-content"><div class="loading"><div class="spinner"></div> Laden…</div></div>
    `;
    await loadData();
  }

  function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    showForm = false;
    document.getElementById('calendar-content').innerHTML = '<div class="loading"><div class="spinner"></div> Laden…</div>';
    loadData();
  }

  async function loadData() {
    try {
      const data = activeTab === 'today' ? await Api.getCalendarToday() : await Api.getCalendarWeek();
      events = data.events || [];
      renderToolbar(data.connected);
      renderEvents();
    } catch (err) {
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
        <span class="card-subtitle">${connected === false ? '&#9888; Kalender nicht verbunden' : ''}</span>
        <button class="btn btn-sm btn-primary" onclick="CalendarView.toggleForm()">+ Termin</button>
      </div>
      <div id="calendar-form-area"></div>
    `;
    if (showForm) renderForm();
  }

  function toggleForm() {
    showForm = !showForm;
    if (showForm) renderForm();
    else {
      const el = document.getElementById('calendar-form-area');
      if (el) el.innerHTML = '';
    }
  }

  function renderForm() {
    const el = document.getElementById('calendar-form-area');
    if (!el) return;
    const now = new Date();
    const later = new Date(now.getTime() + 3600000);
    const fmt = d => d.toISOString().slice(0, 16);
    el.innerHTML = `
      <div class="card event-create-form">
        <input type="text" id="event-summary" placeholder="Titel" class="mb-8">
        <div class="input-group mb-8">
          <input type="datetime-local" id="event-start" value="${fmt(now)}">
          <input type="datetime-local" id="event-end" value="${fmt(later)}">
        </div>
        <input type="text" id="event-location" placeholder="Ort (optional)" class="mb-8">
        <div class="flex-between">
          <button class="btn btn-sm btn-secondary" onclick="CalendarView.toggleForm()">Abbrechen</button>
          <button class="btn btn-sm btn-primary" onclick="CalendarView.createEvent()">Erstellen</button>
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
      alert('Bitte Titel, Start und Ende angeben.');
      return;
    }

    try {
      await Api.createCalendarEvent({
        summary,
        start: new Date(start).toISOString(),
        end: new Date(end).toISOString(),
        location: location || undefined,
      });
      showForm = false;
      await loadData();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  function renderEvents() {
    const el = document.getElementById('calendar-content');
    if (!el) return;

    if (events.length === 0) {
      el.innerHTML = `<div class="empty-state">Keine Termine ${activeTab === 'today' ? 'heute' : 'diese Woche'}</div>`;
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
    return `
      <div class="card">
        <div class="event-time">${formatTime(e.start)}${e.end ? ' – ' + formatTime(e.end) : ''}</div>
        <div class="card-title">${escapeHtml(e.summary || '')}</div>
        ${e.location ? `<div class="card-subtitle">${escapeHtml(e.location)}</div>` : ''}
        ${e.description ? `<div class="card-subtitle mt-8">${escapeHtml(e.description)}</div>` : ''}
      </div>
    `;
  }

  return { render, switchTab, toggleForm, createEvent };
})();
