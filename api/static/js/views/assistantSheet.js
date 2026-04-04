/**
 * Assistant Sheet – Bottom-Sheet mit Chat, Quick-Actions und Schnellerfassung.
 * Ersetzt CommandPalette und QuickCapture als einheitliche Eingabeschicht.
 * Ueberall verfuegbar via FAB oder Ctrl+K.
 */
const AssistantSheet = (() => {
  let overlay = null;
  let isOpen = false;
  let sending = false;
  let lastMessages = [];

  // Kontextabhaengige Vorschlaege pro Route
  const CONTEXT_ACTIONS = {
    '#/dashboard': [
      { label: 'Briefing', msg: 'Gib mir ein Briefing fuer heute', icon: 'wb_sunny' },
      { label: 'Was steht an?', msg: 'Was steht heute an?', icon: 'calendar_month' },
      { label: 'Offene Aufgaben', msg: 'Zeig mir offene Aufgaben', icon: 'check_circle' },
    ],
    '#/shopping': [
      { label: 'Rezept suchen', msg: 'Schlage mir ein Rezept vor', icon: 'restaurant' },
      { label: 'Was fehlt?', msg: 'Was fehlt auf meiner Einkaufsliste?', icon: 'help' },
    ],
    '#/planen': [
      { label: 'Woche planen', msg: 'Hilf mir die Woche zu planen', icon: 'event_note' },
      { label: 'Was koche ich?', msg: 'Was koche ich heute Abend?', icon: 'restaurant' },
    ],
    '#/inbox': [
      { label: 'Zusammenfassung', msg: 'Fasse meine offenen Punkte zusammen', icon: 'summarize' },
    ],
    _default: [
      { label: 'Briefing', msg: 'Gib mir ein Briefing', icon: 'wb_sunny' },
      { label: 'Was koche ich?', msg: 'Was koche ich heute Abend?', icon: 'restaurant' },
      { label: 'Einkaufsliste', msg: 'Zeig die Einkaufsliste', icon: 'shopping_cart' },
      { label: 'Offene Aufgaben', msg: 'Zeig mir offene Aufgaben', icon: 'check_circle' },
    ],
  };

  // QuickCapture Klassifizierung (aus quickCapture.js uebernommen)
  const CAPTURE_RULES = [
    { type: 'shopping', test: (t) => /^(kauf[e]?|buy|besorg[e]?|hol[e]?)\s/i.test(t) },
    { type: 'shopping', test: (t) => /\d+\s*(x|stueck|stück|kg|g|ml|l|liter|packung|pkg|dose[n]?|flasche[n]?)\b/i.test(t) },
    { type: 'task', test: (t) => /\b(todo|aufgabe|muss|mach[e]?|erledige[n]?|fertig|abgabe|deadline)\b/i.test(t) },
    { type: 'reminder', test: (t) => /\b(erinner[a-z]*|remind|weck[a-z]*|alarm)\b/i.test(t) },
  ];

  function classifyInput(text) {
    const t = text.trim();
    for (const rule of CAPTURE_RULES) {
      if (rule.test(t)) return rule.type;
    }
    return null; // kein spezieller Typ → normaler Chat
  }

  function getContextActions() {
    const hash = window.location.hash || '#/dashboard';
    // Suche nach exaktem Match oder Parent-Route
    return CONTEXT_ACTIONS[hash] || CONTEXT_ACTIONS._default;
  }

  // ── Init: FAB und Keyboard ──

  function init() {
    // FAB erstellen
    const fab = document.createElement('button');
    fab.className = 'assistant-fab hidden';
    fab.id = 'assistant-fab';
    fab.innerHTML = '<span class="material-symbols-outlined">chat_bubble</span>';
    fab.addEventListener('click', toggle);
    document.getElementById('app').appendChild(fab);

    // Sichtbarkeit
    window.addEventListener('hashchange', updateFabVisibility);
    updateFabVisibility();

    // Keyboard: Ctrl+K / Cmd+K und Escape
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        SearchView.show();
      }
      if (e.key === 'Escape' && isOpen) close();
    });
  }

  function updateFabVisibility() {
    const fab = document.getElementById('assistant-fab');
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

    overlay = document.createElement('div');
    overlay.className = 'assistant-overlay';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    const sheet = document.createElement('div');
    sheet.className = 'assistant-sheet';
    sheet.innerHTML = buildSheetHTML();
    overlay.appendChild(sheet);
    document.body.appendChild(overlay);

    // Einfahren animieren
    requestAnimationFrame(() => {
      overlay.classList.add('open');
    });

    bindEvents(sheet);
    loadRecentMessages();

    const input = sheet.querySelector('#assistant-input');
    if (input) setTimeout(() => input.focus(), 100);
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    if (overlay) {
      overlay.classList.remove('open');
      setTimeout(() => {
        if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
        overlay = null;
      }, 200);
    }
  }

  function buildSheetHTML() {
    const actions = getContextActions();
    return `
      <div class="assistant-sheet-handle"></div>
      <div class="assistant-sheet-header">
        <span class="assistant-sheet-title">Assistent</span>
        <a href="#/chat" class="assistant-sheet-link" onclick="AssistantSheet.close()">
          Verlauf <span class="material-symbols-outlined" style="font-size:16px;vertical-align:-3px">open_in_new</span>
        </a>
      </div>
      <div class="assistant-messages" id="assistant-messages">
        <div class="assistant-messages-placeholder">
          <span class="material-symbols-outlined" style="font-size:32px;color:var(--text-muted)">chat_bubble_outline</span>
        </div>
      </div>
      <div class="assistant-actions" id="assistant-actions">
        ${actions.map(a => `
          <button class="assistant-action-chip" data-msg="${Utils.escapeHtml(a.msg)}">
            <span class="material-symbols-outlined" style="font-size:16px">${a.icon}</span>
            ${a.label}
          </button>
        `).join('')}
      </div>
      <div class="assistant-capture-hint hidden" id="assistant-capture-hint"></div>
      <div class="assistant-input-area">
        <input type="text" id="assistant-input" class="input" placeholder="Nachricht oder Schnellerfassung…" autocomplete="off">
        <button class="btn btn-primary btn-icon" id="assistant-send">
          <span class="material-symbols-outlined">send</span>
        </button>
      </div>
    `;
  }

  function bindEvents(sheet) {
    const input = sheet.querySelector('#assistant-input');
    const sendBtn = sheet.querySelector('#assistant-send');

    // Send
    sendBtn.addEventListener('click', () => handleSend(input));
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend(input);
      }
    });

    // Quick action chips
    sheet.querySelectorAll('[data-msg]').forEach(chip => {
      chip.addEventListener('click', () => {
        input.value = chip.dataset.msg;
        handleSend(input);
      });
    });

    // Live-Klassifizierung
    input.addEventListener('input', () => {
      const text = input.value.trim();
      const hint = sheet.querySelector('#assistant-capture-hint');
      if (!text || text.length < 3) {
        hint.classList.add('hidden');
        return;
      }
      const type = classifyInput(text);
      if (type) {
        const labels = { shopping: 'Einkauf', task: 'Aufgabe', reminder: 'Erinnerung' };
        hint.innerHTML = `<span class="material-symbols-outlined" style="font-size:14px">lightbulb</span> Wird als <strong>${labels[type]}</strong> erkannt – Enter zum Speichern`;
        hint.classList.remove('hidden');
      } else {
        hint.classList.add('hidden');
      }
    });
  }

  // ── Senden / Schnellerfassung ──

  async function handleSend(input) {
    if (sending) return;
    const text = input.value.trim();
    if (!text) return;

    const captureType = classifyInput(text);
    input.value = '';
    const hint = overlay?.querySelector('#assistant-capture-hint');
    if (hint) hint.classList.add('hidden');

    // Schnellerfassung: direkt anlegen ohne Chat
    if (captureType) {
      await handleCapture(captureType, text);
      return;
    }

    // Normaler Chat
    sending = true;
    const messagesEl = overlay?.querySelector('#assistant-messages');
    if (!messagesEl) { sending = false; return; }

    // Placeholder entfernen
    const placeholder = messagesEl.querySelector('.assistant-messages-placeholder');
    if (placeholder) placeholder.remove();

    // User-Nachricht anzeigen
    messagesEl.innerHTML += `<div class="assistant-msg user">${Utils.escapeHtml(text)}</div>`;
    messagesEl.innerHTML += `<div class="assistant-msg assistant typing"><span class="typing-dots"><span></span><span></span><span></span></span></div>`;
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // Quick Actions ausblenden
    const actionsEl = overlay?.querySelector('#assistant-actions');
    if (actionsEl) actionsEl.style.display = 'none';

    try {
      let fullResponse = '';
      const typingEl = messagesEl.querySelector('.typing');

      await Api.sendMessageStream(
        text,
        null,
        (token) => {
          fullResponse += token;
          if (typingEl) {
            typingEl.classList.remove('typing');
            typingEl.textContent = fullResponse;
          }
          messagesEl.scrollTop = messagesEl.scrollHeight;
        },
        () => {
          if (typingEl) typingEl.textContent = fullResponse;
          messagesEl.scrollTop = messagesEl.scrollHeight;
        },
        () => {
          // Fallback bei Stream-Fehler
          Api.sendMessage(text).then(r => {
            if (typingEl) {
              typingEl.classList.remove('typing');
              typingEl.textContent = r.response;
            }
          }).catch(() => {
            if (typingEl) {
              typingEl.classList.remove('typing');
              typingEl.textContent = 'Fehler beim Senden.';
              typingEl.style.color = 'var(--error)';
            }
          });
        }
      );
    } catch {
      const typingEl = messagesEl.querySelector('.typing');
      if (typingEl) {
        typingEl.classList.remove('typing');
        typingEl.textContent = 'Fehler beim Senden.';
        typingEl.style.color = 'var(--error)';
      }
    } finally {
      sending = false;
      if (actionsEl) actionsEl.style.display = '';
    }
  }

  async function handleCapture(type, text) {
    const messagesEl = overlay?.querySelector('#assistant-messages');
    const placeholder = messagesEl?.querySelector('.assistant-messages-placeholder');
    if (placeholder) placeholder.remove();

    const labels = { shopping: 'Einkauf', task: 'Aufgabe', reminder: 'Erinnerung' };
    const routes = { shopping: '#/shopping', task: '#/tasks', reminder: '#/inbox' };

    try {
      if (type === 'task') {
        await Api.createTask({ title: text, description: '' });
      } else if (type === 'shopping') {
        const itemName = text.replace(/^(kauf[e]?|buy|besorg[e]?|hol[e]?)\s+/i, '');
        await Api.addShoppingItem(itemName);
      } else if (type === 'reminder') {
        await Api.createNotification({ type: 'reminder', title: text });
      }

      if (messagesEl) {
        messagesEl.innerHTML += `
          <div class="assistant-msg assistant">
            ${labels[type]} gespeichert: „${Utils.escapeHtml(text)}"
            <a href="${routes[type]}" onclick="AssistantSheet.close()" style="display:block;margin-top:4px;color:var(--accent)">Anzeigen →</a>
          </div>
        `;
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }
    } catch (e) {
      if (e.isOffline && typeof OfflineQueue !== 'undefined') {
        const endpoint = type === 'task' ? '/tasks' : type === 'shopping' ? '/shopping/items' : null;
        if (endpoint) {
          OfflineQueue.enqueue({
            type: `${type}_create`,
            endpoint,
            method: 'POST',
            body: type === 'task' ? { title: text } : { name: text },
            label: text,
          });
          if (messagesEl) {
            messagesEl.innerHTML += `<div class="assistant-msg assistant">${labels[type]} gespeichert (wird synchronisiert wenn online)</div>`;
          }
        }
      } else if (messagesEl) {
        messagesEl.innerHTML += `<div class="assistant-msg assistant" style="color:var(--error)">Fehler beim Speichern.</div>`;
      }
    }
  }

  // ── Letzte Nachrichten laden ──

  async function loadRecentMessages() {
    try {
      const messages = await Api.getChatHistory(4);
      if (messages.length === 0) return;
      const messagesEl = overlay?.querySelector('#assistant-messages');
      if (!messagesEl) return;

      messagesEl.innerHTML = messages.map(m =>
        `<div class="assistant-msg ${m.role}">${Utils.escapeHtml(m.content.length > 150 ? m.content.slice(0, 150) + '…' : m.content)}</div>`
      ).join('');
      messagesEl.scrollTop = messagesEl.scrollHeight;
    } catch {
      // Stille Fehlerbehandlung – Verlauf ist optional
    }
  }

  return { init, open, close, toggle };
})();
