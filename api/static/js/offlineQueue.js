/**
 * OfflineQueue – Offline-Resilienz fuer DualMind Web-App
 *
 * Trackt Online/Offline-Status, queued fehlgeschlagene Schreiboperationen
 * in localStorage und synchronisiert automatisch bei Wiederverbindung.
 */
const OfflineQueue = (() => {
  const STORAGE_KEY = 'dm_offline_queue';
  const MAX_RETRIES = 3;
  const RETRY_DELAY = 2000;

  let online = navigator.onLine;
  let syncing = false;
  let queue = [];
  let statusListeners = [];
  let bannerEl = null;

  // ── Init ──

  function init() {
    // Restore queue from localStorage
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) queue = JSON.parse(stored);
    } catch (_) {
      queue = [];
    }

    // Listen for online/offline events
    window.addEventListener('online', () => {
      online = true;
      notifyListeners();
      updateBanner();
      // Auto-sync after short delay to let connection stabilize
      if (queue.length > 0) {
        setTimeout(() => processQueue(), 1500);
      }
    });

    window.addEventListener('offline', () => {
      online = false;
      notifyListeners();
      updateBanner();
    });

    // Initial UI
    updateBanner();

    // Try to sync any pending items on startup
    if (online && queue.length > 0) {
      setTimeout(() => processQueue(), 2000);
    }
  }

  // ── Queue Management ──

  function enqueue(action) {
    const item = {
      id: Date.now() + '_' + Math.random().toString(36).slice(2, 8),
      type: action.type || 'unknown',
      endpoint: action.endpoint,
      method: action.method || 'POST',
      body: action.body || null,
      label: action.label || '',
      createdAt: new Date().toISOString(),
      retries: 0,
    };
    queue.push(item);
    persist();
    updateBanner();
    return item.id;
  }

  function dequeue(id) {
    queue = queue.filter(item => item.id !== id);
    persist();
    updateBanner();
  }

  function removeFromQueue(id) {
    dequeue(id);
  }

  function getQueue() {
    return [...queue];
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
    } catch (_) {
      // localStorage voll – aelteste Items entfernen
      if (queue.length > 1) {
        queue.shift();
        persist();
      }
    }
  }

  // ── Sync / Retry ──

  async function processQueue() {
    if (syncing || queue.length === 0 || !online) return;

    syncing = true;
    updateBanner();

    let successCount = 0;
    let failCount = 0;
    const toProcess = [...queue];

    for (const item of toProcess) {
      if (!online) break; // Stop if we went offline during sync

      try {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('dm_access_token');
        if (token) headers['Authorization'] = 'Bearer ' + token;

        const fetchOpts = { method: item.method, headers };
        if (item.body) fetchOpts.body = JSON.stringify(item.body);

        const res = await fetch(item.endpoint, fetchOpts);

        if (res.status === 401) {
          // Try token refresh
          const refreshed = await tryRefreshToken();
          if (refreshed) {
            headers['Authorization'] = 'Bearer ' + refreshed;
            const retryRes = await fetch(item.endpoint, { method: item.method, headers, body: fetchOpts.body });
            if (retryRes.ok || retryRes.status === 201 || retryRes.status === 204) {
              dequeue(item.id);
              successCount++;
              continue;
            }
          }
          // Auth failed – keep in queue for next attempt
          item.retries++;
          failCount++;
          continue;
        }

        if (res.ok || res.status === 201 || res.status === 204) {
          dequeue(item.id);
          successCount++;
        } else if (res.status === 404 || res.status === 409 || res.status === 422) {
          // Unrecoverable – remove from queue
          dequeue(item.id);
          failCount++;
        } else {
          // Server error – retry later
          item.retries++;
          if (item.retries >= MAX_RETRIES) {
            dequeue(item.id);
            failCount++;
          }
          persist();
        }
      } catch (err) {
        // Network error during sync
        item.retries++;
        if (item.retries >= MAX_RETRIES) {
          dequeue(item.id);
          failCount++;
        }
        persist();
        // Likely offline again
        if (!navigator.onLine) {
          online = false;
          break;
        }
      }

      // Small delay between requests
      if (toProcess.indexOf(item) < toProcess.length - 1) {
        await new Promise(r => setTimeout(r, RETRY_DELAY));
      }
    }

    syncing = false;
    persist();
    updateBanner();
    showSyncResult(successCount, failCount);
    notifyListeners();
  }

  async function tryRefreshToken() {
    const rt = localStorage.getItem('dm_refresh_token');
    if (!rt) return null;
    try {
      const res = await fetch('/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      localStorage.setItem('dm_access_token', data.access_token);
      localStorage.setItem('dm_refresh_token', data.refresh_token);
      if (data.user_key) localStorage.setItem('dm_user_key', data.user_key);
      return data.access_token;
    } catch (_) {
      return null;
    }
  }

  // ── UI: Status Banner ──

  function createBanner() {
    if (bannerEl) return bannerEl;
    bannerEl = document.createElement('div');
    bannerEl.className = 'offline-banner';
    bannerEl.setAttribute('role', 'status');
    bannerEl.setAttribute('aria-live', 'polite');
    // Insert at top of #app
    const app = document.getElementById('app');
    if (app) {
      app.insertBefore(bannerEl, app.firstChild);
    } else {
      document.body.prepend(bannerEl);
    }
    return bannerEl;
  }

  function updateBanner() {
    const pending = queue.length;

    if (online && pending === 0 && !syncing) {
      // All good – hide banner
      if (bannerEl) {
        bannerEl.classList.remove('visible');
        setTimeout(() => {
          if (bannerEl && !bannerEl.classList.contains('visible')) {
            bannerEl.remove();
            bannerEl = null;
          }
        }, 300);
      }
      return;
    }

    const banner = createBanner();

    if (!online) {
      banner.className = 'offline-banner offline visible';
      banner.innerHTML = `
        <span class="material-symbols-outlined offline-banner-icon">cloud_off</span>
        <span class="offline-banner-text">Du bist offline${pending > 0 ? ' \u2013 ' + pending + ' Eintr\u00e4ge warten' : ' \u2013 Eingaben werden gespeichert'}</span>
      `;
    } else if (syncing) {
      banner.className = 'offline-banner syncing visible';
      banner.innerHTML = `
        <span class="offline-banner-spinner"></span>
        <span class="offline-banner-text">Daten werden synchronisiert\u2026</span>
      `;
    } else if (pending > 0) {
      banner.className = 'offline-banner pending visible';
      banner.innerHTML = `
        <span class="material-symbols-outlined offline-banner-icon">sync_problem</span>
        <span class="offline-banner-text">${pending} Eintr${pending === 1 ? 'ag wartet' : '\u00e4ge warten'} auf Synchronisierung</span>
        <button class="offline-banner-btn" onclick="OfflineQueue.processQueue()">Jetzt synchronisieren</button>
      `;
    }
  }

  function showSyncResult(success, failed) {
    if (success === 0 && failed === 0) return;

    let message, type;
    if (failed === 0) {
      message = success === 1
        ? 'Eintrag erfolgreich synchronisiert'
        : success + ' Eintr\u00e4ge erfolgreich synchronisiert';
      type = 'success';
    } else if (success === 0) {
      message = failed === 1
        ? 'Eintrag konnte nicht synchronisiert werden'
        : failed + ' Eintr\u00e4ge konnten nicht synchronisiert werden';
      type = 'warning';
    } else {
      message = success + ' synchronisiert, ' + failed + ' fehlgeschlagen';
      type = 'warning';
    }

    if (typeof Toast !== 'undefined' && Toast.show) {
      Toast.show(message, type);
    }
  }

  // ── Status Listeners ──

  function onStatusChange(callback) {
    statusListeners.push(callback);
  }

  function notifyListeners() {
    const status = { online, syncing, pending: queue.length };
    statusListeners.forEach(fn => {
      try { fn(status); } catch (_) {}
    });
  }

  // ── Public Helpers ──

  function isOnline() { return online; }
  function getPendingCount() { return queue.length; }

  return {
    init,
    enqueue,
    isOnline,
    getPendingCount,
    processQueue,
    onStatusChange,
    getQueue,
    removeFromQueue,
  };
})();
