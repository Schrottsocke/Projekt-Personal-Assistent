/**
 * DualMind Vorlagen View
 * Wiederverwendbare Inhaltsbausteine: Einkaufslisten, Nachrichten, Tasks, Routinen, Checklisten, Mealplan.
 */
const TemplatesView = (() => {
  let templates = [];
  let loading = false;
  let container = null;
  let categoryFilter = null;
  let editingId = null;

  const CATEGORIES = {
    shopping:  { icon: 'shopping_cart', label: 'Einkauf',    color: 'var(--accent)' },
    task:      { icon: 'check_circle',  label: 'Aufgabe',    color: 'var(--success)' },
    checklist: { icon: 'checklist',     label: 'Checkliste', color: 'var(--warning)' },
    routine:   { icon: 'repeat',        label: 'Routine',    color: 'var(--error)' },
    mealplan:  { icon: 'restaurant',    label: 'Wochenplan', color: 'var(--info, #42a5f5)' },
    message:   { icon: 'chat_bubble',   label: 'Nachricht',  color: 'var(--text-secondary)' },
  };

  // ── Render: Header + Filters ──

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

  // ── Render: Category-specific content forms ──

  function renderContentForm(category, content) {
    switch (category) {
      case 'shopping':  return renderShoppingForm(content);
      case 'task':      return renderTaskForm(content);
      case 'checklist': return renderChecklistForm(content);
      case 'routine':   return renderRoutineForm(content);
      case 'mealplan':  return renderMealplanForm(content);
      case 'message':   return renderMessageForm(content);
      default:          return '';
    }
  }

  function renderShoppingForm(content) {
    const items = (content && content.items) || [{ name: '', quantity: '', unit: '' }];
    return `
      <div class="tpl-content-section">
        <label class="tpl-content-label">Artikel</label>
        <div id="tpl-shopping-items">
          ${items.map((it, i) => `
            <div class="tpl-item-row" data-idx="${i}">
              <input type="text" class="input tpl-item-name" placeholder="Artikel" value="${esc(it.name || '')}" style="flex:2">
              <input type="text" class="input tpl-item-qty" placeholder="Menge" value="${esc(it.quantity || '')}" style="flex:0.7">
              <select class="input tpl-item-unit" style="flex:0.8">
                ${unitOptions(it.unit)}
              </select>
              <button class="btn-icon tpl-remove-row" title="Entfernen"><span class="material-symbols-outlined">close</span></button>
            </div>
          `).join('')}
        </div>
        <button class="btn btn-sm btn-secondary" id="tpl-add-shopping-item" style="margin-top:6px">
          <span class="material-symbols-outlined" style="font-size:16px">add</span> Artikel
        </button>
      </div>
    `;
  }

  function unitOptions(selected) {
    const units = [
      ['', '--'],
      ['stk', 'Stk'],
      ['g', 'g'],
      ['kg', 'kg'],
      ['ml', 'ml'],
      ['l', 'l'],
      ['pkg', 'Pkg'],
      ['bund', 'Bund'],
      ['dose', 'Dose'],
    ];
    return units.map(([v, l]) => `<option value="${v}" ${v === (selected || '') ? 'selected' : ''}>${l}</option>`).join('');
  }

  function renderTaskForm(content) {
    const c = content || {};
    return `
      <div class="tpl-content-section">
        <input type="text" class="input" id="tpl-task-title" placeholder="Aufgabentitel" value="${esc(c.title || '')}">
        <textarea class="input" id="tpl-task-desc" placeholder="Beschreibung (optional)" rows="2">${esc(c.description || '')}</textarea>
        <div class="tpl-item-row">
          <div style="flex:1">
            <label class="tpl-content-label">Prioritaet</label>
            <select class="input" id="tpl-task-priority">
              <option value="low" ${c.priority === 'low' ? 'selected' : ''}>Niedrig</option>
              <option value="medium" ${(!c.priority || c.priority === 'medium') ? 'selected' : ''}>Mittel</option>
              <option value="high" ${c.priority === 'high' ? 'selected' : ''}>Hoch</option>
            </select>
          </div>
          <div style="flex:1">
            <label class="tpl-content-label">Wiederholung</label>
            <select class="input" id="tpl-task-recurrence">
              <option value="" ${!c.recurrence ? 'selected' : ''}>Keine</option>
              <option value="daily" ${c.recurrence === 'daily' ? 'selected' : ''}>Taeglich</option>
              <option value="weekly" ${c.recurrence === 'weekly' ? 'selected' : ''}>Woechentlich</option>
              <option value="monthly" ${c.recurrence === 'monthly' ? 'selected' : ''}>Monatlich</option>
            </select>
          </div>
        </div>
      </div>
    `;
  }

  function renderChecklistForm(content) {
    const items = (content && content.items) || [''];
    return `
      <div class="tpl-content-section">
        <label class="tpl-content-label">Checkliste</label>
        <div id="tpl-checklist-items">
          ${items.map((it, i) => {
            const text = typeof it === 'string' ? it : (it.title || '');
            return `
              <div class="tpl-item-row" data-idx="${i}">
                <input type="text" class="input tpl-checklist-text" placeholder="Punkt ${i + 1}" value="${esc(text)}" style="flex:1">
                <button class="btn-icon tpl-remove-row" title="Entfernen"><span class="material-symbols-outlined">close</span></button>
              </div>
            `;
          }).join('')}
        </div>
        <button class="btn btn-sm btn-secondary" id="tpl-add-checklist-item" style="margin-top:6px">
          <span class="material-symbols-outlined" style="font-size:16px">add</span> Punkt
        </button>
      </div>
    `;
  }

  function renderRoutineForm(content) {
    const c = content || {};
    const steps = c.steps || [{ name: '', description: '' }];
    const schedule = c.schedule || {};
    return `
      <div class="tpl-content-section">
        <label class="tpl-content-label">Schritte</label>
        <div id="tpl-routine-steps">
          ${steps.map((s, i) => `
            <div class="tpl-step-row" data-idx="${i}">
              <div style="flex:1;display:flex;flex-direction:column;gap:4px">
                <input type="text" class="input tpl-step-name" placeholder="Schritt ${i + 1}" value="${esc(s.name || '')}">
                <input type="text" class="input tpl-step-desc" placeholder="Details (optional)" value="${esc(s.description || '')}" style="font-size:12px">
              </div>
              <button class="btn-icon tpl-remove-row" title="Entfernen"><span class="material-symbols-outlined">close</span></button>
            </div>
          `).join('')}
        </div>
        <button class="btn btn-sm btn-secondary" id="tpl-add-routine-step" style="margin-top:6px">
          <span class="material-symbols-outlined" style="font-size:16px">add</span> Schritt
        </button>
        <label class="tpl-content-label" style="margin-top:12px">Zeitplan (optional)</label>
        <div class="tpl-item-row">
          <select class="input" id="tpl-routine-schedule-type" style="flex:1">
            <option value="" ${!schedule.type ? 'selected' : ''}>Kein Zeitplan</option>
            <option value="daily" ${schedule.type === 'daily' ? 'selected' : ''}>Taeglich</option>
            <option value="weekly" ${schedule.type === 'weekly' ? 'selected' : ''}>Woechentlich</option>
          </select>
          <input type="time" class="input" id="tpl-routine-schedule-time" value="${esc(schedule.time || '')}" style="flex:0.7">
        </div>
      </div>
    `;
  }

  function renderMealplanForm(content) {
    const c = content || {};
    return `
      <div class="tpl-content-section">
        <input type="text" class="input" id="tpl-meal-title" placeholder="Rezeptname" value="${esc(c.recipe_title || '')}">
        <div class="tpl-item-row">
          <div style="flex:1">
            <label class="tpl-content-label">Mahlzeit</label>
            <select class="input" id="tpl-meal-type">
              <option value="breakfast" ${c.meal_type === 'breakfast' ? 'selected' : ''}>Fruehstueck</option>
              <option value="lunch" ${c.meal_type === 'lunch' ? 'selected' : ''}>Mittagessen</option>
              <option value="dinner" ${(!c.meal_type || c.meal_type === 'dinner') ? 'selected' : ''}>Abendessen</option>
            </select>
          </div>
          <div style="flex:0.6">
            <label class="tpl-content-label">Portionen</label>
            <input type="number" class="input" id="tpl-meal-servings" min="1" max="20" value="${c.servings || 4}">
          </div>
        </div>
        <textarea class="input" id="tpl-meal-notes" placeholder="Notizen (optional)" rows="2">${esc(c.notes || '')}</textarea>
      </div>
    `;
  }

  function renderMessageForm(content) {
    const c = content || {};
    return `
      <div class="tpl-content-section">
        <input type="text" class="input" id="tpl-msg-subject" placeholder="Betreff" value="${esc(c.subject || '')}">
        <textarea class="input" id="tpl-msg-body" placeholder="Nachrichtentext" rows="4">${esc(c.body || '')}</textarea>
      </div>
    `;
  }

  // ── Collect content from forms ──

  function collectContent(category) {
    switch (category) {
      case 'shopping': {
        const rows = container.querySelectorAll('#tpl-shopping-items .tpl-item-row');
        const items = [];
        rows.forEach(row => {
          const name = row.querySelector('.tpl-item-name').value.trim();
          if (!name) return;
          items.push({
            name,
            quantity: row.querySelector('.tpl-item-qty').value.trim(),
            unit: row.querySelector('.tpl-item-unit').value,
          });
        });
        return { items };
      }
      case 'task':
        return {
          title: (container.querySelector('#tpl-task-title')?.value || '').trim(),
          description: (container.querySelector('#tpl-task-desc')?.value || '').trim(),
          priority: container.querySelector('#tpl-task-priority')?.value || 'medium',
          recurrence: container.querySelector('#tpl-task-recurrence')?.value || null,
        };
      case 'checklist': {
        const rows = container.querySelectorAll('#tpl-checklist-items .tpl-item-row');
        const items = [];
        rows.forEach(row => {
          const text = row.querySelector('.tpl-checklist-text').value.trim();
          if (text) items.push(text);
        });
        return { items };
      }
      case 'routine': {
        const stepRows = container.querySelectorAll('#tpl-routine-steps .tpl-step-row');
        const steps = [];
        stepRows.forEach(row => {
          const name = row.querySelector('.tpl-step-name').value.trim();
          if (!name) return;
          steps.push({
            name,
            description: row.querySelector('.tpl-step-desc').value.trim(),
          });
        });
        const schedType = container.querySelector('#tpl-routine-schedule-type')?.value || '';
        const schedTime = container.querySelector('#tpl-routine-schedule-time')?.value || '';
        const result = { steps };
        if (schedType) result.schedule = { type: schedType, time: schedTime };
        return result;
      }
      case 'mealplan':
        return {
          recipe_title: (container.querySelector('#tpl-meal-title')?.value || '').trim(),
          meal_type: container.querySelector('#tpl-meal-type')?.value || 'dinner',
          servings: parseInt(container.querySelector('#tpl-meal-servings')?.value) || 4,
          notes: (container.querySelector('#tpl-meal-notes')?.value || '').trim(),
        };
      case 'message':
        return {
          subject: (container.querySelector('#tpl-msg-subject')?.value || '').trim(),
          body: (container.querySelector('#tpl-msg-body')?.value || '').trim(),
        };
      default:
        return {};
    }
  }

  // ── Render: Create/Edit Form ──

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
          <div id="tpl-content-area"></div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-primary" id="tpl-save-btn">Speichern</button>
            <button class="btn btn-secondary" id="tpl-cancel-btn">Abbrechen</button>
          </div>
        </div>
      </div>
    `;
  }

  // ── Render: Template card with preview ──

  function contentPreview(tpl) {
    const c = tpl.content || {};
    switch (tpl.category) {
      case 'shopping': {
        const items = c.items || [];
        if (!items.length) return '';
        const names = items.slice(0, 3).map(i => i.name).join(', ');
        return `<span class="tpl-preview">${items.length} Artikel: ${esc(names)}${items.length > 3 ? '...' : ''}</span>`;
      }
      case 'task':
        return c.title ? `<span class="tpl-preview">${esc(c.title)}</span>` : '';
      case 'checklist': {
        const items = c.items || [];
        return items.length ? `<span class="tpl-preview">${items.length} Punkte</span>` : '';
      }
      case 'routine': {
        const steps = c.steps || [];
        const sched = c.schedule;
        let text = `${steps.length} Schritte`;
        if (sched && sched.type) {
          const labels = { daily: 'taeglich', weekly: 'woechentlich' };
          text += `, ${labels[sched.type] || sched.type}`;
          if (sched.time) text += ` ${sched.time}`;
        }
        return `<span class="tpl-preview">${text}</span>`;
      }
      case 'mealplan':
        return c.recipe_title ? `<span class="tpl-preview">${esc(c.recipe_title)}</span>` : '';
      case 'message':
        return c.subject ? `<span class="tpl-preview">${esc(c.subject)}</span>` : '';
      default:
        return '';
    }
  }

  function renderTemplate(tpl) {
    const meta = CATEGORIES[tpl.category] || CATEGORIES.task;
    const preview = contentPreview(tpl);
    return `
      <div class="card tpl-card" data-id="${tpl.id}" style="margin-bottom:8px">
        <div style="display:flex;align-items:center;gap:12px">
          <span class="material-symbols-outlined" style="color:${meta.color};font-size:28px">${meta.icon}</span>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600">${esc(tpl.name)}</div>
            ${tpl.description ? `<div style="color:var(--text-secondary);font-size:13px">${esc(tpl.description)}</div>` : ''}
            ${preview ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:2px">${preview}</div>` : ''}
            <div style="font-size:12px;color:var(--text-secondary);margin-top:2px">
              <span class="badge" style="font-size:11px">${meta.label}</span>
              ${tpl.is_starter ? '<span class="badge badge-accent" style="font-size:11px;margin-left:4px">Starter</span>' : ''}
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
          <p style="font-size:13px;color:var(--text-secondary)">Erstelle eine Vorlage fuer haeufig genutzte Einkaufslisten, Aufgaben oder Routinen.</p>
        </div>
      `;
    }
    return templates.map(renderTemplate).join('');
  }

  // ── Data ──

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

  // ── Form helpers ──

  function showForm(tpl) {
    const form = container.querySelector('#tpl-form');
    form.style.display = 'block';
    const catSelect = container.querySelector('#tpl-category');
    if (tpl) {
      editingId = tpl.id;
      container.querySelector('#tpl-form-title').textContent = 'Vorlage bearbeiten';
      container.querySelector('#tpl-name').value = tpl.name;
      catSelect.value = tpl.category;
      container.querySelector('#tpl-description').value = tpl.description || '';
      updateContentArea(tpl.category, tpl.content);
    } else {
      editingId = null;
      container.querySelector('#tpl-form-title').textContent = 'Neue Vorlage';
      container.querySelector('#tpl-name').value = '';
      catSelect.value = 'shopping';
      container.querySelector('#tpl-description').value = '';
      updateContentArea('shopping', null);
    }
  }

  function updateContentArea(category, content) {
    const area = container.querySelector('#tpl-content-area');
    if (!area) return;
    area.innerHTML = renderContentForm(category, content);
    bindContentEvents(category);
  }

  function bindContentEvents(category) {
    // Add item buttons
    container.querySelector('#tpl-add-shopping-item')?.addEventListener('click', () => {
      const list = container.querySelector('#tpl-shopping-items');
      const idx = list.querySelectorAll('.tpl-item-row').length;
      const row = document.createElement('div');
      row.className = 'tpl-item-row';
      row.dataset.idx = idx;
      row.innerHTML = `
        <input type="text" class="input tpl-item-name" placeholder="Artikel" style="flex:2">
        <input type="text" class="input tpl-item-qty" placeholder="Menge" style="flex:0.7">
        <select class="input tpl-item-unit" style="flex:0.8">${unitOptions('')}</select>
        <button class="btn-icon tpl-remove-row" title="Entfernen"><span class="material-symbols-outlined">close</span></button>
      `;
      list.appendChild(row);
      row.querySelector('.tpl-remove-row').addEventListener('click', () => row.remove());
      row.querySelector('.tpl-item-name').focus();
    });

    container.querySelector('#tpl-add-checklist-item')?.addEventListener('click', () => {
      const list = container.querySelector('#tpl-checklist-items');
      const idx = list.querySelectorAll('.tpl-item-row').length;
      const row = document.createElement('div');
      row.className = 'tpl-item-row';
      row.dataset.idx = idx;
      row.innerHTML = `
        <input type="text" class="input tpl-checklist-text" placeholder="Punkt ${idx + 1}" style="flex:1">
        <button class="btn-icon tpl-remove-row" title="Entfernen"><span class="material-symbols-outlined">close</span></button>
      `;
      list.appendChild(row);
      row.querySelector('.tpl-remove-row').addEventListener('click', () => row.remove());
      row.querySelector('.tpl-checklist-text').focus();
    });

    container.querySelector('#tpl-add-routine-step')?.addEventListener('click', () => {
      const list = container.querySelector('#tpl-routine-steps');
      const idx = list.querySelectorAll('.tpl-step-row').length;
      const row = document.createElement('div');
      row.className = 'tpl-step-row';
      row.dataset.idx = idx;
      row.innerHTML = `
        <div style="flex:1;display:flex;flex-direction:column;gap:4px">
          <input type="text" class="input tpl-step-name" placeholder="Schritt ${idx + 1}">
          <input type="text" class="input tpl-step-desc" placeholder="Details (optional)" style="font-size:12px">
        </div>
        <button class="btn-icon tpl-remove-row" title="Entfernen"><span class="material-symbols-outlined">close</span></button>
      `;
      list.appendChild(row);
      row.querySelector('.tpl-remove-row').addEventListener('click', () => row.remove());
      row.querySelector('.tpl-step-name').focus();
    });

    // Remove buttons on existing rows
    container.querySelectorAll('.tpl-remove-row').forEach(btn => {
      btn.addEventListener('click', () => btn.closest('.tpl-item-row, .tpl-step-row').remove());
    });
  }

  // ── Events ──

  function bindEvents() {
    if (!container) return;

    // Create button
    container.querySelector('#tpl-create-btn')?.addEventListener('click', () => showForm(null));

    // Cancel
    container.querySelector('#tpl-cancel-btn')?.addEventListener('click', () => {
      container.querySelector('#tpl-form').style.display = 'none';
      editingId = null;
    });

    // Category change → update content form
    container.querySelector('#tpl-category')?.addEventListener('change', (e) => {
      updateContentArea(e.target.value, null);
    });

    // Save
    container.querySelector('#tpl-save-btn')?.addEventListener('click', async () => {
      const name = container.querySelector('#tpl-name').value.trim();
      const category = container.querySelector('#tpl-category').value;
      const description = container.querySelector('#tpl-description').value.trim();

      if (!name) { Toast.show('Name ist erforderlich'); return; }

      const content = collectContent(category);

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
              const msg = result.message || `Vorlage "${result.template.name}" angewendet`;
              Toast.show(msg, 'success');
              // Navigate to target view if applicable
              const nav = { shopping: '#/shopping', task: '#/tasks', checklist: '#/tasks', mealplan: '#/mealplan' };
              if (nav[tpl.category]) {
                setTimeout(() => { window.location.hash = nav[tpl.category]; }, 800);
              }
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

  // ── Helpers ──

  function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Public ──

  async function render(el) {
    container = el;
    categoryFilter = null;
    editingId = null;
    await load();
  }

  return { render };
})();
