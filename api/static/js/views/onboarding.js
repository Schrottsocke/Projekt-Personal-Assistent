/**
 * Onboarding View – 6-step guided setup wizard for new users.
 * Steps: 1) Welcome + usage type, 2) Name household, 3) Choose area,
 *        4a/4b/4c) CSV/Doc/Skip, 5) Notification channel, 6) Done
 *
 * Issue #719: Enhanced multi-step wizard with progress indicator,
 * back/forward navigation, skippable steps, and API integration.
 */
const OnboardingView = (() => {

  const TOTAL_STEPS = 6;

  const USAGE_TYPES = [
    { id: 'solo', icon: 'person', label: 'Solo', desc: 'Nur fuer mich allein' },
    { id: 'partner', icon: 'group', label: 'Partner', desc: 'Gemeinsam zu zweit' },
    { id: 'family', icon: 'family_restroom', label: 'Familie', desc: 'Haushalt mit Kindern' },
  ];

  const AREA_CHOICES = [
    { id: 'finanzen', icon: 'account_balance', label: 'Finanzen', desc: 'Ausgaben, Budgets & Vertraege' },
    { id: 'dokumente', icon: 'description', label: 'Dokumente', desc: 'Scannen, ablegen & finden' },
    { id: 'haushalt', icon: 'home', label: 'Haushalt', desc: 'Listen, Aufgaben & Routinen' },
    { id: 'alles', icon: 'select_all', label: 'Alles', desc: 'Alle Bereiche auf einmal' },
  ];

  const NOTIFICATION_CHANNELS = [
    { id: 'push', icon: 'notifications_active', label: 'Push', desc: 'Browser-Benachrichtigungen' },
    { id: 'telegram', icon: 'send', label: 'Telegram', desc: 'Nachrichten via Telegram Bot' },
    { id: 'email', icon: 'email', label: 'E-Mail', desc: 'Benachrichtigungen per E-Mail' },
    { id: 'none', icon: 'notifications_off', label: 'Keine', desc: 'Spaeter einrichten' },
  ];

  let state = {
    step: 1,
    usage_type: '',
    household_name: '',
    area: '',
    csv_file: null,
    notification_channel: 'none',
    telegram_chat_id: '',
  };

  function esc(str) {
    const d = document.createElement('div');
    d.textContent = str || '';
    return d.innerHTML;
  }

  async function render(container) {
    try {
      const status = await Api.get('/onboarding/status');
      if (status && status.is_onboarded) {
        window.location.hash = '#/dashboard';
        return;
      }
      if (status && status.current_step) {
        state.step = Math.max(1, Math.min(TOTAL_STEPS, status.current_step));
      }
      // Restore any previously saved partial data
      if (status && status.usage_type) state.usage_type = status.usage_type;
      if (status && status.household_name) state.household_name = status.household_name;
      if (status && status.area) state.area = status.area;
      if (status && status.notification_channel) state.notification_channel = status.notification_channel;
    } catch { /* fresh start */ }

    renderStep(container);
  }

  function renderStep(container) {
    const step = state.step;
    container.innerHTML = `
      <div class="onboarding-container">
        <div class="onboarding-progress">
          ${Array.from({ length: TOTAL_STEPS }, (_, i) => i + 1).map(s => `
            <div class="onboarding-step-dot ${s === step ? 'active' : ''} ${s < step ? 'done' : ''}"
                 ${s < step ? `onclick="OnboardingView.goToStep(${s})" style="cursor:pointer"` : ''}>
              ${s < step ? '<span class="material-symbols-outlined" style="font-size:14px">check</span>' : s}
            </div>
            ${s < TOTAL_STEPS ? `<div class="onboarding-step-line ${s < step ? 'done' : ''}"></div>` : ''}
          `).join('')}
        </div>
        <div class="onboarding-progress-text">Schritt ${step} von ${TOTAL_STEPS}</div>
        <div id="onboarding-content"></div>
        <div class="onboarding-actions">
          ${step > 1 ? '<button class="btn btn-secondary" id="ob-back"><span class="material-symbols-outlined mi-sm">arrow_back</span> Zurueck</button>' : '<span></span>'}
          <div class="onboarding-actions-right">
            ${step < TOTAL_STEPS ? '<button class="btn btn-secondary" id="ob-skip">Ueberspringen</button>' : ''}
            <button class="btn btn-primary" id="ob-next">${step === TOTAL_STEPS ? 'Abschliessen' : 'Weiter'} <span class="material-symbols-outlined mi-sm">${step === TOTAL_STEPS ? 'check' : 'arrow_forward'}</span></button>
          </div>
        </div>
      </div>
    `;

    const content = document.getElementById('onboarding-content');
    if (step === 1) renderWelcomeStep(content);
    else if (step === 2) renderHouseholdStep(content);
    else if (step === 3) renderAreaStep(content);
    else if (step === 4) renderAreaActionStep(content);
    else if (step === 5) renderNotificationStep(content);
    else if (step === 6) renderDoneStep(content);

    document.getElementById('ob-next')?.addEventListener('click', () => handleNext(container));
    document.getElementById('ob-skip')?.addEventListener('click', () => handleSkip(container));
    document.getElementById('ob-back')?.addEventListener('click', () => { state.step = Math.max(1, state.step - 1); renderStep(container); });
  }

  function goToStep(step) {
    if (step < state.step) {
      state.step = step;
      const container = document.getElementById('view-container');
      if (container) renderStep(container);
    }
  }

  /* -- Step 1: Welcome + Usage Type -- */
  function renderWelcomeStep(el) {
    el.innerHTML = `
      <div class="ob-step-content">
        <div class="ob-welcome-icon"><span class="material-symbols-outlined" style="font-size:48px;color:var(--accent)">waving_hand</span></div>
        <h2>Willkommen bei DualMind!</h2>
        <p class="text-muted mb-16">Wie moechtest du DualMind nutzen?</p>
        <div class="ob-choice-grid">
          ${USAGE_TYPES.map(t => `
            <div class="ob-choice-card ${state.usage_type === t.id ? 'selected' : ''}" data-value="${t.id}">
              <span class="material-symbols-outlined ob-choice-icon">${t.icon}</span>
              <div class="ob-choice-label">${t.label}</div>
              <div class="ob-choice-desc">${t.desc}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
    el.querySelectorAll('.ob-choice-card').forEach(card => {
      card.addEventListener('click', () => {
        state.usage_type = card.dataset.value;
        el.querySelectorAll('.ob-choice-card').forEach(c => c.classList.toggle('selected', c.dataset.value === state.usage_type));
      });
    });
  }

  /* -- Step 2: Name Household -- */
  function renderHouseholdStep(el) {
    el.innerHTML = `
      <div class="ob-step-content">
        <h2>Benenne deinen Haushalt</h2>
        <p class="text-muted mb-16">Gib deinem Workspace einen Namen.</p>
        <div class="form-group" style="max-width:400px;margin:0 auto">
          <input type="text" id="ob-household-name" class="input" placeholder="z.B. Familie Mueller, Unser Zuhause" value="${esc(state.household_name)}" />
        </div>
        <p class="ob-hint text-muted mt-12" style="text-align:center;font-size:0.85rem">Du kannst den Namen spaeter jederzeit aendern.</p>
      </div>
    `;
  }

  /* -- Step 3: Choose Area -- */
  function renderAreaStep(el) {
    el.innerHTML = `
      <div class="ob-step-content">
        <h2>Womit moechtest du starten?</h2>
        <p class="text-muted mb-16">Waehle deinen ersten Schwerpunkt.</p>
        <div class="ob-choice-grid ob-choice-grid-4">
          ${AREA_CHOICES.map(a => `
            <div class="ob-choice-card ${state.area === a.id ? 'selected' : ''}" data-value="${a.id}">
              <span class="material-symbols-outlined ob-choice-icon">${a.icon}</span>
              <div class="ob-choice-label">${a.label}</div>
              <div class="ob-choice-desc">${a.desc}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
    el.querySelectorAll('.ob-choice-card').forEach(card => {
      card.addEventListener('click', () => {
        state.area = card.dataset.value;
        el.querySelectorAll('.ob-choice-card').forEach(c => c.classList.toggle('selected', c.dataset.value === state.area));
      });
    });
  }

  /* -- Step 4: Area-specific action -- */
  function renderAreaActionStep(el) {
    if (state.area === 'finanzen' || state.area === 'alles') {
      renderCsvUploadStep(el);
    } else if (state.area === 'dokumente') {
      renderDocScanStep(el);
    } else {
      renderSkipActionStep(el);
    }
  }

  function renderCsvUploadStep(el) {
    el.innerHTML = `
      <div class="ob-step-content">
        <h2>Finanzdaten importieren</h2>
        <p class="text-muted mb-16">Lade eine CSV-Datei mit deinen Ausgaben hoch. Du kannst dies auch spaeter nachholen.</p>
        <div class="ob-upload-zone" id="ob-csv-drop">
          <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted)">upload_file</span>
          <p class="text-muted">CSV-Datei hierher ziehen oder klicken</p>
          <input type="file" id="ob-csv-input" accept=".csv" style="display:none" />
          <button class="btn btn-secondary" id="ob-csv-btn">Datei auswaehlen</button>
        </div>
        <div id="ob-csv-status" class="mt-8"></div>
      </div>
    `;
    const dropZone = document.getElementById('ob-csv-drop');
    const fileInput = document.getElementById('ob-csv-input');
    const btn = document.getElementById('ob-csv-btn');

    btn?.addEventListener('click', () => fileInput?.click());
    fileInput?.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        state.csv_file = e.target.files[0];
        document.getElementById('ob-csv-status').innerHTML = `<span class="badge badge-success">${esc(state.csv_file.name)}</span>`;
      }
    });
    dropZone?.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone?.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        state.csv_file = e.dataTransfer.files[0];
        document.getElementById('ob-csv-status').innerHTML = `<span class="badge badge-success">${esc(state.csv_file.name)}</span>`;
      }
    });
  }

  function renderDocScanStep(el) {
    el.innerHTML = `
      <div class="ob-step-content">
        <h2>Erstes Dokument scannen</h2>
        <p class="text-muted mb-16">Scanne oder fotografiere dein erstes Dokument, um die Ablage einzurichten.</p>
        <div class="ob-action-cards">
          <div class="ob-action-link card" id="ob-doc-scan-btn" style="cursor:pointer">
            <span class="material-symbols-outlined" style="font-size:32px;color:var(--accent)">document_scanner</span>
            <div>
              <div class="card-title">Dokument scannen</div>
              <div class="text-muted" style="font-size:0.85rem">Kamera oder Datei waehlen</div>
            </div>
          </div>
          <a href="#/documents" class="ob-action-link card">
            <span class="material-symbols-outlined" style="font-size:32px;color:var(--accent)">folder_open</span>
            <div>
              <div class="card-title">Dokumente-Bereich oeffnen</div>
              <div class="text-muted" style="font-size:0.85rem">Direkt zur Dokumentenverwaltung</div>
            </div>
          </a>
        </div>
        <p class="ob-hint text-muted mt-12">Du kannst dies auch spaeter nachholen.</p>
      </div>
    `;
    document.getElementById('ob-doc-scan-btn')?.addEventListener('click', () => {
      if (typeof CameraCapture !== 'undefined') {
        CameraCapture.open({ onCapture: (file) => {
          if (file) {
            Toast.show('Dokument erfasst: ' + file.name, 'success');
          }
        } });
      } else {
        window.location.hash = '#/documents';
      }
    });
  }

  function renderSkipActionStep(el) {
    el.innerHTML = `
      <div class="ob-step-content">
        <h2>Alles bereit!</h2>
        <p class="text-muted mb-16">Fuer den Bereich <strong>${esc(state.area || 'Haushalt')}</strong> brauchst du keine Erstdaten. Du kannst direkt loslegen.</p>
        <div style="text-align:center;padding:24px 0">
          <span class="material-symbols-outlined" style="font-size:64px;color:var(--accent)">rocket_launch</span>
        </div>
      </div>
    `;
  }

  /* -- Step 5: Notification Channel -- */
  function renderNotificationStep(el) {
    el.innerHTML = `
      <div class="ob-step-content">
        <h2>Wie moechtest du benachrichtigt werden?</h2>
        <p class="text-muted mb-16">Waehle deinen bevorzugten Benachrichtigungskanal.</p>
        <div class="ob-choice-grid ob-choice-grid-4">
          ${NOTIFICATION_CHANNELS.map(ch => `
            <div class="ob-choice-card ${state.notification_channel === ch.id ? 'selected' : ''}" data-value="${ch.id}">
              <span class="material-symbols-outlined ob-choice-icon">${ch.icon}</span>
              <div class="ob-choice-label">${ch.label}</div>
              <div class="ob-choice-desc">${ch.desc}</div>
            </div>
          `).join('')}
        </div>
        <div id="ob-channel-config" class="mt-16"></div>
      </div>
    `;
    el.querySelectorAll('.ob-choice-card').forEach(card => {
      card.addEventListener('click', () => {
        state.notification_channel = card.dataset.value;
        el.querySelectorAll('.ob-choice-card').forEach(c => c.classList.toggle('selected', c.dataset.value === state.notification_channel));
        renderChannelConfig();
      });
    });
    renderChannelConfig();
  }

  function renderChannelConfig() {
    const el = document.getElementById('ob-channel-config');
    if (!el) return;
    if (state.notification_channel === 'push') {
      el.innerHTML = `
        <div class="card" style="padding:12px">
          <p class="text-muted mb-8">Browser-Benachrichtigungen muessen aktiviert werden.</p>
          <button class="btn btn-secondary" id="ob-push-permission">
            <span class="material-symbols-outlined mi-sm">notifications_active</span> Berechtigung anfordern
          </button>
          <div id="ob-push-status" class="mt-8"></div>
        </div>
      `;
      document.getElementById('ob-push-permission')?.addEventListener('click', async () => {
        try {
          const result = await Notification.requestPermission();
          const statusEl = document.getElementById('ob-push-status');
          if (result === 'granted') {
            if (statusEl) statusEl.innerHTML = '<span class="badge badge-success">Berechtigung erteilt</span>';
          } else {
            if (statusEl) statusEl.innerHTML = '<span class="badge badge-warning">Berechtigung abgelehnt</span>';
          }
        } catch {
          Toast.show('Push-Berechtigung konnte nicht angefragt werden', 'error');
        }
      });
    } else if (state.notification_channel === 'telegram') {
      el.innerHTML = `
        <div class="card" style="padding:12px">
          <p class="text-muted mb-8">Gib deine Telegram Chat-ID ein, um Benachrichtigungen via Bot zu erhalten.</p>
          <div class="form-group" style="max-width:300px">
            <input type="text" id="ob-telegram-chat-id" class="input" placeholder="Chat-ID" value="${esc(state.telegram_chat_id)}" />
          </div>
          <p class="text-muted" style="font-size:0.8rem">Sende /start an @DualMindBot, um deine Chat-ID zu erhalten.</p>
        </div>
      `;
      document.getElementById('ob-telegram-chat-id')?.addEventListener('input', (e) => {
        state.telegram_chat_id = e.target.value.trim();
      });
    } else {
      el.innerHTML = '';
    }
  }

  /* -- Step 6: Done Screen -- */
  function renderDoneStep(el) {
    el.innerHTML = `
      <div class="ob-step-content ob-done-screen">
        <div class="ob-done-icon"><span class="material-symbols-outlined" style="font-size:64px;color:var(--accent)">celebration</span></div>
        <h2>Setup abgeschlossen!</h2>
        <p class="text-muted mb-16">DualMind ist bereit. Hier sind deine naechsten Schritte:</p>
        <div class="ob-action-cards">
          <a href="#/dashboard" class="ob-action-link card">
            <span class="material-symbols-outlined" style="font-size:28px;color:var(--accent)">dashboard</span>
            <div>
              <div class="card-title">Dashboard oeffnen</div>
              <div class="text-muted" style="font-size:0.85rem">Deine Tagesuebersicht</div>
            </div>
          </a>
          <a href="#/chat" class="ob-action-link card">
            <span class="material-symbols-outlined" style="font-size:28px;color:var(--accent)">chat</span>
            <div>
              <div class="card-title">Chat starten</div>
              <div class="text-muted" style="font-size:0.85rem">Frag den Assistenten</div>
            </div>
          </a>
          <a href="#/mehr" class="ob-action-link card">
            <span class="material-symbols-outlined" style="font-size:28px;color:var(--accent)">apps</span>
            <div>
              <div class="card-title">Alle Bereiche</div>
              <div class="text-muted" style="font-size:0.85rem">Entdecke alle Features</div>
            </div>
          </a>
        </div>
      </div>
    `;
  }

  /* -- Navigation -- */

  async function handleNext(container) {
    const step = state.step;
    try {
      if (step === 1) {
        if (!state.usage_type) { Toast.show('Bitte waehle einen Nutzungstyp', 'error'); return; }
      } else if (step === 2) {
        state.household_name = (document.getElementById('ob-household-name')?.value || '').trim();
      } else if (step === 4) {
        // CSV upload if file selected
        if (state.csv_file && (state.area === 'finanzen' || state.area === 'alles')) {
          try {
            await Api.uploadFile(state.csv_file, '/finance/import-csv');
            Toast.show('CSV erfolgreich importiert', 'success');
          } catch { /* non-blocking */ }
        }
      } else if (step === 5) {
        // Save telegram chat ID if provided
        if (state.notification_channel === 'telegram') {
          state.telegram_chat_id = (document.getElementById('ob-telegram-chat-id')?.value || '').trim();
        }
      } else if (step === TOTAL_STEPS) {
        // Save profile data via dedicated endpoint before completing
        if (state.usage_type || state.household_name) {
          const sizeMap = { solo: 'single', partner: 'couple', family: 'family' };
          try {
            await Api.post('/onboarding/profile', {
              name: state.household_name || '',
              household_size: sizeMap[state.usage_type] || 'single',
              has_side_business: false,
            });
          } catch { /* non-blocking, profile may already be saved */ }
        }
        // Save area selection as product-lines
        if (state.area) {
          const all = state.area === 'alles';
          try {
            await Api.post('/onboarding/product-lines', {
              finance: all || state.area === 'finanzen',
              inventory: all || state.area === 'dokumente',
              family: all || state.area === 'haushalt',
            });
          } catch { /* non-blocking */ }
        }
        // Save notification channel preference
        if (state.notification_channel && state.notification_channel !== 'none') {
          try {
            await Api.put('/notifications/preferences/general', {
              push_enabled: state.notification_channel === 'push',
              email_enabled: state.notification_channel === 'email',
              quiet_start: '22:00',
              quiet_end: '07:00',
            });
          } catch { /* non-blocking */ }
        }
        // Complete onboarding (endpoint accepts no body)
        await Api.post('/onboarding/complete');
        window.location.hash = '#/dashboard';
        return;
      }
    } catch (err) {
      console.error('Onboarding error:', err);
    }
    state.step = Math.min(TOTAL_STEPS, step + 1);
    renderStep(container);
  }

  async function handleSkip(container) {
    if (state.step === TOTAL_STEPS) {
      try { await Api.post('/onboarding/complete'); } catch { /* ignore */ }
      window.location.hash = '#/dashboard';
      return;
    }
    state.step = Math.min(TOTAL_STEPS, state.step + 1);
    renderStep(container);
  }

  return { render, goToStep };
})();
