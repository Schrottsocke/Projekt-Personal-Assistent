/**
 * DualMind Dienstplan-View – Diensttypen verwalten & Dienste eintragen
 */
const ShiftsView = (() => {
  let activeTab = 'types';
  let shiftTypes = [];
  let shiftEntries = [];
  let currentMonth = null; // Date object for displayed month
  let showTypeForm = false;
  let editingType = null; // null = create, object = edit

  const CATEGORIES = [
    { value: 'work', label: 'Arbeit', icon: 'work' },
    { value: 'free', label: 'Frei', icon: 'event_available' },
    { value: 'vacation', label: 'Urlaub', icon: 'beach_access' },
    { value: 'special', label: 'Sonderdienst', icon: 'star' },
  ];

  function categoryLabel(cat) {
    const c = CATEGORIES.find(x => x.value === cat);
    return c ? c.label : cat;
  }

  // ─── Render ───────────────────────────────────────────────

  async function render(container) {
    showTypeForm = false;
    editingType = null;
    if (!currentMonth) currentMonth = new Date();

    container.innerHTML = `
      <div class="flex-between mb-8">
        <div>
          <a href="#/calendar" class="btn btn-sm btn-ghost" style="margin-bottom:4px">
            <span class="mi-sm material-symbols-outlined">arrow_back</span> Kalender
          </a>
          <h2 style="margin:0">Dienstplan</h2>
        </div>
      </div>
      <div class="tabs mb-8">
        <button class="tab ${activeTab === 'types' ? 'active' : ''}"
                onclick="ShiftsView.switchTab('types')">Diensttypen</button>
        <button class="tab ${activeTab === 'calendar' ? 'active' : ''}"
                onclick="ShiftsView.switchTab('calendar')">Kalender</button>
      </div>
      <div id="shifts-content"><div class="loading"><div class="spinner"></div></div></div>
    `;

    await loadData();
  }

  function switchTab(tab) {
    activeTab = tab;
    showTypeForm = false;
    editingType = null;
    renderContent();
  }

  async function loadData() {
    try {
      shiftTypes = await Api.getShiftTypes(true);
    } catch (e) {
      shiftTypes = [];
    }
    renderContent();
  }

  function renderContent() {
    const el = document.getElementById('shifts-content');
    if (!el) return;
    if (activeTab === 'types') {
      renderTypes(el);
    } else {
      renderCalendar(el);
    }
  }

  // ─── Diensttypen Tab ──────────────────────────────────────

  function renderTypes(el) {
    let html = '';

    // Create / Edit Form
    if (showTypeForm) {
      html += renderTypeForm();
    } else {
      html += `<button class="btn btn-primary mb-8" onclick="ShiftsView.toggleTypeForm()">
        <span class="mi-sm material-symbols-outlined">add</span> Neuer Diensttyp
      </button>`;
    }

    // List
    const active = shiftTypes.filter(t => t.is_active);
    const inactive = shiftTypes.filter(t => !t.is_active);

    if (active.length === 0 && !showTypeForm) {
      html += `<div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:2rem;opacity:.5">work</span>
        <p>Noch keine Diensttypen angelegt.</p>
      </div>`;
    }

    active.forEach(t => { html += renderTypeCard(t); });

    if (inactive.length > 0) {
      html += `<h3 style="margin-top:24px;color:var(--text-secondary)">Inaktiv</h3>`;
      inactive.forEach(t => { html += renderTypeCard(t); });
    }

    el.innerHTML = html;
  }

  function renderTypeCard(t) {
    const timeStr = t.start_time && t.end_time
      ? `${t.start_time} – ${t.end_time}` : 'Keine Zeiten';
    const breakStr = t.break_minutes ? ` (${t.break_minutes} Min. Pause)` : '';
    const opacity = t.is_active ? '1' : '0.5';
    return `
      <div class="card shift-type-card" style="border-left:4px solid ${escapeHtml(t.color)};opacity:${opacity}">
        <div class="flex-between">
          <div>
            <span class="shift-badge" style="background:${escapeHtml(t.color)}22;color:${escapeHtml(t.color)}">
              ${escapeHtml(t.short_name)}
            </span>
            <strong>${escapeHtml(t.name)}</strong>
            <span class="card-subtitle" style="margin-left:8px">${escapeHtml(categoryLabel(t.category))}</span>
          </div>
          <div>
            <button class="btn btn-sm btn-ghost" onclick="ShiftsView.editType(${t.id})" title="Bearbeiten">
              <span class="mi-sm material-symbols-outlined">edit</span>
            </button>
            <button class="btn btn-sm btn-ghost" onclick="ShiftsView.deleteType(${t.id})" title="Loeschen"
                    style="color:var(--error)">
              <span class="mi-sm material-symbols-outlined">delete</span>
            </button>
          </div>
        </div>
        <div class="card-subtitle">${escapeHtml(timeStr)}${escapeHtml(breakStr)}</div>
        ${t.default_note ? `<div class="card-subtitle" style="margin-top:4px;font-style:italic">${escapeHtml(t.default_note)}</div>` : ''}
      </div>
    `;
  }

  function renderTypeForm() {
    const t = editingType || {};
    const isEdit = !!editingType;
    const title = isEdit ? 'Diensttyp bearbeiten' : 'Neuer Diensttyp';
    const btnLabel = isEdit ? 'Speichern' : 'Anlegen';

    return `
      <div class="card mb-8" id="shift-type-form">
        <h3 style="margin-top:0">${title}</h3>
        <div class="input-group">
          <div style="flex:2">
            <label>Name</label>
            <input id="st-name" class="input" value="${escapeHtml(t.name || '')}" placeholder="z.B. Fruhdienst">
          </div>
          <div style="flex:1">
            <label>Kuerzel</label>
            <input id="st-short" class="input" maxlength="10" value="${escapeHtml(t.short_name || '')}" placeholder="z.B. F">
          </div>
          <div style="flex:0 0 60px">
            <label>Farbe</label>
            <input id="st-color" type="color" value="${t.color || '#7c4dff'}" style="width:100%;height:38px;border:none;background:none;cursor:pointer">
          </div>
        </div>
        <div class="input-group" style="margin-top:8px">
          <div style="flex:1">
            <label>Start</label>
            <input id="st-start" type="time" class="input" value="${t.start_time || ''}">
          </div>
          <div style="flex:1">
            <label>Ende</label>
            <input id="st-end" type="time" class="input" value="${t.end_time || ''}">
          </div>
          <div style="flex:1">
            <label>Pause (Min.)</label>
            <input id="st-break" type="number" class="input" min="0" value="${t.break_minutes || 0}">
          </div>
        </div>
        <div class="input-group" style="margin-top:8px">
          <div style="flex:1">
            <label>Kategorie</label>
            <select id="st-category" class="input">
              ${CATEGORIES.map(c => `<option value="${c.value}" ${(t.category || 'work') === c.value ? 'selected' : ''}>${c.label}</option>`).join('')}
            </select>
          </div>
          <div style="flex:2">
            <label>Standard-Notiz</label>
            <input id="st-note" class="input" value="${escapeHtml(t.default_note || '')}" placeholder="Optional">
          </div>
        </div>
        <div style="margin-top:12px;display:flex;gap:8px">
          <button class="btn btn-primary" onclick="ShiftsView.saveType()">${btnLabel}</button>
          <button class="btn btn-secondary" onclick="ShiftsView.toggleTypeForm()">Abbrechen</button>
        </div>
      </div>
    `;
  }

  function toggleTypeForm() {
    showTypeForm = !showTypeForm;
    if (!showTypeForm) editingType = null;
    renderContent();
  }

  function editType(id) {
    editingType = shiftTypes.find(t => t.id === id) || null;
    showTypeForm = true;
    renderContent();
  }

  async function saveType() {
    const name = document.getElementById('st-name').value.trim();
    const short_name = document.getElementById('st-short').value.trim();
    if (!name || !short_name) {
      if (!name) document.getElementById('st-name').classList.add('input-error');
      if (!short_name) document.getElementById('st-short').classList.add('input-error');
      return;
    }

    const data = {
      name,
      short_name,
      color: document.getElementById('st-color').value,
      start_time: document.getElementById('st-start').value || null,
      end_time: document.getElementById('st-end').value || null,
      break_minutes: parseInt(document.getElementById('st-break').value) || 0,
      category: document.getElementById('st-category').value,
      default_note: document.getElementById('st-note').value.trim() || null,
    };

    try {
      if (editingType) {
        await Api.updateShiftType(editingType.id, data);
      } else {
        await Api.createShiftType(data);
      }
      showTypeForm = false;
      editingType = null;
      await loadData();
    } catch (e) {
      alert('Fehler: ' + e.message);
    }
  }

  async function deleteType(id) {
    if (!confirm('Diensttyp wirklich loeschen?')) return;
    try {
      await Api.deleteShiftType(id);
      await loadData();
    } catch (e) {
      alert('Fehler: ' + e.message);
    }
  }

  // ─── Kalender Tab ─────────────────────────────────────────

  async function renderCalendar(el) {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const monthName = currentMonth.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });

    // Load entries for this month
    const firstDay = `${year}-${String(month + 1).padStart(2, '0')}-01`;
    const lastDate = new Date(year, month + 1, 0).getDate();
    const lastDay = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDate).padStart(2, '0')}`;

    try {
      shiftEntries = await Api.getShiftEntries(firstDay, lastDay);
    } catch (e) {
      shiftEntries = [];
    }

    const activeTypes = shiftTypes.filter(t => t.is_active);

    let html = `
      <div class="flex-between mb-8">
        <button class="btn btn-sm btn-ghost" onclick="ShiftsView.prevMonth()">
          <span class="mi-sm material-symbols-outlined">chevron_left</span>
        </button>
        <strong>${escapeHtml(monthName)}</strong>
        <button class="btn btn-sm btn-ghost" onclick="ShiftsView.nextMonth()">
          <span class="mi-sm material-symbols-outlined">chevron_right</span>
        </button>
      </div>
    `;

    if (activeTypes.length === 0) {
      html += `<div class="empty-state">
        <p>Erstelle zuerst Diensttypen im Tab "Diensttypen".</p>
      </div>`;
      el.innerHTML = html;
      return;
    }

    // Day headers
    const dayLabels = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];
    html += '<div class="shift-month-grid">';
    dayLabels.forEach(d => {
      html += `<div class="shift-day-header">${d}</div>`;
    });

    // Calendar grid
    const firstDow = (new Date(year, month, 1).getDay() + 6) % 7; // Mon=0
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    // Empty cells before first day
    for (let i = 0; i < firstDow; i++) {
      html += '<div class="shift-day shift-day-empty"></div>';
    }

    for (let d = 1; d <= lastDate; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const dayEntries = shiftEntries.filter(e => e.date === dateStr);
      const isToday = dateStr === todayStr;

      html += `<div class="shift-day${isToday ? ' shift-day-today' : ''}" onclick="ShiftsView.openDayMenu('${dateStr}', event)">`;
      html += `<div class="shift-day-num">${d}</div>`;

      dayEntries.forEach(entry => {
        const color = entry.shift_type_color || '#7c4dff';
        const label = entry.shift_type_short_name || '?';
        html += `<div class="shift-badge" style="background:${escapeHtml(color)}30;color:${escapeHtml(color)};border:1px solid ${escapeHtml(color)}50"
                      title="${escapeHtml(entry.shift_type_name || '')}${entry.note ? ' – ' + escapeHtml(entry.note) : ''}"
                      onclick="event.stopPropagation();ShiftsView.removeEntry(${entry.id})">
          ${escapeHtml(label)}
        </div>`;
      });

      html += '</div>';
    }

    html += '</div>';

    // Quick-add legend
    html += '<div class="shift-legend">';
    activeTypes.forEach(t => {
      html += `<span class="shift-legend-item">
        <span class="shift-color-dot" style="background:${escapeHtml(t.color)}"></span>
        ${escapeHtml(t.short_name)} = ${escapeHtml(t.name)}
      </span>`;
    });
    html += '</div>';

    el.innerHTML = html;
  }

  function prevMonth() {
    currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
    renderContent();
  }

  function nextMonth() {
    currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);
    renderContent();
  }

  function openDayMenu(dateStr, evt) {
    // Remove existing popover
    const existing = document.getElementById('shift-day-popover');
    if (existing) existing.remove();

    const activeTypes = shiftTypes.filter(t => t.is_active);
    if (activeTypes.length === 0) return;

    const dayLabel = new Date(dateStr + 'T00:00:00').toLocaleDateString('de-DE', {
      weekday: 'short', day: 'numeric', month: 'short',
    });

    let popHtml = `<div id="shift-day-popover" class="shift-popover">
      <div class="shift-popover-title">${escapeHtml(dayLabel)}</div>`;
    activeTypes.forEach(t => {
      popHtml += `<button class="shift-popover-item" onclick="ShiftsView.addEntry('${dateStr}', ${t.id})">
        <span class="shift-color-dot" style="background:${escapeHtml(t.color)}"></span>
        ${escapeHtml(t.short_name)} – ${escapeHtml(t.name)}
      </button>`;
    });
    popHtml += `<button class="shift-popover-item shift-popover-close" onclick="document.getElementById('shift-day-popover').remove()">
      Abbrechen
    </button></div>`;

    document.body.insertAdjacentHTML('beforeend', popHtml);

    // Position popover near click
    const pop = document.getElementById('shift-day-popover');
    const rect = evt.currentTarget.getBoundingClientRect();
    pop.style.top = Math.min(rect.bottom + 4, window.innerHeight - pop.offsetHeight - 8) + 'px';
    pop.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - pop.offsetWidth - 8)) + 'px';

    // Close on outside click
    setTimeout(() => {
      document.addEventListener('click', function handler(e) {
        if (!pop.contains(e.target)) {
          pop.remove();
          document.removeEventListener('click', handler);
        }
      });
    }, 10);
  }

  async function addEntry(dateStr, typeId) {
    const pop = document.getElementById('shift-day-popover');
    if (pop) pop.remove();

    try {
      await Api.createShiftEntry({ shift_type_id: typeId, date: dateStr });
      await renderCalendar(document.getElementById('shifts-content'));
    } catch (e) {
      alert('Fehler: ' + e.message);
    }
  }

  async function removeEntry(entryId) {
    try {
      await Api.deleteShiftEntry(entryId);
      await renderCalendar(document.getElementById('shifts-content'));
    } catch (e) {
      alert('Fehler: ' + e.message);
    }
  }

  return {
    render, switchTab, toggleTypeForm, editType, saveType, deleteType,
    prevMonth, nextMonth, openDayMenu, addEntry, removeEntry,
  };
})();
