/**
 * Command Palette – Globale Suche, Navigation & Schnellaktionen (Ctrl+K / Cmd+K)
 *
 * Schaltzentrale der App: Suche nach Inhalten, springe zu Bereichen,
 * fuehre Aktionen direkt aus. Mit Fuzzy-Matching und Suchverlauf.
 */
const CommandPalette = (() => {
  let overlay = null;
  let input = null;
  let resultsList = null;
  let activeIndex = -1;
  let debounceTimer = null;
  let currentItems = [];   // flat array of { route?, actionFn?, label }
  let isOpen = false;
  let searchRequestId = 0; // prevent stale API results

  // ── Search History (localStorage) ──
  const HISTORY_KEY = 'dm_search_history';
  const HISTORY_MAX = 8;

  function getHistory() {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    } catch { return []; }
  }

  function addToHistory(query) {
    if (!query || query.length < 2) return;
    const history = getHistory().filter(h => h !== query);
    history.unshift(query);
    if (history.length > HISTORY_MAX) history.length = HISTORY_MAX;
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(history)); } catch {}
  }

  function clearHistory() {
    try { localStorage.removeItem(HISTORY_KEY); } catch {}
  }

  // ── Fuzzy matching ──
  function fuzzyMatch(text, query) {
    const tLower = text.toLowerCase();
    const qLower = query.toLowerCase();

    // Exact substring match = best
    if (tLower.includes(qLower)) return { match: true, score: 100 };

    // Fuzzy: all query chars must appear in order
    let ti = 0;
    let matched = 0;
    let consecutive = 0;
    let maxConsecutive = 0;

    for (let qi = 0; qi < qLower.length; qi++) {
      const found = tLower.indexOf(qLower[qi], ti);
      if (found === -1) return { match: false, score: 0 };
      if (found === ti) {
        consecutive++;
        maxConsecutive = Math.max(maxConsecutive, consecutive);
      } else {
        consecutive = 1;
      }
      ti = found + 1;
      matched++;
    }

    // Score based on: matched ratio, consecutive bonus, position bonus
    const ratio = matched / tLower.length;
    const consecutiveBonus = maxConsecutive / qLower.length;
    const score = Math.round((ratio * 30) + (consecutiveBonus * 50) + 10);
    return { match: true, score: Math.min(score, 99) };
  }

  // ── Quick Actions ──
  const quickActions = [
    { icon: 'add_task', label: 'Neue Aufgabe anlegen', type: 'action', route: null, actionFn: () => openQuickCapture('task') },
    { icon: 'event', label: 'Neuen Termin anlegen', type: 'action', route: null, actionFn: () => openQuickCapture('event') },
    { icon: 'add_shopping_cart', label: 'Einkaufsartikel hinzufügen', type: 'action', route: null, actionFn: () => openQuickCapture('shopping') },
    { icon: 'note_add', label: 'Notiz erstellen', type: 'action', route: null, actionFn: () => openQuickCapture('note') },
    { icon: 'chat', label: 'Chat öffnen', type: 'action', route: '#/chat' },
    { icon: 'summarize', label: 'Briefing abrufen', type: 'action', route: '#/dashboard' },
    { icon: 'search', label: 'Rezepte suchen', type: 'action', route: '#/recipes' },
    { icon: 'restaurant_menu', label: 'Wochenplan öffnen', type: 'action', route: '#/mealplan' },
    { icon: 'scanner', label: 'Dokument scannen', type: 'action', route: '#/documents' },
    { icon: 'center_focus_strong', label: 'Fokus starten', type: 'action', route: '#/focus' },
  ];

  // ── Type metadata for API results ──
  const typeIcons = {
    task: 'task_alt', shopping: 'shopping_cart', chat: 'chat_bubble',
    drive: 'folder', calendar: 'event', recipe: 'restaurant',
    mealplan: 'restaurant_menu', note: 'note', document: 'scanner',
    memory: 'psychology',
  };

  const typeLabels = {
    task: 'Aufgaben', shopping: 'Einkauf', chat: 'Chat',
    drive: 'Dateien', calendar: 'Kalender', recipe: 'Rezepte',
    mealplan: 'Wochenplan', note: 'Notizen', document: 'Dokumente',
    memory: 'Gedächtnis',
  };

  // ── Navigation commands (lazy-built from NAV_META) ──
  let navCommands = null;

  function getNavCommands() {
    if (navCommands) return navCommands;
    const meta = window.AppPreferences?.NAV_META || {};
    navCommands = Object.entries(meta).map(([id, m]) => ({
      type: 'nav',
      icon: m.icon || 'arrow_forward',
      label: m.label,
      route: m.route,
      searchText: `${m.label} ${id}`.toLowerCase(),
    }));
    return navCommands;
  }

  // ── QuickCapture integration ──
  function openQuickCapture(type) {
    if (typeof QuickCapture !== 'undefined' && QuickCapture.open) {
      QuickCapture.open();
      if (QuickCapture.selectType) {
        setTimeout(() => QuickCapture.selectType(type), 50);
      }
    }
  }

  // ── Open / Close / Toggle ──
  function open() {
    if (isOpen) return;
    isOpen = true;
    activeIndex = -1;
    currentItems = [];
    searchRequestId = 0;

    overlay = document.createElement('div');
    overlay.className = 'command-palette-overlay';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    overlay.innerHTML = `
      <div class="command-palette">
        <div class="command-palette-input-wrap">
          <span class="material-symbols-outlined">search</span>
          <input type="text" class="command-palette-input" placeholder="Suchen, navigieren oder Aktion ausführen…" autocomplete="off">
          <kbd class="command-palette-kbd">ESC</kbd>
        </div>
        <div class="command-palette-loading-bar"></div>
        <div class="command-palette-results"></div>
        <div class="command-palette-footer">
          <span><kbd>↑↓</kbd> Navigieren</span>
          <span><kbd>↵</kbd> Öffnen</span>
          <span><kbd>Esc</kbd> Schließen</span>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    input = overlay.querySelector('.command-palette-input');
    resultsList = overlay.querySelector('.command-palette-results');

    input.addEventListener('input', onInput);
    input.addEventListener('keydown', onKeydown);
    input.focus();

    renderDefaultView();
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    if (debounceTimer) clearTimeout(debounceTimer);
    searchRequestId++;
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

  // ── Default view (empty query): History + Quick Actions + Navigation ──
  function renderDefaultView() {
    const navItems = getNavCommands();
    const history = getHistory();
    const items = [];
    let html = '';

    // Search history section
    if (history.length > 0) {
      html += '<div class="command-palette-group cp-group-with-action">Letzte Suchen<button class="cp-clear-history" type="button">Löschen</button></div>';
      for (const term of history) {
        const idx = items.length;
        items.push({ historyTerm: term });
        html += renderItem('history', term, '', idx);
      }
    }

    // Quick Actions section
    html += '<div class="command-palette-group">Schnellaktionen</div>';
    for (const a of quickActions) {
      const idx = items.length;
      items.push({ route: a.route, actionFn: a.actionFn });
      html += renderItem(a.icon, a.label, '', idx);
    }

    // Navigation section
    html += '<div class="command-palette-group">Navigation</div>';
    for (const n of navItems) {
      const idx = items.length;
      items.push({ route: n.route });
      html += renderItem(n.icon, n.label, '', idx);
    }

    currentItems = items;
    if (resultsList) {
      resultsList.innerHTML = html;
      bindItemClicks();
      // Bind clear-history button
      const clearBtn = resultsList.querySelector('.cp-clear-history');
      if (clearBtn) {
        clearBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          clearHistory();
          renderDefaultView();
        });
      }
    }
  }

  // ── Filtered view (with query): client-side matches + API results ──
  function renderFilteredView(query, apiResults, isLoading) {
    const q = query.toLowerCase();
    const items = [];
    let html = '';

    // Client-side: matching navigation (fuzzy)
    const navMatches = getNavCommands()
      .map(n => ({ ...n, ...fuzzyMatch(n.searchText, q) }))
      .filter(n => n.match)
      .sort((a, b) => b.score - a.score);
    if (navMatches.length > 0) {
      html += '<div class="command-palette-group">Navigation</div>';
      for (const n of navMatches) {
        const idx = items.length;
        items.push({ route: n.route });
        html += renderItem(n.icon, n.label, '', idx);
      }
    }

    // Client-side: matching quick actions (fuzzy)
    const actionMatches = quickActions
      .map(a => ({ ...a, ...fuzzyMatch(a.label, q) }))
      .filter(a => a.match)
      .sort((a, b) => b.score - a.score);
    if (actionMatches.length > 0) {
      html += '<div class="command-palette-group">Schnellaktionen</div>';
      for (const a of actionMatches) {
        const idx = items.length;
        items.push({ route: a.route, actionFn: a.actionFn });
        html += renderItem(a.icon, a.label, '', idx);
      }
    }

    // API results grouped by type
    if (apiResults && apiResults.length > 0) {
      const grouped = {};
      for (const r of apiResults) {
        if (!grouped[r.type]) grouped[r.type] = [];
        grouped[r.type].push(r);
      }
      const typeOrder = ['task', 'shopping', 'recipe', 'calendar', 'mealplan', 'document', 'drive', 'note', 'chat', 'memory'];
      for (const type of typeOrder) {
        const group = grouped[type];
        if (!group) continue;
        html += `<div class="command-palette-group">${escapeHtml(typeLabels[type] || type)}</div>`;
        for (const item of group) {
          const idx = items.length;
          const icon = typeIcons[type] || 'article';
          items.push({ route: item.route });
          html += renderItem(icon, item.title, item.subtitle, idx, true);
        }
      }
    }

    // Loading state
    if (isLoading) {
      html += '<div class="command-palette-loading"><div class="cp-spinner"></div><span>Suche läuft…</span></div>';
    }

    // No results state
    if (!isLoading && items.length === 0) {
      html += `<div class="command-palette-empty">Keine Ergebnisse für „${escapeHtml(query)}"</div>`;
    }

    currentItems = items;
    if (activeIndex >= items.length) activeIndex = items.length - 1;

    if (resultsList) {
      resultsList.innerHTML = html;
      bindItemClicks();
      updateActive();
    }
  }

  // ── Render a single item ──
  function renderItem(icon, title, subtitle, index, hasSubtitle) {
    const activeClass = index === activeIndex ? ' active' : '';
    let inner = `<span class="material-symbols-outlined">${icon}</span>`;
    if (hasSubtitle && subtitle) {
      inner += `<div class="command-palette-item-text">
        <div class="command-palette-item-title">${escapeHtml(title)}</div>
        <div class="command-palette-item-subtitle">${escapeHtml(subtitle)}</div>
      </div>`;
    } else {
      inner += `<span class="command-palette-item-title">${escapeHtml(title)}</span>`;
    }
    return `<div class="command-palette-item${activeClass}" data-index="${index}">${inner}</div>`;
  }

  // ── Click handling ──
  function bindItemClicks() {
    if (!resultsList) return;
    resultsList.querySelectorAll('.command-palette-item').forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.dataset.index, 10);
        selectItem(idx);
      });
    });
  }

  function selectItem(idx) {
    if (idx < 0 || idx >= currentItems.length) return;
    const item = currentItems[idx];

    // History item: fill the search input and trigger search
    if (item.historyTerm) {
      if (input) {
        input.value = item.historyTerm;
        onInput();
        input.focus();
      }
      return;
    }

    // Save query to history before closing
    if (input && input.value.trim().length >= 2) {
      addToHistory(input.value.trim());
    }

    close();
    if (item.actionFn) {
      item.actionFn();
    } else if (item.route) {
      window.location.hash = item.route;
    }
  }

  // ── Input handling ──
  function onInput() {
    const q = input.value.trim();
    activeIndex = -1;

    if (!q) {
      if (debounceTimer) clearTimeout(debounceTimer);
      renderDefaultView();
      return;
    }

    // Immediately show client-side matches + loading state
    renderFilteredView(q, null, true);
    setLoadingBar(true);

    if (debounceTimer) clearTimeout(debounceTimer);
    const reqId = ++searchRequestId;

    debounceTimer = setTimeout(async () => {
      try {
        const results = await Api.searchGlobal(q);
        if (reqId === searchRequestId && input && input.value.trim() === q) {
          renderFilteredView(q, results, false);
          setLoadingBar(false);
        }
      } catch (e) {
        if (reqId === searchRequestId && input && input.value.trim() === q) {
          renderFilteredView(q, null, false);
          if (resultsList) {
            const errorEl = document.createElement('div');
            errorEl.className = 'command-palette-empty';
            errorEl.textContent = 'Suche nicht verfügbar – Navigation und Aktionen funktionieren weiterhin';
            resultsList.appendChild(errorEl);
          }
          setLoadingBar(false);
        }
      }
    }, 300);
  }

  function setLoadingBar(show) {
    if (!overlay) return;
    const bar = overlay.querySelector('.command-palette-loading-bar');
    if (bar) bar.classList.toggle('active', show);
  }

  // ── Keyboard handling ──
  function onKeydown(e) {
    const total = currentItems.length;

    if (e.key === 'ArrowDown' || (e.key === 'Tab' && !e.shiftKey)) {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % Math.max(total, 1);
      updateActive();
    } else if (e.key === 'ArrowUp' || (e.key === 'Tab' && e.shiftKey)) {
      e.preventDefault();
      activeIndex = activeIndex <= 0 ? total - 1 : activeIndex - 1;
      updateActive();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < total) {
        selectItem(activeIndex);
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
    const active = resultsList.querySelector('.command-palette-item.active');
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  return { open, close, toggle };
})();
