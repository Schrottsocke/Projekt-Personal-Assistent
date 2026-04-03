/**
 * Quick Capture – FAB fuer schnelle Erstellung (Task, Termin, Einkauf, Notiz)
 */
const QuickCapture = (() => {
  let fab = null;
  let overlay = null;
  let isOpen = false;
  let currentType = null;

  const captureTypes = [
    { key: 'task', icon: 'add_task', label: 'Task' },
    { key: 'event', icon: 'event', label: 'Termin' },
    { key: 'shopping', icon: 'add_shopping_cart', label: 'Einkauf' },
    { key: 'note', icon: 'note_add', label: 'Notiz' },
  ];

  function init() {
    if (fab) return;
    fab = document.createElement('button');
    fab.className = 'quick-capture-fab hidden';
    fab.innerHTML = '<span class="material-symbols-outlined">add</span>';
    fab.addEventListener('click', toggle);
    document.getElementById('app').appendChild(fab);

    // Show/hide FAB based on route
    window.addEventListener('hashchange', updateVisibility);
    updateVisibility();

    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen) close();
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

  function open() {
    if (isOpen) return;
    isOpen = true;
    currentType = null;

    overlay = document.createElement('div');
    overlay.className = 'quick-capture-overlay';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    const sheet = document.createElement('div');
    sheet.className = 'quick-capture-sheet';
    sheet.innerHTML = `
      <div class="quick-capture-header">
        <h3>Schnell erfassen</h3>
        <button class="modal-close" onclick="QuickCapture.close()">&times;</button>
      </div>
      <div class="quick-capture-types">
        ${captureTypes.map(t => `
          <button class="quick-capture-chip" data-type="${t.key}">
            <span class="material-symbols-outlined">${t.icon}</span>
            ${escapeHtml(t.label)}
          </button>
        `).join('')}
      </div>
      <div class="quick-capture-form"></div>
    `;

    overlay.appendChild(sheet);
    document.body.appendChild(overlay);

    // Bind type chips
    sheet.querySelectorAll('.quick-capture-chip').forEach(chip => {
      chip.addEventListener('click', () => selectType(chip.dataset.type));
    });
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    currentType = null;
    if (overlay && overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
    overlay = null;
  }

  function selectType(type) {
    currentType = type;
    const form = overlay.querySelector('.quick-capture-form');
    if (!form) return;

    // Highlight active chip
    overlay.querySelectorAll('.quick-capture-chip').forEach(c => {
      c.classList.toggle('active', c.dataset.type === type);
    });

    switch (type) {
      case 'task':
        form.innerHTML = `
          <input type="text" id="qc-title" class="input" placeholder="Aufgabe…" autofocus>
          <button class="btn btn-primary qc-save" onclick="QuickCapture.save()">Speichern</button>
        `;
        break;
      case 'event':
        form.innerHTML = `
          <input type="text" id="qc-title" class="input" placeholder="Termin-Titel…" autofocus>
          <input type="datetime-local" id="qc-start" class="input">
          <button class="btn btn-primary qc-save" onclick="QuickCapture.save()">Speichern</button>
        `;
        break;
      case 'shopping':
        form.innerHTML = `
          <input type="text" id="qc-title" class="input" placeholder="Artikel…" autofocus>
          <button class="btn btn-primary qc-save" onclick="QuickCapture.save()">Speichern</button>
        `;
        break;
      case 'note':
        form.innerHTML = `
          <input type="text" id="qc-title" class="input" placeholder="Notiz…" autofocus>
          <button class="btn btn-primary qc-save" onclick="QuickCapture.save()">Speichern</button>
        `;
        break;
    }

    // Focus and enter-to-save
    const titleInput = form.querySelector('#qc-title');
    if (titleInput) {
      setTimeout(() => titleInput.focus(), 50);
      form.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          save();
        }
      });
    }
  }

  async function save() {
    const titleEl = overlay ? overlay.querySelector('#qc-title') : null;
    if (!titleEl) return;
    const title = titleEl.value.trim();
    if (!title) return;

    try {
      switch (currentType) {
        case 'task':
          await Api.createTask({ title, description: '' });
          showSnackbar('Task gespeichert');
          break;
        case 'event': {
          const startEl = overlay.querySelector('#qc-start');
          const start = startEl ? startEl.value : '';
          if (!start) {
            showSnackbar('Bitte Startzeit angeben');
            return;
          }
          const startDate = new Date(start);
          const endDate = new Date(startDate.getTime() + 60 * 60 * 1000);
          await Api.createCalendarEvent({
            summary: title,
            start: startDate.toISOString(),
            end: endDate.toISOString(),
          });
          showSnackbar('Termin gespeichert');
          break;
        }
        case 'shopping':
          await Api.addShoppingItem(title);
          showSnackbar('Artikel hinzugef\u00fcgt');
          break;
        case 'note':
          await Api.sendMessage(`Notiz: ${title}`);
          showSnackbar('Notiz gespeichert');
          break;
      }
      close();
    } catch (e) {
      if (e.isOffline && typeof OfflineQueue !== 'undefined') {
        // Queue task and shopping captures; events and notes need server
        if (currentType === 'task') {
          OfflineQueue.enqueue({
            type: 'task_create',
            endpoint: '/tasks',
            method: 'POST',
            body: { title, description: '' },
            label: title,
          });
          showSnackbar('Task gespeichert f\u00fcr sp\u00e4ter');
          close();
        } else if (currentType === 'shopping') {
          OfflineQueue.enqueue({
            type: 'shopping_add',
            endpoint: '/shopping/items',
            method: 'POST',
            body: { name: title },
            label: title,
          });
          showSnackbar('Artikel gespeichert f\u00fcr sp\u00e4ter');
          close();
        } else {
          showSnackbar('Du bist offline \u2013 bitte sp\u00e4ter erneut versuchen');
        }
      } else {
        showSnackbar('Fehler beim Speichern');
      }
    }
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

  return { init, open, close, save };
})();
