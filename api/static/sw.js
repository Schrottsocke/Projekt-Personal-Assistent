const CACHE_NAME = 'dualmind-v1';
const SHELL_ASSETS = [
  '/app',
  '/static/css/app.css',
  '/static/js/utils.js',
  '/static/js/api.js',
  '/static/js/router.js',
  '/static/js/app.js',
  '/static/favicon.svg'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((c) => c.addAll(SHELL_ASSETS)));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
});

self.addEventListener('fetch', (e) => {
  // Skip API calls and non-GET requests
  if (e.request.url.includes('/api/') || e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then((r) => r || fetch(e.request))
  );
});
