/**
 * DualMind Hash Router – Simple client-side routing
 */
const Router = (() => {
  const routes = {};
  let currentView = null;

  function register(hash, renderFn) {
    routes[hash] = renderFn;
  }

  function navigate(hash) {
    window.location.hash = hash;
  }

  function getRoute() {
    const hash = window.location.hash || '#/login';
    // Match exact route or find best prefix
    if (routes[hash]) return hash;
    // Default fallback
    return Api.isLoggedIn() ? '#/dashboard' : '#/login';
  }

  async function handleRoute() {
    const hash = getRoute();
    const renderFn = routes[hash];

    if (!renderFn) {
      navigate(Api.isLoggedIn() ? '#/dashboard' : '#/login');
      return;
    }

    // Auth guard: redirect to login if not authenticated (except login route)
    if (hash !== '#/login' && !Api.isLoggedIn()) {
      navigate('#/login');
      return;
    }

    // Skip login if already authenticated
    if (hash === '#/login' && Api.isLoggedIn()) {
      navigate('#/dashboard');
      return;
    }

    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
      const target = item.getAttribute('data-route');
      item.classList.toggle('active', target === hash);
    });

    // Show/hide nav for login
    const nav = document.querySelector('.bottom-nav');
    const header = document.querySelector('.app-header');
    if (nav) nav.classList.toggle('hidden', hash === '#/login');
    if (header) header.classList.toggle('hidden', hash === '#/login');

    // Render view
    const container = document.getElementById('view-container');
    if (container) {
      currentView = hash;
      await renderFn(container);
    }
  }

  function init() {
    window.addEventListener('hashchange', handleRoute);
    handleRoute();
  }

  return { register, navigate, init, getRoute };
})();
