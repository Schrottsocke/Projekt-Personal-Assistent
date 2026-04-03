/**
 * DualMind Web App – Init, Navigation & Preferences
 *
 * Alle Views registrieren sich selbst via Router.register() in ihrer IIFE.
 * Diese Datei laedt User-Preferences und baut die Navigation dynamisch auf.
 */
(function () {
  // ── View-Registry: jedes View-Modul registriert sich hier ──
  // (wird von den einzelnen View-Dateien befuellt)

  // Register all views (static, always available)
  Router.register('#/login', (c) => LoginView.render(c));
  Router.register('#/dashboard', (c) => DashboardView.render(c));
  Router.register('#/shopping', (c) => ShoppingView.render(c));
  Router.register('#/recipes', (c) => RecipesView.render(c));
  Router.register('#/chat', (c) => ChatView.render(c));
  Router.register('#/profile', (c) => ProfileView.render(c));
  Router.register('#/calendar', (c) => CalendarView.render(c));
  Router.register('#/tasks', (c) => TasksView.render(c));
  Router.register('#/mealplan', (c) => MealPlanView.render(c));
  Router.register('#/drive', (c) => DriveView.render(c));
  Router.register('#/issues', (c) => IssuesView.render(c));
  Router.register('#/shifts', (c) => ShiftsView.render(c));
  Router.register('#/notifications', (c) => NotificationsView.render(c));
  Router.register('#/focus', (c) => FocusView.render(c));
  Router.register('#/documents', (c) => DocumentsView.render(c));
  Router.register('#/templates', (c) => TemplatesView.render(c));
  Router.register('#/contacts', (c) => ContactsView.render(c));
  Router.register('#/followups', (c) => FollowUpsView.render(c));
  Router.register('#/weather', (c) => WeatherView.render(c));
  Router.register('#/mobility', (c) => MobilityView.render(c));

  // ── Default Nav (vor Preferences-Load) ──
  const DEFAULT_NAV = [
    { id: 'dashboard', label: 'Home', icon: 'home', route: '#/dashboard', pinned: true, order: 0 },
    { id: 'shopping', label: 'Einkauf', icon: 'shopping_cart', route: '#/shopping', pinned: true, order: 1 },
    { id: 'recipes', label: 'Rezepte', icon: 'restaurant', route: '#/recipes', pinned: true, order: 2 },
    { id: 'chat', label: 'Chat', icon: 'chat_bubble', route: '#/chat', pinned: true, order: 3 },
    { id: 'profile', label: 'Profil', icon: 'person', route: '#/profile', pinned: true, order: 4 },
  ];

  // Mapping von Nav-ID zu Route und Meta
  const NAV_META = {
    dashboard: { route: '#/dashboard', icon: 'home', label: 'Home' },
    shopping: { route: '#/shopping', icon: 'shopping_cart', label: 'Einkauf' },
    recipes: { route: '#/recipes', icon: 'restaurant', label: 'Rezepte' },
    chat: { route: '#/chat', icon: 'chat_bubble', label: 'Chat' },
    profile: { route: '#/profile', icon: 'person', label: 'Profil' },
    calendar: { route: '#/calendar', icon: 'calendar_month', label: 'Kalender' },
    tasks: { route: '#/tasks', icon: 'check_circle', label: 'Aufgaben' },
    mealplan: { route: '#/mealplan', icon: 'restaurant_menu', label: 'Wochenplan' },
    drive: { route: '#/drive', icon: 'folder', label: 'Drive' },
    shifts: { route: '#/shifts', icon: 'work', label: 'Dienste' },
    issues: { route: '#/issues', icon: 'bug_report', label: 'Issues' },
    focus: { route: '#/focus', icon: 'center_focus_strong', label: 'Fokus' },
    documents: { route: '#/documents', icon: 'scanner', label: 'Dokumente' },
    templates: { route: '#/templates', icon: 'library_books', label: 'Vorlagen' },
    notifications: { route: '#/notifications', icon: 'notifications', label: 'Alerts' },
    contacts: { route: '#/contacts', icon: 'contacts', label: 'Kontakte' },
    followups: { route: '#/followups', icon: 'reply_all', label: 'Follow-ups' },
    weather: { route: '#/weather', icon: 'cloud', label: 'Wetter' },
    mobility: { route: '#/mobility', icon: 'route', label: 'Mobilität' },
  };

  // ── Cached Preferences ──
  let _cachedPrefs = null;

  /**
   * Baut die Bottom-Nav aus Preferences-Daten oder Defaults auf.
   */
  function buildNav(navItems) {
    const nav = document.getElementById('bottom-nav');
    if (!nav) return;

    // Nur angepinnte + aktivierte Items anzeigen, sortiert nach order
    const pinned = (navItems || DEFAULT_NAV)
      .filter(i => i.enabled !== false && i.pinned)
      .sort((a, b) => (a.order || 0) - (b.order || 0));

    nav.innerHTML = pinned.map(item => {
      const meta = NAV_META[item.id] || {};
      const route = meta.route || item.route || `#/${item.id}`;
      const icon = meta.icon || item.icon || 'circle';
      const label = meta.label || item.label || item.id;
      return `<a class="nav-item" data-route="${route}" href="${route}">
        <span class="nav-icon material-symbols-outlined">${icon}</span>
        <span>${label}</span>
      </a>`;
    }).join('');
  }

  /**
   * Laedt User-Preferences und aktualisiert Nav + Dashboard-Config.
   */
  async function loadPreferences() {
    if (!Api.isLoggedIn()) {
      buildNav(null);
      return null;
    }
    try {
      const prefs = await Api.getPreferences();
      _cachedPrefs = prefs;
      if (prefs.nav && prefs.nav.items) {
        buildNav(prefs.nav.items);
      }
      return prefs;
    } catch {
      // Fallback auf Defaults bei Fehler
      buildNav(null);
      return null;
    }
  }

  /**
   * Gibt die gecachten Preferences zurueck (oder null).
   */
  function getCachedPreferences() {
    return _cachedPrefs;
  }

  /**
   * Aktualisiert Preferences auf dem Server und refresht die Nav.
   */
  async function savePreferences(updates) {
    const result = await Api.updatePreferences(updates);
    _cachedPrefs = result;
    if (result.nav && result.nav.items) {
      buildNav(result.nav.items);
    }
    return result;
  }

  // Expose globally for other views (ProfileView etc.)
  window.AppPreferences = {
    load: loadPreferences,
    getCached: getCachedPreferences,
    save: savePreferences,
    buildNav,
    NAV_META,
    DEFAULT_NAV,
  };

  // Global keyboard shortcut: Ctrl+K / Cmd+K for Command Palette
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      CommandPalette.toggle();
    }
  });

  // Init router on DOM ready, then load preferences + Quick Capture
  async function startup() {
    // Build default nav immediately (before preferences load)
    buildNav(null);
    Router.init();
    QuickCapture.init();
    // Load preferences in background (updates nav when ready)
    await loadPreferences();
    // Init notification bell (polling + badge)
    if (Api.isLoggedIn()) {
      document.querySelector('.notification-bell')?.classList.remove('hidden');
      NotificationBell.init();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startup);
  } else {
    startup();
  }
})();
