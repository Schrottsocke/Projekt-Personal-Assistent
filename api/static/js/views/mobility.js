/**
 * Mobility View – Tagesfluss-Timeline und Fahrzeit-Rechner.
 */
const MobilityView = (() => {

  const TYPE_STYLES = {
    event: { icon: 'event', color: 'var(--accent)' },
    departure: { icon: 'directions_car', color: '#4caf50' },
    weather_warning: { icon: 'cloud', color: '#ff9800' },
  };

  async function render(container) {
    container.innerHTML = `
      <div class="view-header">
        <h2><span class="material-symbols-outlined">route</span> Mobilit\u00e4t</h2>
      </div>
      <div id="daily-flow-section">
        <div class="section-header">
          <span class="section-icon material-symbols-outlined">timeline</span> Tagesfluss
        </div>
        <div id="daily-flow-content">
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
        </div>
      </div>
      <div id="travel-calc-section" class="mt-24">
        <div class="section-header">
          <span class="section-icon material-symbols-outlined">directions_car</span> Fahrzeit berechnen
        </div>
        <div class="card">
          <div class="mb-8">
            <input type="text" id="travel-origin" class="input" placeholder="Startadresse">
          </div>
          <div class="mb-8">
            <input type="text" id="travel-destination" class="input" placeholder="Zieladresse">
          </div>
          <div class="mb-8">
            <select id="travel-profile" class="input">
              <option value="auto">Auto</option>
              <option value="fahrrad">Fahrrad</option>
              <option value="laufen">Zu Fu\u00df</option>
            </select>
          </div>
          <button class="btn btn-primary" id="travel-calc-btn" style="width:100%">
            <span class="material-symbols-outlined mi-sm">calculate</span> Berechnen
          </button>
          <div id="travel-result" class="mt-8"></div>
        </div>
      </div>
    `;

    document.getElementById('travel-calc-btn').addEventListener('click', calculateTravelTime);

    await loadDailyFlow();
  }

  async function loadDailyFlow() {
    const el = document.getElementById('daily-flow-content');
    if (!el) return;

    try {
      const data = await Api.get('/mobility/daily-flow');
      renderDailyFlow(el, data);
    } catch (err) {
      el.innerHTML = `
        <div class="error-state">
          <p>${err.message || 'Tagesfluss konnte nicht geladen werden'}</p>
          <button class="btn btn-secondary" onclick="MobilityView.render(document.getElementById('view-container'))">
            Erneut versuchen
          </button>
        </div>
      `;
    }
  }

  function renderDailyFlow(el, data) {
    if (!data.entries || data.entries.length === 0) {
      el.innerHTML = `<div class="empty-state">Keine Eintr\u00e4ge f\u00fcr heute</div>`;
      return;
    }

    let html = '';

    if (data.weather_summary) {
      html += `
        <div class="card" style="border-left:4px solid #ff9800">
          <div class="card-subtitle">\u2601\ufe0f Wetter</div>
          <div class="card-title">${escapeHtml(data.weather_summary)}</div>
        </div>
      `;
    }

    data.entries.forEach(entry => {
      const style = TYPE_STYLES[entry.type] || TYPE_STYLES.event;
      const icon = entry.icon || '';
      const materialIcon = style.icon;

      html += `
        <div class="card" style="border-left:4px solid ${style.color}">
          <div class="flex-between">
            <div>
              <div class="event-time">
                <span class="material-symbols-outlined mi-sm">${materialIcon}</span>
                ${escapeHtml(entry.time)}
              </div>
              <div class="card-title">${icon ? icon + ' ' : ''}${escapeHtml(entry.title)}</div>
              ${entry.detail ? `<div class="card-subtitle">${escapeHtml(entry.detail)}</div>` : ''}
            </div>
            <span class="badge badge-accent">${escapeHtml(entry.type)}</span>
          </div>
        </div>
      `;
    });

    el.innerHTML = html;
  }

  async function calculateTravelTime() {
    const origin = document.getElementById('travel-origin').value.trim();
    const destination = document.getElementById('travel-destination').value.trim();
    const profile = document.getElementById('travel-profile').value;
    const resultEl = document.getElementById('travel-result');

    if (!origin || !destination) {
      resultEl.innerHTML = `<div class="card-subtitle" style="color:var(--error)">Bitte Start und Ziel eingeben</div>`;
      return;
    }

    resultEl.innerHTML = `<div class="skeleton skeleton-card"></div>`;

    try {
      const data = await Api.post('/mobility/travel-time', { origin, destination, profile });
      resultEl.innerHTML = `
        <div class="card" style="border-left:4px solid var(--accent)">
          <div class="card-title">${escapeHtml(data.summary)}</div>
          <div class="flex-between mt-8">
            <span class="badge badge-accent">${data.duration_minutes} Min.</span>
            <span class="badge badge-accent">${data.distance_km} km</span>
          </div>
        </div>
      `;
    } catch (err) {
      resultEl.innerHTML = `
        <div class="card-subtitle" style="color:var(--error)">${err.message || 'Berechnung fehlgeschlagen'}</div>
      `;
    }
  }

  return { render };
})();
