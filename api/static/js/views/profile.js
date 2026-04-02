/**
 * Profile View – Settings, Navigation Config, Dashboard Widgets, Features, Logout
 */
const ProfileView = (() => {

  async function render(container) {
    const user = Api.getUserKey() || '';
    const initial = user.charAt(0).toUpperCase();
    const name = user.charAt(0).toUpperCase() + user.slice(1);

    container.innerHTML = `
      <div class="profile-header">
        <div class="profile-avatar">${initial}</div>
        <div class="profile-name">${escapeHtml(name)}</div>
        <div class="profile-email">${escapeHtml(user)}@dualmind.app</div>
      </div>

      <div class="section-header"><span class="section-icon material-symbols-outlined">navigation</span> Navigation</div>
      <div class="settings-hint">Bereiche ein-/ausschalten und in die Navbar pinnen (max. 5).</div>
      <div id="nav-config-list"><div class="loading"><div class="spinner"></div></div></div>

      <div class="section-header"><span class="section-icon material-symbols-outlined">dashboard</span> Dashboard-Widgets</div>
      <div class="settings-hint">Widgets auf dem Home-Screen ein-/ausblenden.</div>
      <div id="widget-config-list"><div class="loading"><div class="spinner"></div></div></div>

      <div class="section-header"><span class="section-icon material-symbols-outlined">palette</span> Darstellung</div>
      <div class="settings-list">
        <div class="settings-item">
          <span><span class="material-symbols-outlined mi-sm">dark_mode</span> Design</span>
          <label class="toggle">
            <input type="checkbox" id="theme-toggle" ${ProfileView.getTheme() === 'light' ? 'checked' : ''}
                   onchange="ProfileView.toggleTheme(this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div class="section-header"><span class="section-icon material-symbols-outlined">link</span> Verbundene Dienste</div>
      <div id="services-list"><div class="loading"><div class="spinner"></div></div></div>

      <div class="section-header"><span class="section-icon material-symbols-outlined">tune</span> Features</div>
      <div id="features-list"><div class="loading"><div class="spinner"></div></div></div>

      <div class="section-header"><span class="section-icon material-symbols-outlined">info</span> Sonstige Einstellungen</div>
      <div class="settings-list">
        <div class="settings-item">
          <span>Briefing-Zeit</span>
          <span class="card-subtitle">08:00 Uhr</span>
        </div>
        <div class="settings-item">
          <span>Zeitzone</span>
          <span class="card-subtitle">Europe/Berlin</span>
        </div>
      </div>

      <div class="section-header"><span class="section-icon material-symbols-outlined">code</span> Entwickler</div>
      <div class="settings-list">
        <a href="#/issues" class="settings-item" style="text-decoration:none;color:inherit">
          <span><span class="material-symbols-outlined mi-sm">bug_report</span> GitHub Issues</span>
          <span class="card-subtitle"><span class="material-symbols-outlined mi-sm">chevron_right</span></span>
        </a>
      </div>

      <div class="text-center mt-16">
        <button class="btn btn-danger" onclick="ProfileView.confirmLogout()">Abmelden</button>
      </div>
    `;

    await Promise.all([loadNavConfig(), loadWidgetConfig(), loadServices(), loadFeatures()]);
  }

  // ── Nav Configuration ──

  async function loadNavConfig() {
    const el = document.getElementById('nav-config-list');
    try {
      const prefs = window.AppPreferences ? window.AppPreferences.getCached() : null;
      const data = prefs || await Api.getPreferences();
      const items = (data.nav && data.nav.items) || [];
      const maxPinned = (data.nav && data.nav.maxPinned) || 5;
      const meta = window.AppPreferences ? window.AppPreferences.NAV_META : {};

      // Sort by order
      items.sort((a, b) => (a.order || 0) - (b.order || 0));

      el.innerHTML = '<div class="nav-config-grid">' + items.map(item => {
        const m = meta[item.id] || {};
        const icon = m.icon || item.icon || 'circle';
        const label = m.label || item.label || item.id;
        const enabled = item.enabled !== false;
        const pinned = item.pinned || false;
        const pinnedCount = items.filter(i => i.enabled !== false && i.pinned).length;
        const canPin = pinned || pinnedCount < maxPinned;

        return `
          <div class="nav-config-item ${enabled ? '' : 'disabled'}">
            <div class="nav-config-info">
              <span class="material-symbols-outlined mi-sm">${icon}</span>
              <span class="nav-config-label">${label}</span>
            </div>
            <div class="nav-config-actions">
              <label class="toggle toggle-sm" title="Bereich aktivieren">
                <input type="checkbox" ${enabled ? 'checked' : ''}
                       onchange="ProfileView.toggleNavItem('${item.id}', 'enabled', this.checked)">
                <span class="toggle-slider"></span>
              </label>
              <button class="btn-icon ${pinned ? 'active' : ''} ${!enabled || !canPin ? 'btn-disabled' : ''}"
                      title="${pinned ? 'Aus Navbar entfernen' : 'In Navbar pinnen'}"
                      onclick="ProfileView.toggleNavItem('${item.id}', 'pinned', ${!pinned})"
                      ${!enabled || (!pinned && !canPin) ? 'disabled' : ''}>
                <span class="material-symbols-outlined mi-sm">${pinned ? 'push_pin' : 'push_pin'}</span>
              </button>
            </div>
          </div>
        `;
      }).join('') + '</div>';
    } catch {
      el.innerHTML = '<div class="card-subtitle">Navigation konnte nicht geladen werden</div>';
    }
  }

  async function toggleNavItem(itemId, field, value) {
    try {
      const prefs = window.AppPreferences ? window.AppPreferences.getCached() : await Api.getPreferences();
      const items = (prefs.nav && prefs.nav.items) || [];
      const item = items.find(i => i.id === itemId);
      if (!item) return;

      item[field] = value;
      // If disabling, also unpin
      if (field === 'enabled' && !value) {
        item.pinned = false;
      }

      await window.AppPreferences.save({ nav: { items } });
      // Re-render nav config
      await loadNavConfig();
    } catch (err) {
      Toast.show('Fehler: ' + err.message);
    }
  }

  // ── Dashboard Widget Configuration ──

  async function loadWidgetConfig() {
    const el = document.getElementById('widget-config-list');
    try {
      const prefs = window.AppPreferences ? window.AppPreferences.getCached() : null;
      const data = prefs || await Api.getPreferences();
      const widgets = (data.dashboard && data.dashboard.widgets) || [];

      // Sort by order
      widgets.sort((a, b) => (a.order || 0) - (b.order || 0));

      // Widget display labels
      const widgetLabels = {
        emails: { icon: 'mail', label: 'E-Mails' },
        shifts: { icon: 'work', label: 'Dienste heute' },
        events: { icon: 'calendar_month', label: 'Termine heute' },
        tasks: { icon: 'check_circle', label: 'Offene Aufgaben' },
        shopping: { icon: 'shopping_cart', label: 'Einkaufsliste' },
        mealplan: { icon: 'restaurant', label: 'Wochenplan' },
        drive: { icon: 'folder', label: 'Drive' },
      };

      el.innerHTML = '<div class="widget-config-grid">' + widgets.map(w => {
        const meta = widgetLabels[w.id] || { icon: 'widgets', label: w.id };
        const enabled = w.enabled !== false;

        return `
          <div class="widget-config-item ${enabled ? '' : 'disabled'}">
            <div class="widget-config-info">
              <span class="material-symbols-outlined mi-sm">${meta.icon}</span>
              <span>${meta.label}</span>
            </div>
            <label class="toggle toggle-sm">
              <input type="checkbox" ${enabled ? 'checked' : ''}
                     onchange="ProfileView.toggleWidget('${w.id}', this.checked)">
              <span class="toggle-slider"></span>
            </label>
          </div>
        `;
      }).join('') + '</div>';
    } catch {
      el.innerHTML = '<div class="card-subtitle">Widgets konnten nicht geladen werden</div>';
    }
  }

  async function toggleWidget(widgetId, enabled) {
    try {
      const prefs = window.AppPreferences ? window.AppPreferences.getCached() : await Api.getPreferences();
      const widgets = (prefs.dashboard && prefs.dashboard.widgets) || [];
      const widget = widgets.find(w => w.id === widgetId);
      if (!widget) return;

      widget.enabled = enabled;
      await window.AppPreferences.save({ dashboard: { widgets } });
      await loadWidgetConfig();
    } catch (err) {
      Toast.show('Fehler: ' + err.message);
    }
  }

  // ── Services ──

  async function loadServices() {
    const el = document.getElementById('services-list');
    try {
      const data = await Api.getDashboard();
      el.innerHTML = `
        <div class="service-list">
          <div class="service-item">
            <div class="service-info">
              <span class="service-icon material-symbols-outlined">calendar_month</span>
              <span class="service-name">Google Calendar</span>
            </div>
            <div class="status-dot ${data.calendar_connected ? 'connected' : 'disconnected'}"></div>
          </div>
          <div class="service-item">
            <div class="service-info">
              <span class="service-icon material-symbols-outlined">mail</span>
              <span class="service-name">Gmail</span>
            </div>
            <div class="status-dot ${data.email_connected ? 'connected' : 'disconnected'}"></div>
          </div>
        </div>
      `;
    } catch {
      el.innerHTML = '<div class="card-subtitle">Dienste konnten nicht geladen werden</div>';
    }
  }

  // ── Features ──

  async function loadFeatures() {
    const el = document.getElementById('features-list');
    try {
      const features = await Api.getFeatures();
      if (features.length === 0) {
        el.innerHTML = '<div class="empty-state">Keine Features verfuegbar</div>';
        return;
      }
      el.innerHTML = '<div class="feature-list">' + features.map(f => `
        <div class="feature-item">
          <div class="feature-info">
            <span class="feature-icon">${f.emoji || '&#9881;'}</span>
            <div>
              <div class="feature-name">${escapeHtml(f.name)}</div>
              <div class="feature-desc">${escapeHtml(f.description)}${!f.available ? ' <span class="badge badge-warning">API-Keys fehlen</span>' : ''}</div>
            </div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${f.enabled ? 'checked' : ''} ${!f.available ? 'disabled' : ''}
                   onchange="ProfileView.toggleFeature('${f.id}')">
            <span class="toggle-slider"></span>
          </label>
        </div>
      `).join('') + '</div>';
    } catch {
      el.innerHTML = '<div class="card-subtitle">Features konnten nicht geladen werden</div>';
    }
  }

  async function toggleFeature(featureId) {
    try {
      await Api.toggleFeature(featureId);
    } catch (err) {
      alert('Fehler: ' + err.message);
      loadFeatures();
    }
  }

  // ── Theme ──

  function getTheme() {
    return localStorage.getItem('dualmind-theme') || 'dark';
  }

  function toggleTheme(isLight) {
    const theme = isLight ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('dualmind-theme', theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = isLight ? '#f5f5f7' : '#7c4dff';
    // Save to server
    if (window.AppPreferences) {
      window.AppPreferences.save({ appearance: { theme } }).catch(() => {});
    }
  }

  function confirmLogout() {
    if (confirm('Moechtest du dich wirklich abmelden?')) {
      Api.logout();
    }
  }

  // Apply saved theme on load
  (function initTheme() {
    const saved = localStorage.getItem('dualmind-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.content = saved === 'light' ? '#f5f5f7' : '#7c4dff';
    }
  })();

  return { render, toggleFeature, confirmLogout, getTheme, toggleTheme, toggleNavItem, toggleWidget };
})();
