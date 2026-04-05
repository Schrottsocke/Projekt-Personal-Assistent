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
      <div class="weather-current-card card">
        <div class="weather-current-main">
          <div class="weather-current-icon">
            <span class="material-symbols-outlined">${icon}</span>
          </div>
          <div class="weather-current-temp">${c.temp_c}\u00b0C</div>
        </div>
        <div class="weather-current-location">${escapeHtml(c.location)}</div>
        <div class="weather-current-desc">${escapeHtml(c.description)}</div>
        <div class="weather-current-feels">Gef\u00fchlt ${c.feels_like_c}\u00b0C</div>
        <div class="weather-detail-grid">
          <div class="weather-detail-item">
            <span class="material-symbols-outlined mi-sm">thermostat</span>
            <span>${c.min_temp_c}\u00b0 \u2013 ${c.max_temp_c}\u00b0</span>
          </div>
          <div class="weather-detail-item">
            <span class="material-symbols-outlined mi-sm">water_drop</span>
            <span>${c.humidity}%</span>
          </div>
          <div class="weather-detail-item">
            <span class="material-symbols-outlined mi-sm">air</span>
            <span>${c.wind_kmph} km/h</span>
          </div>
        </div>
      </div>
    `;

    if (data.forecast && data.forecast.length > 0) {
      html += `<div class="section-header"><span class="section-icon material-symbols-outlined">calendar_month</span> Vorhersage</div>`;
      html += `<div class="weather-forecast-grid">`;
      data.forecast.forEach(day => {
        const dayIcon = weatherIcon(day.description);
        const dateStr = new Date(day.date).toLocaleDateString('de-DE', { weekday: 'short', day: 'numeric', month: 'short' });
        html += `
          <div class="card weather-forecast-card">
            <div class="weather-forecast-day">${dateStr}</div>
            <span class="material-symbols-outlined weather-forecast-icon">${dayIcon}</span>
            <div class="weather-forecast-temps">
              <span class="weather-forecast-max">${day.max_temp_c}\u00b0</span>
              <span class="weather-forecast-min">${day.min_temp_c}\u00b0</span>
            </div>
            <div class="weather-forecast-desc">${escapeHtml(day.description || '')}</div>
          </div>
        `;
      });
      html += `</div>`;
    }

    el.innerHTML = html;
  }

  return { render };
})();
