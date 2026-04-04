/**
 * Memory View – Semantische Suche im Gedaechtnis des Assistenten
 */
const MemoryView = (() => {
  let searchTimer = null;
  let currentOffset = 0;
  const PAGE_SIZE = 20;

  async function render(container) {
    container.innerHTML = `
      <div class="memory-view">
        <div class="section-header">
          <span class="section-icon material-symbols-outlined">psychology</span>
          Gedaechtnis
        </div>
        <div class="memory-search-wrap">
          <span class="material-symbols-outlined memory-search-icon">search</span>
          <input type="text" id="memory-search" class="memory-search-input"
                 placeholder="Was weiss ich ueber dich?" autocomplete="off">
        </div>
        <div id="memory-results">
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-card"></div>
        </div>
        <div id="memory-load-more" class="hidden"></div>
      </div>
    `;

    const input = document.getElementById('memory-search');
    input.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        const q = input.value.trim();
        if (q.length > 0) {
          doSearch(q);
        } else {
          currentOffset = 0;
          loadAll();
        }
      }, 300);
    });

    currentOffset = 0;
    await loadAll();
  }

  async function loadAll() {
    const el = document.getElementById('memory-results');
    const moreEl = document.getElementById('memory-load-more');
    if (!el) return;

    try {
      const data = await Api.getMemories(currentOffset, PAGE_SIZE);
      if (data.items.length === 0 && currentOffset === 0) {
        el.innerHTML = `
          <div class="empty-state">
            <span class="material-symbols-outlined empty-state-icon">psychology</span>
            <div class="empty-state-text">Noch keine Erinnerungen gespeichert</div>
            <div class="empty-state-hint">Dein Assistent merkt sich wichtige Dinge aus euren Gespraechen.</div>
          </div>
        `;
        moreEl.classList.add('hidden');
        return;
      }

      if (currentOffset === 0) {
        el.innerHTML = '';
      }
      el.insertAdjacentHTML('beforeend', renderCards(data.items, false));

      if (currentOffset + PAGE_SIZE < data.total) {
        moreEl.classList.remove('hidden');
        moreEl.innerHTML = `<button class="btn btn-secondary memory-load-more-btn" onclick="MemoryView.loadMore()">Weitere laden</button>`;
      } else {
        moreEl.classList.add('hidden');
      }
    } catch (err) {
      el.innerHTML = `
        <div class="error-state">
          <p>${escapeHtml(err.message)}</p>
          <button class="btn btn-secondary" onclick="MemoryView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

  async function doSearch(query) {
    const el = document.getElementById('memory-results');
    const moreEl = document.getElementById('memory-load-more');
    if (!el) return;

    el.innerHTML = `
      <div class="skeleton skeleton-card"></div>
      <div class="skeleton skeleton-card"></div>
    `;
    moreEl.classList.add('hidden');

    try {
      const results = await Api.searchMemories(query);
      if (results.length === 0) {
        el.innerHTML = `
          <div class="empty-state">
            <span class="material-symbols-outlined empty-state-icon">search_off</span>
            <div class="empty-state-text">Keine Erinnerungen gefunden</div>
            <div class="empty-state-hint">Versuch es mit anderen Begriffen.</div>
          </div>
        `;
        return;
      }
      el.innerHTML = renderCards(results, true);
    } catch (err) {
      el.innerHTML = `
        <div class="error-state">
          <p>${escapeHtml(err.message)}</p>
          <button class="btn btn-secondary" onclick="MemoryView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

  function renderCards(items, isSearch) {
    return items.map(m => {
      const text = m.memory || '';
      const id = m.id || '';
      return `
        <div class="card memory-card" data-id="${escapeHtml(id)}">
          <div class="memory-card-text">${escapeHtml(text)}</div>
          <div class="memory-card-actions">
            <button class="btn btn-sm btn-secondary" onclick="MemoryView.useInChat('${escapeHtml(text.replace(/'/g, "\\'"))}')">
              <span class="material-symbols-outlined mi-sm">chat</span> Im Chat verwenden
            </button>
            <button class="btn btn-sm btn-icon memory-delete-btn" onclick="MemoryView.remove('${escapeHtml(id)}')" title="Loeschen">
              <span class="material-symbols-outlined mi-sm">delete</span>
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  function useInChat(text) {
    // Store text for chat pre-fill, then navigate
    sessionStorage.setItem('dm_chat_prefill', text);
    Router.navigate('#/chat');
  }

  function remove(id) {
    if (!id) return;
    const card = document.querySelector(`.memory-card[data-id="${id}"]`);
    if (!card) return;

    // Optimistic: hide card immediately
    const parent = card.parentNode;
    const nextSibling = card.nextSibling;
    card.remove();

    let cancelled = false;
    Toast.showUndo('Erinnerung gelöscht', () => {
      cancelled = true;
      // Restore card into its original position
      if (parent) {
        if (nextSibling) {
          parent.insertBefore(card, nextSibling);
        } else {
          parent.appendChild(card);
        }
      }
    });

    setTimeout(async () => {
      if (cancelled) return;
      try {
        await Api.deleteMemory(id);
      } catch (err) {
        // Restore on error
        if (parent) {
          if (nextSibling) {
            parent.insertBefore(card, nextSibling);
          } else {
            parent.appendChild(card);
          }
        }
        Toast.show('Löschen fehlgeschlagen: ' + err.message, 'error');
      }
    }, 5000);
  }

  function loadMore() {
    currentOffset += PAGE_SIZE;
    loadAll();
  }

  return { render, useInChat, remove, loadMore };
})();
