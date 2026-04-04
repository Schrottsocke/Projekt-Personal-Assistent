const CACHE_NAME = 'dualmind-v9';
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
  '/static/favicon.svg'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((c) => c.addAll(SHELL_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // Only cache static assets and app shell – skip all API endpoints and non-GET
  if (e.request.method !== 'GET') return;
  if (!url.pathname.startsWith('/static/') && url.pathname !== '/app') return;
  e.respondWith(
    caches.match(e.request).then((r) => r || fetch(e.request))
  );
});
