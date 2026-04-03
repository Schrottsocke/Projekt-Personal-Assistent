/**
 * DualMind Follow-ups View
 * Zeigt Follow-ups mit Status-Filter, Faelligkeits-Anzeige und Erstellformular.
 */
const FollowUpsView = (() => {
  let followups = [];
  let activeStatus = 'open';
  let loading = false;
  let container = null;

  const TYPE_META = {
    email:      { icon: 'mail',        label: 'E-Mail',   color: 'var(--accent)' },
    commitment: { icon: 'handshake',   label: 'Zusage',   color: 'var(--warning)' },
    task:       { icon: 'check_circle', label: 'Aufgabe', color: 'var(--success)' },
  };

  const STATUS_META = {
    open:      { label: 'Offen',      class: 'badge-accent' },
    done:      { label: 'Erledigt',   class: 'badge-success' },
    cancelled: { label: 'Abgebrochen', class: 'badge' },
  };

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function isDue(dateStr) {
    if (!dateStr) return false;
    return dateStr <= new Date().toISOString().slice(0, 10);
  }

  async function loadFollowups() {
    loading = true;
    renderList();
    try {
      const params = new URLSearchParams();
      if (activeStatus) params.set('status', activeStatus);
      followups = await Api.get(`/followups?${params}`);
    } catch (e) {
      followups = [];
    }
    loading = false;
    renderList();
  }

  function renderList() {
    if (!container) return;

    const statusFilters = [
      { key: 'open', label: 'Offen' },
      { key: 'done', label: 'Erledigt' },
      { key: 'cancelled', label: 'Abgebrochen' },
      { key: '', label: 'Alle' },
    ];

    const listHtml = followups.length === 0
      ? `<p class="empty-state">${loading ? 'Lade...' : 'Keine Follow-ups gefunden.'}</p>`
      : followups.map(f => {
        const meta = TYPE_META[f.type] || { icon: 'flag', label: f.type, color: 'var(--text-muted)' };
        const sMeta = STATUS_META[f.status] || { label: f.status, class: 'badge' };
        const due = isDue(f.due_date);
        return `
          <div class="card" style="margin-bottom:8px;${due && f.status === 'open' ? 'border-left:3px solid var(--error)' : ''}">
            <div style="display:flex;align-items:center;gap:12px">
              <span class="material-symbols-outlined" style="font-size:28px;color:${meta.color}">${meta.icon}</span>
              <div style="flex:1;min-width:0">
                <strong>${Utils.escapeHtml(f.title)}</strong>
                <div class="text-muted" style="font-size:0.85rem">
                  ${meta.label}${f.due_date ? ` &middot; Faellig: ${formatDate(f.due_date)}` : ''}
                  ${due && f.status === 'open' ? ' <span style="color:var(--error);font-weight:600">Ueberfaellig</span>' : ''}
                </div>
                ${f.reference ? `<div class="text-muted" style="font-size:0.8rem">Ref: ${Utils.escapeHtml(f.reference)}</div>` : ''}
                ${f.notes ? `<div class="text-muted" style="font-size:0.8rem">${Utils.escapeHtml(f.notes)}</div>` : ''}
              </div>
              <span class="${sMeta.class}">${sMeta.label}</span>
              ${f.status === 'open' ? `<button class="btn btn-sm btn-success followup-done-btn" data-id="${f.id}" title="Erledigt">
                <span class="material-symbols-outlined" style="font-size:18px">check</span>
              </button>` : ''}
            </div>
          </div>
        `;
      }).join('');

    container.innerHTML = `
      <div class="view-header">
        <h2>Follow-ups</h2>
        <button class="btn btn-primary btn-sm" id="followup-add-btn">
          <span class="material-symbols-outlined">add</span> Neu
        </button>
      </div>
      <div class="notification-filter-row" style="margin-bottom:16px">
        ${statusFilters.map(s => `
          <button class="filter-chip ${activeStatus === s.key ? 'active' : ''}"
                  data-status="${s.key}">${s.label}</button>
        `).join('')}
      </div>
      <div id="followups-list">${listHtml}</div>
      <div id="followup-form-area"></div>
    `;

    // Event: Status-Filter
    container.querySelectorAll('.filter-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        activeStatus = btn.dataset.status;
        loadFollowups();
      });
    });

    // Event: Erledigt-Buttons
    container.querySelectorAll('.followup-done-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        try {
          await Api.patch(`/followups/${btn.dataset.id}`, { status: 'done' });
          await loadFollowups();
        } catch (err) {
          alert('Fehler beim Aktualisieren.');
        }
      });
    });

    // Event: Neu
    container.querySelector('#followup-add-btn')?.addEventListener('click', showCreateForm);
  }

  function showCreateForm() {
    const area = container.querySelector('#followup-form-area');
    if (!area) return;
    area.innerHTML = `
      <div class="card" style="margin-top:16px">
        <h3>Neues Follow-up</h3>
        <form id="followup-form">
          <div class="form-group">
            <label>Typ *</label>
            <select class="input" name="type" required>
              <option value="email">E-Mail</option>
              <option value="commitment">Zusage</option>
              <option value="task">Aufgabe</option>
            </select>
          </div>
          <div class="form-group"><label>Titel *</label><input class="input" name="title" required></div>
          <div class="form-group"><label>Referenz</label><input class="input" name="reference" placeholder="z.B. E-Mail-Betreff"></div>
          <div class="form-group"><label>Faellig am</label><input class="input" name="due_date" type="date"></div>
          <div class="form-group"><label>Notizen</label><textarea class="input" name="notes" rows="3"></textarea></div>
          <button type="submit" class="btn btn-primary">Speichern</button>
          <button type="button" class="btn" id="followup-cancel">Abbrechen</button>
        </form>
      </div>
    `;
    area.querySelector('#followup-cancel')?.addEventListener('click', () => { area.innerHTML = ''; });
    area.querySelector('#followup-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const data = {
        type: fd.get('type'),
        title: fd.get('title'),
        reference: fd.get('reference') || null,
        due_date: fd.get('due_date') || null,
        notes: fd.get('notes') || null,
      };
      try {
        await Api.post('/followups', data);
        area.innerHTML = '';
        await loadFollowups();
      } catch (err) {
        alert('Fehler beim Erstellen.');
      }
    });
  }

  async function render(c) {
    container = c;
    container.innerHTML = '<p class="empty-state">Lade Follow-ups...</p>';
    await loadFollowups();
  }

  return { render };
})();
