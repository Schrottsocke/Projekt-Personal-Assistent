/**
 * SearchView – Global search overlay.
 * Opens via Ctrl+K or header search button.
 * Queries /search endpoint and groups results by type.
 */
const SearchView = (() => {
  let overlay = null;
  let debounceTimer = null;

  const TYPE_ICONS = {
    task: 'check_circle', shopping: 'shopping_cart', recipe: 'restaurant',
    mealplan: 'restaurant_menu', document: 'scanner', note: 'sticky_note_2',
    chat: 'chat_bubble', memory: 'psychology', calendar: 'calendar_month', drive: 'folder'
  };
  const TYPE_LABELS = {
    task: 'Aufgaben', shopping: 'Einkauf', recipe: 'Rezepte',
    mealplan: 'Wochenplan', document: 'Dokumente', note: 'Notizen',
    chat: 'Chat', memory: 'Erinnerungen', calendar: 'Kalender', drive: 'Drive'
  };

  function show() {
    if (overlay) return;

    overlay = document.createElement('div');
    overlay.className = 'search-overlay';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) hide();
    });

    const container = document.createElement('div');
    container.className = 'search-container';
    container.innerHTML = `
      <div class="search-header">
        <span class="material-symbols-outlined">search</span>
        <input type="text" class="search-input" placeholder="Suche..." autocomplete="off">
        <button class="search-close" title="Schliessen">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <div class="search-results">
        <div class="search-hint">Mindestens 3 Zeichen eingeben</div>
      </div>
    `;

    overlay.appendChild(container);
    document.body.appendChild(overlay);

    const input = container.querySelector('.search-input');
    const closeBtn = container.querySelector('.search-close');

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const query = input.value.trim();
      if (query.length < 3) {
        renderHint('Mindestens 3 Zeichen eingeben');
        return;
      }
      renderLoading();
      debounceTimer = setTimeout(() => doSearch(query), 300);
    });

    closeBtn.addEventListener('click', hide);

    document.addEventListener('keydown', onKeyDown);

    setTimeout(() => input.focus(), 50);
  }

  function hide() {
    if (!overlay) return;
    overlay.style.opacity = '0';
    setTimeout(() => {
      if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
      overlay = null;
    }, 150);
    document.removeEventListener('keydown', onKeyDown);
    clearTimeout(debounceTimer);
  }

  function onKeyDown(e) {
    if (e.key === 'Escape') hide();
  }

  function getResultsEl() {
    return overlay?.querySelector('.search-results');
  }

  function renderHint(text) {
    const el = getResultsEl();
    if (el) el.innerHTML = `<div class="search-hint">${escapeHtml(text)}</div>`;
  }

  function renderLoading() {
    const el = getResultsEl();
    if (el) el.innerHTML = '<div class="search-loading"><span class="material-symbols-outlined" style="animation:spin 1s linear infinite">progress_activity</span></div>';
  }

  async function doSearch(query) {
    try {
      const results = await Api.searchGlobal(query);
      const el = getResultsEl();
      if (!el) return;

      if (!results || results.length === 0) {
        el.innerHTML = `<div class="search-empty">Keine Treffer f\u00fcr \u201e${escapeHtml(query)}\u201c</div>`;
        return;
      }

      // Group by type
      const groups = {};
      for (const r of results) {
        if (!groups[r.type]) groups[r.type] = [];
        groups[r.type].push(r);
      }

      let html = '';
      for (const [type, items] of Object.entries(groups)) {
        const label = TYPE_LABELS[type] || type;
        html += `<div class="search-group-header">${escapeHtml(label)}</div>`;
        for (const item of items) {
          const icon = TYPE_ICONS[type] || 'article';
          html += `
            <div class="search-result-item" data-route="${escapeHtml(item.route || '')}">
              <span class="material-symbols-outlined search-result-icon">${icon}</span>
              <div class="search-result-text">
                <div class="search-result-title">${escapeHtml(item.title || '')}</div>
                ${item.subtitle ? `<div class="search-result-subtitle">${escapeHtml(item.subtitle)}</div>` : ''}
              </div>
            </div>
          `;
        }
      }

      el.innerHTML = html;

      // Bind click handlers
      el.querySelectorAll('.search-result-item[data-route]').forEach(row => {
        row.addEventListener('click', () => {
          const route = row.dataset.route;
          if (route) {
            hide();
            window.location.hash = route;
          }
        });
      });
    } catch (err) {
      const el = getResultsEl();
      if (el) el.innerHTML = '<div class="search-empty">Fehler bei der Suche.</div>';
    }
  }

  function render(container) {
    container.innerHTML = `
      <div style="padding: 16px;">
        <div class="search-header" style="background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
          <span class="material-symbols-outlined">search</span>
          <input type="text" class="search-input" placeholder="Suche..." autocomplete="off">
        </div>
        <div class="search-results" style="margin-top: 16px;">
          <div class="search-hint">Mindestens 3 Zeichen eingeben</div>
        </div>
      </div>
    `;

    const input = container.querySelector('.search-input');
    const resultsEl = container.querySelector('.search-results');

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const query = input.value.trim();
      if (query.length < 3) {
        resultsEl.innerHTML = '<div class="search-hint">Mindestens 3 Zeichen eingeben</div>';
        return;
      }
      resultsEl.innerHTML = '<div class="search-loading"><span class="material-symbols-outlined" style="animation:spin 1s linear infinite">progress_activity</span></div>';
      debounceTimer = setTimeout(async () => {
        try {
          const results = await Api.searchGlobal(query);
          if (!results || results.length === 0) {
            resultsEl.innerHTML = `<div class="search-empty">Keine Treffer f\u00fcr \u201e${escapeHtml(query)}\u201c</div>`;
            return;
          }
          const groups = {};
          for (const r of results) {
            if (!groups[r.type]) groups[r.type] = [];
            groups[r.type].push(r);
          }
          let html = '';
          for (const [type, items] of Object.entries(groups)) {
            const label = TYPE_LABELS[type] || type;
            html += `<div class="search-group-header">${escapeHtml(label)}</div>`;
            for (const item of items) {
              const icon = TYPE_ICONS[type] || 'article';
              html += `
                <div class="search-result-item" data-route="${escapeHtml(item.route || '')}">
                  <span class="material-symbols-outlined search-result-icon">${icon}</span>
                  <div class="search-result-text">
                    <div class="search-result-title">${escapeHtml(item.title || '')}</div>
                    ${item.subtitle ? `<div class="search-result-subtitle">${escapeHtml(item.subtitle)}</div>` : ''}
                  </div>
                </div>
              `;
            }
          }
          resultsEl.innerHTML = html;
          resultsEl.querySelectorAll('.search-result-item[data-route]').forEach(row => {
            row.addEventListener('click', () => {
              const route = row.dataset.route;
              if (route) window.location.hash = route;
            });
          });
        } catch {
          resultsEl.innerHTML = '<div class="search-empty">Fehler bei der Suche.</div>';
        }
      }, 300);
    });

    setTimeout(() => input.focus(), 50);
  }

  return { show, hide, render };
})();
