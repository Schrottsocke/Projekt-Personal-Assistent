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

  // Init router on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Router.init());
  } else {
    Router.init();
  }
})();
