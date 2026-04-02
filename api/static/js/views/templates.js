/**
 * DualMind Vorlagen View
 * Wiederverwendbare Inhaltsbausteine: Einkaufslisten, Nachrichten, Tasks, Routinen.
 */
const TemplatesView = (() => {
  let templates = [];
  let loading = false;
  let container = null;
  let categoryFilter = null;
  let editingId = null;

  const CATEGORIES = {
    shopping:  { icon: 'shopping_cart', label: 'Einkauf',    color: 'var(--accent)' },
    message:   { icon: 'chat_bubble',   label: 'Nachricht',  color: 'var(--info, #42a5f5)' },
    task:      { icon: 'check_circle',  label: 'Aufgabe',    color: 'var(--success)' },
    routine:   { icon: 'repeat',        label: 'Routine',    color: 'var(--warning)' },
    checklist: { icon: 'checklist',     label: 'Checkliste', color: 'var(--error)' },
  };

  function renderHeader() {
    return `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">library_books</span> Vorlagen</h2>
        <button class="btn btn-sm btn-primary" id="tpl-create-btn">
          <span class="material-symbols-outlined">add</span> Neue Vorlage
        </button>
      </div>
    `;
  }

  function renderFilters() {
    const cats = Object.entries(CATEGORIES);
    return `
      <div class="notification-filter-row" style="margin-bottom:12px">
        <button class="filter-chip ${!categoryFilter ? 'active' : ''}" data-tpl-cat="">Alle</button>
        ${cats.map(([key, meta]) => `
          <button class="filter-chip ${categoryFilter === key ? 'active' : ''}" data-tpl-cat="${key}">
            <span class="material-symbols-outlined" style="font-size:14px">${meta.icon}</span>
            ${meta.label}
          </button>
        `).join('')}
      </div>
    `;
  }

  function renderCreateForm() {
    return `
      <div id="tpl-form" class="card" style="display:none;margin-bottom:16px">
        <h3 id="tpl-form-title">Neue Vorlage</h3>
        <div style="display:flex;flex-direction:column;gap:10px">
          <input type="text" id="tpl-name" class="input" placeholder="Name der Vorlage" maxlength="200">
          <select id="tpl-category" class="input">
            ${Object.entries(CATEGORIES).map(([key, meta]) =>
              `<option value="${key}">${meta.label}</option>`
            ).join('')}
          </select>
          <textarea id="tpl-description" class="input" placeholder="Beschreibung (optional)" rows="2" maxlength="1000"></textarea>
          <textarea id="tpl-content" class="input" placeholder='Inhalt als JSON, z.B. {"items": ["Milch", "Brot"]}' rows="4"></textarea>
          <div style="display:flex;gap:8px">
            <button class="btn btn-primary" id="tpl-save-btn">Speichern</button>
            <button class="btn btn-secondary" id="tpl-cancel-btn">Abbrechen</button>
          </div>
        </div>
      </div>
    `;
  }

  function renderTemplate(tpl) {
    const meta = CATEGORIES[tpl.category] || CATEGORIES.task;
    return `
      <div class="card tpl-card" data-id="${tpl.id}" style="margin-bottom:8px">
        <div style="display:flex;align-items:center;gap:12px">
          <span class="material-symbols-outlined" style="color:${meta.color};font-size:28px">${meta.icon}</span>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600">${tpl.name}</div>
            ${tpl.description ? `<div style="color:var(--text-secondary);font-size:13px">${tpl.description}</div>` : ''}
            <div style="font-size:12px;color:var(--text-secondary);margin-top:2px">
              <span class="badge" style="font-size:11px">${meta.label}</span>
              ${tpl.use_count > 0 ? `<span style="margin-left:8px">${tpl.use_count}x verwendet</span>` : ''}
            </div>
          </div>
          <div style="display:flex;gap:4px">
            <button class="btn-icon" data-action="apply" title="Anwenden"><span class="material-symbols-outlined">play_arrow</span></button>
            <button class="btn-icon" data-action="edit" title="Bearbeiten"><span class="material-symbols-outlined">edit</span></button>
            <button class="btn-icon" data-action="delete" title="Loeschen"><span class="material-symbols-outlined">delete</span></button>
          </div>
        </div>
      </div>
    `;
  }

  function renderList() {
    if (loading) return '<div class="loading"><div class="spinner"></div></div>';
    if (!templates.length) {
      return `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-secondary)">library_books</span>
          <p>Keine Vorlagen vorhanden</p>
          <p style="font-size:13px;color:var(--text-secondary)">Erstelle eine Vorlage fuer haeufig genutzte Einkaufslisten, Nachrichten oder Aufgaben.</p>
        </div>
      `;
    }
    return templates.map(renderTemplate).join('');
  }

  async function load() {
    loading = true;
    update();
    try {
      const params = new URLSearchParams();
      if (categoryFilter) params.set('category', categoryFilter);
      const qs = params.toString();
      templates = await Api.request(`/templates${qs ? '?' + qs : ''}`);
    } catch (err) {
      templates = [];
    } finally {
      loading = false;
    }
    update();
  }

  function update() {
    if (!container) return;
    container.innerHTML = `
      ${renderHeader()}
      ${renderCreateForm()}
      ${renderFilters()}
      <div class="tpl-list">${renderList()}</div>
    `;
    bindEvents();
  }

  function showForm(tpl) {
    const form = container.querySelector('#tpl-form');
    form.style.display = 'block';
    if (tpl) {
      editingId = tpl.id;
      container.querySelector('#tpl-form-title').textContent = 'Vorlage bearbeiten';
      container.querySelector('#tpl-name').value = tpl.name;
      container.querySelector('#tpl-category').value = tpl.category;
      container.querySelector('#tpl-description').value = tpl.description || '';
      container.querySelector('#tpl-content').value = JSON.stringify(tpl.content, null, 2);
    } else {
      editingId = null;
      container.querySelector('#tpl-form-title').textContent = 'Neue Vorlage';
      container.querySelector('#tpl-name').value = '';
      container.querySelector('#tpl-category').value = 'shopping';
      container.querySelector('#tpl-description').value = '';
      container.querySelector('#tpl-content').value = '';
    }
  }

  function bindEvents() {
    if (!container) return;

    // Create button
    container.querySelector('#tpl-create-btn')?.addEventListener('click', () => showForm(null));

    // Cancel
    container.querySelector('#tpl-cancel-btn')?.addEventListener('click', () => {
      container.querySelector('#tpl-form').style.display = 'none';
      editingId = null;
    });

    // Save
    container.querySelector('#tpl-save-btn')?.addEventListener('click', async () => {
      const name = container.querySelector('#tpl-name').value.trim();
      const category = container.querySelector('#tpl-category').value;
      const description = container.querySelector('#tpl-description').value.trim();
      const contentRaw = container.querySelector('#tpl-content').value.trim();

      if (!name) { Toast.show('Name ist erforderlich'); return; }

      let content = {};
      if (contentRaw) {
        try { content = JSON.parse(contentRaw); }
        catch { Toast.show('Inhalt ist kein gueltiges JSON'); return; }
      }

      try {
        if (editingId) {
          await Api.request(`/templates/${editingId}`, {
            method: 'PATCH',
            body: { name, content, description },
          });
          Toast.show('Vorlage aktualisiert', 'success');
        } else {
          await Api.request('/templates', {
            method: 'POST',
            body: { name, category, content, description },
          });
          Toast.show('Vorlage erstellt', 'success');
        }
        container.querySelector('#tpl-form').style.display = 'none';
        editingId = null;
        await load();
      } catch (err) {
        Toast.show(err.message || 'Fehler beim Speichern');
      }
    });

    // Category filters
    container.querySelectorAll('[data-tpl-cat]').forEach(btn => {
      btn.addEventListener('click', () => {
        categoryFilter = btn.dataset.tplCat || null;
        load();
      });
    });

    // Per-template actions
    container.querySelectorAll('.tpl-card').forEach(card => {
      const id = card.dataset.id;
      const tpl = templates.find(t => t.id === id);
      if (!tpl) return;

      card.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const action = btn.dataset.action;

          if (action === 'apply') {
            try {
              const result = await Api.request(`/templates/${id}/apply`, { method: 'POST' });
              Toast.show(`Vorlage "${result.name}" angewendet`, 'success');
              await load();
            } catch (err) {
              Toast.show(err.message || 'Fehler beim Anwenden');
            }
          } else if (action === 'edit') {
            showForm(tpl);
          } else if (action === 'delete') {
            if (!confirm(`Vorlage "${tpl.name}" wirklich loeschen?`)) return;
            try {
              await Api.request(`/templates/${id}`, { method: 'DELETE' });
              Toast.show('Vorlage geloescht', 'success');
              await load();
            } catch (err) {
              Toast.show(err.message || 'Fehler beim Loeschen');
            }
          }
        });
      });
    });
  }

  async function render(el) {
    container = el;
    categoryFilter = null;
    editingId = null;
    await load();
  }

  return { render };
})();
