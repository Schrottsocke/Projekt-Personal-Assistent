/**
 * DualMind Dienstplan-View – Diensttypen, Kalender mit Tracking, Monatsauswertung
 */
const ShiftsView = (() => {
  let activeTab = 'types';
  let shiftTypes = [];
  let shiftEntries = [];
  let currentMonth = null;
  let showTypeForm = false;
  let editingType = null;
  let reportMonth = null; // YYYY-MM for report tab
  let reportData = null;

  const CATEGORIES = [
    { value: 'work', label: 'Arbeit', icon: 'work' },
    { value: 'free', label: 'Frei', icon: 'event_available' },
    { value: 'vacation', label: 'Urlaub', icon: 'beach_access' },
    { value: 'special', label: 'Sonderdienst', icon: 'star' },
  ];

  const STATUS_META = {
    pending:   { label: 'Offen',      icon: 'schedule',        color: 'var(--warning)' },
    confirmed: { label: 'Bestätigt',  icon: 'check_circle',    color: 'var(--success)' },
    deviation: { label: 'Abweichung', icon: 'error_outline',   color: '#ff9800' },
    cancelled: { label: 'Ausgefallen',icon: 'cancel',          color: 'var(--text-muted)' },
  };

  function categoryLabel(cat) {
    const c = CATEGORIES.find(x => x.value === cat);
    return c ? c.label : cat;
  }

  function statusMeta(s) {
    return STATUS_META[s] || STATUS_META.pending;
  }

  function fmtDuration(minutes) {
    if (minutes == null) return '–';
    const h = Math.floor(Math.abs(minutes) / 60);
    const m = Math.abs(minutes) % 60;
    const sign = minutes < 0 ? '-' : '';
    return `${sign}${h}h ${m > 0 ? m + 'min' : ''}`.trim();
  }

  function fmtDate(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' });
  }

  // ─── Render ───────────────────────────────────────────────

  async function render(container) {
    showTypeForm = false;
    editingType = null;
    if (!currentMonth) currentMonth = new Date();
    if (!reportMonth) {
      const now = new Date();
      reportMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    }

    container.innerHTML = `
      <div class="flex-between mb-8">
        <div>
          <a href="#/mehr" class="btn btn-sm btn-ghost" style="margin-bottom:4px">
            <span class="mi-sm material-symbols-outlined">arrow_back</span> Mehr
          </a>
          <h2 style="margin:0">Dienstplan</h2>
        </div>
      </div>
      <div class="tabs mb-8" id="shifts-tabs">
        <button class="tab ${activeTab === 'types' ? 'active' : ''}" data-tab="types"
                onclick="ShiftsView.switchTab('types')">Diensttypen</button>
        <button class="tab ${activeTab === 'calendar' ? 'active' : ''}" data-tab="calendar"
                onclick="ShiftsView.switchTab('calendar')">Kalender</button>
        <button class="tab ${activeTab === 'report' ? 'active' : ''}" data-tab="report"
                onclick="ShiftsView.switchTab('report')">Auswertung</button>
      </div>
      <div id="shifts-content"><div class="loading"><div class="spinner"></div></div></div>
    `;

    await loadData();
  }

  async function switchTab(tab) {
    activeTab = tab;
    showTypeForm = false;
    editingType = null;
    updateTabButtons();
    await renderContent();
  }

  function updateTabButtons() {
    document.querySelectorAll('#shifts-tabs .tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === activeTab);
    });
  }

  async function loadData() {
    try {
      shiftTypes = await Api.getShiftTypes(true);
    } catch (e) {
      shiftTypes = [];
    }
    await renderContent();
  }

  async function renderContent() {
    const el = document.getElementById('shifts-content');
    if (!el) return;
    if (activeTab === 'types') {
      renderTypes(el);
    } else if (activeTab === 'calendar') {
      await renderCalendar(el);
    } else if (activeTab === 'report') {
      await renderReport(el);
    }
  }

  // ─── Diensttypen Tab ──────────────────────────────────────

  function renderTypes(el) {
    let html = '';

    if (showTypeForm) {
      html += renderTypeForm();
    } else {
      html += `<button class="btn btn-primary mb-8" onclick="ShiftsView.toggleTypeForm()">
        <span class="mi-sm material-symbols-outlined">add</span> Neuer Diensttyp
      </button>`;
    }

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
      Toast.show('Fehler: ' + e.message);
    }
  }

  async function deleteType(id) {
    if (!confirm('Diensttyp wirklich loeschen?')) return;
    try {
      await Api.deleteShiftType(id);
      await loadData();
    } catch (e) {
      Toast.show('Fehler: ' + e.message);
    }
  }

  // ─── Kalender Tab ─────────────────────────────────────────

  async function renderCalendar(el) {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const monthName = currentMonth.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });

    el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

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

    const dayLabels = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];
    html += '<div class="shift-month-grid">';
    dayLabels.forEach(d => {
      html += `<div class="shift-day-header">${d}</div>`;
    });

    const firstDow = (new Date(year, month, 1).getDay() + 6) % 7;
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

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
        const st = statusMeta(entry.confirmation_status || 'pending');
        const statusIcon = entry.confirmation_status && entry.confirmation_status !== 'pending'
          ? `<span class="material-symbols-outlined" style="font-size:10px;color:${st.color}">${st.icon}</span>` : '';
        html += `<div class="shift-badge" style="background:${escapeHtml(color)}30;color:${escapeHtml(color)};border:1px solid ${escapeHtml(color)}50"
                      title="${escapeHtml(entry.shift_type_name || '')} – ${st.label}${entry.note ? ' – ' + escapeHtml(entry.note) : ''}"
                      onclick="event.stopPropagation();ShiftsView.openEntryAction(${entry.id})">
          ${escapeHtml(label)}${statusIcon}
        </div>`;
      });

      html += '</div>';
    }

    html += '</div>';

    // Legend
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

    const pop = document.getElementById('shift-day-popover');
    const rect = evt.currentTarget.getBoundingClientRect();
    pop.style.top = Math.min(rect.bottom + 4, window.innerHeight - pop.offsetHeight - 8) + 'px';
    pop.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - pop.offsetWidth - 8)) + 'px';

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
      Toast.show('Fehler: ' + e.message);
    }
  }

  // ─── Entry Action Modal (Confirm / Edit / Delete) ─────────

  function openEntryAction(entryId) {
    const entry = shiftEntries.find(e => e.id === entryId);
    if (!entry) return;

    closeModal();

    const st = statusMeta(entry.confirmation_status || 'pending');
    const typeName = entry.shift_type_name || 'Dienst';
    const dateLabel = fmtDate(entry.date);
    const plannedStart = entry.planned_start || entry.shift_type_start_time || '–';
    const plannedEnd = entry.planned_end || entry.shift_type_end_time || '–';
    const isPending = !entry.confirmation_status || entry.confirmation_status === 'pending';

    let html = `<div class="modal-overlay" id="shift-modal" onclick="if(event.target===this)ShiftsView.closeModal()">
      <div class="modal-content">
        <div class="modal-header">
          <div>
            <h3 style="margin:0">${escapeHtml(typeName)}</h3>
            <div class="card-subtitle">${escapeHtml(dateLabel)} &middot; Geplant: ${escapeHtml(plannedStart)} – ${escapeHtml(plannedEnd)}</div>
          </div>
          <button class="modal-close" onclick="ShiftsView.closeModal()">&times;</button>
        </div>

        <div class="shift-status-line">
          <span class="material-symbols-outlined" style="color:${st.color};font-size:18px">${st.icon}</span>
          <span style="color:${st.color};font-weight:600">${st.label}</span>
        </div>`;

    // Show actual times if recorded
    if (entry.actual_start || entry.actual_end) {
      html += `<div class="card" style="margin:12px 0;padding:12px">
        <div class="card-subtitle" style="margin-bottom:4px">Ist-Zeiten</div>
        <div>${entry.actual_start || '–'} – ${entry.actual_end || '–'}
        ${entry.actual_break_minutes ? ` (${entry.actual_break_minutes} Min. Pause)` : ''}</div>
        ${entry.actual_duration_minutes != null ? `<div class="card-subtitle">Dauer: ${fmtDuration(entry.actual_duration_minutes)}</div>` : ''}
        ${entry.delta_minutes != null ? `<div class="card-subtitle">Abweichung: ${fmtDuration(entry.delta_minutes)}</div>` : ''}
      </div>`;
    }

    if (entry.deviation_note) {
      html += `<div class="card-subtitle" style="margin:8px 0;font-style:italic">Notiz: ${escapeHtml(entry.deviation_note)}</div>`;
    }

    // Actions
    html += '<div class="shift-modal-actions">';

    if (isPending) {
      html += `
        <button class="btn btn-primary" onclick="ShiftsView.confirmEntry(${entry.id}, 'confirm')">
          <span class="mi-sm material-symbols-outlined">check</span> Normal beendet
        </button>
        <button class="btn btn-secondary" onclick="ShiftsView.showDeviationForm(${entry.id})">
          <span class="mi-sm material-symbols-outlined">edit_note</span> Abweichungen
        </button>
        <button class="btn btn-ghost" onclick="ShiftsView.confirmEntry(${entry.id}, 'cancel')" style="color:var(--text-secondary)">
          <span class="mi-sm material-symbols-outlined">block</span> Ausgefallen
        </button>`;
    } else {
      html += `
        <button class="btn btn-secondary" onclick="ShiftsView.showEditForm(${entry.id})">
          <span class="mi-sm material-symbols-outlined">edit</span> Zeiten bearbeiten
        </button>`;
    }

    html += `
        <button class="btn btn-ghost" onclick="ShiftsView.removeEntry(${entry.id})" style="color:var(--error)">
          <span class="mi-sm material-symbols-outlined">delete</span> Loeschen
        </button>
      </div>

      <div id="shift-modal-extra"></div>
    </div></div>`;

    document.body.insertAdjacentHTML('beforeend', html);
  }

  function closeModal() {
    const m = document.getElementById('shift-modal');
    if (m) m.remove();
  }

  async function confirmEntry(entryId, action) {
    try {
      await Api.confirmShiftEntry(entryId, { action });
      closeModal();
      Toast.show(action === 'cancel' ? 'Dienst als ausgefallen markiert' : 'Dienst bestätigt', 'success');
      await renderCalendar(document.getElementById('shifts-content'));
    } catch (e) {
      Toast.show('Fehler: ' + e.message);
    }
  }

  // ─── Deviation Form ───────────────────────────────────────

  function showDeviationForm(entryId) {
    const entry = shiftEntries.find(e => e.id === entryId);
    if (!entry) return;

    const extra = document.getElementById('shift-modal-extra');
    if (!extra) return;

    const defStart = entry.planned_start || entry.shift_type_start_time || '';
    const defEnd = entry.planned_end || entry.shift_type_end_time || '';

    extra.innerHTML = `
      <div class="card" style="margin-top:16px;padding:16px">
        <h4 style="margin:0 0 12px">Tatsächliche Zeiten</h4>
        <div class="input-group">
          <div style="flex:1">
            <label>Beginn</label>
            <input id="dev-start" type="time" class="input" value="${defStart}">
          </div>
          <div style="flex:1">
            <label>Ende</label>
            <input id="dev-end" type="time" class="input" value="${defEnd}">
          </div>
          <div style="flex:1">
            <label>Pause (Min.)</label>
            <input id="dev-break" type="number" class="input" min="0" value="0">
          </div>
        </div>
        <div style="margin-top:8px">
          <label>Notiz (optional)</label>
          <input id="dev-note" class="input" placeholder="Grund der Abweichung">
        </div>
        <div style="margin-top:12px;display:flex;gap:8px">
          <button class="btn btn-primary" onclick="ShiftsView.submitDeviation(${entryId})">Speichern</button>
          <button class="btn btn-ghost" onclick="document.getElementById('shift-modal-extra').innerHTML=''">Abbrechen</button>
        </div>
      </div>
    `;
  }

  async function submitDeviation(entryId) {
    const actual_start = document.getElementById('dev-start').value || null;
    const actual_end = document.getElementById('dev-end').value || null;
    const actual_break_minutes = parseInt(document.getElementById('dev-break').value) || 0;
    const deviation_note = document.getElementById('dev-note').value.trim() || null;

    if (!actual_start || !actual_end) {
      Toast.show('Bitte Start- und Endzeit angeben');
      return;
    }

    try {
      await Api.confirmShiftEntry(entryId, {
        action: 'deviation',
        actual_start,
        actual_end,
        actual_break_minutes,
        deviation_note,
      });
      closeModal();
      Toast.show('Abweichung gespeichert', 'success');
      await renderCalendar(document.getElementById('shifts-content'));
    } catch (e) {
      Toast.show('Fehler: ' + e.message);
    }
  }

  // ─── Edit Form (manual time editing) ──────────────────────

  function showEditForm(entryId) {
    const entry = shiftEntries.find(e => e.id === entryId);
    if (!entry) return;

    const extra = document.getElementById('shift-modal-extra');
    if (!extra) return;

    extra.innerHTML = `
      <div class="card" style="margin-top:16px;padding:16px">
        <h4 style="margin:0 0 12px">Ist-Zeiten bearbeiten</h4>
        <div class="input-group">
          <div style="flex:1">
            <label>Beginn</label>
            <input id="edit-start" type="time" class="input" value="${entry.actual_start || ''}">
          </div>
          <div style="flex:1">
            <label>Ende</label>
            <input id="edit-end" type="time" class="input" value="${entry.actual_end || ''}">
          </div>
          <div style="flex:1">
            <label>Pause (Min.)</label>
            <input id="edit-break" type="number" class="input" min="0" value="${entry.actual_break_minutes || 0}">
          </div>
        </div>
        <div style="margin-top:8px">
          <label>Notiz</label>
          <input id="edit-note" class="input" value="${escapeHtml(entry.deviation_note || '')}" placeholder="Optional">
        </div>
        <div style="margin-top:12px;display:flex;gap:8px">
          <button class="btn btn-primary" onclick="ShiftsView.submitEdit(${entryId})">Speichern</button>
          <button class="btn btn-ghost" onclick="document.getElementById('shift-modal-extra').innerHTML=''">Abbrechen</button>
        </div>
      </div>
    `;
  }

  async function submitEdit(entryId) {
    const data = {
      actual_start: document.getElementById('edit-start').value || null,
      actual_end: document.getElementById('edit-end').value || null,
      actual_break_minutes: parseInt(document.getElementById('edit-break').value) || 0,
      deviation_note: document.getElementById('edit-note').value.trim() || null,
    };

    try {
      await Api.updateShiftEntry(entryId, data);
      closeModal();
      Toast.show('Zeiten aktualisiert', 'success');
      await renderCalendar(document.getElementById('shifts-content'));
    } catch (e) {
      Toast.show('Fehler: ' + e.message);
    }
  }

  async function removeEntry(entryId) {
    if (!confirm('Eintrag wirklich loeschen?')) return;
    closeModal();
    try {
      await Api.deleteShiftEntry(entryId);
      await renderCalendar(document.getElementById('shifts-content'));
    } catch (e) {
      Toast.show('Fehler: ' + e.message);
    }
  }

  // ─── Report / Auswertung Tab ──────────────────────────────

  async function renderReport(el) {
    el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
      reportData = await Api.getShiftReport(reportMonth);
    } catch (e) {
      el.innerHTML = `<div class="empty-state"><p>Auswertung konnte nicht geladen werden.</p></div>`;
      return;
    }

    const [y, m] = reportMonth.split('-').map(Number);
    const monthLabel = new Date(y, m - 1, 1).toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });

    let html = `
      <div class="flex-between mb-8">
        <button class="btn btn-sm btn-ghost" onclick="ShiftsView.prevReportMonth()">
          <span class="mi-sm material-symbols-outlined">chevron_left</span>
        </button>
        <strong>${escapeHtml(monthLabel)}</strong>
        <button class="btn btn-sm btn-ghost" onclick="ShiftsView.nextReportMonth()">
          <span class="mi-sm material-symbols-outlined">chevron_right</span>
        </button>
      </div>`;

    const s = reportData.summary;
    if (s) {
      html += `
        <div class="shift-report-summary">
          <div class="shift-summary-card">
            <div class="shift-summary-value">${s.planned_hours != null ? s.planned_hours.toFixed(1) : '–'}h</div>
            <div class="shift-summary-label">Soll</div>
          </div>
          <div class="shift-summary-card">
            <div class="shift-summary-value">${s.actual_hours != null ? s.actual_hours.toFixed(1) : '–'}h</div>
            <div class="shift-summary-label">Ist</div>
          </div>
          <div class="shift-summary-card">
            <div class="shift-summary-value" style="color:${(s.delta_hours || 0) < 0 ? 'var(--error)' : 'var(--success)'}">${s.delta_hours != null ? (s.delta_hours >= 0 ? '+' : '') + s.delta_hours.toFixed(1) : '–'}h</div>
            <div class="shift-summary-label">Differenz</div>
          </div>
          <div class="shift-summary-card">
            <div class="shift-summary-value">${s.confirmed_count || 0}<span style="color:var(--text-muted);font-size:var(--text-sm)">/${(s.confirmed_count || 0) + (s.pending_count || 0) + (s.deviation_count || 0) + (s.cancelled_count || 0)}</span></div>
            <div class="shift-summary-label">Bestätigt</div>
          </div>
        </div>`;
    }

    // CSV export button
    html += `<div style="margin-bottom:12px;text-align:right">
      <a class="btn btn-sm btn-ghost" href="${Api.getShiftReportCsvUrl(reportMonth)}" target="_blank">
        <span class="mi-sm material-symbols-outlined">download</span> CSV Export
      </a>
    </div>`;

    // Table
    const entries = reportData.entries || [];
    if (entries.length === 0) {
      html += `<div class="empty-state"><p>Keine Einträge in diesem Monat.</p></div>`;
    } else {
      html += `<div class="shift-report-table-wrap"><table class="shift-report-table">
        <thead><tr>
          <th>Datum</th><th>Typ</th><th>Soll</th><th>Ist</th><th>Soll-Dauer</th><th>Ist-Dauer</th><th>Diff.</th><th>Status</th>
        </tr></thead><tbody>`;

      entries.forEach(e => {
        const st = statusMeta(e.confirmation_status || 'pending');
        const plannedTime = (e.planned_start && e.planned_end) ? `${e.planned_start}–${e.planned_end}` : '–';
        const actualTime = (e.actual_start && e.actual_end) ? `${e.actual_start}–${e.actual_end}` : '–';
        html += `<tr>
          <td>${fmtDate(e.date)}</td>
          <td><span class="shift-badge" style="background:${escapeHtml(e.shift_type_color || '#7c4dff')}22;color:${escapeHtml(e.shift_type_color || '#7c4dff')}">${escapeHtml(e.shift_type_short_name || '?')}</span></td>
          <td>${escapeHtml(plannedTime)}</td>
          <td>${escapeHtml(actualTime)}</td>
          <td>${fmtDuration(e.planned_duration_minutes)}</td>
          <td>${fmtDuration(e.actual_duration_minutes)}</td>
          <td style="color:${(e.delta_minutes || 0) < 0 ? 'var(--error)' : (e.delta_minutes || 0) > 0 ? 'var(--success)' : 'inherit'}">${e.delta_minutes != null ? (e.delta_minutes >= 0 ? '+' : '') + e.delta_minutes + ' min' : '–'}</td>
          <td><span class="shift-status-badge" style="color:${st.color}"><span class="material-symbols-outlined" style="font-size:14px">${st.icon}</span> ${st.label}</span></td>
        </tr>`;
      });

      html += '</tbody></table></div>';
    }

    el.innerHTML = html;
  }

  function prevReportMonth() {
    const [y, m] = reportMonth.split('-').map(Number);
    const d = new Date(y, m - 2, 1);
    reportMonth = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    renderContent();
  }

  function nextReportMonth() {
    const [y, m] = reportMonth.split('-').map(Number);
    const d = new Date(y, m, 1);
    reportMonth = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    renderContent();
  }

  return {
    render, switchTab, toggleTypeForm, editType, saveType, deleteType,
    prevMonth, nextMonth, openDayMenu, addEntry, removeEntry,
    openEntryAction, closeModal, confirmEntry,
    showDeviationForm, submitDeviation,
    showEditForm, submitEdit,
    prevReportMonth, nextReportMonth,
  };
})();
