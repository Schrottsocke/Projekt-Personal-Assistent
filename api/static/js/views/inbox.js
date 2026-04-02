/**
 * DualMind Inbox View
 * Zentrale Aktions-Inbox fuer Vorschlaege, Freigaben und Folgeaktionen.
 */
const InboxView = (() => {
  let items = [];
  let activeStatus = 'pending';
  let activeCategory = null;
  let loading = false;
  let container = null;

  const CATEGORY_META = {
    proposal:  { icon: 'lightbulb',    label: 'Vorschlag',  color: 'var(--accent)' },
    approval:  { icon: 'thumb_up',     label: 'Freigabe',   color: 'var(--warning)' },
    followup:  { icon: 'reply',        label: 'Folgeaktion', color: 'var(--success)' },
    system:    { icon: 'settings',     label: 'System',     color: 'var(--error)' },
  };

  const STATUS_META = {
    pending:   { label: 'Offen',       class: 'badge-accent' },
    approved:  { label: 'Genehmigt',   class: 'badge-success' },
    dismissed: { label: 'Abgelehnt',   class: 'badge' },
    snoozed:   { label: 'Zurueckgestellt', class: 'badge' },
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
    const statusFilters = [
      { key: 'pending', label: 'Offen' },
      { key: null, label: 'Alle' },
      { key: 'approved', label: 'Genehmigt' },
      { key: 'dismissed', label: 'Abgelehnt' },
      { key: 'snoozed', label: 'Zurueckgestellt' },
    ];
    const categories = Object.entries(CATEGORY_META);

    return `
      <div class="notification-filters">
        <div class="notification-filter-row">
          ${statusFilters.map(s => `
            <button class="filter-chip ${activeStatus === s.key ? 'active' : ''}"
                    data-status-filter="${s.key || ''}">${s.label}</button>
          `).join('')}
        </div>
        <div class="notification-filter-row">
          <button class="filter-chip ${!activeCategory ? 'active' : ''}"
                  data-category-filter="">Alle Typen</button>
          ${categories.map(([key, meta]) => `
            <button class="filter-chip ${activeCategory === key ? 'active' : ''}"
                    data-category-filter="${key}">
              <span class="material-symbols-outlined" style="font-size:14px">${meta.icon}</span>
              ${meta.label}
            </button>
          `).join('')}
        </div>
      </div>
    `;
  }

  function renderItem(item) {
    const meta = CATEGORY_META[item.category] || CATEGORY_META.system;
    const statusMeta = STATUS_META[item.status] || STATUS_META.pending;
    const isPending = item.status === 'pending';

    return `
      <div class="notification-card ${isPending ? 'notification-new' : ''}" data-id="${item.id}">
        <div class="notification-icon" style="color:${meta.color}">
          <span class="material-symbols-outlined">${meta.icon}</span>
        </div>
        <div class="notification-content">
          <div class="notification-header">
            <span class="notification-title">${item.title}</span>
            <span class="${statusMeta.class}" style="font-size:11px">${statusMeta.label}</span>
          </div>
          ${item.message ? `<p class="notification-message">${item.message}</p>` : ''}
          <div class="notification-meta">
            <span class="notification-type-label">${meta.label}</span>
            ${item.source ? `<span>· ${item.source}</span>` : ''}
            <span class="notification-time">${formatTime(item.created_at)}</span>
            <span style="font-size:11px;color:var(--text-secondary)">Prio ${item.priority}</span>
          </div>
        </div>
        <div class="notification-actions">
          ${item.link ? `<button class="btn-icon" data-action="open" title="Oeffnen"><span class="material-symbols-outlined">open_in_new</span></button>` : ''}
          ${isPending ? `<button class="btn-icon" data-action="approve" title="Genehmigen"><span class="material-symbols-outlined">check_circle</span></button>` : ''}
          ${isPending ? `<button class="btn-icon" data-action="snooze" title="Zurueckstellen"><span class="material-symbols-outlined">snooze</span></button>` : ''}
          ${isPending ? `<button class="btn-icon" data-action="dismiss" title="Ablehnen"><span class="material-symbols-outlined">close</span></button>` : ''}
        </div>
      </div>
    `;
  }

  function renderList() {
    if (loading) {
      return '<div class="loading"><div class="spinner"></div></div>';
    }
    if (!items.length) {
      return `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-secondary)">inbox</span>
          <p>Keine Inbox-Eintraege</p>
        </div>
      `;
    }
    return items.map(renderItem).join('');
  }

  function renderHeader() {
    const pendingCount = items.filter(i => i.status === 'pending').length;
    return `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">inbox</span> Inbox</h2>
        ${pendingCount > 0 ? `<span class="badge-accent" style="font-size:12px">${pendingCount} offen</span>` : ''}
      </div>
    `;
  }

  async function load() {
    loading = true;
    update();
    try {
      const params = {};
      if (activeStatus) params.status = activeStatus;
      if (activeCategory) params.category = activeCategory;
      items = await Api.getInboxItems(params);
    } catch (err) {
      items = [];
      if (container) {
        container.innerHTML = `
          ${renderHeader()}
          ${renderFilters()}
          <div class="error-state">
            <p>Fehler beim Laden: ${err.message}</p>
            <button class="btn btn-sm btn-primary" id="inbox-retry-btn">Erneut versuchen</button>
          </div>
        `;
        container.querySelector('#inbox-retry-btn')?.addEventListener('click', load);
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

    // Filter chips - status
    container.querySelectorAll('[data-status-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        const val = btn.dataset.statusFilter;
        activeStatus = val || null;
        load();
      });
    });

    // Filter chips - category
    container.querySelectorAll('[data-category-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        const val = btn.dataset.categoryFilter;
        activeCategory = val || null;
        load();
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
          try {
            if (action === 'open' && item.link) {
              window.location.hash = item.link;
              return;
            }
            if (['approve', 'dismiss', 'snooze'].includes(action)) {
              const result = await Api.actionInboxItem(id, action);
              Object.assign(item, result);
              // Remove from list if filtered by pending
              if (activeStatus === 'pending') {
                items = items.filter(i => i.id !== id);
              }
              update();
            }
          } catch (_) { /* Toast handles error */ }
        });
      });

      // Click on card opens link
      card.addEventListener('click', () => {
        if (item.link) {
          window.location.hash = item.link;
        }
      });
    });
  }

  async function render(el) {
    container = el;
    activeStatus = 'pending';
    activeCategory = null;
    await load();
  }

  return { render };
})();
