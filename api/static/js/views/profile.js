/**
 * Profile View – Services, Features, Logout
 */
const ProfileView = (() => {

  async function render(container) {
    const user = Api.getUserKey() || '';
    const initial = user.charAt(0).toUpperCase();
    const name = user.charAt(0).toUpperCase() + user.slice(1);

    container.innerHTML = `
      <div class="profile-header">
        <div class="profile-avatar">${initial}</div>
        <div class="profile-name">${escapeHtml(name)}</div>
        <div class="profile-email">${escapeHtml(user)}@dualmind.app</div>
      </div>

      <div class="section-header"><span class="section-icon">&#128279;</span> Verbundene Dienste</div>
      <div id="services-list"><div class="loading"><div class="spinner"></div></div></div>

      <div class="section-header"><span class="section-icon">&#9881;</span> Features</div>
      <div id="features-list"><div class="loading"><div class="spinner"></div></div></div>

      <div class="section-header"><span class="section-icon">&#9881;</span> Einstellungen</div>
      <div class="settings-list">
        <div class="settings-item">
          <span>Briefing-Zeit</span>
          <span class="card-subtitle">08:00 Uhr</span>
        </div>
        <div class="settings-item">
          <span>Zeitzone</span>
          <span class="card-subtitle">Europe/Berlin</span>
        </div>
      </div>

      <div class="text-center mt-16">
        <button class="btn btn-danger" onclick="ProfileView.confirmLogout()">Abmelden</button>
      </div>
    `;

    loadServices();
    loadFeatures();
  }

  async function loadServices() {
    const el = document.getElementById('services-list');
    try {
      const data = await Api.getDashboard();
      el.innerHTML = `
        <div class="service-list">
          <div class="service-item">
            <div class="service-info">
              <span class="service-icon">&#128197;</span>
              <span class="service-name">Google Calendar</span>
            </div>
            <div class="status-dot ${data.calendar_connected ? 'connected' : 'disconnected'}"></div>
          </div>
          <div class="service-item">
            <div class="service-info">
              <span class="service-icon">&#9993;</span>
              <span class="service-name">Gmail</span>
            </div>
            <div class="status-dot ${data.email_connected ? 'connected' : 'disconnected'}"></div>
          </div>
        </div>
      `;
    } catch {
      el.innerHTML = '<div class="card-subtitle">Dienste konnten nicht geladen werden</div>';
    }
  }

  async function loadFeatures() {
    const el = document.getElementById('features-list');
    try {
      const features = await Api.getFeatures();
      if (features.length === 0) {
        el.innerHTML = '<div class="empty-state">Keine Features verfuegbar</div>';
        return;
      }
      el.innerHTML = '<div class="feature-list">' + features.map(f => `
        <div class="feature-item">
          <div class="feature-info">
            <span class="feature-icon">${f.emoji || '&#9881;'}</span>
            <div>
              <div class="feature-name">${escapeHtml(f.name)}</div>
              <div class="feature-desc">${escapeHtml(f.description)}${!f.available ? ' <span class="badge badge-warning">API-Keys fehlen</span>' : ''}</div>
            </div>
          </div>
          <label class="toggle">
            <input type="checkbox" ${f.enabled ? 'checked' : ''} ${!f.available ? 'disabled' : ''}
                   onchange="ProfileView.toggleFeature('${f.id}')">
            <span class="toggle-slider"></span>
          </label>
        </div>
      `).join('') + '</div>';
    } catch {
      el.innerHTML = '<div class="card-subtitle">Features konnten nicht geladen werden</div>';
    }
  }

  async function toggleFeature(featureId) {
    try {
      await Api.toggleFeature(featureId);
    } catch (err) {
      alert('Fehler: ' + err.message);
      loadFeatures(); // reload to reset toggle
    }
  }

  function confirmLogout() {
    if (confirm('Moechtest du dich wirklich abmelden?')) {
      Api.logout();
    }
  }

  return { render, toggleFeature, confirmLogout };
})();
