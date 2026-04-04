/**
 * Weather View – Aktuelles Wetter und Vorhersage.
 */
const WeatherView = (() => {
  let _location = localStorage.getItem('dm_weather_location') || 'Schwerin';

  function weatherIcon(desc) {
    const d = (desc || '').toLowerCase();
    if (d.includes('regen') || d.includes('rain')) return 'rainy';
    if (d.includes('schnee') || d.includes('snow')) return 'ac_unit';
    if (d.includes('wolke') || d.includes('cloud') || d.includes('bewölkt')) return 'cloud';
    if (d.includes('sonne') || d.includes('klar') || d.includes('sunny') || d.includes('clear')) return 'wb_sunny';
    if (d.includes('gewitter') || d.includes('thunder')) return 'thunderstorm';
    if (d.includes('nebel') || d.includes('fog')) return 'foggy';
    return 'thermostat';
  }

  async function render(container) {
    container.innerHTML = `
      <div class="view-header">
        <h2><span class="material-symbols-outlined">cloud</span> Wetter</h2>
      </div>
      <div class="mb-16">
        <div class="input-row">
          <input type="text" id="weather-location" class="input" placeholder="Ort eingeben..." value="${escapeHtml(_location)}">
          <button class="btn btn-primary" id="weather-search-btn">
            <span class="material-symbols-outlined mi-sm">search</span> Laden
          </button>
        </div>
      </div>
      <div id="weather-content">
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
      </div>
    `;

    document.getElementById('weather-search-btn').addEventListener('click', () => {
      const loc = document.getElementById('weather-location').value.trim();
      if (loc) {
        _location = loc;
        localStorage.setItem('dm_weather_location', loc);
        loadWeather();
      }
    });

    document.getElementById('weather-location').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const loc = e.target.value.trim();
        if (loc) {
          _location = loc;
          localStorage.setItem('dm_weather_location', loc);
          loadWeather();
        }
      }
    });

    await loadWeather();
  }

  async function loadWeather() {
    const el = document.getElementById('weather-content');
    if (!el) return;

    el.innerHTML = `
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;

    try {
      const data = await Api.get(`/weather/current?location=${encodeURIComponent(_location)}`);
      renderWeather(el, data);
    } catch (err) {
      el.innerHTML = `
        <div class="error-state">
          <p>${err.message || 'Wetter konnte nicht geladen werden'}</p>
          <button class="btn btn-secondary" onclick="WeatherView.render(document.getElementById('view-container'))">
            Erneut versuchen
          </button>
        </div>
      `;
    }
  }

  function renderWeather(el, data) {
    const c = data.current;
    const icon = weatherIcon(c.description);

    let html = `
      <div class="card" style="border-left:4px solid var(--accent)">
        <div class="flex-between mb-8">
          <div>
            <div class="card-title" style="font-size:1.2rem">
              <span class="material-symbols-outlined">${icon}</span>
              ${escapeHtml(c.location)}
            </div>
            <div class="card-subtitle">${escapeHtml(c.description)}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:2rem;font-weight:700;color:var(--accent)">${c.temp_c}\u00b0C</div>
            <div class="card-subtitle">gef\u00fchlt ${c.feels_like_c}\u00b0C</div>
          </div>
        </div>
        <div class="flex-between" style="gap:12px;flex-wrap:wrap">
          <span class="badge badge-accent">\U0001f4ca ${c.min_temp_c}\u00b0 \u2013 ${c.max_temp_c}\u00b0</span>
          <span class="badge badge-accent">\U0001f4a7 ${c.humidity}%</span>
          <span class="badge badge-accent">\U0001f4a8 ${c.wind_kmph} km/h</span>
        </div>
      </div>
    `;

    if (data.forecast && data.forecast.length > 0) {
      html += `<div class="section-header"><span class="section-icon material-symbols-outlined">calendar_month</span> Vorhersage</div>`;
      data.forecast.forEach(day => {
        const dayIcon = weatherIcon(day.description);
        const dateStr = new Date(day.date).toLocaleDateString('de-DE', { weekday: 'short', day: 'numeric', month: 'short' });
        html += `
          <div class="card">
            <div class="flex-between">
              <div>
                <div class="card-title">
                  <span class="material-symbols-outlined mi-sm">${dayIcon}</span>
                  ${dateStr}
                </div>
                <div class="card-subtitle">${escapeHtml(day.description || '')}</div>
              </div>
              <div style="text-align:right;white-space:nowrap">
                <span style="color:var(--text-secondary)">${day.min_temp_c}\u00b0</span>
                <span style="margin:0 4px">\u2013</span>
                <span style="font-weight:600">${day.max_temp_c}\u00b0</span>
              </div>
            </div>
          </div>
        `;
      });
    }

    el.innerHTML = html;
  }

  return { render };
})();
