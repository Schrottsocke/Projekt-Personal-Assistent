const CACHE_NAME = 'dualmind-v11';
const API_CACHE_NAME = 'dualmind-api-v1';

const SHELL_ASSETS = [
  '/app',
  '/static/css/app.css',
  '/static/js/utils.js',
  '/static/js/api.js',
  '/static/js/offlineQueue.js',
  '/static/js/router.js',
  '/static/js/views/calendar.js',
  '/static/js/views/chat.js',
  '/static/js/views/assistantSheet.js',
  '/static/js/views/dashboard.js',
  '/static/js/views/documents.js',
  '/static/js/views/drive.js',
  '/static/js/views/issues.js',
  '/static/js/views/automation.js',
  '/static/js/views/contacts.js',
  '/static/js/views/login.js',
  '/static/js/views/mealplan.js',
  '/static/js/views/memory.js',
  '/static/js/views/mobility.js',
  '/static/js/views/profile.js',
  '/static/js/views/recipes.js',
  '/static/js/views/shifts.js',
  '/static/js/views/shopping.js',
  '/static/js/views/tasks.js',
  '/static/js/views/templates.js',
  '/static/js/views/unifiedInbox.js',
  '/static/js/views/weather.js',
  '/static/js/views/planen.js',
  '/static/js/views/mehr.js',
  '/static/js/app.js',
  '/static/favicon.svg',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

// API paths eligible for stale-while-revalidate caching
const API_CACHE_PATHS = [
  '/dashboard/today',
  '/calendar/today',
  '/calendar/week',
  '/chat/history',
  '/inbox/unified',
];

function isApiCacheable(pathname) {
  return API_CACHE_PATHS.some((p) => pathname.startsWith(p));
}

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((c) => c.addAll(SHELL_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((n) => n !== 'dualmind-v11' && n !== API_CACHE_NAME)
          .map((n) => caches.delete(n))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;

  // Static assets: cache-first
  if (url.pathname.startsWith('/static/') || url.pathname === '/app') {
    e.respondWith(
      caches.match(e.request).then((r) => r || fetch(e.request))
    );
    return;
  }

  // API GET requests: stale-while-revalidate
  if (isApiCacheable(url.pathname)) {
    e.respondWith(
      caches.open(API_CACHE_NAME).then((cache) =>
        cache.match(e.request).then((cached) => {
          const networkFetch = fetch(e.request)
            .then((response) => {
              if (response.ok) {
                cache.put(e.request, response.clone());
              }
              return response;
            })
            .catch(() => cached);
          return cached || networkFetch;
        })
      )
    );
    return;
  }
});
