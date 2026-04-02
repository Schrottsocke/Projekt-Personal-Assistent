/**
 * Dashboard View – Greeting, Events, Tasks, Shopping Preview
 */
const DashboardView = (() => {
  function getGreeting() {
    const h = new Date().getHours();
    if (h < 12) return 'Guten Morgen';
    if (h < 18) return 'Guten Tag';
    return 'Guten Abend';
  }

  function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
  }

  function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }

  function priorityBadge(p) {
    const map = { high: 'badge-error', medium: 'badge-warning', low: 'badge-success' };
    return `<span class="badge ${map[p] || 'badge-accent'} task-priority">${p || 'normal'}</span>`;
  }

  async function render(container) {
    const user = capitalize(Api.getUserKey());
    container.innerHTML = `
      <div class="greeting">${getGreeting()}, ${user}</div>
      <div class="greeting-sub">Hier ist dein Tagesüberblick</div>
      <div id="dashboard-content">
        <div class="skeleton skeleton-section-header"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-section-header"></div>
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-section-header"></div>
        <div class="skeleton skeleton-card"></div>
      </div>
    `;

    try {
      const data = await Api.getDashboard();
      renderContent(data);
    } catch (err) {
      document.getElementById('dashboard-content').innerHTML = `
        <div class="error-state">
          <p>${err.message}</p>
          <button class="btn btn-secondary" onclick="DashboardView.render(document.getElementById('view-container'))">
            Erneut versuchen
          </button>
        </div>
      `;
    }
  }

  function renderContent(data) {
    const el = document.getElementById('dashboard-content');
    if (!el) return;

    const events = (data.events_today || []).slice(0, 3);
    const tasks = (data.open_tasks || []).slice(0, 3);
    const shop = data.shopping_preview || {};
    const emails = data.unread_emails || 0;

    let html = '';

    // Email badge
    if (emails > 0) {
      html += `<div class="mb-16"><span class="badge badge-accent email-badge"><span class="material-symbols-outlined mi-sm">mail</span> ${emails} ungelesene E-Mail${emails > 1 ? 's' : ''}</span></div>`;
    }

    // Shifts today
    const shifts = (data.shifts_today || []).slice(0, 3);
    if (shifts.length > 0) {
      html += `<a class="section-header section-link" href="#/shifts"><span class="section-icon material-symbols-outlined">work</span> Dienste heute <span class="section-arrow">Verwalten &#8594;</span></a>`;
      shifts.forEach(s => {
        const color = s.shift_color || 'var(--accent)';
        html += `
          <div class="card" style="border-left:4px solid ${color}">
            <div class="event-time">${formatTime(s.start)}${s.end ? ' – ' + formatTime(s.end) : ''}</div>
            <div class="card-title"><span class="shift-badge" style="background:${color}22;color:${color}">${escapeHtml(s.shift_short_name || '')}</span> ${escapeHtml(s.summary || '')}</div>
            ${s.description ? `<div class="card-subtitle">${escapeHtml(s.description)}</div>` : ''}
          </div>
        `;
      });
    }

    // Events
    html += `<a class="section-header section-link" href="#/calendar"><span class="section-icon material-symbols-outlined">calendar_month</span> Termine heute <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
    if (events.length === 0) {
      html += `<div class="empty-state">Keine Termine heute</div>`;
    } else {
      events.forEach(e => {
        html += `
          <div class="card">
            <div class="event-time">${formatTime(e.start)}${e.end ? ' – ' + formatTime(e.end) : ''}</div>
            <div class="card-title">${escapeHtml(e.summary)}</div>
            ${e.location ? `<div class="card-subtitle">${escapeHtml(e.location)}</div>` : ''}
          </div>
        `;
      });
    }

    // Tasks
    html += `<a class="section-header section-link" href="#/tasks"><span class="section-icon material-symbols-outlined">check_circle</span> Offene Aufgaben <span class="badge badge-accent">${data.task_count || tasks.length}</span> <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
    if (tasks.length === 0) {
      html += `<div class="empty-state">Keine offenen Aufgaben</div>`;
    } else {
      tasks.forEach(t => {
        html += `
          <div class="card">
            <div class="flex-between">
              <div class="card-title">${escapeHtml(t.title)}</div>
              ${priorityBadge(t.priority)}
            </div>
            ${t.description ? `<div class="card-subtitle">${escapeHtml(t.description)}</div>` : ''}
          </div>
        `;
      });
    }

    // Shopping preview
    const total = shop.total || 0;
    const checked = shop.checked || 0;
    const pending = shop.pending || (total - checked);
    const pct = total > 0 ? Math.round((checked / total) * 100) : 0;

    html += `<a class="section-header section-link" href="#/shopping"><span class="section-icon material-symbols-outlined">shopping_cart</span> Einkaufsliste <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
    if (total === 0) {
      html += `<div class="empty-state">Einkaufsliste ist leer</div>`;
    } else {
      html += `
        <div class="card card-clickable" onclick="Router.navigate('#/shopping')">
          <div class="flex-between mb-8">
            <span>${pending} offen</span>
            <span class="card-subtitle">${checked}/${total} erledigt</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div class="progress-text">${pct}%</div>
        </div>
      `;
    }

    el.innerHTML = html;

    // Load extra previews (MealPlan, Drive) without blocking dashboard
    loadExtraPreviews(el);
  }

  async function loadExtraPreviews(container) {
    let extraHtml = '';

    const [mealsResult, driveResult] = await Promise.allSettled([
      Api.getMealPlanWeek(),
      Api.getDriveFiles(null, 2),
    ]);

    // MealPlan preview
    if (mealsResult.status === 'fulfilled') {
      try {
        const meals = mealsResult.value;
        const today = new Date().toISOString().slice(0, 10);
        const todayMeals = meals.filter(m => m.planned_date === today);

        extraHtml += `<a class="section-header section-link" href="#/mealplan"><span class="section-icon material-symbols-outlined">restaurant</span> Wochenplan <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
        if (todayMeals.length === 0) {
          extraHtml += `<div class="empty-state">Keine Mahlzeiten heute geplant</div>`;
        } else {
          todayMeals.forEach(m => {
            const typeLabels = { breakfast: 'Fruehstueck', lunch: 'Mittagessen', dinner: 'Abendessen' };
            extraHtml += `
              <div class="card card-clickable" onclick="Router.navigate('#/mealplan')">
                <div class="card-subtitle">${typeLabels[m.meal_type] || m.meal_type}</div>
                <div class="card-title">${escapeHtml(m.recipe_title)}</div>
              </div>
            `;
          });
        }
      } catch {
        // Render error – skip silently
      }
    }

    // Drive preview
    if (driveResult.status === 'fulfilled') {
      try {
        const driveData = driveResult.value;
        extraHtml += `<a class="section-header section-link" href="#/drive"><span class="section-icon material-symbols-outlined">folder</span> Drive <span class="section-arrow">Alle anzeigen &#8594;</span></a>`;
        if (driveData.connected === false) {
          extraHtml += `<div class="empty-state">Drive nicht verbunden</div>`;
        } else if ((driveData.files || []).length === 0) {
          extraHtml += `<div class="empty-state">Keine Dateien</div>`;
        } else {
          driveData.files.forEach(f => {
            extraHtml += `
              <div class="card card-clickable" onclick="Router.navigate('#/drive')">
                <div class="card-title">${escapeHtml(f.name)}</div>
                ${f.modified_time ? `<div class="card-subtitle">${new Date(f.modified_time).toLocaleDateString('de-DE', { day: 'numeric', month: 'short' })}</div>` : ''}
              </div>
            `;
          });
        }
      } catch {
        // Render error – skip silently
      }
    }

    if (extraHtml) {
      container.insertAdjacentHTML('beforeend', extraHtml);
    }
  }

  return { render };
})();
