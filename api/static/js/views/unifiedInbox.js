/**
 * DualMind Unified Inbox View
 * Zentrale Uebersicht: Notifications, Inbox-Items und Follow-ups in einem Stream.
 */
const UnifiedInboxView = (() => {
  let items = [];
  let counts = { actionable: 0, total: 0 };
  let activeFilter = 'actionable';
  let activeSource = null;
  let loading = false;
  let container = null;

  const CATEGORY_META = {
    reminder:    { icon: 'schedule',      label: 'Erinnerung',          color: 'var(--accent)' },
    follow_up:   { icon: 'reply',         label: 'Follow-up',           color: 'var(--warning)' },
    document:    { icon: 'description',   label: 'Dokument',            color: 'var(--success)' },
    inbox:       { icon: 'inbox',         label: 'Posteingang',         color: 'var(--info, #42a5f5)' },
    weather:     { icon: 'cloud',         label: 'Wetter',              color: 'var(--warning)' },
    system:      { icon: 'info',          label: 'System',              color: 'var(--text-secondary)' },
    proposal:    { icon: 'lightbulb',     label: 'Vorschlag',           color: 'var(--accent)' },
    approval:    { icon: 'thumb_up',      label: 'Freigabe',            color: 'var(--warning)' },
    followup:    { icon: 'reply_all',     label: 'Folgeaktion',         color: 'var(--success)' },
    email:       { icon: 'mail',          label: 'E-Mail',              color: 'var(--accent)' },
    commitment:  { icon: 'handshake',     label: 'Zusage',              color: 'var(--warning)' },
    task:        { icon: 'check_circle',  label: 'Aufgabe',             color: 'var(--success)' },
  };

  const STATUS_LABELS = {
    actionable: 'Offen',
    read:       'Gelesen',
    done:       'Erledigt',
    archived:   'Archiviert',
  };

  const ACTION_META = {
    read:     { icon: 'done',         label: 'Gelesen',       class: '' },
    complete: { icon: 'check_circle', label: 'Erledigen',     class: '' },
    hide:     { icon: 'visibility_off', label: 'Ausblenden', class: '' },
    approve:  { icon: 'check_circle', label: 'Genehmigen',    class: 'btn-icon-success' },
    dismiss:  { icon: 'close',        label: 'Ablehnen',      class: 'btn-icon-danger' },
    snooze:   { icon: 'snooze',       label: 'Spaeter',       class: '' },
  };

  const formatTime = Utils.formatTime;
  const formatDueDate = Utils.formatDateShort;

  function renderFilters() {
    const statusFilters = [
      { key: 'actionable', label: `Offen (${counts.actionable})` },
      { key: 'all', label: 'Alle' },
      { key: 'done', label: 'Erledigt' },
    ];
    const sourceFilters = [
      { key: null, label: 'Alle Quellen' },
      { key: 'notification', label: 'Benachrichtigungen', icon: 'notifications' },
      { key: 'inbox', label: 'Aktionen', icon: 'inbox' },
      { key: 'followup', label: 'Follow-ups', icon: 'reply_all' },
    ];

    return `
      <div class="notification-filters">
        <div class="notification-filter-row">
          ${statusFilters.map(s => `
            <button class="filter-chip ${activeFilter === s.key ? 'active' : ''}"
                    data-filter="${s.key}">${s.label}</button>
          `).join('')}
        </div>
        <div class="notification-filter-row">
          ${sourceFilters.map(s => `
            <button class="filter-chip ${activeSource === s.key ? 'active' : ''}"
                    data-source="${s.key || ''}">
              ${s.icon ? `<span class="material-symbols-outlined" style="font-size:14px">${s.icon}</span>` : ''}
              ${s.label}
            </button>
          `).join('')}
        </div>
      </div>
    `;
  }

  function renderItem(item) {
    const meta = CATEGORY_META[item.category] || CATEGORY_META.system;
    const isActionable = item.status === 'actionable';
    const sourceTag = {
      notification: 'Notification',
      inbox: 'Inbox',
      followup: 'Follow-up',
    }[item.source] || item.source;

    return `
      <div class="notification-card ${isActionable ? 'notification-new' : ''} ${item.is_overdue ? 'unified-overdue' : ''}"
           data-id="${item.id}">
        <div class="notification-icon" style="color:${meta.color}">
          <span class="material-symbols-outlined">${meta.icon}</span>
        </div>
        <div class="notification-content">
          <div class="notification-header">
            <span class="notification-title">${Utils.escapeHtml(item.title)}</span>
            <span class="unified-source-badge">${sourceTag}</span>
          </div>
          ${item.message ? `<p class="notification-message">${Utils.escapeHtml(item.message).substring(0, 120)}${item.message.length > 120 ? '...' : ''}</p>` : ''}
          <div class="notification-meta">
            <span class="notification-type-label">${item.source_label}</span>
            ${item.due_date ? `<span class="${item.is_overdue ? 'unified-due-overdue' : 'unified-due'}">Faellig: ${formatDueDate(item.due_date)}</span>` : ''}
            <span class="notification-time">${formatTime(item.created_at)}</span>
          </div>
        </div>
        <div class="notification-actions">
          ${item.link ? `<button class="btn-icon" data-action="open" title="Oeffnen"><span class="material-symbols-outlined">open_in_new</span></button>` : ''}
          ${item.actions.map(a => {
            const am = ACTION_META[a] || { icon: a, label: a, class: '' };
            return `<button class="btn-icon ${am.class}" data-action="${a}" title="${am.label}"><span class="material-symbols-outlined">${am.icon}</span></button>`;
          }).join('')}
        </div>
      </div>
    `;
  }

  function renderList() {
    if (loading) {
      return `
        <div class="skeleton skeleton-card" style="height:80px;margin-bottom:8px"></div>
        <div class="skeleton skeleton-card" style="height:80px;margin-bottom:8px"></div>
        <div class="skeleton skeleton-card" style="height:80px;margin-bottom:8px"></div>
      `;
    }

    const filtered = activeSource
      ? items.filter(i => i.source === activeSource)
      : items;

    if (!filtered.length) {
      const emptyMessages = {
        actionable: { icon: 'check_circle', text: 'Alles erledigt – keine offenen Punkte', cta: '' },
        done:       { icon: 'inventory_2', text: 'Noch nichts erledigt', cta: '' },
        all:        { icon: 'inbox', text: 'Deine Inbox ist leer', cta: '' },
      };
      const em = emptyMessages[activeFilter] || emptyMessages.all;
      return `
        <div class="empty-state">
          <span class="material-symbols-outlined empty-state-icon">${em.icon}</span>
          <div class="empty-state-text">${em.text}</div>
          ${em.cta}
        </div>
      `;
    }

    // Group: actionable items first, then the rest
    const actionable = filtered.filter(i => i.status === 'actionable');
    const rest = filtered.filter(i => i.status !== 'actionable');

    let html = '';

    if (activeFilter === 'all' || activeFilter === 'actionable') {
      if (actionable.length > 0) {
        html += `<div class="unified-section-header" data-section="open">
          <span class="material-symbols-outlined" style="font-size:18px">priority_high</span>
          Offen (${actionable.length})
        </div>`;
        html += actionable.map(renderItem).join('');
      }
    }

    if (activeFilter === 'all' && rest.length > 0) {
      html += `<div class="unified-section-header unified-section-muted" data-section="done">
        <span class="material-symbols-outlined" style="font-size:18px">done_all</span>
        Erledigt &amp; Archiviert (${rest.length})
      </div>`;
      html += rest.map(renderItem).join('');
    }

    if (activeFilter === 'done') {
      html += rest.map(renderItem).join('');
    }

    return html;
  }

  function renderHeader() {
    return `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">all_inbox</span> Inbox</h2>
        <button class="btn btn-sm btn-secondary" id="unified-refresh" title="Aktualisieren">
          <span class="material-symbols-outlined" style="font-size:18px">refresh</span>
        </button>
      </div>
    `;
  }

  const INBOX_CACHE_KEY = 'dm_cache_inbox';

  async function load() {
    loading = true;
    update();
    try {
      const params = {};
      if (activeFilter && activeFilter !== 'all') params.filter = activeFilter;
      if (activeFilter === 'all') params.limit = 100;
      const data = await Api.getUnifiedInbox(params);
      items = data.items || [];
      counts = data.counts || { actionable: 0, total: 0 };
      OfflineQueue.saveCache(INBOX_CACHE_KEY, { items, counts });
      // Remove offline banner on success
      const offBanner = container?.querySelector('#inbox-offline-banner');
      if (offBanner) offBanner.remove();
    } catch (err) {
      // Offline fallback: show cached inbox
      if (err.isOffline || (typeof OfflineQueue !== 'undefined' && !OfflineQueue.isOnline())) {
        const cached = OfflineQueue.loadCache(INBOX_CACHE_KEY);
        if (cached && cached.data) {
          items = cached.data.items || [];
          counts = cached.data.counts || { actionable: 0, total: 0 };
          loading = false;
          update();
          if (container) {
            const ts = new Date(cached.ts).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
            const list = container.querySelector('#unified-list');
            if (list) {
              list.insertAdjacentHTML('afterbegin',
                `<div id="inbox-offline-banner" class="offline-cache-banner">
                  <span class="material-symbols-outlined mi-sm">cloud_off</span>
                  Offline \u2014 zuletzt aktualisiert: ${ts}
                </div>`);
            }
          }
          return;
        }
      }
      items = [];
      counts = { actionable: 0, total: 0 };
      if (container) {
        container.innerHTML = `
          ${renderHeader()}
          <div class="error-state">
            <p>Fehler beim Laden: ${err.message}</p>
            <button class="btn btn-sm btn-primary" id="unified-retry">Erneut versuchen</button>
          </div>
        `;
        container.querySelector('#unified-retry')?.addEventListener('click', load);
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
      <div class="notification-list" id="unified-list">
        ${renderList()}
      </div>
    `;
    bindEvents();
  }

  function bindEvents() {
    if (!container) return;

    // Refresh
    container.querySelector('#unified-refresh')?.addEventListener('click', load);

    // Filter chips
    container.querySelectorAll('[data-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeFilter = btn.dataset.filter;
        load();
      });
    });

    // Source filter chips
    container.querySelectorAll('[data-source]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeSource = btn.dataset.source || null;
        update();
      });
    });

    // Per-item actions
    container.querySelectorAll('.notification-card').forEach(card => {
      const id = card.dataset.id;
      const item = items.find(i => i.id === id);
      if (!item) return;

      card.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const action = btn.dataset.action;

          if (action === 'open' && item.link) {
            window.location.hash = item.link;
            return;
          }

          try {
            btn.disabled = true;
            await Api.unifiedInboxAction(id, action);
            // Reload to get fresh state
            await load();
            // Refresh bell badge
            if (typeof NotificationBell !== 'undefined') NotificationBell.refresh();
          } catch (actionErr) {
            if (actionErr.isOffline || (typeof OfflineQueue !== 'undefined' && !OfflineQueue.isOnline())) {
              OfflineQueue.enqueueInboxAction(id, action);
              Toast.show('Aktion wird ausgefuehrt wenn online', 'warning');
              // Optimistic UI: remove card
              card.style.opacity = '0.5';
            }
            btn.disabled = false;
          }
        });
      });

      // Click card → navigate if link available
      card.addEventListener('click', () => {
        if (item.link) {
          window.location.hash = item.link;
        }
      });
    });
  }

  async function render(el) {
    container = el;
    activeFilter = 'actionable';
    activeSource = null;
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
      const data = await Api.getUnifiedInboxCount();
      updateBadge(data.total || 0);
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
