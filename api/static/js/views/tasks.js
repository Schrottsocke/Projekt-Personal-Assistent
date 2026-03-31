/**
 * Tasks View – CRUD, Filter, Status Toggle
 */
const TasksView = (() => {
  let tasks = [];
  let filterStatus = 'open';
  let filterPriority = 'all';
  let showForm = false;

  function priorityBadge(p) {
    const map = { high: 'badge-error', medium: 'badge-warning', low: 'badge-success' };
    return `<span class="badge ${map[p] || 'badge-accent'} task-priority">${escapeHtml(p || 'normal')}</span>`;
  }

  function statusBadge(s) {
    const map = { open: 'badge-warning', in_progress: 'badge-accent', done: 'badge-success' };
    const labels = { open: 'Offen', in_progress: 'In Arbeit', done: 'Erledigt' };
    return `<span class="badge ${map[s] || 'badge-accent'}">${labels[s] || s}</span>`;
  }

  function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'short' });
  }

  async function render(container) {
    showForm = false;
    container.innerHTML = `
      <a class="view-back" href="#/dashboard">&#8592; Dashboard</a>
      <div class="section-header"><span class="section-icon">&#9745;</span> Aufgaben</div>
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
      <div id="task-list"><div class="loading"><div class="spinner"></div> Laden…</div></div>
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
      el.innerHTML = `<div class="empty-state">${msg}</div>`;
      return;
    }

    el.innerHTML = filtered.map(t => `
      <div class="task-item">
        <input type="checkbox" class="task-checkbox"
               ${t.status === 'done' ? 'checked' : ''}
               onchange="TasksView.toggleStatus(${t.id}, this.checked)">
        <div class="task-content ${t.status === 'done' ? 'task-done' : ''}">
          <div class="flex-between">
            <span class="task-title">${escapeHtml(t.title)}</span>
            <div class="task-badges">
              ${priorityBadge(t.priority)}
              ${statusBadge(t.status)}
            </div>
          </div>
          ${t.description ? `<div class="card-subtitle">${escapeHtml(t.description)}</div>` : ''}
          ${t.due_date ? `<div class="card-subtitle mt-8">&#128197; ${formatDate(t.due_date)}</div>` : ''}
        </div>
        <button class="item-delete" onclick="TasksView.deleteTask(${t.id})" title="Loeschen">&#128465;</button>
      </div>
    `).join('');
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
          <select id="task-priority" style="width:100%;padding:10px;background:var(--bg-input);border:1px solid var(--border);border-radius:var(--radius-sm);color:var(--text-primary);font-size:0.9rem">
            <option value="medium">Mittel</option>
            <option value="high">Hoch</option>
            <option value="low">Niedrig</option>
          </select>
          <input type="date" id="task-due" style="background:var(--bg-input);border:1px solid var(--border);border-radius:var(--radius-sm);color:var(--text-primary);padding:10px;font-size:0.9rem">
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
    if (!title) { alert('Bitte Titel angeben.'); return; }

    const desc = document.getElementById('task-desc').value.trim();
    const priority = document.getElementById('task-priority').value;
    const due = document.getElementById('task-due').value;

    const data = { title, priority };
    if (desc) data.description = desc;
    if (due) data.due_date = new Date(due).toISOString();

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
      if (idx >= 0) tasks[idx] = updated;
      renderList();
    } catch (err) {
      alert('Fehler: ' + err.message);
      await loadTasks();
    }
  }

  async function deleteTask(id) {
    if (!confirm('Aufgabe loeschen?')) return;
    try {
      await Api.deleteTask(id);
      tasks = tasks.filter(t => t.id !== id);
      renderList();
    } catch (err) {
      alert('Fehler: ' + err.message);
    }
  }

  return { render, setFilter, toggleForm, createTask, toggleStatus, deleteTask };
})();
