/**
 * Onboarding View – Step-by-step setup for new private customers.
 * Steps: 1) Profile, 2) Product Lines, 3) First Action, 4) Dashboard
 */
const OnboardingView = (() => {

  const PRODUCT_LINES = [
    { id: 'finance', icon: 'account_balance', name: 'Finanzhub', desc: 'Ausgaben, Vertraege, Budgets und Rechnungen verwalten' },
    { id: 'inventory', icon: 'inventory_2', name: 'Haushaltsordner', desc: 'Inventar, Garantien und Dokumente organisieren' },
    { id: 'family', icon: 'family_restroom', name: 'Familien-Modus', desc: 'Gemeinsamer Workspace mit Aufgaben-Rotation' },
  ];

  const FIRST_ACTIONS = {
    finance: { label: 'CSV-Import oder erste Ausgabe', route: '#/finance' },
    inventory: { label: 'Erstes Dokument scannen', route: '#/documents' },
    family: { label: 'Workspace erstellen', route: '#/family' },
  };

  let state = { step: 1, name: '', household_size: 'single', has_side_business: false, lines: {}, widgets: [] };

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  async function render(container) {
    // Load current status
    try {
      const status = await Api.get('/onboarding/status');
      if (status.is_onboarded) {
        window.location.hash = '#/dashboard';
        return;
      }
      state.step = Math.max(1, (status.current_step || 0) + 1);
      if (state.step > 4) state.step = 4;
      state.lines = status.product_lines || {};
      state.household_size = status.household_size || 'single';
      state.has_side_business = status.has_side_business || false;
    } catch { /* fresh start */ }

    renderStep(container);
  }

  function renderStep(container) {
    const step = state.step;
    container.innerHTML = `
      <div class="onboarding-container">
        <div class="onboarding-progress">
          ${[1,2,3,4].map(s => `<div class="onboarding-step-dot ${s === step ? 'active' : ''} ${s < step ? 'done' : ''}">${s}</div>`).join('<div class="onboarding-step-line"></div>')}
        </div>
        <div class="onboarding-title">Schritt ${step} von 4</div>
        <div id="onboarding-content"></div>
        <div class="onboarding-actions">
          ${step > 1 ? '<button class="btn btn-secondary" id="ob-back">Zurueck</button>' : ''}
          <button class="btn btn-secondary" id="ob-skip">Ueberspringen</button>
          <button class="btn btn-primary" id="ob-next">Weiter</button>
        </div>
      </div>
    `;

    const content = document.getElementById('onboarding-content');
    if (step === 1) renderProfileStep(content);
    else if (step === 2) renderProductLinesStep(content);
    else if (step === 3) renderFirstActionStep(content);
    else if (step === 4) renderDashboardStep(content);

    document.getElementById('ob-next')?.addEventListener('click', () => handleNext(container));
    document.getElementById('ob-skip')?.addEventListener('click', () => handleSkip(container));
    document.getElementById('ob-back')?.addEventListener('click', () => { state.step = Math.max(1, state.step - 1); renderStep(container); });
  }

  function renderProfileStep(el) {
    el.innerHTML = `
      <h2>Willkommen! Erzaehl uns von dir.</h2>
      <div class="form-group">
        <label for="ob-name">Dein Name</label>
        <input type="text" id="ob-name" class="input" placeholder="Name" value="${escapeHtml(state.name)}" />
      </div>
      <div class="form-group">
        <label>Haushaltsgroesse</label>
        <div class="ob-radio-group">
          ${['single', 'couple', 'family'].map(v => `
            <label class="ob-radio ${state.household_size === v ? 'selected' : ''}">
              <input type="radio" name="household" value="${v}" ${state.household_size === v ? 'checked' : ''} />
              ${v === 'single' ? 'Einzelperson' : v === 'couple' ? 'Paar' : 'Familie mit Kindern'}
            </label>
          `).join('')}
        </div>
      </div>
      <div class="form-group">
        <label class="ob-checkbox">
          <input type="checkbox" id="ob-business" ${state.has_side_business ? 'checked' : ''} />
          Nebengewerbe aktiv (Rechnungs-Feature)
        </label>
      </div>
    `;
    el.querySelectorAll('input[name="household"]').forEach(r => {
      r.addEventListener('change', () => { state.household_size = r.value; renderProfileStep(el); });
    });
  }

  function renderProductLinesStep(el) {
    el.innerHTML = `
      <h2>Welche Bereiche moechtest du nutzen?</h2>
      <div class="ob-product-grid">
        ${PRODUCT_LINES.map(pl => `
          <div class="ob-product-card ${state.lines[pl.id] ? 'selected' : ''}" data-line="${pl.id}">
            <span class="material-symbols-outlined ob-product-icon">${pl.icon}</span>
            <div class="ob-product-name">${pl.name}</div>
            <div class="ob-product-desc">${pl.desc}</div>
            ${pl.id === 'finance' ? '<div class="ob-privacy-hint">Finanzdaten werden lokal verarbeitet</div>' : ''}
          </div>
        `).join('')}
      </div>
    `;
    el.querySelectorAll('.ob-product-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.dataset.line;
        state.lines[id] = !state.lines[id];
        card.classList.toggle('selected', state.lines[id]);
      });
    });
  }

  function renderFirstActionStep(el) {
    const active = PRODUCT_LINES.filter(pl => state.lines[pl.id]);
    if (active.length === 0) {
      el.innerHTML = `<h2>Erste Schritte</h2><p>Du hast keine Produktlinie aktiviert. Du kannst diesen Schritt ueberspringen.</p>`;
      return;
    }
    el.innerHTML = `
      <h2>Starte mit einer ersten Aktion</h2>
      <div class="ob-action-list">
        ${active.map(pl => {
          const action = FIRST_ACTIONS[pl.id];
          return `
            <div class="card ob-action-card">
              <span class="material-symbols-outlined">${pl.icon}</span>
              <div>
                <div class="card-title">${pl.name}</div>
                <div class="card-subtitle">${action.label}</div>
              </div>
              <a href="${action.route}" class="btn btn-secondary btn-sm">Starten</a>
            </div>
          `;
        }).join('')}
      </div>
      <p class="ob-hint">Du kannst dies auch spaeter nachholen.</p>
    `;
  }

  function renderDashboardStep(el) {
    const defaultWidgets = ['notifications', 'events', 'tasks', 'shopping'];
    const extraWidgets = [];
    if (state.lines.finance) extraWidgets.push({ id: 'finance', label: 'Finanzhub' });
    if (state.lines.inventory) extraWidgets.push({ id: 'inventory', label: 'Haushaltsordner' });
    if (state.lines.family) extraWidgets.push({ id: 'family', label: 'Familien-Hub' });

    if (!state.widgets || state.widgets.length === 0) {
      state.widgets = [...defaultWidgets, ...extraWidgets.map(w => w.id)];
    }

    el.innerHTML = `
      <h2>Dein Dashboard einrichten</h2>
      <p>Welche Widgets moechtest du sehen?</p>
      <div class="ob-widget-list">
        ${[...defaultWidgets.map(id => ({ id, label: id.charAt(0).toUpperCase() + id.slice(1) })), ...extraWidgets].map(w => `
          <label class="ob-checkbox ob-widget-check">
            <input type="checkbox" value="${w.id}" ${state.widgets.includes(w.id) ? 'checked' : ''} />
            ${w.label}
          </label>
        `).join('')}
      </div>
    `;
    el.querySelectorAll('.ob-widget-check input').forEach(cb => {
      cb.addEventListener('change', () => {
        if (cb.checked && !state.widgets.includes(cb.value)) state.widgets.push(cb.value);
        else state.widgets = state.widgets.filter(w => w !== cb.value);
      });
    });
  }

  async function handleNext(container) {
    const step = state.step;
    try {
      if (step === 1) {
        const name = document.getElementById('ob-name')?.value?.trim() || '';
        if (!name) { alert('Bitte gib deinen Namen ein.'); return; }
        state.name = name;
        state.has_side_business = document.getElementById('ob-business')?.checked || false;
        await Api.post('/onboarding/profile', {
          name: state.name,
          household_size: state.household_size,
          has_side_business: state.has_side_business,
        });
      } else if (step === 2) {
        await Api.post('/onboarding/product-lines', {
          finance: !!state.lines.finance,
          inventory: !!state.lines.inventory,
          family: !!state.lines.family,
        });
      } else if (step === 3) {
        const active = PRODUCT_LINES.filter(pl => state.lines[pl.id]);
        for (const pl of active) {
          await Api.post('/onboarding/first-action', { action: pl.id });
        }
      } else if (step === 4) {
        await Api.post('/onboarding/dashboard', { widgets: state.widgets });
        await Api.post('/onboarding/complete', {});
        window.location.hash = '#/dashboard';
        return;
      }
    } catch (err) {
      console.error('Onboarding error:', err);
    }
    state.step = Math.min(4, step + 1);
    renderStep(container);
  }

  async function handleSkip(container) {
    if (state.step === 4) {
      try { await Api.post('/onboarding/complete', {}); } catch { /* ignore */ }
      window.location.hash = '#/dashboard';
      return;
    }
    state.step = Math.min(4, state.step + 1);
    renderStep(container);
  }

  return { render };
})();
