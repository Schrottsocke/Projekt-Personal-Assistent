/**
 * Quick Capture – Universal text-first input for fast creation
 * (Task, Shopping Item, Reminder, Note)
 */
const QuickCapture = (() => {
  let fab = null;
  let overlay = null;
  let isOpen = false;
  let detectedType = 'note';
  let selectedType = 'note';
  let manualOverride = false;
  let inputEl = null;

  const captureTypes = [
    { key: 'task',     icon: 'add_task',            label: 'Task',       route: '#/tasks' },
    { key: 'shopping', icon: 'add_shopping_cart',    label: 'Einkauf',    route: '#/shopping' },
    { key: 'reminder', icon: 'notifications_active', label: 'Erinnerung', route: '#/notifications' },
    { key: 'note',     icon: 'note_add',             label: 'Notiz',      route: '#/chat' },
  ];

  // ── Classification patterns (evaluated in order) ──

  const classifyRules = [
    // Shopping – high: starts with buy-verb
    { type: 'shopping', confidence: 'high', test: (t) => /^(kauf[e]?|buy|besorg[e]?|hol[e]?)\s/i.test(t) },
    // Shopping – low: quantity pattern
    { type: 'shopping', confidence: 'low',  test: (t) => /\d+\s*(x|stueck|stück|kg|g|ml|l|liter|packung|pkg|dose[n]?|flasche[n]?)\b/i.test(t) },
    // Reminder – high: explicit reminder words
    { type: 'reminder', confidence: 'high', test: (t) => /\b(erinner[a-z]*|remind|weck[a-z]*|alarm)\b/i.test(t) },
    // Reminder – low: time expressions
    { type: 'reminder', confidence: 'low',  test: (t) => /\bum\s+\d{1,2}(:\d{2})?\s*(uhr)?\b/i.test(t) },
    // Task – high: action keywords
    { type: 'task', confidence: 'high', test: (t) => /\b(todo|aufgabe|muss|mach[e]?|erledige[n]?|fertig|abgabe|deadline)\b/i.test(t) },
    // Note – high: explicit note keywords
    { type: 'note', confidence: 'high', test: (t) => /\b(notiz|note|merk[e]?|merke\s*dir)\b/i.test(t) },
  ];

  function classify(text) {
    const t = text.trim();
    if (!t) return { type: 'note', confidence: 'low' };

    // First pass: find high-confidence match
    for (const rule of classifyRules) {
      if (rule.confidence === 'high' && rule.test(t)) {
        return { type: rule.type, confidence: 'high' };
      }
    }
    // Second pass: find low-confidence match
    for (const rule of classifyRules) {
      if (rule.confidence === 'low' && rule.test(t)) {
        return { type: rule.type, confidence: 'low' };
      }
    }
    // Fallback
    return { type: 'note', confidence: 'low' };
  }

  // ── Init ──

  function init() {
    if (fab) return;
    fab = document.createElement('button');
    fab.className = 'quick-capture-fab hidden';
    fab.innerHTML = '<span class="material-symbols-outlined">add</span>';
    fab.addEventListener('click', toggle);
    document.getElementById('app').appendChild(fab);

    window.addEventListener('hashchange', updateVisibility);
    updateVisibility();

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen) { close(); return; }
      if (e.ctrlKey && e.shiftKey && e.code === 'Space') {
        e.preventDefault();
        if (Api.isLoggedIn()) toggle();
      }
    });
  }

  function updateVisibility() {
    if (!fab) return;
    const hash = window.location.hash;
    if (hash === '#/login' || hash === '' || !Api.isLoggedIn()) {
      fab.classList.add('hidden');
    } else {
      fab.classList.remove('hidden');
    }
  }

  function toggle() {
    isOpen ? close() : open();
  }

  // ── Open / Close ──

  function open() {
    if (isOpen) return;
    isOpen = true;
    detectedType = 'note';
    selectedType = 'note';
    manualOverride = false;

    overlay = document.createElement('div');
    overlay.className = 'quick-capture-overlay';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    const sheet = document.createElement('div');
    sheet.className = 'quick-capture-sheet';

    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const hotkeyLabel = isMac ? '⌃⇧Space' : 'Ctrl+Shift+Space';

    sheet.innerHTML = `
      <div class="quick-capture-header">
        <h3>Schnell erfassen</h3>
        <kbd class="qc-hotkey-hint">${escapeHtml(hotkeyLabel)}</kbd>
        <button class="modal-close" onclick="QuickCapture.close()">&times;</button>
      </div>
      <div class="quick-capture-form">
        <input type="text" id="qc-input" class="input" placeholder="Was m\u00f6chtest du erfassen?" autofocus>
      </div>
      <div class="quick-capture-types">
        ${captureTypes.map(t => `
          <button class="quick-capture-chip" data-type="${t.key}">
            <span class="material-symbols-outlined">${t.icon}</span>
            ${escapeHtml(t.label)}
          </button>
        `).join('')}
      </div>
      <div class="qc-actions">
        <button class="btn btn-primary qc-save" disabled onclick="QuickCapture.save()">Speichern</button>
      </div>
    `;

    overlay.appendChild(sheet);
    document.body.appendChild(overlay);

    // Bind events
    inputEl = sheet.querySelector('#qc-input');
    inputEl.addEventListener('input', onInputChange);
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        save();
      }
    });

    sheet.querySelectorAll('.quick-capture-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        manualOverride = true;
        selectedType = chip.dataset.type;
        updateChips({ type: selectedType, confidence: 'high' });
      });
    });

    setTimeout(() => { if (inputEl) inputEl.focus(); }, 50);
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    detectedType = 'note';
    selectedType = 'note';
    manualOverride = false;
    inputEl = null;
    if (overlay && overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
    overlay = null;
  }

  // ── Real-time classification ──

  function onInputChange() {
    const text = inputEl.value.trim();
    const saveBtn = overlay.querySelector('.qc-save');

    if (!text) {
      detectedType = 'note';
      selectedType = 'note';
      manualOverride = false;
      saveBtn.disabled = true;
      updateChips(null);
      return;
    }

    saveBtn.disabled = false;
    const result = classify(text);
    detectedType = result.type;

    // Only auto-select if user hasn't manually overridden
    if (!manualOverride) {
      selectedType = result.type;
    }

    updateChips(manualOverride ? { type: selectedType, confidence: 'high' } : result);
  }

  function updateChips(result) {
    if (!overlay) return;
    overlay.querySelectorAll('.quick-capture-chip').forEach(chip => {
      chip.classList.remove('active', 'suggested');
      if (result && chip.dataset.type === result.type) {
        if (result.confidence === 'high') {
          chip.classList.add('active');
        } else {
          chip.classList.add('suggested');
        }
      }
    });
  }

  // ── Save ──

  async function save() {
    if (!inputEl) return;
    const text = inputEl.value.trim();
    if (!text) return;

    const type = selectedType;
    const typeInfo = captureTypes.find(t => t.key === type);
    const saveBtn = overlay ? overlay.querySelector('.qc-save') : null;

    // Disable button to prevent double submit
    if (saveBtn) saveBtn.disabled = true;

    try {
      switch (type) {
        case 'task':
          await Api.createTask({ title: text, description: '' });
          break;
        case 'shopping': {
          const itemName = text.replace(/^(kauf[e]?|buy|besorg[e]?|hol[e]?)\s+/i, '');
          await Api.addShoppingItem(itemName);
          break;
        }
        case 'reminder':
          await Api.createNotification({ type: 'reminder', title: text });
          break;
        case 'note':
          await Api.sendMessage('Notiz: ' + text);
          break;
      }
      close();
      showSuccessSnackbar(typeInfo.label, typeInfo.route);
    } catch (e) {
      if (e.isOffline && typeof OfflineQueue !== 'undefined') {
        if (type === 'task') {
          OfflineQueue.enqueue({
            type: 'task_create',
            endpoint: '/tasks',
            method: 'POST',
            body: { title: text, description: '' },
            label: text,
          });
          close();
          showSnackbar('Task gespeichert f\u00fcr sp\u00e4ter');
        } else if (type === 'shopping') {
          const itemName = text.replace(/^(kauf[e]?|buy|besorg[e]?|hol[e]?)\s+/i, '');
          OfflineQueue.enqueue({
            type: 'shopping_add',
            endpoint: '/shopping/items',
            method: 'POST',
            body: { name: itemName },
            label: itemName,
          });
          close();
          showSnackbar('Artikel gespeichert f\u00fcr sp\u00e4ter');
        } else {
          if (saveBtn) saveBtn.disabled = false;
          showSnackbar('Du bist offline \u2013 bitte sp\u00e4ter erneut versuchen');
        }
      } else {
        if (saveBtn) saveBtn.disabled = false;
        showSnackbar('Fehler beim Speichern');
      }
    }
  }

  // ── Feedback ──

  function showSuccessSnackbar(typeLabel, route) {
    const existing = document.querySelector('.snackbar');
    if (existing) existing.remove();

    const snackbar = document.createElement('div');
    snackbar.className = 'snackbar qc-snackbar-success';
    snackbar.innerHTML = `
      <span>${escapeHtml(typeLabel)} gespeichert</span>
      <a class="qc-snackbar-action">Anzeigen</a>
    `;

    snackbar.querySelector('.qc-snackbar-action').addEventListener('click', (e) => {
      e.preventDefault();
      snackbar.remove();
      Router.navigate(route);
    });

    document.body.appendChild(snackbar);
    setTimeout(() => {
      snackbar.classList.add('snackbar-hide');
      setTimeout(() => snackbar.remove(), 300);
    }, 4000);
  }

  function showSnackbar(message) {
    const existing = document.querySelector('.snackbar');
    if (existing) existing.remove();

    const snackbar = document.createElement('div');
    snackbar.className = 'snackbar';
    snackbar.textContent = message;
    document.body.appendChild(snackbar);

    setTimeout(() => {
      snackbar.classList.add('snackbar-hide');
      setTimeout(() => snackbar.remove(), 300);
    }, 3000);
  }

  function selectType(type) {
    if (!overlay) return;
    manualOverride = true;
    selectedType = type;
    updateChips({ type, confidence: 'high' });
  }

  return { init, open, close, save, selectType };
})();
