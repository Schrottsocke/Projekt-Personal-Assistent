/**
 * Command Palette – Globale Suche + Schnellaktionen (Ctrl+K / Cmd+K)
 */
const CommandPalette = (() => {
  let overlay = null;
  let input = null;
  let resultsList = null;
  let activeIndex = -1;
  let debounceTimer = null;
  let currentResults = [];
  let isOpen = false;

  const quickActions = [
    { icon: 'add_task', label: 'Task anlegen', route: '#/tasks', action: 'task' },
    { icon: 'event', label: 'Termin anlegen', route: '#/calendar', action: 'calendar' },
    { icon: 'add_shopping_cart', label: 'Einkaufsartikel hinzufügen', route: '#/shopping', action: 'shopping' },
    { icon: 'chat', label: 'Chat öffnen', route: '#/chat', action: 'chat' },
    { icon: 'summarize', label: 'Briefing abrufen', route: '#/dashboard', action: 'dashboard' },
  ];

  const typeIcons = {
    task: 'task_alt',
    shopping: 'shopping_cart',
    chat: 'chat_bubble',
    drive: 'folder',
    calendar: 'event',
  };

  function open() {
    if (isOpen) return;
    isOpen = true;
    activeIndex = -1;
    currentResults = [];

    overlay = document.createElement('div');
    overlay.className = 'command-palette-overlay';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    overlay.innerHTML = `
      <div class="command-palette">
        <div class="command-palette-input-wrap">
          <span class="material-symbols-outlined">search</span>
          <input type="text" class="command-palette-input" placeholder="Suchen oder Aktion ausführen…" autocomplete="off">
          <kbd class="command-palette-kbd">ESC</kbd>
        </div>
        <div class="command-palette-results"></div>
      </div>
    `;

    document.body.appendChild(overlay);
    input = overlay.querySelector('.command-palette-input');
    resultsList = overlay.querySelector('.command-palette-results');

    input.addEventListener('input', onInput);
    input.addEventListener('keydown', onKeydown);
    input.focus();

    renderQuickActions();
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    if (debounceTimer) clearTimeout(debounceTimer);
    if (overlay && overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
    overlay = null;
    input = null;
    resultsList = null;
  }

  function toggle() {
    isOpen ? close() : open();
  }

  function renderQuickActions() {
    if (!resultsList) return;
    resultsList.innerHTML = `
      <div class="command-palette-group">Schnellaktionen</div>
      <div class="command-palette-actions">
        ${quickActions.map((a, i) => `
          <div class="command-palette-item${i === activeIndex ? ' active' : ''}" data-index="${i}" data-route="${escapeHtml(a.route)}">
            <span class="material-symbols-outlined">${a.icon}</span>
            <span>${escapeHtml(a.label)}</span>
          </div>
        `).join('')}
      </div>
    `;
    currentResults = quickActions.map(a => ({ route: a.route }));
    bindItemClicks();
  }

  function renderSearchResults(results) {
    if (!resultsList) return;
    currentResults = results;

    if (results.length === 0) {
      resultsList.innerHTML = '<div class="command-palette-empty">Keine Ergebnisse gefunden</div>';
      return;
    }

    // Group by type
    const grouped = {};
    results.forEach(r => {
      if (!grouped[r.type]) grouped[r.type] = [];
      grouped[r.type].push(r);
    });

    const typeLabels = {
      task: 'Aufgaben',
      shopping: 'Einkauf',
      chat: 'Chat',
      drive: 'Dateien',
      calendar: 'Kalender',
    };

    let html = '';
    let globalIdx = 0;
    for (const [type, items] of Object.entries(grouped)) {
      html += `<div class="command-palette-group">${escapeHtml(typeLabels[type] || type)}</div>`;
      for (const item of items) {
        const icon = typeIcons[type] || 'article';
        html += `
          <div class="command-palette-item${globalIdx === activeIndex ? ' active' : ''}" data-index="${globalIdx}" data-route="${escapeHtml(item.route)}">
            <span class="material-symbols-outlined">${icon}</span>
            <div class="command-palette-item-text">
              <div class="command-palette-item-title">${escapeHtml(item.title)}</div>
              ${item.subtitle ? `<div class="command-palette-item-subtitle">${escapeHtml(item.subtitle)}</div>` : ''}
            </div>
          </div>
        `;
        globalIdx++;
      }
    }

    resultsList.innerHTML = html;
    bindItemClicks();
  }

  function bindItemClicks() {
    if (!resultsList) return;
    resultsList.querySelectorAll('.command-palette-item').forEach(el => {
      el.addEventListener('click', () => {
        const route = el.dataset.route;
        if (route) {
          close();
          window.location.hash = route;
        }
      });
    });
  }

  function onInput() {
    const q = input.value.trim();
    activeIndex = -1;

    if (!q) {
      renderQuickActions();
      return;
    }

    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        const results = await Api.searchGlobal(q);
        if (input && input.value.trim() === q) {
          renderSearchResults(results);
        }
      } catch (e) {
        if (resultsList) {
          resultsList.innerHTML = '<div class="command-palette-empty">Suche fehlgeschlagen</div>';
        }
      }
    }, 300);
  }

  function onKeydown(e) {
    const total = currentResults.length;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % Math.max(total, 1);
      updateActive();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = activeIndex <= 0 ? total - 1 : activeIndex - 1;
      updateActive();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < total) {
        const items = resultsList.querySelectorAll('.command-palette-item');
        const item = items[activeIndex];
        if (item && item.dataset.route) {
          close();
          window.location.hash = item.dataset.route;
        }
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      close();
    }
  }

  function updateActive() {
    if (!resultsList) return;
    resultsList.querySelectorAll('.command-palette-item').forEach((el, i) => {
      el.classList.toggle('active', i === activeIndex);
    });
    // Scroll active into view
    const active = resultsList.querySelector('.command-palette-item.active');
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  return { open, close, toggle };
})();
