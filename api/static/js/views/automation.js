/**
 * DualMind Automation View
 * Regel- und Automationscenter fuer bereichsuebergreifende Workflows.
 */
const AutomationView = (() => {
  let rules = [];
  let loading = false;
  let container = null;
  let showForm = false;

  const TRIGGER_TYPES = {
    schedule:  { icon: 'schedule',       label: 'Zeitplan' },
    event:     { icon: 'bolt',           label: 'Ereignis' },
    condition: { icon: 'rule',           label: 'Bedingung' },
  };

  const ACTION_TYPES = {
    notification: { icon: 'notifications', label: 'Benachrichtigung' },
    task:         { icon: 'check_circle',  label: 'Aufgabe' },
    email:        { icon: 'email',         label: 'E-Mail' },
    inbox:        { icon: 'inbox',         label: 'Inbox-Eintrag' },
  };

  function renderRule(rule) {
    const trigger = TRIGGER_TYPES[rule.trigger_type] || TRIGGER_TYPES.event;
    const action = ACTION_TYPES[rule.action_type] || ACTION_TYPES.notification;

    return `
      <div class="card" data-id="${rule.id}" style="margin-bottom:12px">
        <div style="display:flex;align-items:center;gap:12px">
          <div style="flex:1">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
              <span class="material-symbols-outlined" style="font-size:18px;color:${rule.active ? 'var(--accent)' : 'var(--text-secondary)'}">${rule.active ? 'toggle_on' : 'toggle_off'}</span>
              <strong>${rule.name}</strong>
              ${!rule.active ? '<span class="badge" style="font-size:10px">Inaktiv</span>' : ''}
            </div>
            ${rule.description ? `<p style="color:var(--text-secondary);font-size:13px;margin:4px 0">${rule.description}</p>` : ''}
            <div style="display:flex;gap:12px;font-size:12px;color:var(--text-secondary);margin-top:6px">
              <span><span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle">${trigger.icon}</span> ${trigger.label}</span>
              <span>→</span>
              <span><span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle">${action.icon}</span> ${action.label}</span>
              <span>Ausloesungen: ${rule.trigger_count || 0}</span>
            </div>
          </div>
          <div style="display:flex;gap:4px">
            <button class="btn-icon" data-action="toggle" title="${rule.active ? 'Deaktivieren' : 'Aktivieren'}">
              <span class="material-symbols-outlined">${rule.active ? 'pause' : 'play_arrow'}</span>
            </button>
            <button class="btn-icon" data-action="delete" title="Loeschen">
              <span class="material-symbols-outlined">delete</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function renderForm() {
    if (!showForm) return '';
    return `
      <div class="card" id="automation-form" style="margin-bottom:16px">
        <h3 style="margin-bottom:12px">Neue Regel erstellen</h3>
        <div style="display:flex;flex-direction:column;gap:10px">
          <input type="text" id="rule-name" class="input" placeholder="Name der Regel" />
          <textarea id="rule-description" class="input" placeholder="Beschreibung (optional)" rows="2"></textarea>
          <div style="display:flex;gap:10px">
            <select id="rule-trigger-type" class="input" style="flex:1">
              <option value="schedule">Zeitplan</option>
              <option value="event">Ereignis</option>
              <option value="condition">Bedingung</option>
            </select>
            <select id="rule-action-type" class="input" style="flex:1">
              <option value="notification">Benachrichtigung</option>
              <option value="task">Aufgabe</option>
              <option value="email">E-Mail</option>
              <option value="inbox">Inbox-Eintrag</option>
            </select>
          </div>
          <div style="display:flex;gap:8px;justify-content:flex-end">
            <button class="btn btn-sm btn-secondary" id="cancel-rule">Abbrechen</button>
            <button class="btn btn-sm btn-primary" id="save-rule">Erstellen</button>
          </div>
        </div>
      </div>
    `;
  }

  function renderList() {
    if (loading) {
      return '<div class="loading"><div class="spinner"></div></div>';
    }
    if (!rules.length) {
      return `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-secondary)">smart_toy</span>
          <p>Keine Automatisierungen vorhanden</p>
          <p style="font-size:13px;color:var(--text-secondary)">Erstelle Regeln wie "Wenn X, dann Y" fuer automatische Workflows.</p>
        </div>
      `;
    }
    return rules.map(renderRule).join('');
  }

  async function load() {
    loading = true;
    update();
    try {
      rules = await Api.getAutomationRules();
    } catch (err) {
      rules = [];
      if (container) {
        container.innerHTML = `
          <div class="section-header">
            <h2><span class="material-symbols-outlined">smart_toy</span> Automation</h2>
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

  function update() {
    if (!container) return;
    const activeCount = rules.filter(r => r.active).length;
    container.innerHTML = `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">smart_toy</span> Automation</h2>
        <button class="btn btn-sm btn-primary" id="add-rule-btn">
          <span class="material-symbols-outlined" style="font-size:16px">add</span> Neue Regel
        </button>
      </div>
      ${activeCount > 0 ? `<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">${activeCount} aktive Regel${activeCount !== 1 ? 'n' : ''}</p>` : ''}
      ${renderForm()}
      <div class="automation-list">
        ${renderList()}
      </div>
    `;
    bindEvents();
  }

  function bindEvents() {
    if (!container) return;

    // Add rule button
    container.querySelector('#add-rule-btn')?.addEventListener('click', () => {
      showForm = !showForm;
      update();
    });

    // Cancel form
    container.querySelector('#cancel-rule')?.addEventListener('click', () => {
      showForm = false;
      update();
    });

    // Save rule
    container.querySelector('#save-rule')?.addEventListener('click', async () => {
      const name = container.querySelector('#rule-name')?.value?.trim();
      if (!name) {
        Toast.show('Bitte einen Namen eingeben.', 'error');
        return;
      }
      const data = {
        name,
        description: container.querySelector('#rule-description')?.value?.trim() || '',
        trigger_type: container.querySelector('#rule-trigger-type')?.value || 'event',
        trigger_config: {},
        action_type: container.querySelector('#rule-action-type')?.value || 'notification',
        action_config: {},
      };
      try {
        await Api.createAutomationRule(data);
        showForm = false;
        await load();
      } catch (_) { /* Toast handles error */ }
    });

    // Per-rule actions
    container.querySelectorAll('.card[data-id]').forEach(card => {
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

  async function render(el) {
    container = el;
    showForm = false;
    await load();
  }

  return { render };
})();
