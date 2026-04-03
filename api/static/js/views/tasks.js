/**
 * Tasks View – CRUD, Filter, Status Toggle, Recurring Tasks
 */
const TasksView = (() => {
  let tasks = [];
  let filterStatus = 'open';
  let filterPriority = 'all';
  let showForm = false;

  const RECURRENCE_LABELS = { daily: 'Täglich', weekly: 'Wöchentlich', monthly: 'Monatlich' };

  function priorityBadge(p) {
    const map = { high: 'badge-error', medium: 'badge-warning', low: 'badge-success' };
    return `<span class="badge ${map[p] || 'badge-accent'} task-priority">${escapeHtml(p || 'normal')}</span>`;
  }

  function statusBadge(s) {
    const map = { open: 'badge-warning', in_progress: 'badge-accent', done: 'badge-success' };
    const labels = { open: 'Offen', in_progress: 'In Arbeit', done: 'Erledigt' };
    return `<span class="badge ${map[s] || 'badge-accent'}">${labels[s] || s}</span>`;
  }

  function recurrenceBadge(r) {
    if (!r) return '';
    return `<span class="badge badge-accent recurrence-badge"><span class="material-symbols-outlined mi-sm">repeat</span> ${RECURRENCE_LABELS[r] || r}</span>`;
  }

  function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'short' });
  }

  function lastCompletedText(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    let ago;
    if (diffDays === 0) ago = 'heute';
    else if (diffDays === 1) ago = 'gestern';
    else ago = `vor ${diffDays} Tagen`;
    return `Zuletzt erledigt: ${ago}`;
  }

  async function render(container) {
    showForm = false;
    container.innerHTML = `
      <a class="view-back" href="#/dashboard"><span class="material-symbols-outlined mi-sm">arrow_back</span> Dashboard</a>
      <div class="section-header"><span class="section-icon material-symbols-outlined">check_circle</span> Aufgaben</div>
      <div class="flex-between mb-8">
        <div></div>
        <button class="btn btn-sm btn-primary" onclick="TasksView.toggleForm()">+ Aufgabe</button>
      </div>
      <div id="task-form-area"></div>
      <div class="task-filters mb-8">
        <div class="filter-group">
          <button class="filter-btn ${filterStatus === 'all' ? 'active' : ''}" onclick="TasksView.setFilter('status','all',this)">Alle</button>
          <button class="filter-btn ${filterStatus === 'open' ? 'active' : ''}" onclick="TasksView.setFilter('status','open',this)">Offen</button>
          <button class="filter-btn ${filterStatus === 'done' ? 'active' : ''}" onclick="TasksView.setFilter('status','done',this)">Erledigt</button>
        </div>
        <div class="filter-group">
          <button class="filter-btn ${filterPriority === 'all' ? 'active' : ''}" onclick="TasksView.setFilter('priority','all',this)">Alle</button>
          <button class="filter-btn ${filterPriority === 'high' ? 'active' : ''}" onclick="TasksView.setFilter('priority','high',this)">Hoch</button>
          <button class="filter-btn ${filterPriority === 'medium' ? 'active' : ''}" onclick="TasksView.setFilter('priority','medium',this)">Mittel</button>
          <button class="filter-btn ${filterPriority === 'low' ? 'active' : ''}" onclick="TasksView.setFilter('priority','low',this)">Niedrig</button>
        </div>
      </div>
      <div id="task-list">
        <div class="skeleton skeleton-task"></div>
        <div class="skeleton skeleton-task"></div>
        <div class="skeleton skeleton-task"></div>
      </div>
    `;
    await loadTasks();
  }

  async function loadTasks() {
    try {
      tasks = await Api.getTasks(true);
      renderList();
    } catch (err) {
      document.getElementById('task-list').innerHTML = `
        <div class="error-state"><p>${escapeHtml(err.message)}</p>
          <button class="btn btn-secondary" onclick="TasksView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

  function setFilter(type, value, el) {
    if (type === 'status') filterStatus = value;
    else filterPriority = value;

    // Update button states
    document.querySelectorAll('.task-filters .filter-group').forEach((group, i) => {
      if ((type === 'status' && i === 0) || (type === 'priority' && i === 1)) {
        group.querySelectorAll('.filter-btn').forEach(btn => {
          btn.classList.remove('active');
        });
      }
    });
    if (el) el.classList.add('active');

    renderList();
  }

  function renderList() {
    const el = document.getElementById('task-list');
    if (!el) return;

    let filtered = tasks;
    if (filterStatus !== 'all') {
      filtered = filtered.filter(t => t.status === filterStatus);
    }
    if (filterPriority !== 'all') {
      filtered = filtered.filter(t => t.priority === filterPriority);
    }

    if (filtered.length === 0) {
      const msg = tasks.length === 0 ? 'Keine Aufgaben vorhanden' : 'Keine passenden Aufgaben';
      el.innerHTML = `<div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted);display:block;margin-bottom:8px">check_circle</span>
        ${msg}
        ${tasks.length === 0 ? '<br><button class="btn btn-sm btn-primary mt-8" onclick="TasksView.toggleForm()">+ Neue Aufgabe</button>' : ''}
      </div>`;
      return;
    }

    el.innerHTML = filtered.map(t => {
      const isRecurring = !!t.recurrence;
      const lastDone = isRecurring ? lastCompletedText(t.last_completed_at) : '';
      return `
      <div class="task-item">
        <input type="checkbox" class="task-checkbox"
               ${t.status === 'done' ? 'checked' : ''}
               onchange="TasksView.toggleStatus(${t.id}, this.checked)">
        <div class="task-content ${t.status === 'done' ? 'task-done' : ''}">
          <div class="flex-between">
            <span class="task-title">${escapeHtml(t.title)}</span>
            <div class="task-badges">
              ${recurrenceBadge(t.recurrence)}
              ${priorityBadge(t.priority)}
              ${statusBadge(t.status)}
            </div>
          </div>
          ${t.description ? `<div class="card-subtitle">${escapeHtml(t.description)}</div>` : ''}
          <div class="task-meta-row">
            ${t.due_date ? `<span class="card-subtitle"><span class="material-symbols-outlined mi-sm">event</span> ${formatDate(t.due_date)}</span>` : ''}
            ${lastDone ? `<span class="task-last-completed"><span class="material-symbols-outlined mi-sm">check</span> ${lastDone}</span>` : ''}
          </div>
        </div>
        <button class="item-delete" onclick="TasksView.deleteTask(${t.id})" title="Löschen"><span class="material-symbols-outlined">delete</span></button>
      </div>
    `;
    }).join('');
  }

  function toggleForm() {
    showForm = !showForm;
    const el = document.getElementById('task-form-area');
    if (!el) return;
    if (!showForm) { el.innerHTML = ''; return; }

    el.innerHTML = `
      <div class="card event-create-form">
        <input type="text" id="task-title" placeholder="Aufgabe" class="mb-8">
        <input type="text" id="task-desc" placeholder="Beschreibung (optional)" class="mb-8">
        <div class="input-group mb-8">
          <select id="task-priority">
            <option value="medium">Mittel</option>
            <option value="high">Hoch</option>
            <option value="low">Niedrig</option>
          </select>
          <input type="date" id="task-due">
        </div>
        <div class="input-group mb-8">
          <select id="task-recurrence">
            <option value="">Einmalig</option>
            <option value="daily">Täglich</option>
            <option value="weekly">Wöchentlich</option>
            <option value="monthly">Monatlich</option>
          </select>
        </div>
        <div class="flex-between">
          <button class="btn btn-sm btn-secondary" onclick="TasksView.toggleForm()">Abbrechen</button>
          <button class="btn btn-sm btn-primary" onclick="TasksView.createTask()">Erstellen</button>
        </div>
      </div>
    `;
  }

  async function createTask() {
    const title = document.getElementById('task-title').value.trim();
    if (!title) { document.getElementById('task-title').classList.add('input-error'); return; }

    const desc = document.getElementById('task-desc').value.trim();
    const priority = document.getElementById('task-priority').value;
    const due = document.getElementById('task-due').value;
    const recurrence = document.getElementById('task-recurrence').value;

    const data = { title, priority };
    if (desc) data.description = desc;
    if (due) data.due_date = new Date(due).toISOString();
    if (recurrence) data.recurrence = recurrence;

    try {
      const newTask = await Api.createTask(data);
      tasks.unshift(newTask);
      showForm = false;
      document.getElementById('task-form-area').innerHTML = '';
      renderList();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  async function toggleStatus(id, checked) {
    const newStatus = checked ? 'done' : 'open';
    try {
      const updated = await Api.updateTaskStatus(id, newStatus);
      const idx = tasks.findIndex(t => t.id === id);
      if (updated && idx >= 0) tasks[idx] = updated;
      renderList();
    } catch (err) {
      alert('Fehler: ' + err.message);
      await loadTasks();
    }
  }

  async function deleteTask(id) {
    if (!confirm('Aufgabe löschen?')) return;
    try {
      await Api.deleteTask(id);
      tasks = tasks.filter(t => t.id !== id);
      renderList();
    } catch (err) {
      alert('Fehler beim Löschen: ' + err.message);
      await loadTasks();
    }
  }

  return { render, setFilter, toggleForm, createTask, toggleStatus, deleteTask };
})();
