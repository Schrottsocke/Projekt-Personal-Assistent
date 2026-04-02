/**
 * DualMind API Client – JWT Auth, Auto-Refresh, Error Handling
 */

/* ── Global Toast Notifications ─────────────────── */
const Toast = (() => {
  let container = null;

  function ensureContainer() {
    if (container && document.body.contains(container)) return container;
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
  }

  function show(message, type = 'error') {
    const c = ensureContainer();
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    c.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(100%)';
      el.style.transition = '0.3s ease';
      setTimeout(() => el.remove(), 300);
    }, 5000);
  }

  return { show };
})();

const Api = (() => {
  const TOKEN_KEY = 'dm_access_token';
  const REFRESH_KEY = 'dm_refresh_token';
  const USER_KEY = 'dm_user_key';

  let _refreshing = null;

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function getRefreshToken() { return localStorage.getItem(REFRESH_KEY); }
  function getUserKey() { return localStorage.getItem(USER_KEY); }

  function saveAuth(data) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
    localStorage.setItem(USER_KEY, data.user_key);
  }

  function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function isLoggedIn() {
    return !!getToken();
  }

  async function refreshToken() {
    const rt = getRefreshToken();
    if (!rt) { throw new Error('No refresh token'); }

    const res = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    });

    if (!res.ok) {
      clearAuth();
      throw new Error('Refresh failed');
    }

    const data = await res.json();
    saveAuth(data);
    return data.access_token;
  }

  async function request(path, options = {}) {
    const { body, method = 'GET', noAuth = false, timeoutMs = 0 } = options;

    const headers = { 'Content-Type': 'application/json' };
    if (!noAuth) {
      const token = getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    const fetchOpts = { method, headers };
    if (body !== undefined) fetchOpts.body = JSON.stringify(body);

    // Timeout via AbortController (0 = kein Timeout)
    let controller, timer;
    if (timeoutMs > 0) {
      controller = new AbortController();
      fetchOpts.signal = controller.signal;
      timer = setTimeout(() => controller.abort(), timeoutMs);
    }

    let res;
    try {
      res = await fetch(path, fetchOpts);
    } catch (err) {
      if (timer) clearTimeout(timer);
      if (err.name === 'AbortError') {
        const msg = 'Zeitüberschreitung – der Server hat zu lange gebraucht. Bitte versuche es erneut.';
        Toast.show(msg);
        throw new Error(msg);
      }
      Toast.show(err.message || 'Netzwerkfehler');
      throw err;
    }
    if (timer) clearTimeout(timer);

    // Auto-refresh on 401
    if (res.status === 401 && !noAuth && getRefreshToken()) {
      if (!_refreshing) {
        _refreshing = refreshToken().finally(() => { _refreshing = null; });
      }
      try {
        const newToken = await _refreshing;
        headers['Authorization'] = `Bearer ${newToken}`;
        res = await fetch(path, { method, headers, body: fetchOpts.body });
      } catch {
        clearAuth();
        window.location.hash = '#/login';
        throw new Error('Session abgelaufen');
      }
    }

    if (res.status === 204) return null;

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const msg = err.detail || `HTTP ${res.status}`;
      Toast.show(msg);
      throw new Error(msg);
    }

    return res.json();
  }

  // Auth
  async function login(username, password) {
    const data = await request('/auth/login', {
      method: 'POST',
      body: { username, password },
      noAuth: true,
    });
    saveAuth(data);
    return data;
  }

  function logout() {
    clearAuth();
    window.location.hash = '#/login';
  }

  // Dashboard
  function getDashboard() { return request('/dashboard/today'); }

  // Shopping
  function getShoppingItems(includeChecked = true) {
    return request(`/shopping/items?include_checked=${includeChecked}`);
  }
  function addShoppingItem(name) {
    return request('/shopping/items', { method: 'POST', body: { name } });
  }
  function toggleShoppingItem(id, checked) {
    return request(`/shopping/items/${id}`, { method: 'PATCH', body: { checked } });
  }
  function updateShoppingItem(id, data) {
    return request(`/shopping/items/${id}`, { method: 'PATCH', body: data });
  }
  function deleteShoppingItem(id) {
    return request(`/shopping/items/${id}`, { method: 'DELETE' });
  }
  function clearCheckedItems() {
    return request('/shopping/items/checked', { method: 'DELETE' });
  }

  // Recipes
  function searchRecipes(query, limit = 12) {
    return request(`/recipes/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  }
  function getSavedRecipes() { return request('/recipes/saved'); }
  function saveRecipe(recipe) {
    return request('/recipes/saved', { method: 'POST', body: recipe });
  }
  function deleteRecipe(id) {
    return request(`/recipes/saved/${id}`, { method: 'DELETE' });
  }
  function toggleFavorite(id) {
    return request(`/recipes/saved/${id}/favorite`, { method: 'PATCH' });
  }
  function addRecipeToShopping(chefkochId, servings) {
    return request(`/recipes/${chefkochId}/to-shopping`, {
      method: 'POST',
      body: { servings },
    });
  }

  // Chat
  function getChatHistory(limit = 50) {
    return request(`/chat/history?limit=${limit}`);
  }
  function sendMessage(message) {
    return request('/chat/message', { method: 'POST', body: { message }, timeoutMs: 30000 });
  }

  async function sendMessageStream(message, chatId, onToken, onDone, onError) {
    const token = getToken();
    try {
      const res = await fetch('/chat/message/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message: message, chat_id: chatId }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) onToken(data.token);
            if (data.done) onDone();
            if (data.error) onError(data.error);
          } catch (_) { /* ignore malformed SSE lines */ }
        }
      }
      // Flush remaining buffer
      if (buffer.startsWith('data: ')) {
        try {
          const data = JSON.parse(buffer.slice(6));
          if (data.token) onToken(data.token);
          if (data.done) onDone();
          if (data.error) onError(data.error);
        } catch (_) { /* ignore */ }
      }
    } catch (err) {
      onError(err.message);
    }
  }

  // Voice transcription
  async function transcribeVoice(audioBlob) {
    const formData = new FormData();
    formData.append('file', audioBlob, 'voice.webm');

    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    let res = await fetch('/chat/voice', { method: 'POST', headers, body: formData });

    if (res.status === 401 && getRefreshToken()) {
      if (!_refreshing) {
        _refreshing = refreshToken().finally(() => { _refreshing = null; });
      }
      try {
        const newToken = await _refreshing;
        headers['Authorization'] = `Bearer ${newToken}`;
        res = await fetch('/chat/voice', { method: 'POST', headers, body: formData });
      } catch {
        clearAuth();
        window.location.hash = '#/login';
        throw new Error('Session abgelaufen');
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  // Features
  function getFeatures() { return request('/features'); }
  function toggleFeature(featureId) {
    return request(`/features/${featureId}/toggle`, { method: 'POST' });
  }

  // Calendar
  function getCalendarToday() { return request('/calendar/today'); }
  function getCalendarWeek(days = 7) {
    return request(`/calendar/week?days=${days}`);
  }
  function createCalendarEvent(data) {
    return request('/calendar/events', { method: 'POST', body: data });
  }

  // Tasks
  function getTasks(all = false) {
    return request(`/tasks${all ? '?all=true' : ''}`);
  }
  function createTask(data) {
    return request('/tasks', { method: 'POST', body: data });
  }
  function updateTaskStatus(id, status) {
    return request(`/tasks/${id}`, { method: 'PATCH', body: { status } });
  }
  function deleteTask(id) {
    return request(`/tasks/${id}`, { method: 'DELETE' });
  }

  // MealPlan
  function getMealPlanWeek(start) {
    const qs = start ? `?start=${start}` : '';
    return request(`/meal-plan/week${qs}`);
  }
  function createMealPlan(data) {
    return request('/meal-plan', { method: 'POST', body: data });
  }
  function deleteMealPlan(id) {
    return request(`/meal-plan/${id}`, { method: 'DELETE' });
  }

  // Drive
  function getDriveFiles(q, limit = 20) {
    const params = [];
    if (q) params.push(`q=${encodeURIComponent(q)}`);
    if (limit !== 20) params.push(`limit=${limit}`);
    const qs = params.length ? '?' + params.join('&') : '';
    return request(`/drive/files${qs}`);
  }

  async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    let res = await fetch('/drive/upload', { method: 'POST', headers, body: formData });

    // Auto-refresh on 401
    if (res.status === 401 && getRefreshToken()) {
      if (!_refreshing) {
        _refreshing = refreshToken().finally(() => { _refreshing = null; });
      }
      try {
        const newToken = await _refreshing;
        headers['Authorization'] = `Bearer ${newToken}`;
        res = await fetch('/drive/upload', { method: 'POST', headers, body: formData });
      } catch {
        clearAuth();
        window.location.hash = '#/login';
        throw new Error('Session abgelaufen');
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    return res.json();
  }

  // Search
  function searchGlobal(query, limit = 20) {
    return request(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  // GitHub Issues
  function getGitHubLabels() { return request('/github/labels', { timeoutMs: 10000 }); }
  function getGitHubIssues() { return request('/github/issues', { timeoutMs: 10000 }); }
  function createGitHubIssue(data) { return request('/github/issues', { method: 'POST', body: data, timeoutMs: 15000 }); }

  // Shifts / Dienstplan
  function getShiftTypes(all = false) {
    return request(`/shifts/types${all ? '?all=true' : ''}`);
  }
  function createShiftType(data) {
    return request('/shifts/types', { method: 'POST', body: data });
  }
  function updateShiftType(id, data) {
    return request(`/shifts/types/${id}`, { method: 'PATCH', body: data });
  }
  function deleteShiftType(id) {
    return request(`/shifts/types/${id}`, { method: 'DELETE' });
  }
  function getShiftEntries(start, end) {
    return request(`/shifts/entries?start=${start}&end=${end}`);
  }
  function createShiftEntry(data) {
    return request('/shifts/entries', { method: 'POST', body: data });
  }
  function deleteShiftEntry(id) {
    return request(`/shifts/entries/${id}`, { method: 'DELETE' });
  }

  return {
    getToken, getUserKey, isLoggedIn, login, logout, clearAuth,
    getDashboard,
    getShoppingItems, addShoppingItem, toggleShoppingItem, updateShoppingItem, deleteShoppingItem, clearCheckedItems,
    searchRecipes, getSavedRecipes, saveRecipe, deleteRecipe, toggleFavorite, addRecipeToShopping,
    getChatHistory, sendMessage, sendMessageStream, transcribeVoice,
    getFeatures, toggleFeature,
    getCalendarToday, getCalendarWeek, createCalendarEvent,
    getTasks, createTask, updateTaskStatus, deleteTask,
    getMealPlanWeek, createMealPlan, deleteMealPlan,
    getDriveFiles, uploadFile,
    getGitHubLabels, getGitHubIssues, createGitHubIssue,
    getShiftTypes, createShiftType, updateShiftType, deleteShiftType,
    getShiftEntries, createShiftEntry, deleteShiftEntry,
    searchGlobal,
  };
})();
