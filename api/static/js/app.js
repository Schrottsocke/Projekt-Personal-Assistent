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
  // Redirect: Focus → Dashboard (Focus View wurde ins Dashboard integriert)
  Router.register('#/focus', () => { window.location.hash = '#/dashboard'; });
  Router.register('#/templates', (c) => TemplatesView.render(c));
  Router.register('#/documents', (c) => DocumentsView.render(c));
  Router.register('#/contacts', (c) => ContactsView.render(c));
  // Redirect: alte Follow-ups Route → Inbox
  Router.register('#/followups', () => { window.location.hash = '#/inbox'; });
  Router.register('#/weather', (c) => WeatherView.render(c));
  Router.register('#/mobility', (c) => MobilityView.render(c));
  Router.register('#/automation', (c) => AutomationView.render(c));
  // Konsolidierte Inbox: UnifiedInboxView ist jetzt die einzige Inbox
  Router.register('#/inbox', (c) => UnifiedInboxView.render(c));
  // Redirect: alte Routen → Inbox
  Router.register('#/unified-inbox', () => { window.location.hash = '#/inbox'; });
  Router.register('#/notifications', () => { window.location.hash = '#/inbox'; });
  Router.register('#/memory', (c) => MemoryView.render(c));
  // Neue Hub-Views
  Router.register('#/planen', (c) => PlanenView.render(c));
  Router.register('#/mehr', (c) => MehrView.render(c));

  // ── Feste 4-Tab Navigation ──
  const FIXED_NAV = [
    { id: 'dashboard', label: 'Heute', icon: 'today', route: '#/dashboard' },
    { id: 'inbox', label: 'Inbox', icon: 'all_inbox', route: '#/inbox' },
    { id: 'planen', label: 'Planen', icon: 'event_note', route: '#/planen' },
    { id: 'mehr', label: 'Mehr', icon: 'menu', route: '#/mehr' },
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
    focus: { route: '#/dashboard', icon: 'center_focus_strong', label: 'Heute' },
    notifications: { route: '#/inbox', icon: 'notifications', label: 'Inbox' },
    templates: { route: '#/templates', icon: 'library_books', label: 'Vorlagen' },
    documents: { route: '#/documents', icon: 'scanner', label: 'Dokumente' },
    contacts: { route: '#/contacts', icon: 'contacts', label: 'Kontakte' },
    followups: { route: '#/inbox', icon: 'reply_all', label: 'Inbox' },
    weather: { route: '#/weather', icon: 'cloud', label: 'Wetter' },
    mobility: { route: '#/mobility', icon: 'route', label: 'Mobilität' },
    automation: { route: '#/automation', icon: 'smart_toy', label: 'Automation' },
    inbox: { route: '#/inbox', icon: 'all_inbox', label: 'Inbox' },
    'unified-inbox': { route: '#/inbox', icon: 'all_inbox', label: 'Inbox' },
    memory: { route: '#/memory', icon: 'psychology', label: 'Gedaechtnis' },
  };

  // ── Cached Preferences ──
  let _cachedPrefs = null;

  /**
   * Baut die feste 4-Tab Bottom-Nav auf.
   */
  function buildNav() {
    const nav = document.getElementById('bottom-nav');
    if (!nav) return;

    nav.innerHTML = FIXED_NAV.map(item => `
      <a class="nav-item" data-route="${item.route}" href="${item.route}">
        <span class="nav-icon material-symbols-outlined">${item.icon}</span>
        <span>${item.label}</span>
      </a>
    `).join('');
  }

  /**
   * Laedt User-Preferences und aktualisiert Nav + Dashboard-Config.
   */
  async function loadPreferences() {
    if (!Api.isLoggedIn()) return null;
    try {
      const prefs = await Api.getPreferences();
      _cachedPrefs = prefs;
      return prefs;
    } catch {
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
    return result;
  }

  // Expose globally for other views (ProfileView etc.)
  window.AppPreferences = {
    load: loadPreferences,
    getCached: getCachedPreferences,
    save: savePreferences,
    buildNav,
    NAV_META,
    FIXED_NAV,
  };

  // Ctrl+K wird vom AssistantSheet selbst gehandelt (in assistantSheet.js init)

  // Init router on DOM ready, then load preferences + Quick Capture
  async function startup() {
    // Feste 4-Tab Navigation aufbauen
    buildNav();
    Router.init();
    AssistantSheet.init();
    // Init offline queue (status tracking + auto-sync)
    if (typeof OfflineQueue !== 'undefined') {
      OfflineQueue.init();
    }
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
