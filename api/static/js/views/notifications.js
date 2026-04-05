/**
 * Notifications View – Benachrichtigungen & Einstellungen
 * Issue #685: Notifications-Center-View
 */
const NotificationsView = (() => {
  let activeTab = 'notifications';
  let notifications = [];
  let settings = {};
  let savingSettings = false;

  const CATEGORY_ICONS = {
    finance:   'account_balance',
    inventory: 'inventory_2',
    tasks:     'check_circle',
    calendar:  'calendar_month',
    system:    'settings',
    family:    'group',
  };

  const CATEGORY_LABELS = {
    finance:   'Finanzen',
    inventory: 'Inventar',
    tasks:     'Aufgaben',
    calendar:  'Kalender',
    system:    'System',
    family:    'Familie',
  };

  function esc(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function relativeTime(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHrs = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMin < 1)  return 'Gerade eben';
    if (diffMin < 60) return `vor ${diffMin} Min`;
    if (diffHrs < 24) return `vor ${diffHrs} Std`;
    if (diffDays === 1) return 'Gestern';
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function categoryIcon(category) {
    return CATEGORY_ICONS[category] || 'notifications';
  }

  /* ── Render ──────────────────────────────────────────────── */

  async function render(container) {
    activeTab = 'notifications';
    container.innerHTML = `
      <div class="notifications-view">
        <div class="section-header">
          <span class="section-icon material-symbols-outlined">notifications</span>
          Benachrichtigungen
        </div>
        <div class="tabs mb-8" id="notifications-tabs">
          <button class="tab active" data-tab="notifications"
                  onclick="NotificationsView.switchTab('notifications')">Benachrichtigungen</button>
          <button class="tab" data-tab="settings"
                  onclick="NotificationsView.switchTab('settings')">Einstellungen</button>
        </div>
        <div id="notifications-content">
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
        </div>
      </div>
    `;
    await loadNotifications();
  }

  async function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('#notifications-tabs .tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    if (tab === 'notifications') {
      await loadNotifications();
    } else {
      await loadSettings();
    }
  }

  /* ── Notifications Tab ───────────────────────────────────── */

  async function loadNotifications() {
    const el = document.getElementById('notifications-content');
    if (!el) return;
    el.innerHTML = `
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;
    try {
      const [list, countData] = await Promise.all([
        Api.getNotifications(),
        Api.getNotificationCount(),
      ]);
      notifications = list || [];
      renderNotificationsList(countData);
    } catch (err) {
      el.innerHTML = `
        <div class="error-state">
          <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted);display:block;margin-bottom:8px">error_outline</span>
          <p>${esc(err.message)}</p>
          <button class="btn btn-secondary" onclick="NotificationsView.switchTab('notifications')">Erneut versuchen</button>
        </div>
      `;
    }
  }

  function renderNotificationsList(countData) {
    const el = document.getElementById('notifications-content');
    if (!el) return;

    const unread = countData ? countData.unread : notifications.filter(n => !n.is_read).length;

    let html = `<div class="notifications-header flex-between mb-8">`;
    html += `<div>`;
    if (unread > 0) {
      html += `<span class="badge badge-accent">${unread} ungelesen</span>`;
    } else {
      html += `<span class="badge badge-muted">Alle gelesen</span>`;
    }
    html += `</div>`;
    if (unread > 0) {
      html += `<button class="btn btn-secondary btn-sm" onclick="NotificationsView.markAllRead()">
        <span class="material-symbols-outlined mi-sm">done_all</span> Alle als gelesen
      </button>`;
    }
    html += `</div>`;

    if (notifications.length === 0) {
      html += `<div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted);display:block;margin-bottom:8px">notifications_off</span>
        Keine Benachrichtigungen vorhanden
      </div>`;
      el.innerHTML = html;
      return;
    }

    html += `<div class="notification-list">`;
    notifications.forEach(n => {
      const icon = categoryIcon(n.category);
      const time = relativeTime(n.created_at);
      const unreadStyle = !n.is_read
        ? 'border-left: 3px solid var(--accent); background: var(--surface-2, var(--card-bg));'
        : 'opacity: 0.7;';
      const titleStyle = !n.is_read ? 'font-weight: 700;' : '';

      html += `
        <div class="card notification-item" style="${unreadStyle} cursor:pointer; margin-bottom:8px; padding:12px;"
             onclick="NotificationsView.handleNotificationClick(${n.id}, '${esc(n.action_url || '')}')">
          <div style="display:flex; align-items:flex-start; gap:10px;">
            <span class="material-symbols-outlined" style="color:var(--accent);flex-shrink:0;">${icon}</span>
            <div style="flex:1;min-width:0;">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">
                <span style="${titleStyle} font-size:0.95rem;">${esc(n.title)}</span>
                <span style="font-size:0.75rem;color:var(--text-muted);white-space:nowrap;">${time}</span>
              </div>
              ${n.message ? `<div style="font-size:0.85rem;color:var(--text-muted);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(n.message)}</div>` : ''}
              ${n.category ? `<div style="margin-top:4px;"><span class="badge badge-muted" style="font-size:0.7rem;">${esc(CATEGORY_LABELS[n.category] || n.category)}</span></div>` : ''}
            </div>
            <button class="btn btn-sm btn-danger" style="flex-shrink:0;padding:4px 8px;"
                    onclick="event.stopPropagation(); NotificationsView.deleteNotification(${n.id})"
                    title="Löschen">
              <span class="material-symbols-outlined mi-sm">delete</span>
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;

    el.innerHTML = html;
  }

  async function handleNotificationClick(id, actionUrl) {
    const n = notifications.find(x => x.id === id);
    if (n && !n.is_read) {
      try {
        await Api.updateNotification(id, { is_read: true });
        n.is_read = true;
        renderNotificationsList(null);
      } catch (e) {
        // non-critical, continue navigation
      }
    }
    if (actionUrl && actionUrl.startsWith('#/')) {
      Router.navigate(actionUrl);
    } else if (actionUrl) {
      window.open(actionUrl, '_blank', 'noopener');
    }
  }

  async function markAllRead() {
    try {
      await Api.markAllNotificationsRead();
      notifications.forEach(n => { n.is_read = true; });
      renderNotificationsList({ total: notifications.length, unread: 0 });
      Toast.show('Alle Benachrichtigungen als gelesen markiert', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function deleteNotification(id) {
    try {
      await Api.delete(`/notifications/${id}`);
      notifications = notifications.filter(n => n.id !== id);
      renderNotificationsList(null);
      Toast.show('Benachrichtigung gelöscht', 'success');
    } catch (err) {
      Toast.show('Fehler beim Löschen: ' + err.message, 'error');
    }
  }

  /* ── Settings Tab ────────────────────────────────────────── */

  async function loadSettings() {
    const el = document.getElementById('notifications-content');
    if (!el) return;
    el.innerHTML = `
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;
    try {
      settings = await Api.get('/notifications/settings') || {};
      renderSettingsTab();
    } catch (err) {
      el.innerHTML = `
        <div class="error-state">
          <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted);display:block;margin-bottom:8px">error_outline</span>
          <p>${esc(err.message)}</p>
          <button class="btn btn-secondary" onclick="NotificationsView.switchTab('settings')">Erneut versuchen</button>
        </div>
      `;
    }
  }

  function renderSettingsTab() {
    const el = document.getElementById('notifications-content');
    if (!el) return;

    const categories = Object.keys(CATEGORY_LABELS);

    let html = `
      <div class="section-header" style="margin-bottom:8px;">
        <span class="section-icon material-symbols-outlined">tune</span>
        Benachrichtigungs-Einstellungen
      </div>
      <div class="card" style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
          <thead>
            <tr style="border-bottom:1px solid var(--border, #333);">
              <th style="text-align:left;padding:8px 4px;">Kategorie</th>
              <th style="text-align:center;padding:8px 4px;white-space:nowrap;">
                <span class="material-symbols-outlined mi-sm" title="Push">notifications</span>
                <span style="font-size:0.75rem;display:block;">Push</span>
              </th>
              <th style="text-align:center;padding:8px 4px;white-space:nowrap;">
                <span class="material-symbols-outlined mi-sm" title="In-App">smartphone</span>
                <span style="font-size:0.75rem;display:block;">In-App</span>
              </th>
              <th style="text-align:center;padding:8px 4px;white-space:nowrap;">
                <span class="material-symbols-outlined mi-sm" title="E-Mail">email</span>
                <span style="font-size:0.75rem;display:block;">E-Mail</span>
              </th>
            </tr>
          </thead>
          <tbody>
    `;

    categories.forEach(cat => {
      const icon = categoryIcon(cat);
      const label = CATEGORY_LABELS[cat] || cat;
      const catSettings = (settings && settings[cat]) || {};
      const pushChecked   = catSettings.push   !== false;
      const inAppChecked  = catSettings.in_app !== false;
      const emailChecked  = catSettings.email  !== false;

      html += `
        <tr style="border-bottom:1px solid var(--border-light, #2a2a2a);">
          <td style="padding:10px 4px;">
            <span class="material-symbols-outlined mi-sm" style="vertical-align:middle;margin-right:6px;color:var(--accent);">${icon}</span>
            ${esc(label)}
          </td>
          <td style="text-align:center;padding:10px 4px;">
            <label class="toggle-label">
              <input type="checkbox" class="notification-toggle"
                     data-category="${esc(cat)}" data-channel="push"
                     ${pushChecked ? 'checked' : ''}
                     onchange="NotificationsView.onToggleChange()">
            </label>
          </td>
          <td style="text-align:center;padding:10px 4px;">
            <label class="toggle-label">
              <input type="checkbox" class="notification-toggle"
                     data-category="${esc(cat)}" data-channel="in_app"
                     ${inAppChecked ? 'checked' : ''}
                     onchange="NotificationsView.onToggleChange()">
            </label>
          </td>
          <td style="text-align:center;padding:10px 4px;">
            <label class="toggle-label">
              <input type="checkbox" class="notification-toggle"
                     data-category="${esc(cat)}" data-channel="email"
                     ${emailChecked ? 'checked' : ''}
                     onchange="NotificationsView.onToggleChange()">
            </label>
          </td>
        </tr>
      `;
    });

    html += `
          </tbody>
        </table>
      </div>
      <div style="margin-top:16px;text-align:right;">
        <button id="save-settings-btn" class="btn btn-primary" onclick="NotificationsView.saveSettings()">
          <span class="material-symbols-outlined mi-sm">save</span> Speichern
        </button>
      </div>
    `;

    el.innerHTML = html;
  }

  function onToggleChange() {
    // live capture into settings object so saveSettings can read current state
    document.querySelectorAll('.notification-toggle').forEach(input => {
      const cat = input.dataset.category;
      const channel = input.dataset.channel;
      if (!settings[cat]) settings[cat] = {};
      settings[cat][channel] = input.checked;
    });
  }

  async function saveSettings() {
    if (savingSettings) return;
    savingSettings = true;
    const btn = document.getElementById('save-settings-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-symbols-outlined mi-sm">hourglass_empty</span> Speichern…';
    }

    // Collect current toggle state
    const payload = {};
    document.querySelectorAll('.notification-toggle').forEach(input => {
      const cat = input.dataset.category;
      const channel = input.dataset.channel;
      if (!payload[cat]) payload[cat] = {};
      payload[cat][channel] = input.checked;
    });

    try {
      await Api.patch('/notifications/settings', payload);
      settings = payload;
      Toast.show('Einstellungen gespeichert', 'success');
    } catch (err) {
      Toast.show('Fehler beim Speichern: ' + err.message, 'error');
    } finally {
      savingSettings = false;
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined mi-sm">save</span> Speichern';
      }
    }
  }

  /* ── Public API ──────────────────────────────────────────── */

  return {
    render,
    switchTab,
    markAllRead,
    deleteNotification,
    handleNotificationClick,
    onToggleChange,
    saveSettings,
  };
})();
