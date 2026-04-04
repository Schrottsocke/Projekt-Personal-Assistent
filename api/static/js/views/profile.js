/**
 * Profile View – Redesigned Personal Control Center
 * Sections: Identity, Services, Features (grouped), Settings, Advanced
 */
const ProfileView = (() => {

  /* ── Feature Group Definitions ── */

  const FEATURE_GROUPS = [
    {
      id: 'daily',
      title: 'Alltag & Organisation',
      desc: 'Termine, Aufgaben und Erinnerungen im Griff',
      icon: 'event_note',
      features: ['calendar', 'tasks', 'reminders']
    },
    {
      id: 'communication',
      title: 'Kommunikation',
      desc: 'E-Mails und Sprachnachrichten',
      icon: 'forum',
      features: ['email', 'tts']
    },
    {
      id: 'shopping',
      title: 'Einkaufen & Rezepte',
      desc: 'Einkaufslisten und Rezeptideen',
      icon: 'local_grocery_store',
      features: ['shopping', 'recipes']
    },
    {
      id: 'productivity',
      title: 'Dokumente & Produktivit\u00e4t',
      desc: 'Dateien, Dokumente und Websuche',
      icon: 'description',
      features: ['drive', 'documents', 'tables', 'websearch']
    },
    {
      id: 'smart',
      title: 'Smartes Zuhause & Medien',
      desc: 'Musik und Smart-Home-Steuerung',
      icon: 'devices',
      features: ['spotify', 'smarthome']
    }
  ];

  const ALWAYS_ACTIVE = ['core', 'weather', 'mobility'];

  const FEATURE_BENEFITS = {
    calendar: 'Termine aus Google Calendar anzeigen und erstellen',
    tasks: 'Aufgaben erstellen und verwalten',
    reminders: 'Erinnerungen zu bestimmten Zeiten erhalten',
    email: 'E-Mails lesen und schreiben',
    tts: 'Antworten als Sprachnachricht erhalten',
    shopping: 'Einkaufslisten erstellen und teilen',
    recipes: 'Rezepte suchen und speichern',
    drive: 'Dateien in Google Drive verwalten',
    documents: 'Dokumente scannen und erkennen',
    tables: 'Tabellen und Pr\u00e4sentationen erstellen',
    websearch: 'Im Web nach Informationen suchen',
    spotify: 'Musik abspielen und steuern',
    smarthome: 'Smart-Home-Ger\u00e4te steuern',
    core: 'KI-Chat \u2013 immer verf\u00fcgbar',
    weather: 'Wetter abfragen',
    mobility: 'Fahrzeiten und Routen berechnen'
  };

  const PREREQ_LABELS = {
    GOOGLE_CREDENTIALS_PATH: 'Google',
    SPOTIFY_CLIENT_ID: 'Spotify',
    SPOTIFY_CLIENT_SECRET: 'Spotify',
    HA_URL: 'Home Assistant',
    HA_TOKEN: 'Home Assistant',
    OPENROUTE_API_KEY: 'OpenRoute'
  };

  const SERVICE_DEFS = [
    { id: 'calendar', emoji: '\ud83d\udcc5', name: 'Google Calendar', desc: 'Termine synchronisieren', connKey: 'calendar_connected' },
    { id: 'email', emoji: '\ud83d\udce7', name: 'Gmail', desc: 'E-Mails verwalten', connKey: 'email_connected' },
    { id: 'drive', emoji: '\ud83d\udcbe', name: 'Google Drive', desc: 'Dateien speichern und teilen', connKey: 'drive_connected' }
  ];

  let _devDataLoaded = false;

  /* ── Render ── */

  async function render(container) {
    _devDataLoaded = false;
    const user = Api.getUserKey() || '';
    const initial = user.charAt(0).toUpperCase();
    const name = user.charAt(0).toUpperCase() + user.slice(1);

    container.innerHTML = `
      <div class="profile-header">
        <div class="profile-avatar">${initial}</div>
        <div class="profile-name">${escapeHtml(name)}</div>
        <div class="profile-email">${escapeHtml(user)}@dualmind.app</div>
        <div class="profile-status-bar" id="profile-status-bar">
          <div class="profile-stat"><div class="spinner" style="width:12px;height:12px;border-width:1.5px"></div></div>
        </div>
      </div>

      <!-- Services -->
      <div class="profile-section">
        <div class="profile-section-title">
          <span class="material-symbols-outlined">link</span>
          Deine verbundenen Dienste
        </div>
        <div class="section-intro">DualMind arbeitet mit diesen Diensten f\u00fcr dich.</div>
        <div id="services-list" class="service-cards-grid">
          <div class="loading"><div class="spinner"></div></div>
        </div>
      </div>

      <!-- Features -->
      <div class="profile-section">
        <div class="profile-section-title">
          <span class="material-symbols-outlined">auto_awesome</span>
          Was dein Assistent kann
        </div>
        <div class="section-intro">Funktionen ein- und ausschalten.</div>
        <div id="always-active-strip"></div>
        <div id="features-list" class="feature-groups">
          <div class="loading"><div class="spinner"></div></div>
        </div>
      </div>

      <!-- Settings -->
      <div class="profile-section">
        <div class="profile-section-title">
          <span class="material-symbols-outlined">settings</span>
          Deine Einstellungen
        </div>
        <div class="section-intro">Passe DualMind an deine Vorlieben an.</div>
        <div class="pref-sections">
          <!-- Appearance -->
          <div class="pref-section">
            <div class="pref-section-header" onclick="ProfileView.togglePrefSection('pref-appearance')">
              <div class="pref-section-label">
                <span class="material-symbols-outlined">palette</span>
                Erscheinungsbild
              </div>
              <span class="material-symbols-outlined collapse-icon" id="pref-appearance-icon">expand_more</span>
            </div>
            <div class="pref-section-content" id="pref-appearance">
              <div class="pref-section-inner">
                <div class="settings-item">
                  <span class="settings-item-label">Design</span>
                  <label class="toggle toggle-sm">
                    <input type="checkbox" id="theme-toggle" ${ProfileView.getTheme() === 'light' ? 'checked' : ''}
                           onchange="ProfileView.toggleTheme(this.checked)">
                    <span class="toggle-slider"></span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- Daily Routine -->
          <div class="pref-section">
            <div class="pref-section-header" onclick="ProfileView.togglePrefSection('pref-routine')">
              <div class="pref-section-label">
                <span class="material-symbols-outlined">schedule</span>
                Tagesablauf
              </div>
              <span class="material-symbols-outlined collapse-icon" id="pref-routine-icon">chevron_right</span>
            </div>
            <div class="pref-section-content collapsed" id="pref-routine">
              <div class="pref-section-inner">
                <div class="settings-item">
                  <span class="settings-item-label">T\u00e4gliches Briefing</span>
                  <span class="settings-item-value">08:00 Uhr</span>
                </div>
                <div class="settings-item">
                  <span class="settings-item-label">Deine Zeitzone</span>
                  <span class="settings-item-value">Europe/Berlin</span>
                </div>
                <div class="settings-item">
                  <span class="settings-item-label">Proaktive Vorschlaege</span>
                  <label class="toggle toggle-sm">
                    <input type="checkbox" id="proactive-toggle" checked
                           onchange="ProfileView.toggleProactive(this.checked)">
                    <span class="toggle-slider"></span>
                  </label>
                </div>
                <div class="settings-hint">Zeigt Erinnerungen und Vorschlaege auf dem Dashboard.</div>
              </div>
            </div>
          </div>

          <!-- Notifications -->
          <div class="pref-section">
            <div class="pref-section-header" onclick="ProfileView.togglePrefSection('pref-notifications')">
              <div class="pref-section-label">
                <span class="material-symbols-outlined">notifications</span>
                Benachrichtigungen
              </div>
              <span class="material-symbols-outlined collapse-icon" id="pref-notifications-icon">chevron_right</span>
            </div>
            <div class="pref-section-content collapsed" id="pref-notifications">
              <div class="pref-section-inner">
                <div class="settings-hint">Erinnerungen und Systemhinweise erscheinen automatisch. Einzelne Benachrichtigungen kannst du im Notification Center ausblenden.</div>
                <div class="settings-item">
                  <span class="settings-item-label">Im Dashboard anzeigen</span>
                  <label class="toggle toggle-sm">
                    <input type="checkbox" id="notif-widget-toggle" checked
                           onchange="ProfileView.toggleNotifWidget(this.checked)">
                    <span class="toggle-slider"></span>
                  </label>
                </div>
                <a href="#/notifications" style="text-decoration:none;color:inherit">
                  <div class="settings-item" style="cursor:pointer">
                    <span class="settings-item-label"><span class="material-symbols-outlined mi-sm">inbox</span> Zum Notification Center</span>
                    <span class="material-symbols-outlined mi-sm" style="color:var(--text-muted)">chevron_right</span>
                  </div>
                </a>
              </div>
            </div>
          </div>

          <!-- Dashboard Widgets -->
          <div class="pref-section">
            <div class="pref-section-header" onclick="ProfileView.togglePrefSection('pref-widgets')">
              <div class="pref-section-label">
                <span class="material-symbols-outlined">dashboard</span>
                Dashboard anpassen
              </div>
              <span class="material-symbols-outlined collapse-icon" id="pref-widgets-icon">chevron_right</span>
            </div>
            <div class="pref-section-content collapsed" id="pref-widgets">
              <div class="pref-section-inner">
                <div class="settings-hint">Widgets auf dem Home-Screen ein-/ausblenden.</div>
                <div id="widget-config-list"><div class="loading"><div class="spinner"></div></div></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Advanced / Developer -->
      <div class="dev-section">
        <div class="pref-sections">
          <div class="pref-section">
            <div class="pref-section-header" onclick="ProfileView.togglePrefSection('pref-dev')">
              <div class="pref-section-label">
                <span class="material-symbols-outlined">code</span>
                Erweitert
              </div>
              <span class="material-symbols-outlined collapse-icon" id="pref-dev-icon">chevron_right</span>
            </div>
            <div class="pref-section-content collapsed" id="pref-dev">
              <div class="pref-section-inner dev-widgets">
                <!-- Health Monitor Widget -->
                <div class="dev-widget" id="dev-health-widget">
                  <div class="dev-widget-header">
                    <span class="dev-widget-title">
                      <span class="material-symbols-outlined mi-sm">monitor_heart</span>
                      API Health
                    </span>
                    <button class="btn-icon btn-icon-sm" onclick="ProfileView.refreshHealth()" title="Aktualisieren">
                      <span class="material-symbols-outlined mi-sm">refresh</span>
                    </button>
                  </div>
                  <div id="dev-health-content">
                    <div class="loading"><div class="spinner"></div></div>
                  </div>
                </div>
                <!-- GitHub Issues Widget -->
                <div class="dev-widget" id="dev-issues-widget">
                  <div class="dev-widget-header">
                    <span class="dev-widget-title">
                      <span class="material-symbols-outlined mi-sm">bug_report</span>
                      Offene Issues
                    </span>
                    <a href="#/issues" class="btn-icon btn-icon-sm" title="Alle Issues">
                      <span class="material-symbols-outlined mi-sm">open_in_new</span>
                    </a>
                  </div>
                  <div id="dev-issues-content">
                    <div class="loading"><div class="spinner"></div></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Logout -->
      <div class="profile-logout">
        <button class="btn btn-danger" onclick="ProfileView.confirmLogout()">Abmelden</button>
      </div>
    `;

    await Promise.allSettled([loadServices(), loadFeatures(), loadWidgetConfig()]);
    _initProactiveToggle();
  }

  /* ── Status Bar (computed after data loads) ── */

  function updateStatusBar(featureCount, serviceCount, totalServices) {
    const el = document.getElementById('profile-status-bar');
    if (!el) return;
    el.innerHTML = `
      <div class="profile-stat">
        <span class="material-symbols-outlined profile-stat-accent">auto_awesome</span>
        ${featureCount} Funktionen aktiv
      </div>
      <div class="profile-stat">
        <span class="material-symbols-outlined profile-stat-success">link</span>
        ${serviceCount} von ${totalServices} Diensten verbunden
      </div>
    `;
  }

  /* ── Services ── */

  let _serviceData = null;

  async function loadServices() {
    const el = document.getElementById('services-list');
    try {
      const data = await Api.getDashboard();
      _serviceData = data;

      // Drive connected status: same as calendar (same Google credentials)
      const connMap = {
        calendar_connected: !!data.calendar_connected,
        email_connected: !!data.email_connected,
        drive_connected: !!data.calendar_connected
      };

      const connCount = Object.values(connMap).filter(Boolean).length;

      const SERVICE_ROUTES = { calendar: '#/calendar', email: '#/inbox', drive: '#/drive' };

      el.innerHTML = SERVICE_DEFS.map(svc => {
        const connected = connMap[svc.connKey];
        const chipClass = connected ? 'connected' : 'not-setup';
        const chipText = connected ? 'Verbunden' : 'Noch nicht eingerichtet';
        const route = SERVICE_ROUTES[svc.id] || '#/profile';
        const hint = !connected && svc.id === 'calendar'
          ? '<div class="service-card-hint">Wende dich an den Administrator, um den Kalender zu verbinden.</div>'
          : '';
        return `
          <div class="service-card card-clickable" onclick="Router.navigate('${route}')">
            <div class="service-card-icon">${svc.emoji}</div>
            <div class="service-card-body">
              <div class="service-card-name">${escapeHtml(svc.name)}</div>
              <div class="service-card-desc">${escapeHtml(svc.desc)}</div>
              ${hint}
            </div>
            <div class="service-status-chip ${chipClass}">
              <span class="service-status-dot"></span>
              ${chipText}
            </div>
          </div>
        `;
      }).join('');

      // Update status bar with service count
      window._profileServiceCount = connCount;
      window._profileTotalServices = SERVICE_DEFS.length;
      tryUpdateStatusBar();
    } catch {
      el.innerHTML = '<div class="empty-state">Dienste konnten nicht geladen werden</div>';
    }
  }

  /* ── Features ── */

  let _featuresCache = null;

  async function loadFeatures() {
    const el = document.getElementById('features-list');
    const stripEl = document.getElementById('always-active-strip');
    try {
      const features = await Api.getFeatures();
      _featuresCache = features;

      if (features.length === 0) {
        el.innerHTML = '<div class="empty-state">Keine Funktionen verf\u00fcgbar</div>';
        return;
      }

      const featureMap = {};
      features.forEach(f => { featureMap[f.id] = f; });

      // Always-active strip
      const alwaysActive = ALWAYS_ACTIVE.map(id => featureMap[id]).filter(Boolean);
      if (stripEl && alwaysActive.length > 0) {
        stripEl.innerHTML = '<div class="always-active-strip">' +
          alwaysActive.map(f => `
            <span class="always-active-chip">${f.emoji || ''} ${escapeHtml(f.name)}</span>
          `).join('') + '</div>';
      }

      // Count enabled features
      const enabledCount = features.filter(f => f.enabled).length;
      window._profileFeatureCount = enabledCount;
      tryUpdateStatusBar();

      // Render groups
      el.innerHTML = FEATURE_GROUPS.map((group, gi) => {
        const groupFeatures = group.features.map(id => featureMap[id]).filter(Boolean);
        if (groupFeatures.length === 0) return '';

        const enabledInGroup = groupFeatures.filter(f => f.enabled).length;
        const isFirst = gi === 0;
        const collapsedClass = isFirst ? '' : 'collapsed';
        const collapseIcon = isFirst ? 'expand_more' : 'chevron_right';

        return `
          <div class="feature-group">
            <div class="feature-group-header" onclick="ProfileView.toggleFeatureGroup('fg-${group.id}')">
              <div class="feature-group-icon">
                <span class="material-symbols-outlined">${group.icon}</span>
              </div>
              <div class="feature-group-info">
                <div class="feature-group-title">${escapeHtml(group.title)}</div>
                <div class="feature-group-desc">${escapeHtml(group.desc)}</div>
              </div>
              <div class="feature-group-meta">
                <span class="feature-group-count">${enabledInGroup}/${groupFeatures.length}</span>
                <span class="material-symbols-outlined collapse-icon" id="fg-${group.id}-icon">${collapseIcon}</span>
              </div>
            </div>
            <div class="feature-group-content ${collapsedClass}" id="fg-${group.id}">
              <div class="feature-group-list">
                ${groupFeatures.map(f => renderFeatureCard(f)).join('')}
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch {
      el.innerHTML = '<div class="empty-state">Funktionen konnten nicht geladen werden</div>';
    }
  }

  function renderFeatureCard(f) {
    const benefit = FEATURE_BENEFITS[f.id] || f.description || '';
    const available = f.available !== false;

    let prereqHtml = '';
    if (!available && f.required_settings && f.required_settings.length > 0) {
      const services = [...new Set(f.required_settings.map(s => PREREQ_LABELS[s] || s))];
      prereqHtml = `
        <div class="feature-prereq">
          <span class="material-symbols-outlined">info</span>
          Verf\u00fcgbar nach Einrichtung von ${escapeHtml(services.join(', '))}
        </div>
      `;
    }

    return `
      <div class="feature-card">
        <span class="feature-card-emoji">${f.emoji || '\u2699'}</span>
        <div class="feature-card-body">
          <div class="feature-card-name">${escapeHtml(f.name)}</div>
          <div class="feature-card-benefit">${escapeHtml(benefit)}</div>
          ${prereqHtml}
        </div>
        <label class="toggle toggle-sm">
          <input type="checkbox" ${f.enabled ? 'checked' : ''} ${!available ? 'disabled' : ''}
                 onchange="ProfileView.toggleFeature('${f.id}')">
          <span class="toggle-slider"></span>
        </label>
      </div>
    `;
  }

  function tryUpdateStatusBar() {
    if (window._profileFeatureCount !== undefined && window._profileServiceCount !== undefined) {
      updateStatusBar(window._profileFeatureCount, window._profileServiceCount, window._profileTotalServices || 3);
    }
  }

  /* ── Feature Toggle ── */

  async function toggleFeature(featureId) {
    try {
      await Api.toggleFeature(featureId);
      await loadFeatures();
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
      await loadFeatures();
    }
  }

  /* ── Collapsible Helpers ── */

  function toggleFeatureGroup(contentId) {
    const content = document.getElementById(contentId);
    const icon = document.getElementById(contentId + '-icon');
    if (!content) return;
    const isCollapsed = content.classList.toggle('collapsed');
    if (icon) icon.textContent = isCollapsed ? 'chevron_right' : 'expand_more';
  }

  function togglePrefSection(contentId) {
    const content = document.getElementById(contentId);
    const icon = document.getElementById(contentId + '-icon');
    if (!content) return;
    const isCollapsed = content.classList.toggle('collapsed');
    if (icon) icon.textContent = isCollapsed ? 'chevron_right' : 'expand_more';

    // Lazy-load widget config when first opened
    if (!isCollapsed) {
      if (contentId === 'pref-widgets') loadWidgetConfig();
      if (contentId === 'pref-dev') loadDevWidgets();
      if (contentId === 'pref-notifications') syncNotifToggle();
    }
  }

  /* ── Dashboard Widget Configuration ── */

  async function loadWidgetConfig() {
    const el = document.getElementById('widget-config-list');
    if (!el) return;
    try {
      const prefs = window.AppPreferences ? window.AppPreferences.getCached() : null;
      const data = prefs || await Api.getPreferences();
      const widgets = (data.dashboard && data.dashboard.widgets) || [];

      widgets.sort((a, b) => (a.order || 0) - (b.order || 0));

      const widgetLabels = {
        notifications: { icon: 'notifications', label: 'Benachrichtigungen' },
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
      el.innerHTML = '<div class="empty-state">Widgets konnten nicht geladen werden</div>';
    }
  }

  function syncNotifToggle() {
    const toggle = document.getElementById('notif-widget-toggle');
    if (!toggle) return;
    const prefs = window.AppPreferences ? window.AppPreferences.getCached() : null;
    if (prefs && prefs.dashboard && prefs.dashboard.widgets) {
      const w = prefs.dashboard.widgets.find(w => w.id === 'notifications');
      toggle.checked = w ? w.enabled !== false : true;
    }
  }

  async function toggleNotifWidget(enabled) {
    await toggleWidget('notifications', enabled);
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

  /* ── Theme ── */

  function getTheme() {
    return localStorage.getItem('dualmind-theme') || 'dark';
  }

  function toggleTheme(isLight) {
    const theme = isLight ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('dualmind-theme', theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = isLight ? '#f5f5f7' : '#7c4dff';
    if (window.AppPreferences) {
      window.AppPreferences.save({ appearance: { theme } }).catch(() => {});
    }
  }

  /* ── Proaktive Vorschlaege ── */

  async function toggleProactive(enabled) {
    try {
      if (window.AppPreferences) {
        await window.AppPreferences.save({ proactive_suggestions: enabled });
      }
      Toast.show(enabled ? 'Proaktive Vorschlaege aktiviert' : 'Proaktive Vorschlaege deaktiviert', 'info');
    } catch {
      Toast.show('Einstellung konnte nicht gespeichert werden', 'error');
    }
  }

  function _initProactiveToggle() {
    const toggle = document.getElementById('proactive-toggle');
    if (!toggle) return;
    const prefs = window.AppPreferences ? window.AppPreferences.getCached() : null;
    if (prefs && prefs.proactive_suggestions === false) {
      toggle.checked = false;
    }
  }

  /* ── Logout ── */

  function confirmLogout() {
    if (confirm('M\u00f6chtest du dich wirklich abmelden?')) {
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

  /* ── Developer Widgets ── */

  async function loadDevWidgets() {
    if (_devDataLoaded) return;
    _devDataLoaded = true;
    await Promise.all([loadDevHealth(), loadDevIssues()]);
  }

  async function loadDevHealth() {
    const el = document.getElementById('dev-health-content');
    if (!el) return;
    try {
      const [health, detailRes] = await Promise.allSettled([
        Api.getStatusHealth(),
        Api.getStatusDetail()
      ]);
      if (health.status !== 'fulfilled') {
        el.innerHTML = '<div class="empty-state">Health-Daten nicht verf\u00fcgbar</div>';
        return;
      }
      const detail = detailRes.status === 'fulfilled' ? detailRes.value : null;
      renderHealthWidget(el, health.value, detail);
    } catch {
      el.innerHTML = '<div class="empty-state">Health-Daten nicht verf\u00fcgbar</div>';
    }
  }

  function renderHealthWidget(el, health, detail) {
    const now = new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });

    function dot(status) {
      const cls = status === 'healthy' ? 'health-dot-ok' : 'health-dot-err';
      return `<span class="health-dot ${cls}"></span>`;
    }
    function row(name, svc) {
      const meta = svc.response_ms != null ? `${svc.response_ms}ms` : (svc.error || svc.status || '?');
      return `<div class="health-row">${dot(svc.status)}<span class="health-svc-name">${escapeHtml(name)}</span><span class="health-svc-meta">${escapeHtml(meta)}</span></div>`;
    }

    // Alle Services aus Health-Response rendern
    const svcEntries = Object.entries(health.services || {});
    const healthyRows = svcEntries.filter(([, s]) => s.status === 'healthy');
    const downRows = svcEntries.filter(([, s]) => s.status !== 'healthy');

    let rows = '';
    // Down-Services zuerst (wichtiger)
    for (const [name, svc] of downRows) rows += row(name, svc);
    for (const [name, svc] of healthyRows) rows += row(name, svc);

    // Systemd-Services aus /status/detail (falls verfuegbar)
    if (detail && detail.services) {
      for (const [key, label] of [['personal-assistant', 'Bot'], ['personal-assistant-api', 'API'], ['personal-assistant-webhook', 'Webhook']]) {
        const s = detail.services[key];
        if (s) {
          const svcObj = { status: s.active ? 'healthy' : 'down' };
          rows += row(label, svcObj);
        }
      }
    }

    const okClass = health.overall === 'healthy' ? 'health-dot-ok' : 'health-dot-err';
    const uptime = health.uptime || (detail && detail.uptime) || '?';
    const commit = health.commit || (detail && detail.git && detail.git.commit) || '?';
    const branch = (detail && detail.git && detail.git.branch) || '';
    const branchInfo = branch ? `${branch}@${commit}` : commit;

    el.innerHTML = `
      <div class="health-summary">
        <span class="health-dot ${okClass}"></span>
        <span>${health.overall === 'healthy' ? 'Alle Systeme OK' : 'Probleme erkannt'}</span>
        <span class="health-meta">Uptime: ${escapeHtml(uptime)}</span>
      </div>
      <div class="health-rows">${rows}</div>
      <div class="health-footer">
        <span class="health-meta">${escapeHtml(branchInfo)}</span>
        <span class="health-meta">${escapeHtml(String(healthyRows.length))}/${escapeHtml(String(svcEntries.length))} Services OK</span>
        <span class="health-meta">Gepr\u00fcft: ${now}</span>
      </div>`;
  }

  async function refreshHealth() {
    const el = document.getElementById('dev-health-content');
    if (!el) return;
    el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    await loadDevHealth();
  }

  async function loadDevIssues() {
    const el = document.getElementById('dev-issues-content');
    if (!el) return;
    try {
      const [issuesRes, labelsRes] = await Promise.allSettled([
        Api.getGitHubIssues(),
        Api.getGitHubLabels()
      ]);
      const labels = labelsRes.status === 'fulfilled' ? labelsRes.value : [];
      const issues = issuesRes.status === 'fulfilled' ? issuesRes.value : null;
      if (!issues) {
        el.innerHTML = '<div class="empty-state">Issues nicht verf\u00fcgbar</div>';
        return;
      }
      renderIssuesWidget(el, issues, labels);
    } catch {
      el.innerHTML = '<div class="empty-state">Issues nicht verf\u00fcgbar</div>';
    }
  }

  function renderIssuesWidget(el, issues, labels) {
    if (issues.length === 0) {
      el.innerHTML = '<div class="empty-state">Keine offenen Issues</div>';
      return;
    }
    function badge(name) {
      const ld = labels.find(l => l.name === name);
      if (ld && ld.color) {
        return `<span class="badge" style="background:#${ld.color}33;color:#${ld.color}">${escapeHtml(name)}</span>`;
      }
      return `<span class="badge badge-accent">${escapeHtml(name)}</span>`;
    }
    const shown = issues.slice(0, 8);
    const remaining = issues.length - shown.length;
    el.innerHTML = shown.map(iss => `
      <a href="${escapeHtml(iss.html_url)}" target="_blank" rel="noopener" class="dev-issue-row">
        <span class="dev-issue-num">#${iss.number}</span>
        <span class="dev-issue-title">${escapeHtml(iss.title)}</span>
        ${iss.labels.length ? `<span class="dev-issue-labels">${iss.labels.map(l => badge(l)).join('')}</span>` : ''}
      </a>`).join('') +
      (remaining > 0 ? `<a href="#/issues" class="dev-issues-more">+${remaining} weitere &rarr;</a>` : '');
  }

  return {
    render,
    toggleFeature,
    toggleFeatureGroup,
    togglePrefSection,
    confirmLogout,
    getTheme,
    toggleTheme,
    toggleWidget,
    refreshHealth,
    toggleProactive,
    toggleNotifWidget
  };
})();
