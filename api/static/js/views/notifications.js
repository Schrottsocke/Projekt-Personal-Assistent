/**
 * Notifications View – Benachrichtigungs-Kanal-Wahl pro Alert-Typ
 * Issue #685: Notifications-Center-View
 * Issue #721: Per alert-type channel selection (Push/Telegram/E-Mail/None)
 */
const NotificationsView = (() => {
  let activeTab = 'notifications';
  let notifications = [];
  let settings = {};
  let channelSetup = { push: false, telegram: false, email: false };
  let savingSettings = false;
  let testingChannel = null;

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

  // Alert types for per-type channel selection (#721)
  const ALERT_TYPES = [
    { id: 'contract_deadline', icon: 'gavel', label: 'Vertragsfrist' },
    { id: 'invoice_due', icon: 'receipt_long', label: 'Rechnung f\u00e4llig' },
    { id: 'warranty_expiry', icon: 'verified_user', label: 'Garantieablauf' },
    { id: 'budget_warning', icon: 'account_balance_wallet', label: 'Budget-Warnung' },
    { id: 'document_reminder', icon: 'description', label: 'Dokument-Erinnerung' },
  ];

  const CHANNELS = [
    { id: 'push', icon: 'notifications', label: 'Push' },
    { id: 'telegram', icon: 'send', label: 'Telegram' },
    { id: 'email', icon: 'email', label: 'E-Mail' },
    { id: 'none', icon: 'notifications_off', label: 'Keine' },
  ];

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

  /* -- Render -- */

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
          <button class="tab" data-tab="channels"
                  onclick="NotificationsView.switchTab('channels')">Kan\u00e4le</button>
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
    } else if (tab === 'channels') {
      await loadChannelSettings();
    } else {
      await loadSettings();
    }
  }

  /* -- Notifications Tab -- */

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
                    title="L\u00f6schen">
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
      await Api.delete(`/notifications/events/${id}`);
      notifications = notifications.filter(n => n.id !== id);
      renderNotificationsList(null);
      Toast.show('Benachrichtigung gel\u00f6scht', 'success');
    } catch (err) {
      Toast.show('Fehler beim L\u00f6schen: ' + err.message, 'error');
    }
  }

  /* -- Channels Tab (per alert-type selection, #721) -- */

  async function loadChannelSettings() {
    const el = document.getElementById('notifications-content');
    if (!el) return;
    el.innerHTML = `
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;
    try {
      const prefs = await Api.get('/notifications/preferences') || [];
      // Convert preferences array to settings object
      settings = {};
      prefs.forEach(p => {
        settings[p.category] = {
          push: p.push_enabled,
          email: p.email_enabled,
          quiet_start: p.quiet_start,
          quiet_end: p.quiet_end,
        };
      });
      channelSetup = {
        push: false,
        telegram: false,
        email: false,
      };
    } catch {
      settings = {};
      channelSetup = { push: false, telegram: false, email: false };
    }
    renderChannelsTab();
  }

  function renderChannelsTab() {
    const el = document.getElementById('notifications-content');
    if (!el) return;

    // Channel setup section
    let setupHtml = `
      <div class="card mb-16">
        <div class="card-title"><span class="material-symbols-outlined mi-sm">settings</span> Kanal-Einrichtung</div>
        <p class="text-muted mb-12" style="font-size:0.85rem">Richte deine Benachrichtigungskan\u00e4le ein, bevor du sie pro Alert-Typ konfigurierst.</p>
        <div class="notif-channel-setup">
          <div class="notif-channel-setup-item">
            <div class="notif-channel-setup-info">
              <span class="material-symbols-outlined" style="color:var(--accent)">notifications</span>
              <div>
                <strong>Push</strong>
                <div class="text-muted" style="font-size:0.8rem">${channelSetup.push ? 'Aktiviert' : 'Browser-Berechtigung erforderlich'}</div>
              </div>
            </div>
            <div class="notif-channel-setup-actions">
              ${channelSetup.push
                ? '<span class="badge badge-success">Aktiv</span>'
                : '<button class="btn btn-sm btn-secondary" onclick="NotificationsView.setupPush()">Aktivieren</button>'}
              <button class="btn btn-sm btn-secondary" onclick="NotificationsView.testChannel('push')" ${testingChannel === 'push' ? 'disabled' : ''}>
                <span class="material-symbols-outlined mi-sm">send</span> Test
              </button>
            </div>
          </div>
          <div class="notif-channel-setup-item">
            <div class="notif-channel-setup-info">
              <span class="material-symbols-outlined" style="color:var(--accent)">send</span>
              <div>
                <strong>Telegram</strong>
                <div class="text-muted" style="font-size:0.8rem">${channelSetup.telegram ? 'Verbunden' : 'Chat-ID erforderlich'}</div>
              </div>
            </div>
            <div class="notif-channel-setup-actions">
              ${channelSetup.telegram
                ? '<span class="badge badge-success">Aktiv</span>'
                : `<div class="notif-telegram-setup">
                    <input type="text" id="notif-telegram-chatid" class="input" placeholder="Chat-ID" style="width:120px;font-size:0.85rem" />
                    <button class="btn btn-sm btn-primary" onclick="NotificationsView.setupTelegram()">Verbinden</button>
                  </div>`}
              <button class="btn btn-sm btn-secondary" onclick="NotificationsView.testChannel('telegram')" ${testingChannel === 'telegram' ? 'disabled' : ''}>
                <span class="material-symbols-outlined mi-sm">send</span> Test
              </button>
            </div>
          </div>
          <div class="notif-channel-setup-item">
            <div class="notif-channel-setup-info">
              <span class="material-symbols-outlined" style="color:var(--accent)">email</span>
              <div>
                <strong>E-Mail</strong>
                <div class="text-muted" style="font-size:0.8rem">${channelSetup.email ? 'Konfiguriert (aus Profil)' : 'Wird aus Profil \u00fcbernommen'}</div>
              </div>
            </div>
            <div class="notif-channel-setup-actions">
              ${channelSetup.email
                ? '<span class="badge badge-success">Aktiv</span>'
                : '<span class="badge badge-muted">Auto</span>'}
              <button class="btn btn-sm btn-secondary" onclick="NotificationsView.testChannel('email')" ${testingChannel === 'email' ? 'disabled' : ''}>
                <span class="material-symbols-outlined mi-sm">send</span> Test
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Per alert-type channel selection
    let alertTypeHtml = `
      <div class="card mb-16">
        <div class="card-title"><span class="material-symbols-outlined mi-sm">tune</span> Kanal pro Alert-Typ</div>
        <p class="text-muted mb-12" style="font-size:0.85rem">W\u00e4hle f\u00fcr jeden Alert-Typ den bevorzugten Benachrichtigungskanal.</p>
        <div class="notif-alert-type-list">
    `;

    ALERT_TYPES.forEach(at => {
      const currentChannel = (settings.alert_channels && settings.alert_channels[at.id]) || 'none';
      alertTypeHtml += `
        <div class="notif-alert-type-row">
          <div class="notif-alert-type-info">
            <span class="material-symbols-outlined mi-sm" style="color:var(--accent)">${at.icon}</span>
            <span>${esc(at.label)}</span>
          </div>
          <div class="notif-alert-type-channels">
            ${CHANNELS.map(ch => `
              <label class="notif-channel-radio ${currentChannel === ch.id ? 'selected' : ''}">
                <input type="radio" name="alert-${at.id}" value="${ch.id}" ${currentChannel === ch.id ? 'checked' : ''}
                  onchange="NotificationsView.onAlertChannelChange('${at.id}', '${ch.id}')">
                <span class="material-symbols-outlined mi-sm">${ch.icon}</span>
                <span class="notif-channel-radio-label">${ch.label}</span>
              </label>
            `).join('')}
          </div>
        </div>
      `;
    });

    alertTypeHtml += `
        </div>
        <div style="margin-top:16px;text-align:right;">
          <button class="btn btn-primary" onclick="NotificationsView.saveChannelSettings()">
            <span class="material-symbols-outlined mi-sm">save</span> Speichern
          </button>
        </div>
      </div>
    `;

    el.innerHTML = setupHtml + alertTypeHtml;
  }

  function onAlertChannelChange(alertType, channel) {
    if (!settings.alert_channels) settings.alert_channels = {};
    settings.alert_channels[alertType] = channel;
    // Update visual selection
    const row = document.querySelector(`input[name="alert-${alertType}"][value="${channel}"]`);
    if (row) {
      row.closest('.notif-alert-type-row')?.querySelectorAll('.notif-channel-radio').forEach(r => {
        r.classList.toggle('selected', r.querySelector('input')?.value === channel);
      });
    }
  }

  async function saveChannelSettings() {
    try {
      // Save each alert type channel as a preference
      const alertChannels = settings.alert_channels || {};
      await Promise.all(Object.entries(alertChannels).map(([category, channel]) => {
        return Api.put(`/notifications/preferences/${category}`, {
          push_enabled: channel === 'push',
          email_enabled: channel === 'email',
          quiet_start: '22:00',
          quiet_end: '07:00',
        });
      }));
      Toast.show('Kanal-Einstellungen gespeichert', 'success');
    } catch (err) {
      Toast.show('Fehler beim Speichern: ' + err.message, 'error');
    }
  }

  async function setupPush() {
    try {
      const result = await Notification.requestPermission();
      if (result === 'granted') {
        channelSetup.push = true;
        renderChannelsTab();
        Toast.show('Push-Berechtigung erteilt', 'success');
      } else {
        Toast.show('Push-Berechtigung abgelehnt', 'warning');
      }
    } catch {
      Toast.show('Push-Berechtigung konnte nicht angefragt werden', 'error');
    }
  }

  async function setupTelegram() {
    const chatIdEl = document.getElementById('notif-telegram-chatid');
    const chatId = chatIdEl ? chatIdEl.value.trim() : '';
    if (!chatId) {
      Toast.show('Bitte Chat-ID eingeben', 'error');
      return;
    }
    try {
      await Api.put('/notifications/preferences/telegram', {
        push_enabled: false,
        email_enabled: false,
        quiet_start: '22:00',
        quiet_end: '07:00',
      });
      channelSetup.telegram = true;
      renderChannelsTab();
      Toast.show('Telegram verbunden', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function testChannel(channel) {
    testingChannel = channel;
    renderChannelsTab();
    try {
      await Api.post('/notifications', { type: 'test', title: 'Test', message: 'Test-Benachrichtigung', channel: channel });
      Toast.show(`Test-Benachrichtigung via ${channel} gesendet`, 'success');
    } catch (err) {
      Toast.show(`Test fehlgeschlagen: ${err.message}`, 'error');
    } finally {
      testingChannel = null;
      // Don't re-render to avoid losing state
    }
  }

  /* -- Settings Tab (category-level, existing) -- */

  async function loadSettings() {
    const el = document.getElementById('notifications-content');
    if (!el) return;
    el.innerHTML = `
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;
    try {
      const prefs = await Api.get('/notifications/preferences') || [];
      settings = {};
      prefs.forEach(p => {
        settings[p.category] = {
          push: p.push_enabled,
          email: p.email_enabled,
          in_app: true,
        };
      });
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
      btn.innerHTML = '<span class="material-symbols-outlined mi-sm">hourglass_empty</span> Speichern\u2026';
    }

    const payload = {};
    document.querySelectorAll('.notification-toggle').forEach(input => {
      const cat = input.dataset.category;
      const channel = input.dataset.channel;
      if (!payload[cat]) payload[cat] = {};
      payload[cat][channel] = input.checked;
    });

    try {
      await Promise.all(Object.entries(payload).map(([cat, vals]) => {
        return Api.put(`/notifications/preferences/${cat}`, {
          push_enabled: !!vals.push,
          email_enabled: !!vals.email,
          quiet_start: '22:00',
          quiet_end: '07:00',
        });
      }));
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

  /* -- Public API -- */

  return {
    render,
    switchTab,
    markAllRead,
    deleteNotification,
    handleNotificationClick,
    onToggleChange,
    saveSettings,
    // Channel settings (#721)
    onAlertChannelChange,
    saveChannelSettings,
    setupPush,
    setupTelegram,
    testChannel,
  };
})();
