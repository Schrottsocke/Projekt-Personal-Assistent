/**
 * DualMind Automation View – Regel- und Automationscenter
 * Wenn-Dann Regeln erstellen, verwalten, testen.
 */
const AutomationView = (() => {
  let rules = [];
  let meta = null;      // { triggers, actions, templates }
  let loading = false;
  let container = null;
  let showForm = false;
  let editingRule = null;
  let evaluating = false;

  // ── Helpers ──

  function triggerLabel(id) {
    if (!meta) return id;
    const t = meta.triggers.find(tr => tr.id === id);
    return t ? t.label : id;
  }

  function triggerIcon(id) {
    if (!meta) return 'bolt';
    const t = meta.triggers.find(tr => tr.id === id);
    return t ? t.icon : 'bolt';
  }

  function actionLabel(id) {
    if (!meta) return id;
    const a = meta.actions.find(ac => ac.id === id);
    return a ? a.label : id;
  }

  function actionIcon(id) {
    if (!meta) return 'play_arrow';
    const a = meta.actions.find(ac => ac.id === id);
    return a ? a.icon : 'play_arrow';
  }

  function triggerDescription(id) {
    if (!meta) return '';
    const t = meta.triggers.find(tr => tr.id === id);
    return t ? t.description : '';
  }

  function actionDescription(id) {
    if (!meta) return '';
    const a = meta.actions.find(ac => ac.id === id);
    return a ? a.description : '';
  }

  function timeAgo(iso) {
    if (!iso) return 'Nie';
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'Gerade eben';
    if (mins < 60) return `Vor ${mins} Min.`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `Vor ${hours} Std.`;
    const days = Math.floor(hours / 24);
    return `Vor ${days} Tag${days !== 1 ? 'en' : ''}`;
  }

  function summarizeConfig(type, config, registry) {
    if (!config || !Object.keys(config).length) return '';
    const entry = registry.find(r => r.id === type);
    if (!entry) return '';
    const parts = [];
    for (const field of entry.config_fields || []) {
      const val = config[field.key];
      if (val) {
        if (field.type === 'select' && field.options) {
          const opt = field.options.find(o => o.value === val);
          parts.push(`${field.label}: ${opt ? opt.label : val}`);
        } else {
          parts.push(`${field.label}: ${val}`);
        }
      }
    }
    return parts.join(' · ');
  }

  // ── Render: Rule Card ──

  function renderRule(rule) {
    const tIcon = triggerIcon(rule.trigger_type);
    const tLabel = triggerLabel(rule.trigger_type);
    const aIcon = actionIcon(rule.action_type);
    const aLabel = actionLabel(rule.action_type);

    const triggerConf = meta ? summarizeConfig(rule.trigger_type, rule.trigger_config, meta.triggers) : '';
    const actionConf = meta ? summarizeConfig(rule.action_type, rule.action_config, meta.actions) : '';

    return `
      <div class="automation-rule-card ${rule.active ? '' : 'automation-rule-inactive'}" data-id="${rule.id}">
        <div class="automation-rule-header">
          <div class="automation-rule-toggle" data-action="toggle" title="${rule.active ? 'Deaktivieren' : 'Aktivieren'}">
            <span class="material-symbols-outlined" style="font-size:28px;color:${rule.active ? 'var(--success)' : 'var(--text-secondary)'}">${rule.active ? 'toggle_on' : 'toggle_off'}</span>
          </div>
          <div class="automation-rule-info">
            <div class="automation-rule-name">${escapeHtml(rule.name)}</div>
            ${rule.description ? `<div class="automation-rule-desc">${escapeHtml(rule.description)}</div>` : ''}
          </div>
          <div class="automation-rule-actions">
            <button class="btn-icon" data-action="delete" title="Loeschen">
              <span class="material-symbols-outlined">delete</span>
            </button>
          </div>
        </div>
        <div class="automation-rule-flow">
          <div class="automation-flow-step">
            <span class="material-symbols-outlined automation-flow-icon">${tIcon}</span>
            <div>
              <div class="automation-flow-label">Wenn</div>
              <div class="automation-flow-value">${tLabel}</div>
              ${triggerConf ? `<div class="automation-flow-config">${escapeHtml(triggerConf)}</div>` : ''}
            </div>
          </div>
          <span class="material-symbols-outlined automation-flow-arrow">arrow_forward</span>
          <div class="automation-flow-step">
            <span class="material-symbols-outlined automation-flow-icon">${aIcon}</span>
            <div>
              <div class="automation-flow-label">Dann</div>
              <div class="automation-flow-value">${aLabel}</div>
              ${actionConf ? `<div class="automation-flow-config">${escapeHtml(actionConf)}</div>` : ''}
            </div>
          </div>
        </div>
        <div class="automation-rule-meta">
          <span><span class="material-symbols-outlined mi-sm">play_circle</span> ${rule.trigger_count || 0}x ausgeloest</span>
          <span><span class="material-symbols-outlined mi-sm">schedule</span> ${timeAgo(rule.last_triggered_at)}</span>
        </div>
      </div>
    `;
  }

  // ── Render: Create/Edit Form ──

  function renderConfigFields(fields, values) {
    if (!fields || !fields.length) return '';
    return fields.map(f => {
      const val = (values && values[f.key]) || '';
      if (f.type === 'select' && f.options) {
        const opts = f.options.map(o =>
          `<option value="${o.value}" ${val === o.value ? 'selected' : ''}>${escapeHtml(o.label)}</option>`
        ).join('');
        return `
          <div class="automation-field">
            <label>${escapeHtml(f.label)}${f.required ? ' *' : ''}</label>
            <select class="input" data-config-key="${f.key}">${opts}</select>
          </div>`;
      }
      if (f.type === 'textarea') {
        return `
          <div class="automation-field">
            <label>${escapeHtml(f.label)}${f.required ? ' *' : ''}</label>
            <textarea class="input" data-config-key="${f.key}" placeholder="${escapeHtml(f.placeholder || '')}" rows="2">${escapeHtml(val)}</textarea>
          </div>`;
      }
      const inputType = f.type === 'number' ? 'number' : f.type === 'time' ? 'time' : 'text';
      return `
        <div class="automation-field">
          <label>${escapeHtml(f.label)}${f.required ? ' *' : ''}</label>
          <input type="${inputType}" class="input" data-config-key="${f.key}" placeholder="${escapeHtml(f.placeholder || '')}" value="${escapeHtml(val)}" />
        </div>`;
    }).join('');
  }

  function renderForm() {
    if (!showForm || !meta) return '';

    const isEdit = !!editingRule;
    const rule = editingRule || {};
    const selTrigger = rule.trigger_type || (meta.triggers[0] && meta.triggers[0].id) || '';
    const selAction = rule.action_type || (meta.actions[0] && meta.actions[0].id) || '';

    const triggerEntry = meta.triggers.find(t => t.id === selTrigger);
    const actionEntry = meta.actions.find(a => a.id === selAction);

    return `
      <div class="card automation-form" id="automation-form">
        <h3>${isEdit ? 'Regel bearbeiten' : 'Neue Regel erstellen'}</h3>

        <div class="automation-field">
          <label>Name *</label>
          <input type="text" id="rule-name" class="input" placeholder="z.B. Morgenroutine" value="${escapeHtml(rule.name || '')}" />
        </div>
        <div class="automation-field">
          <label>Beschreibung</label>
          <input type="text" id="rule-description" class="input" placeholder="Kurze Beschreibung (optional)" value="${escapeHtml(rule.description || '')}" />
        </div>

        <div class="automation-section-label"><span class="material-symbols-outlined mi-sm">bolt</span> Wenn (Trigger)</div>
        <div class="automation-option-grid" id="trigger-options">
          ${meta.triggers.map(t => `
            <div class="automation-option-card ${t.id === selTrigger ? 'selected' : ''}" data-trigger="${t.id}">
              <span class="material-symbols-outlined">${t.icon}</span>
              <div class="automation-option-label">${t.label}</div>
              <div class="automation-option-desc">${t.description}</div>
            </div>
          `).join('')}
        </div>
        <div id="trigger-config-fields">
          ${renderConfigFields(triggerEntry ? triggerEntry.config_fields : [], rule.trigger_config)}
        </div>

        <div class="automation-section-label"><span class="material-symbols-outlined mi-sm">play_arrow</span> Dann (Aktion)</div>
        <div class="automation-option-grid" id="action-options">
          ${meta.actions.map(a => `
            <div class="automation-option-card ${a.id === selAction ? 'selected' : ''}" data-action-type="${a.id}">
              <span class="material-symbols-outlined">${a.icon}</span>
              <div class="automation-option-label">${a.label}</div>
              <div class="automation-option-desc">${a.description}</div>
            </div>
          `).join('')}
        </div>
        <div id="action-config-fields">
          ${renderConfigFields(actionEntry ? actionEntry.config_fields : [], rule.action_config)}
        </div>

        <div class="automation-form-buttons">
          <button class="btn btn-secondary" id="cancel-rule">Abbrechen</button>
          <button class="btn btn-primary" id="save-rule">${isEdit ? 'Speichern' : 'Erstellen'}</button>
        </div>
      </div>
    `;
  }

  // ── Render: Templates ──

  function renderTemplates() {
    if (!meta || !meta.templates || !meta.templates.length) return '';
    return `
      <div class="automation-templates">
        <div class="automation-section-label"><span class="material-symbols-outlined mi-sm">auto_fix_high</span> Vorlagen</div>
        <div class="automation-template-grid">
          ${meta.templates.map((tpl, i) => `
            <div class="automation-template-card" data-template="${i}">
              <div class="automation-template-name">${escapeHtml(tpl.name)}</div>
              <div class="automation-template-desc">${escapeHtml(tpl.description)}</div>
              <div class="automation-template-flow">
                <span class="material-symbols-outlined mi-sm">${triggerIcon(tpl.trigger_type)}</span>
                ${triggerLabel(tpl.trigger_type)}
                <span class="material-symbols-outlined mi-sm" style="margin:0 4px">arrow_forward</span>
                <span class="material-symbols-outlined mi-sm">${actionIcon(tpl.action_type)}</span>
                ${actionLabel(tpl.action_type)}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // ── Render: Main ──

  function renderList() {
    if (loading) {
      return '<div class="loading"><div class="spinner"></div></div>';
    }
    if (!rules.length) {
      return `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-secondary)">smart_toy</span>
          <p>Keine Automationen vorhanden</p>
          <p style="font-size:var(--text-sm);color:var(--text-secondary)">Erstelle Wenn-Dann Regeln, um Ablaeufe zu automatisieren.</p>
        </div>
        ${renderTemplates()}
      `;
    }
    return rules.map(renderRule).join('');
  }

  function update() {
    if (!container) return;
    const activeCount = rules.filter(r => r.active).length;
    container.innerHTML = `
      <a class="view-back" href="#/dashboard"><span class="material-symbols-outlined mi-sm">arrow_back</span> Dashboard</a>
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">smart_toy</span> Automationen
      </div>
      <div class="flex-between mb-8">
        <div>
          ${activeCount > 0 ? `<span style="font-size:var(--text-sm);color:var(--text-secondary)">${activeCount} aktive Regel${activeCount !== 1 ? 'n' : ''}</span>` : ''}
        </div>
        <div style="display:flex;gap:8px">
          ${rules.length > 0 ? `<button class="btn btn-sm btn-secondary" id="evaluate-btn" ${evaluating ? 'disabled' : ''}>
            <span class="material-symbols-outlined mi-sm">${evaluating ? 'hourglass_top' : 'play_circle'}</span> ${evaluating ? 'Pruefe...' : 'Jetzt pruefen'}
          </button>` : ''}
          <button class="btn btn-sm btn-primary" id="add-rule-btn">
            <span class="material-symbols-outlined mi-sm">add</span> Neue Regel
          </button>
        </div>
      </div>
      ${renderForm()}
      <div class="automation-list">
        ${renderList()}
      </div>
    `;
    bindEvents();
  }

  // ── Events ──

  function bindEvents() {
    if (!container) return;

    // Add rule
    container.querySelector('#add-rule-btn')?.addEventListener('click', () => {
      editingRule = null;
      showForm = !showForm;
      update();
    });

    // Cancel form
    container.querySelector('#cancel-rule')?.addEventListener('click', () => {
      showForm = false;
      editingRule = null;
      update();
    });

    // Evaluate
    container.querySelector('#evaluate-btn')?.addEventListener('click', async () => {
      evaluating = true;
      update();
      try {
        const result = await Api.evaluateAutomation();
        const msg = result.triggered > 0
          ? `${result.triggered} von ${result.evaluated} Regeln ausgeloest`
          : `${result.evaluated} Regeln geprueft – keine ausgeloest`;
        Toast.show(msg, result.triggered > 0 ? 'success' : 'info');
        await load();
      } catch (err) {
        Toast.show('Fehler: ' + err.message, 'error');
      } finally {
        evaluating = false;
        update();
      }
    });

    // Trigger option cards
    container.querySelectorAll('#trigger-options .automation-option-card').forEach(card => {
      card.addEventListener('click', () => {
        container.querySelectorAll('#trigger-options .automation-option-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        const triggerId = card.dataset.trigger;
        const entry = meta.triggers.find(t => t.id === triggerId);
        const configEl = container.querySelector('#trigger-config-fields');
        if (configEl) configEl.innerHTML = renderConfigFields(entry ? entry.config_fields : [], {});
      });
    });

    // Action option cards
    container.querySelectorAll('#action-options .automation-option-card').forEach(card => {
      card.addEventListener('click', () => {
        container.querySelectorAll('#action-options .automation-option-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        const actionId = card.dataset.actionType;
        const entry = meta.actions.find(a => a.id === actionId);
        const configEl = container.querySelector('#action-config-fields');
        if (configEl) configEl.innerHTML = renderConfigFields(entry ? entry.config_fields : [], {});
      });
    });

    // Save rule
    container.querySelector('#save-rule')?.addEventListener('click', async () => {
      const name = container.querySelector('#rule-name')?.value?.trim();
      if (!name) {
        Toast.show('Bitte einen Namen eingeben.', 'error');
        return;
      }

      const selTrigger = container.querySelector('#trigger-options .automation-option-card.selected');
      const selAction = container.querySelector('#action-options .automation-option-card.selected');

      if (!selTrigger || !selAction) {
        Toast.show('Bitte Trigger und Aktion auswaehlen.', 'error');
        return;
      }

      const triggerConfig = {};
      container.querySelectorAll('#trigger-config-fields [data-config-key]').forEach(el => {
        const v = el.value.trim();
        if (v) triggerConfig[el.dataset.configKey] = v;
      });

      const actionConfig = {};
      container.querySelectorAll('#action-config-fields [data-config-key]').forEach(el => {
        const v = el.value.trim();
        if (v) actionConfig[el.dataset.configKey] = v;
      });

      // Validate required fields
      const triggerId = selTrigger.dataset.trigger;
      const actionId = selAction.dataset.actionType;
      const triggerEntry = meta.triggers.find(t => t.id === triggerId);
      const actionEntry = meta.actions.find(a => a.id === actionId);

      for (const f of (triggerEntry?.config_fields || [])) {
        if (f.required && !triggerConfig[f.key]) {
          Toast.show(`Trigger-Feld "${f.label}" ist erforderlich.`, 'error');
          return;
        }
      }
      for (const f of (actionEntry?.config_fields || [])) {
        if (f.required && !actionConfig[f.key]) {
          Toast.show(`Aktions-Feld "${f.label}" ist erforderlich.`, 'error');
          return;
        }
      }

      const data = {
        name,
        description: container.querySelector('#rule-description')?.value?.trim() || '',
        trigger_type: triggerId,
        trigger_config: triggerConfig,
        action_type: actionId,
        action_config: actionConfig,
      };

      try {
        if (editingRule) {
          await Api.updateAutomationRule(editingRule.id, data);
        } else {
          await Api.createAutomationRule(data);
        }
        showForm = false;
        editingRule = null;
        await load();
      } catch (err) {
        Toast.show('Fehler: ' + err.message, 'error');
      }
    });

    // Template cards
    container.querySelectorAll('.automation-template-card').forEach(card => {
      card.addEventListener('click', () => {
        const idx = parseInt(card.dataset.template, 10);
        const tpl = meta.templates[idx];
        if (!tpl) return;
        editingRule = { ...tpl };
        showForm = true;
        update();
      });
    });

    // Per-rule actions
    container.querySelectorAll('.automation-rule-card[data-id]').forEach(card => {
      const id = card.dataset.id;

      card.querySelector('[data-action="toggle"]')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        try {
          const result = await Api.toggleAutomationRule(id);
          const rule = rules.find(r => r.id === id);
          if (rule) Object.assign(rule, result);
          update();
        } catch (_) { /* Toast handles error */ }
      });

      card.querySelector('[data-action="delete"]')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm('Regel wirklich loeschen?')) return;
        try {
          await Api.deleteAutomationRule(id);
          rules = rules.filter(r => r.id !== id);
          update();
        } catch (_) { /* Toast handles error */ }
      });
    });
  }

  // ── Load Data ──

  async function load() {
    loading = true;
    update();
    try {
      const [rulesData, metaData] = await Promise.all([
        Api.getAutomationRules(),
        meta ? Promise.resolve(meta) : Api.getAutomationMeta(),
      ]);
      rules = rulesData;
      meta = metaData;
    } catch (err) {
      rules = [];
      if (container) {
        container.innerHTML = `
          <div class="section-header">
            <span class="section-icon material-symbols-outlined">smart_toy</span> Automationen
          </div>
          <div class="error-state">
            <p>Fehler beim Laden: ${err.message}</p>
            <button class="btn btn-sm btn-primary" id="auto-retry-btn">Erneut versuchen</button>
          </div>
        `;
        container.querySelector('#auto-retry-btn')?.addEventListener('click', load);
      }
      return;
    } finally {
      loading = false;
    }
    update();
  }

  async function render(el) {
    container = el;
    showForm = false;
    editingRule = null;
    meta = null;
    await load();
  }

  return { render };
})();
