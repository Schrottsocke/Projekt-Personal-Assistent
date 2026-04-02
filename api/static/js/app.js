/**
 * DualMind Web App – Init & Navigation
 */
(function () {
  // Register all views
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

  // Global keyboard shortcut: Ctrl+K / Cmd+K for Command Palette
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      CommandPalette.toggle();
    }
  });

  // Init router on DOM ready, then init Quick Capture FAB
  function startup() {
    Router.init();
    QuickCapture.init();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startup);
  } else {
    startup();
  }
})();
