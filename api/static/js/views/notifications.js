/**
 * DualMind Notification Center View
 * Zeigt zentrale Benachrichtigungen: Erinnerungen, Warnungen, Systemhinweise.
 */
const NotificationsView = (() => {
  let notifications = [];
  let activeTypeFilter = null;
  let activeStatusFilter = null;
  let loading = false;
  let container = null;

  const TYPE_META = {
    reminder:  { icon: 'schedule',    label: 'Erinnerung', color: 'var(--accent)' },
    follow_up: { icon: 'reply',       label: 'Follow-up',  color: 'var(--warning)' },
    document:  { icon: 'description', label: 'Dokument',   color: 'var(--success)' },
    inbox:     { icon: 'inbox',       label: 'Inbox',      color: 'var(--info, #42a5f5)' },
    weather:   { icon: 'cloud',       label: 'Wetter',     color: 'var(--warning)' },
    system:    { icon: 'info',        label: 'System',     color: 'var(--error)' },
  };

  const STATUS_META = {
    new:       { label: 'Neu',        class: 'badge-accent' },
    read:      { label: 'Gelesen',    class: 'badge' },
    completed: { label: 'Erledigt',   class: 'badge-success' },
    hidden:    { label: 'Ausgeblendet', class: 'badge' },
  };

  function formatTime(dateStr) {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Gerade eben';
    if (diff < 3600000) return `vor ${Math.floor(diff / 60000)} Min.`;
    if (diff < 86400000) return `vor ${Math.floor(diff / 3600000)} Std.`;
    if (diff < 172800000) return 'Gestern';
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
  }

  function renderFilters() {
    const types = Object.entries(TYPE_META);
    const statusFilters = [
      { key: null, label: 'Alle' },
      { key: 'new', label: 'Neu' },
      { key: 'read', label: 'Gelesen' },
      { key: 'completed', label: 'Erledigt' },
    ];

    return `
      <div class="notification-filters">
        <div class="notification-filter-row">
          ${statusFilters.map(s => `
            <button class="filter-chip ${activeStatusFilter === s.key ? 'active' : ''}"
                    data-status-filter="${s.key || ''}">${s.label}</button>
          `).join('')}
        </div>
        <div class="notification-filter-row">
          <button class="filter-chip ${!activeTypeFilter ? 'active' : ''}"
                  data-type-filter="">Alle Typen</button>
          ${types.map(([key, meta]) => `
            <button class="filter-chip ${activeTypeFilter === key ? 'active' : ''}"
                    data-type-filter="${key}">
              <span class="material-symbols-outlined" style="font-size:14px">${meta.icon}</span>
              ${meta.label}
            </button>
          `).join('')}
        </div>
      </div>
    `;
  }

  function renderNotification(n) {
    const meta = TYPE_META[n.type] || TYPE_META.system;
    const statusMeta = STATUS_META[n.status] || STATUS_META.new;
    const isNew = n.status === 'new';

    return `
      <div class="notification-card ${isNew ? 'notification-new' : ''}" data-id="${n.id}">
        <div class="notification-icon" style="color:${meta.color}">
          <span class="material-symbols-outlined">${meta.icon}</span>
        </div>
        <div class="notification-content">
          <div class="notification-header">
            <span class="notification-title">${n.title}</span>
            <span class="${statusMeta.class}" style="font-size:11px">${statusMeta.label}</span>
          </div>
          ${n.message ? `<p class="notification-message">${n.message}</p>` : ''}
          <div class="notification-meta">
            <span class="notification-type-label">${meta.label}</span>
            <span class="notification-time">${formatTime(n.created_at)}</span>
          </div>
        </div>
        <div class="notification-actions">
          ${n.link ? `<button class="btn-icon" data-action="open" title="Oeffnen"><span class="material-symbols-outlined">open_in_new</span></button>` : ''}
          ${['reminder', 'follow_up'].includes(n.type) ? `<button class="btn-icon notification-action-btn" data-action="to-task" title="Als Aufgabe erstellen"><span class="material-symbols-outlined">add_task</span></button>` : ''}
          ${n.type === 'reminder' ? `<button class="btn-icon notification-action-btn" data-action="to-calendar" title="Im Kalender ansehen"><span class="material-symbols-outlined">calendar_month</span></button>` : ''}
          ${n.status === 'new' ? `<button class="btn-icon" data-action="read" title="Als gelesen markieren"><span class="material-symbols-outlined">done</span></button>` : ''}
          ${n.status !== 'completed' ? `<button class="btn-icon" data-action="complete" title="Erledigen"><span class="material-symbols-outlined">check_circle</span></button>` : ''}
          ${n.status !== 'hidden' ? `<button class="btn-icon" data-action="hide" title="Ausblenden"><span class="material-symbols-outlined">visibility_off</span></button>` : ''}
        </div>
      </div>
    `;
  }

  function renderList() {
    if (loading) {
      return '<div class="loading"><div class="spinner"></div></div>';
    }
    if (!notifications.length) {
      return `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-secondary)">notifications_none</span>
          <p>Keine Benachrichtigungen</p>
        </div>
      `;
    }
    return notifications.map(renderNotification).join('');
  }

  function renderHeader() {
    const unreadCount = notifications.filter(n => n.status === 'new').length;
    return `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">notifications</span> Benachrichtigungen</h2>
        ${unreadCount > 0 ? `<button class="btn btn-sm btn-secondary" id="mark-all-read">Alle als gelesen</button>` : ''}
      </div>
    `;
  }

  async function load() {
    loading = true;
    update();
    try {
      const params = {};
      if (activeTypeFilter) params.type = activeTypeFilter;
      if (activeStatusFilter) params.status = activeStatusFilter;
      notifications = await Api.getNotifications(params);
    } catch (err) {
      notifications = [];
      if (container) {
        container.innerHTML = `
          ${renderHeader()}
          ${renderFilters()}
          <div class="error-state">
            <p>Fehler beim Laden: ${err.message}</p>
            <button class="btn btn-sm btn-primary" id="retry-btn">Erneut versuchen</button>
          </div>
        `;
        container.querySelector('#retry-btn')?.addEventListener('click', load);
      }
      return;
    } finally {
      loading = false;
    }
    update();
  }

  function update() {
    if (!container) return;
    container.innerHTML = `
      ${renderHeader()}
      ${renderFilters()}
      <div class="notification-list">
        ${renderList()}
      </div>
    `;
    bindEvents();
  }

  function bindEvents() {
    if (!container) return;

    // Mark all read
    container.querySelector('#mark-all-read')?.addEventListener('click', async () => {
      try {
        await Api.markAllNotificationsRead();
        notifications.forEach(n => { if (n.status === 'new') n.status = 'read'; });
        update();
        NotificationBell.refresh();
      } catch (_) { /* Toast handles error */ }
    });

    // Filter chips - status
    container.querySelectorAll('[data-status-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        const val = btn.dataset.statusFilter;
        activeStatusFilter = val || null;
        load();
      });
    });

    // Filter chips - type
    container.querySelectorAll('[data-type-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        const val = btn.dataset.typeFilter;
        activeTypeFilter = val || null;
        load();
      });
    });

    // Per-notification actions
    container.querySelectorAll('.notification-card').forEach(card => {
      const id = parseInt(card.dataset.id);
      const notif = notifications.find(n => n.id === id);
      if (!notif) return;

      card.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const action = btn.dataset.action;
          try {
            if (action === 'open' && notif.link) {
              // Mark as read when opening
              if (notif.status === 'new') {
                await Api.updateNotification(id, 'read');
                notif.status = 'read';
                NotificationBell.refresh();
              }
              window.location.hash = notif.link;
              return;
            }
            if (action === 'to-task') {
              // Navigate to tasks view – user creates task manually
              if (notif.status === 'new') {
                await Api.updateNotification(id, 'read');
                notif.status = 'read';
                NotificationBell.refresh();
              }
              window.location.hash = '#/tasks';
              return;
            }
            if (action === 'to-calendar') {
              if (notif.status === 'new') {
                await Api.updateNotification(id, 'read');
                notif.status = 'read';
                NotificationBell.refresh();
              }
              window.location.hash = '#/calendar';
              return;
            }
            if (action === 'read') {
              await Api.updateNotification(id, 'read');
              notif.status = 'read';
            } else if (action === 'complete') {
              await Api.updateNotification(id, 'completed');
              notif.status = 'completed';
            } else if (action === 'hide') {
              await Api.updateNotification(id, 'hidden');
              // Remove from visible list if no status filter for hidden
              if (activeStatusFilter !== 'hidden') {
                notifications = notifications.filter(n => n.id !== id);
              } else {
                notif.status = 'hidden';
              }
            }
            update();
            NotificationBell.refresh();
          } catch (_) { /* Toast handles error */ }
        });
      });

      // Click on card itself opens deep link
      card.addEventListener('click', async () => {
        if (notif.status === 'new') {
          try {
            await Api.updateNotification(id, 'read');
            notif.status = 'read';
            NotificationBell.refresh();
          } catch (_) {}
        }
        if (notif.link) {
          window.location.hash = notif.link;
        }
      });
    });
  }

  async function render(el) {
    container = el;
    activeTypeFilter = null;
    activeStatusFilter = null;
    await load();
  }

  return { render };
})();

/**
 * Notification Bell – Header-Badge mit Unread-Counter.
 * Wird global initialisiert und pollt alle 60s.
 */
const NotificationBell = (() => {
  let _interval = null;
  let _badge = null;

  async function refresh() {
    if (!Api.isLoggedIn()) {
      updateBadge(0);
      return;
    }
    try {
      const data = await Api.getNotificationCount();
      updateBadge(data.unread || 0);
    } catch (_) {
      // Silent fail – don't show toast for background polling
    }
  }

  function updateBadge(count) {
    _badge = document.getElementById('notification-badge');
    if (!_badge) return;
    if (count > 0) {
      _badge.textContent = count > 99 ? '99+' : count;
      _badge.classList.remove('hidden');
    } else {
      _badge.classList.add('hidden');
    }
  }

  function init() {
    refresh();
    if (_interval) clearInterval(_interval);
    _interval = setInterval(refresh, 60000);
  }

  function stop() {
    if (_interval) { clearInterval(_interval); _interval = null; }
  }

  return { init, stop, refresh };
})();
