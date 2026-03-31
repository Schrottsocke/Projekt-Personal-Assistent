/**
 * Dashboard View – Greeting, Events, Tasks, Shopping Preview
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

  async function render(container) {
    const user = capitalize(Api.getUserKey());
    container.innerHTML = `
      <div class="greeting">${getGreeting()}, ${user}</div>
      <div class="greeting-sub">Hier ist dein Tagesueberblick</div>
      <div id="dashboard-content"><div class="loading"><div class="spinner"></div> Laden…</div></div>
    `;

    try {
      const data = await Api.getDashboard();
      renderContent(data);
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

  function renderContent(data) {
    const el = document.getElementById('dashboard-content');
    if (!el) return;

    const events = (data.events_today || []).slice(0, 3);
    const tasks = (data.open_tasks || []).slice(0, 3);
    const shop = data.shopping_preview || {};
    const emails = data.unread_emails || 0;

    let html = '';

    // Email badge
    if (emails > 0) {
      html += `<div class="mb-16"><span class="badge badge-accent email-badge">&#9993; ${emails} ungelesene E-Mail${emails > 1 ? 's' : ''}</span></div>`;
    }

    // Events
    html += `<div class="section-header"><span class="section-icon">&#128197;</span> Termine heute</div>`;
    if (events.length === 0) {
      html += `<div class="empty-state">Keine Termine heute</div>`;
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

    // Tasks
    html += `<div class="section-header"><span class="section-icon">&#9745;</span> Offene Aufgaben <span class="badge badge-accent">${data.task_count || tasks.length}</span></div>`;
    if (tasks.length === 0) {
      html += `<div class="empty-state">Keine offenen Aufgaben</div>`;
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

    // Shopping preview
    const total = shop.total || 0;
    const checked = shop.checked || 0;
    const pending = shop.pending || (total - checked);
    const pct = total > 0 ? Math.round((checked / total) * 100) : 0;

    html += `<div class="section-header"><span class="section-icon">&#128722;</span> Einkaufsliste</div>`;
    if (total === 0) {
      html += `<div class="empty-state">Einkaufsliste ist leer</div>`;
    } else {
      html += `
        <div class="card" style="cursor:pointer" onclick="Router.navigate('#/shopping')">
          <div class="flex-between mb-8">
            <span>${pending} offen</span>
            <span class="card-subtitle">${checked}/${total} erledigt</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div class="progress-text">${pct}%</div>
        </div>
      `;
    }

    el.innerHTML = html;
  }

  return { render };
})();
