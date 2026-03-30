/**
 * DualMind API Client – JWT Auth, Auto-Refresh, Error Handling
 */
const Api = (() => {
  const TOKEN_KEY = 'dm_access_token';
  const REFRESH_KEY = 'dm_refresh_token';
  const USER_KEY = 'dm_user_key';

  let _refreshing = null;

  function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
  function getRefreshToken() { return sessionStorage.getItem(REFRESH_KEY); }
  function getUserKey() { return sessionStorage.getItem(USER_KEY); }

  function saveAuth(data) {
    sessionStorage.setItem(TOKEN_KEY, data.access_token);
    sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
    sessionStorage.setItem(USER_KEY, data.user_key);
  }

  function clearAuth() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
    sessionStorage.removeItem(USER_KEY);
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
    const { body, method = 'GET', noAuth = false } = options;

    const headers = { 'Content-Type': 'application/json' };
    if (!noAuth) {
      const token = getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    const fetchOpts = { method, headers };
    if (body !== undefined) fetchOpts.body = JSON.stringify(body);

    let res = await fetch(path, fetchOpts);

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
      throw new Error(err.detail || `HTTP ${res.status}`);
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
    return request('/chat/message', { method: 'POST', body: { message } });
  }

  // Features
  function getFeatures() { return request('/features'); }
  function toggleFeature(featureId) {
    return request(`/features/${featureId}/toggle`, { method: 'POST' });
  }

  return {
    getToken, getUserKey, isLoggedIn, login, logout, clearAuth,
    getDashboard,
    getShoppingItems, addShoppingItem, toggleShoppingItem, deleteShoppingItem, clearCheckedItems,
    searchRecipes, getSavedRecipes, saveRecipe, deleteRecipe, toggleFavorite, addRecipeToShopping,
    getChatHistory, sendMessage,
    getFeatures, toggleFeature,
  };
})();
