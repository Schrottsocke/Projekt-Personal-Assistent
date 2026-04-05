/**
 * Family View – Haushalt-Verwaltung mit Mitgliedern, Listen, Aufgaben, Routinen
 */
const FamilyView = (() => {
  // ── State ──
  let workspaces = [];
  let currentWorkspace = null;
  let members = [];
  let activeTab = 'members';
  let taskFilter = 'all';

  // Tab-State
  let lists = [];
  let selectedList = null;
  let listItems = [];
  let tasks = [];
  let routines = [];

  // Form visibility flags
  let showWorkspaceForm = false;
  let showMemberForm = false;
  let showListForm = false;
  let showListItemForm = false;
  let showTaskForm = false;
  let showRoutineForm = false;

  // ── Helpers ──
  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(iso) {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString('de-DE', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return iso;
    }
  }

  function isOverdue(due_date, status) {
    if (!due_date || status === 'done') return false;
    return new Date(due_date) < new Date();
  }

  function roleBadge(role) {
    const map = { owner: 'badge-accent', admin: 'badge-warning', member: '' };
    const labels = { owner: 'Inhaber', admin: 'Admin', member: 'Mitglied' };
    const cls = map[role] || '';
    return `<span class="badge ${cls}">${esc(labels[role] || role)}</span>`;
  }

  function taskStatusBadge(task) {
    if (task.status === 'done') return `<span class="badge badge-success">Erledigt</span>`;
    if (isOverdue(task.due_date, task.status)) return `<span class="badge badge-error">Überfällig</span>`;
    return `<span class="badge badge-accent">Offen</span>`;
  }

  function intervalLabel(interval) {
    const map = { daily: 'Täglich', weekly: 'Wöchentlich', monthly: 'Monatlich' };
    return map[interval] || interval;
  }

  function memberName(userId) {
    if (!userId) return '–';
    const m = members.find(m => m.user_id === userId || m.id === userId);
    return m ? (m.display_name || m.username || m.user_id || String(m.id)) : String(userId);
  }

  function currentUserId() {
    // Try to get from JWT payload stored by Api
    try {
      const token = localStorage.getItem('access_token') || '';
      if (!token) return null;
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.sub || payload.user_id || null;
    } catch {
      return null;
    }
  }

  function isOwner() {
    const uid = currentUserId();
    if (!uid || !currentWorkspace) return false;
    const me = members.find(m => String(m.user_id) === String(uid));
    return me ? me.role === 'owner' : false;
  }

  // ── Render Entry ──

  async function render(container) {
    activeTab = 'members';
    showWorkspaceForm = false;
    showMemberForm = false;
    showListForm = false;
    showListItemForm = false;
    showTaskForm = false;
    showRoutineForm = false;
    selectedList = null;

    container.innerHTML = `
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">home</span> Haushalt
      </div>
      <div id="family-workspace-bar">
        <div class="skeleton" style="height:40px;border-radius:8px;margin-bottom:8px"></div>
      </div>
      <div id="family-content"></div>
    `;

    await loadWorkspaces(container);
  }

  async function loadWorkspaces(container) {
    try {
      workspaces = await Api.get('/family/workspaces');
    } catch (err) {
      workspaces = [];
      Toast.show('Fehler beim Laden der Haushalte: ' + err.message, 'error');
    }

    if (!currentWorkspace && workspaces.length > 0) {
      currentWorkspace = workspaces[0];
    } else if (currentWorkspace) {
      // refresh current workspace reference
      const updated = workspaces.find(w => w.id === currentWorkspace.id);
      if (updated) currentWorkspace = updated;
    }

    renderWorkspaceBar();
    if (currentWorkspace) {
      await loadMembers();
      renderView();
    } else {
      renderNoWorkspace();
    }
  }

  function renderWorkspaceBar() {
    const bar = document.getElementById('family-workspace-bar');
    if (!bar) return;

    let html = `<div class="family-workspace-bar">`;

    if (workspaces.length > 1) {
      html += `<select class="input" id="workspace-select" onchange="FamilyView.switchWorkspace(this.value)" style="flex:1;min-width:0">`;
      workspaces.forEach(w => {
        html += `<option value="${esc(w.id)}" ${currentWorkspace && currentWorkspace.id === w.id ? 'selected' : ''}>${esc(w.name)}</option>`;
      });
      html += `</select>`;
    } else if (currentWorkspace) {
      html += `<span class="family-workspace-name">${esc(currentWorkspace.name)}</span>`;
    }

    html += `<button class="btn btn-sm btn-secondary" onclick="FamilyView.toggleWorkspaceForm()" title="Neuer Haushalt">
      <span class="material-symbols-outlined mi-sm">add_home</span> Neuer Haushalt
    </button>`;
    html += `</div>`;

    if (showWorkspaceForm) {
      html += `
        <div class="card" style="margin-top:8px;padding:12px">
          <div class="form-group">
            <input type="text" id="new-workspace-name" class="input" placeholder="Haushalt-Name" />
          </div>
          <div class="form-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
            <button class="btn btn-secondary btn-sm" onclick="FamilyView.toggleWorkspaceForm()">Abbrechen</button>
            <button class="btn btn-primary btn-sm" onclick="FamilyView.createWorkspace()">Erstellen</button>
          </div>
        </div>`;
    }

    bar.innerHTML = html;
  }

  function renderNoWorkspace() {
    const content = document.getElementById('family-content');
    if (!content) return;
    content.innerHTML = `
      <div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-muted);display:block;margin-bottom:12px">home</span>
        <p>Noch kein Haushalt vorhanden.</p>
        <button class="btn btn-primary" onclick="FamilyView.toggleWorkspaceForm()">
          <span class="material-symbols-outlined mi-sm">add_home</span> Haushalt erstellen
        </button>
      </div>`;
  }

  function renderView() {
    const content = document.getElementById('family-content');
    if (!content) return;

    content.innerHTML = `
      <div class="family-tabs">
        <button class="family-tab ${activeTab === 'members' ? 'active' : ''}" onclick="FamilyView.switchTab('members')">
          <span class="material-symbols-outlined mi-sm">group</span> Mitglieder
        </button>
        <button class="family-tab ${activeTab === 'lists' ? 'active' : ''}" onclick="FamilyView.switchTab('lists')">
          <span class="material-symbols-outlined mi-sm">list</span> Listen
        </button>
        <button class="family-tab ${activeTab === 'tasks' ? 'active' : ''}" onclick="FamilyView.switchTab('tasks')">
          <span class="material-symbols-outlined mi-sm">check_circle</span> Aufgaben
        </button>
        <button class="family-tab ${activeTab === 'routines' ? 'active' : ''}" onclick="FamilyView.switchTab('routines')">
          <span class="material-symbols-outlined mi-sm">repeat</span> Routinen
        </button>
      </div>
      <div id="family-tab-content">
        <div class="skeleton" style="height:60px;border-radius:8px;margin-bottom:8px"></div>
        <div class="skeleton" style="height:60px;border-radius:8px;margin-bottom:8px"></div>
      </div>
    `;

    loadTabContent();
  }

  async function loadTabContent() {
    if (!currentWorkspace) return;

    try {
      if (activeTab === 'members') {
        await loadMembers();
        renderMembers();
      } else if (activeTab === 'lists') {
        await loadLists();
        renderLists();
      } else if (activeTab === 'tasks') {
        await loadTasks();
        renderTasks();
      } else if (activeTab === 'routines') {
        await loadRoutines();
        renderRoutines();
      }
    } catch (err) {
      const el = document.getElementById('family-tab-content');
      if (el) el.innerHTML = `<div class="error-state"><p>${esc(err.message)}</p>
        <button class="btn btn-secondary" onclick="FamilyView.reloadTab()">Erneut versuchen</button></div>`;
    }
  }

  // ── Workspace CRUD ──

  function toggleWorkspaceForm() {
    showWorkspaceForm = !showWorkspaceForm;
    renderWorkspaceBar();
  }

  async function createWorkspace() {
    const nameEl = document.getElementById('new-workspace-name');
    const name = nameEl ? nameEl.value.trim() : '';
    if (!name) {
      if (nameEl) nameEl.classList.add('input-error');
      return;
    }
    try {
      const ws = await Api.post('/family/workspaces', { name });
      workspaces.push(ws);
      currentWorkspace = ws;
      showWorkspaceForm = false;
      renderWorkspaceBar();
      await loadMembers();
      renderView();
      Toast.show('Haushalt erstellt', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function switchWorkspace(id) {
    const ws = workspaces.find(w => String(w.id) === String(id));
    if (!ws) return;
    currentWorkspace = ws;
    selectedList = null;
    showMemberForm = false;
    showListForm = false;
    showTaskForm = false;
    showRoutineForm = false;
    await loadMembers();
    renderView();
  }

  // ── Members ──

  async function loadMembers() {
    if (!currentWorkspace) return;
    members = await Api.get(`/family/workspaces/${currentWorkspace.id}/members`);
  }

  function renderMembers() {
    const el = document.getElementById('family-tab-content');
    if (!el) return;

    const canManage = isOwner();

    let html = `<div class="family-section-actions">`;
    if (canManage) {
      html += `<button class="btn btn-sm btn-primary" onclick="FamilyView.toggleMemberForm()">
        <span class="material-symbols-outlined mi-sm">person_add</span> Mitglied hinzufügen
      </button>`;
    }
    html += `</div>`;

    if (showMemberForm) {
      html += `
        <div class="card" style="margin-bottom:12px;padding:12px">
          <div class="form-group">
            <input type="text" id="new-member-key" class="input" placeholder="Benutzername oder E-Mail" />
          </div>
          <div class="form-group">
            <select id="new-member-role" class="input">
              <option value="member">Mitglied</option>
              <option value="admin">Admin</option>
              <option value="owner">Inhaber</option>
            </select>
          </div>
          <div class="form-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
            <button class="btn btn-secondary btn-sm" onclick="FamilyView.toggleMemberForm()">Abbrechen</button>
            <button class="btn btn-primary btn-sm" onclick="FamilyView.addMember()">Hinzufügen</button>
          </div>
        </div>`;
    }

    if (members.length === 0) {
      html += `<div class="empty-state">Keine Mitglieder gefunden.</div>`;
    } else {
      html += `<div class="family-member-list">`;
      members.forEach(m => {
        const name = m.display_name || m.username || m.user_id || String(m.id);
        html += `
          <div class="card family-member-item">
            <div class="family-member-avatar">
              <span class="material-symbols-outlined" style="font-size:28px;color:var(--accent)">person</span>
            </div>
            <div class="family-member-info">
              <span class="family-member-name">${esc(name)}</span>
              ${m.joined_at ? `<span class="text-muted" style="font-size:0.8rem">Seit ${formatDate(m.joined_at)}</span>` : ''}
            </div>
            <div class="family-member-actions">
              ${roleBadge(m.role)}
              ${canManage && m.role !== 'owner' ? `
                <select class="input" style="font-size:0.8rem;padding:2px 4px;height:auto"
                  onchange="FamilyView.changeRole(${esc(m.id)}, this.value)">
                  <option value="member" ${m.role === 'member' ? 'selected' : ''}>Mitglied</option>
                  <option value="admin" ${m.role === 'admin' ? 'selected' : ''}>Admin</option>
                  <option value="owner" ${m.role === 'owner' ? 'selected' : ''}>Inhaber</option>
                </select>
                <button class="btn btn-sm btn-danger" onclick="FamilyView.removeMember(${esc(m.id)})">
                  <span class="material-symbols-outlined mi-sm">person_remove</span>
                </button>
              ` : ''}
            </div>
          </div>`;
      });
      html += `</div>`;
    }

    el.innerHTML = html;
  }

  function toggleMemberForm() {
    showMemberForm = !showMemberForm;
    renderMembers();
  }

  async function addMember() {
    const keyEl = document.getElementById('new-member-key');
    const roleEl = document.getElementById('new-member-role');
    const user_key = keyEl ? keyEl.value.trim() : '';
    const role = roleEl ? roleEl.value : 'member';
    if (!user_key) {
      if (keyEl) keyEl.classList.add('input-error');
      return;
    }
    try {
      const m = await Api.post(`/family/workspaces/${currentWorkspace.id}/members`, { user_key, role });
      members.push(m);
      showMemberForm = false;
      renderMembers();
      Toast.show('Mitglied hinzugefügt', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function removeMember(memberId) {
    if (!confirm('Mitglied wirklich entfernen?')) return;
    try {
      await Api.delete(`/family/workspaces/${currentWorkspace.id}/members/${memberId}`);
      members = members.filter(m => m.id !== memberId);
      renderMembers();
      Toast.show('Mitglied entfernt', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function changeRole(memberId, role) {
    try {
      const updated = await Api.patch(`/family/workspaces/${currentWorkspace.id}/members/${memberId}`, { role });
      const idx = members.findIndex(m => m.id === memberId);
      if (idx >= 0 && updated) members[idx] = updated;
      renderMembers();
      Toast.show('Rolle aktualisiert', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  // ── Lists ──

  async function loadLists() {
    lists = await Api.get(`/family/workspaces/${currentWorkspace.id}/lists`);
    if (selectedList) {
      const found = lists.find(l => l.id === selectedList.id);
      if (found) selectedList = found;
      else selectedList = null;
    }
    if (selectedList) {
      listItems = await Api.get(`/family/lists/${selectedList.id}/items`);
    } else {
      listItems = [];
    }
  }

  function renderLists() {
    const el = document.getElementById('family-tab-content');
    if (!el) return;

    let html = `<div class="family-section-actions">
      <button class="btn btn-sm btn-primary" onclick="FamilyView.toggleListForm()">
        <span class="material-symbols-outlined mi-sm">playlist_add</span> Neue Liste
      </button>
    </div>`;

    if (showListForm) {
      html += `
        <div class="card" style="margin-bottom:12px;padding:12px">
          <div class="form-group">
            <input type="text" id="new-list-name" class="input" placeholder="Listen-Name" />
          </div>
          <div class="form-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
            <button class="btn btn-secondary btn-sm" onclick="FamilyView.toggleListForm()">Abbrechen</button>
            <button class="btn btn-primary btn-sm" onclick="FamilyView.createList()">Erstellen</button>
          </div>
        </div>`;
    }

    if (lists.length === 0) {
      html += `<div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted);display:block;margin-bottom:8px">list</span>
        Noch keine geteilten Listen.
      </div>`;
    } else {
      html += `<div class="family-list-sidebar">`;
      lists.forEach(l => {
        const active = selectedList && selectedList.id === l.id;
        html += `<button class="family-list-btn ${active ? 'active' : ''}" onclick="FamilyView.selectList(${esc(l.id)})">
          <span class="material-symbols-outlined mi-sm">list</span> ${esc(l.name)}
        </button>`;
      });
      html += `</div>`;
    }

    if (selectedList) {
      html += renderListItems();
    }

    el.innerHTML = html;
  }

  function renderListItems() {
    const checkedCount = listItems.filter(i => i.checked).length;
    let html = `
      <div class="card" style="margin-top:12px">
        <div class="family-list-header">
          <strong>${esc(selectedList.name)}</strong>
          <span class="badge badge-accent">${checkedCount}/${listItems.length}</span>
        </div>`;

    if (showListItemForm) {
      html += `
        <div style="margin:8px 0;padding:8px;background:var(--surface2);border-radius:8px">
          <div class="form-group">
            <input type="text" id="new-item-text" class="input" placeholder="Aufgabe / Eintrag" />
          </div>
          <div class="form-group">
            <select id="new-item-assignee" class="input">
              <option value="">– Zuweisung (optional) –</option>
              ${members.map(m => `<option value="${esc(m.user_id || m.id)}">${esc(m.display_name || m.username || m.user_id || m.id)}</option>`).join('')}
            </select>
          </div>
          <div class="form-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
            <button class="btn btn-secondary btn-sm" onclick="FamilyView.toggleListItemForm()">Abbrechen</button>
            <button class="btn btn-primary btn-sm" onclick="FamilyView.addListItem()">Hinzufügen</button>
          </div>
        </div>`;
    }

    html += `<button class="btn btn-sm btn-secondary" style="margin-bottom:8px" onclick="FamilyView.toggleListItemForm()">
      <span class="material-symbols-outlined mi-sm">add</span> Eintrag hinzufügen
    </button>`;

    if (listItems.length === 0) {
      html += `<div class="empty-state" style="padding:12px">Keine Einträge.</div>`;
    } else {
      listItems.forEach(item => {
        const assigneeName = item.assigned_to ? memberName(item.assigned_to) : null;
        html += `
          <div class="family-list-item ${item.checked ? 'checked' : ''}">
            <input type="checkbox" ${item.checked ? 'checked' : ''}
              onchange="FamilyView.toggleListItem(${esc(item.id)}, this.checked)" />
            <span class="family-list-item-text">${esc(item.text)}</span>
            ${assigneeName ? `<span class="badge" style="font-size:0.75rem">${esc(assigneeName)}</span>` : ''}
            <button class="btn-icon" onclick="FamilyView.deleteListItem(${esc(item.id)})" title="Löschen">
              <span class="material-symbols-outlined" style="font-size:16px">delete</span>
            </button>
          </div>`;
      });
    }

    html += `</div>`;
    return html;
  }

  function toggleListForm() {
    showListForm = !showListForm;
    renderLists();
  }

  function toggleListItemForm() {
    showListItemForm = !showListItemForm;
    const el = document.getElementById('family-tab-content');
    if (el) el.innerHTML = renderListsHtml();
    // Re-render cleanly
    renderLists();
  }

  async function createList() {
    const nameEl = document.getElementById('new-list-name');
    const name = nameEl ? nameEl.value.trim() : '';
    if (!name) {
      if (nameEl) nameEl.classList.add('input-error');
      return;
    }
    try {
      const list = await Api.post(`/family/workspaces/${currentWorkspace.id}/lists`, { name });
      lists.push(list);
      selectedList = list;
      listItems = [];
      showListForm = false;
      renderLists();
      Toast.show('Liste erstellt', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function selectList(id) {
    const list = lists.find(l => l.id === id);
    if (!list) return;
    selectedList = list;
    showListItemForm = false;
    try {
      listItems = await Api.get(`/family/lists/${id}/items`);
    } catch (err) {
      listItems = [];
      Toast.show('Fehler beim Laden: ' + err.message, 'error');
    }
    renderLists();
  }

  async function addListItem() {
    const textEl = document.getElementById('new-item-text');
    const assigneeEl = document.getElementById('new-item-assignee');
    const text = textEl ? textEl.value.trim() : '';
    if (!text) {
      if (textEl) textEl.classList.add('input-error');
      return;
    }
    const assigned_to = assigneeEl && assigneeEl.value ? assigneeEl.value : null;
    try {
      const item = await Api.post(`/family/lists/${selectedList.id}/items`, { text, assigned_to });
      listItems.push(item);
      showListItemForm = false;
      renderLists();
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function toggleListItem(itemId, checked) {
    const item = listItems.find(i => i.id === itemId);
    if (item) item.checked = checked;
    renderLists();
    try {
      await Api.patch(`/family/lists/${selectedList.id}/items/${itemId}`, { checked });
    } catch (err) {
      if (item) item.checked = !checked;
      renderLists();
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function deleteListItem(itemId) {
    const prev = [...listItems];
    listItems = listItems.filter(i => i.id !== itemId);
    renderLists();
    try {
      await Api.delete(`/family/lists/${selectedList.id}/items/${itemId}`);
    } catch (err) {
      listItems = prev;
      renderLists();
      Toast.show('Löschen fehlgeschlagen: ' + err.message, 'error');
    }
  }

  // ── Tasks ──

  async function loadTasks() {
    tasks = await Api.get(`/family/workspaces/${currentWorkspace.id}/tasks`);
  }

  function renderTasks() {
    const el = document.getElementById('family-tab-content');
    if (!el) return;

    const uid = currentUserId();

    let html = `
      <div class="family-section-actions">
        <div class="filter-group">
          <button class="filter-btn ${taskFilter === 'all' ? 'active' : ''}" onclick="FamilyView.setTaskFilter('all', this)">Alle</button>
          <button class="filter-btn ${taskFilter === 'mine' ? 'active' : ''}" onclick="FamilyView.setTaskFilter('mine', this)">Meine</button>
        </div>
        <button class="btn btn-sm btn-primary" onclick="FamilyView.toggleTaskForm()">
          <span class="material-symbols-outlined mi-sm">add_task</span> Neue Aufgabe
        </button>
      </div>`;

    if (showTaskForm) {
      html += `
        <div class="card" style="margin-bottom:12px;padding:12px">
          <div class="form-group">
            <input type="text" id="new-task-title" class="input" placeholder="Titel" />
          </div>
          <div class="form-group">
            <input type="text" id="new-task-desc" class="input" placeholder="Beschreibung (optional)" />
          </div>
          <div class="form-row" style="gap:8px">
            <div class="form-group" style="flex:1">
              <select id="new-task-assignee" class="input">
                <option value="">– Zuweisung –</option>
                ${members.map(m => `<option value="${esc(m.user_id || m.id)}">${esc(m.display_name || m.username || m.user_id || m.id)}</option>`).join('')}
              </select>
            </div>
            <div class="form-group" style="flex:1">
              <input type="date" id="new-task-due" class="input" />
            </div>
          </div>
          <div class="form-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
            <button class="btn btn-secondary btn-sm" onclick="FamilyView.toggleTaskForm()">Abbrechen</button>
            <button class="btn btn-primary btn-sm" onclick="FamilyView.createTask()">Erstellen</button>
          </div>
        </div>`;
    }

    let filtered = tasks;
    if (taskFilter === 'mine' && uid) {
      filtered = tasks.filter(t => String(t.assigned_to) === String(uid));
    }

    if (filtered.length === 0) {
      html += `<div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted);display:block;margin-bottom:8px">check_circle</span>
        ${tasks.length === 0 ? 'Noch keine Aufgaben.' : 'Keine passenden Aufgaben.'}
      </div>`;
    } else {
      filtered.forEach(t => {
        const assignee = t.assigned_to ? memberName(t.assigned_to) : null;
        html += `
          <div class="card family-task-item">
            <div class="family-task-main">
              <span class="family-task-title">${esc(t.title)}</span>
              <div class="family-task-meta">
                ${assignee ? `<span class="text-muted" style="font-size:0.8rem"><span class="material-symbols-outlined mi-sm">person</span>${esc(assignee)}</span>` : ''}
                ${t.due_date ? `<span class="text-muted" style="font-size:0.8rem"><span class="material-symbols-outlined mi-sm">event</span>${formatDate(t.due_date)}</span>` : ''}
              </div>
              ${t.description ? `<div class="text-muted" style="font-size:0.85rem;margin-top:2px">${esc(t.description)}</div>` : ''}
            </div>
            <div class="family-task-actions">
              ${taskStatusBadge(t)}
              ${t.status !== 'done' ? `<button class="btn btn-sm btn-secondary" onclick="FamilyView.markTaskDone(${esc(t.id)})">
                <span class="material-symbols-outlined mi-sm">check</span> Erledigt
              </button>` : ''}
              <button class="btn-icon" onclick="FamilyView.deleteTask(${esc(t.id)})" title="Löschen">
                <span class="material-symbols-outlined" style="font-size:16px">delete</span>
              </button>
            </div>
          </div>`;
      });
    }

    el.innerHTML = html;
  }

  function setTaskFilter(filter, btnEl) {
    taskFilter = filter;
    document.querySelectorAll('#family-tab-content .filter-btn').forEach(b => b.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    renderTasks();
  }

  function toggleTaskForm() {
    showTaskForm = !showTaskForm;
    renderTasks();
  }

  async function createTask() {
    const titleEl = document.getElementById('new-task-title');
    const descEl = document.getElementById('new-task-desc');
    const assigneeEl = document.getElementById('new-task-assignee');
    const dueEl = document.getElementById('new-task-due');

    const title = titleEl ? titleEl.value.trim() : '';
    if (!title) {
      if (titleEl) titleEl.classList.add('input-error');
      return;
    }
    const data = { title };
    if (descEl && descEl.value.trim()) data.description = descEl.value.trim();
    if (assigneeEl && assigneeEl.value) data.assigned_to = assigneeEl.value;
    if (dueEl && dueEl.value) data.due_date = new Date(dueEl.value).toISOString();

    try {
      const task = await Api.post(`/family/workspaces/${currentWorkspace.id}/tasks`, data);
      tasks.unshift(task);
      showTaskForm = false;
      renderTasks();
      Toast.show('Aufgabe erstellt', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function markTaskDone(taskId) {
    try {
      const updated = await Api.patch(`/family/tasks/${taskId}`, { status: 'done' });
      const idx = tasks.findIndex(t => t.id === taskId);
      if (idx >= 0 && updated) tasks[idx] = updated;
      renderTasks();
      Toast.show('Aufgabe erledigt', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function deleteTask(taskId) {
    const task = tasks.find(t => t.id === taskId);
    tasks = tasks.filter(t => t.id !== taskId);
    renderTasks();

    let cancelled = false;
    Toast.showUndo('Aufgabe gelöscht', () => {
      cancelled = true;
      if (task) tasks.unshift(task);
      renderTasks();
    });

    setTimeout(async () => {
      if (cancelled) return;
      try {
        await Api.delete(`/family/tasks/${taskId}`);
      } catch (err) {
        if (task) tasks.unshift(task);
        renderTasks();
        Toast.show('Löschen fehlgeschlagen: ' + err.message, 'error');
      }
    }, 5000);
  }

  // ── Routines ──

  async function loadRoutines() {
    routines = await Api.get(`/family/workspaces/${currentWorkspace.id}/routines`);
  }

  function renderRoutines() {
    const el = document.getElementById('family-tab-content');
    if (!el) return;

    let html = `
      <div class="family-section-actions">
        <button class="btn btn-sm btn-primary" onclick="FamilyView.toggleRoutineForm()">
          <span class="material-symbols-outlined mi-sm">add</span> Neue Routine
        </button>
      </div>`;

    if (showRoutineForm) {
      html += `
        <div class="card" style="margin-bottom:12px;padding:12px">
          <div class="form-group">
            <input type="text" id="new-routine-name" class="input" placeholder="Routine-Name (z. B. Küche putzen)" />
          </div>
          <div class="form-group">
            <select id="new-routine-interval" class="input">
              <option value="daily">Täglich</option>
              <option value="weekly" selected>Wöchentlich</option>
              <option value="monthly">Monatlich</option>
            </select>
          </div>
          <div class="form-group">
            <label style="font-size:0.85rem;color:var(--text-muted)">Mitglieder (Rotation)</label>
            <div id="routine-member-checkboxes" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:4px">
              ${members.map(m => {
                const uid = m.user_id || m.id;
                const name = m.display_name || m.username || m.user_id || m.id;
                return `<label style="display:flex;align-items:center;gap:4px;font-size:0.85rem">
                  <input type="checkbox" value="${esc(uid)}" /> ${esc(name)}
                </label>`;
              }).join('')}
            </div>
          </div>
          <div class="form-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
            <button class="btn btn-secondary btn-sm" onclick="FamilyView.toggleRoutineForm()">Abbrechen</button>
            <button class="btn btn-primary btn-sm" onclick="FamilyView.createRoutine()">Erstellen</button>
          </div>
        </div>`;
    }

    if (routines.length === 0) {
      html += `<div class="empty-state">
        <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted);display:block;margin-bottom:8px">repeat</span>
        Noch keine Routinen.
      </div>`;
    } else {
      routines.forEach(r => {
        const currentAssignee = r.current_assignee ? memberName(r.current_assignee) : null;
        const nextAssignee = r.next_assignee ? memberName(r.next_assignee) : null;
        html += `
          <div class="card family-routine-item">
            <div class="family-routine-main">
              <span class="family-routine-name">${esc(r.name)}</span>
              <div class="family-routine-meta">
                <span class="badge badge-accent">${esc(intervalLabel(r.interval))}</span>
                ${currentAssignee ? `<span class="text-muted" style="font-size:0.85rem"><span class="material-symbols-outlined mi-sm">person</span>${esc(currentAssignee)}</span>` : ''}
                ${r.last_completed_at ? `<span class="text-muted" style="font-size:0.8rem">Zuletzt: ${formatDate(r.last_completed_at)}</span>` : ''}
              </div>
            </div>
            <div class="family-routine-actions">
              <button class="btn btn-sm btn-primary" onclick="FamilyView.completeRoutine(${esc(r.id)})">
                <span class="material-symbols-outlined mi-sm">check</span> Erledigt
              </button>
              <button class="btn-icon" onclick="FamilyView.deleteRoutine(${esc(r.id)})" title="Löschen">
                <span class="material-symbols-outlined" style="font-size:16px">delete</span>
              </button>
            </div>
          </div>
          ${nextAssignee ? `<div style="font-size:0.8rem;color:var(--text-muted);padding:0 4px 8px">Nächste Runde: <strong>${esc(nextAssignee)}</strong></div>` : ''}`;
      });
    }

    el.innerHTML = html;
  }

  function toggleRoutineForm() {
    showRoutineForm = !showRoutineForm;
    renderRoutines();
  }

  async function createRoutine() {
    const nameEl = document.getElementById('new-routine-name');
    const intervalEl = document.getElementById('new-routine-interval');
    const name = nameEl ? nameEl.value.trim() : '';
    if (!name) {
      if (nameEl) nameEl.classList.add('input-error');
      return;
    }
    const interval = intervalEl ? intervalEl.value : 'weekly';
    const checkboxes = document.querySelectorAll('#routine-member-checkboxes input[type=checkbox]:checked');
    const assigned_members = Array.from(checkboxes).map(cb => cb.value);

    try {
      const routine = await Api.post(`/family/workspaces/${currentWorkspace.id}/routines`, { name, interval, assigned_members });
      routines.push(routine);
      showRoutineForm = false;
      renderRoutines();
      Toast.show('Routine erstellt', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function completeRoutine(routineId) {
    try {
      const result = await Api.post(`/family/routines/${routineId}/complete`, {});
      const idx = routines.findIndex(r => r.id === routineId);
      if (idx >= 0 && result) routines[idx] = result;
      renderRoutines();
      const nextAssignee = result && result.next_assignee ? memberName(result.next_assignee) : null;
      Toast.show(nextAssignee ? `Erledigt! Nächste Runde: ${nextAssignee}` : 'Routine erledigt', 'success');
    } catch (err) {
      Toast.show('Fehler: ' + err.message, 'error');
    }
  }

  async function deleteRoutine(routineId) {
    const routine = routines.find(r => r.id === routineId);
    routines = routines.filter(r => r.id !== routineId);
    renderRoutines();
    try {
      await Api.delete(`/family/routines/${routineId}`);
      Toast.show('Routine gelöscht', 'success');
    } catch (err) {
      if (routine) routines.push(routine);
      renderRoutines();
      Toast.show('Löschen fehlgeschlagen: ' + err.message, 'error');
    }
  }

  // ── Tab Switching ──

  async function switchTab(tab) {
    activeTab = tab;
    showMemberForm = false;
    showListForm = false;
    showListItemForm = false;
    showTaskForm = false;
    showRoutineForm = false;

    // Update tab button styles
    document.querySelectorAll('.family-tab').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.querySelector(`.family-tab[onclick="FamilyView.switchTab('${tab}')"]`);
    if (activeBtn) activeBtn.classList.add('active');

    const el = document.getElementById('family-tab-content');
    if (el) {
      el.innerHTML = `
        <div class="skeleton" style="height:60px;border-radius:8px;margin-bottom:8px"></div>
        <div class="skeleton" style="height:60px;border-radius:8px;margin-bottom:8px"></div>`;
    }

    await loadTabContent();
  }

  async function reloadTab() {
    await loadTabContent();
  }

  // ── Public API ──
  return {
    render,
    // Workspace
    toggleWorkspaceForm, createWorkspace, switchWorkspace,
    // Members
    toggleMemberForm, addMember, removeMember, changeRole,
    // Lists
    toggleListForm, createList, selectList,
    toggleListItemForm, addListItem, toggleListItem, deleteListItem,
    // Tasks
    setTaskFilter, toggleTaskForm, createTask, markTaskDone, deleteTask,
    // Routines
    toggleRoutineForm, createRoutine, completeRoutine, deleteRoutine,
    // Navigation
    switchTab, reloadTab,
  };
})();
