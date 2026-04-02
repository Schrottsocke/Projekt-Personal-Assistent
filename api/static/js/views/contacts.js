/**
 * DualMind Contacts View
 * Zeigt Kontakte mit Suche, Detail-Ansicht und Bearbeitung.
 */
const ContactsView = (() => {
  let contacts = [];
  let searchQuery = '';
  let loading = false;
  let container = null;
  let selectedContact = null;

  async function loadContacts() {
    loading = true;
    render(container);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.set('q', searchQuery);
      contacts = await Api.get(`/contacts?${params}`);
    } catch (e) {
      contacts = [];
    }
    loading = false;
    renderList();
  }

  function renderList() {
    if (!container) return;

    const listHtml = contacts.length === 0
      ? `<p class="empty-state">${loading ? 'Lade...' : 'Keine Kontakte gefunden.'}</p>`
      : contacts.map(c => `
        <div class="card contact-card" data-id="${c.id}" style="cursor:pointer">
          <div style="display:flex;align-items:center;gap:12px">
            <span class="material-symbols-outlined" style="font-size:32px;color:var(--accent)">person</span>
            <div style="flex:1;min-width:0">
              <strong>${Utils.escapeHtml(c.name)}</strong>
              ${c.email ? `<div class="text-muted" style="font-size:0.85rem">${Utils.escapeHtml(c.email)}</div>` : ''}
              ${c.phone ? `<div class="text-muted" style="font-size:0.85rem">${Utils.escapeHtml(c.phone)}</div>` : ''}
            </div>
            ${c.tags && c.tags.length ? `<div>${c.tags.map(t => `<span class="badge">${Utils.escapeHtml(t)}</span>`).join(' ')}</div>` : ''}
          </div>
        </div>
      `).join('');

    container.innerHTML = `
      <div class="view-header">
        <h2>Kontakte</h2>
        <button class="btn btn-primary btn-sm" id="contact-add-btn">
          <span class="material-symbols-outlined">person_add</span> Neu
        </button>
      </div>
      <div class="search-bar" style="margin-bottom:16px">
        <input type="text" id="contact-search" class="input" placeholder="Kontakt suchen..."
               value="${Utils.escapeHtml(searchQuery)}">
      </div>
      <div id="contacts-list">${listHtml}</div>
      <div id="contact-detail"></div>
    `;

    // Event: Suche
    const searchInput = container.querySelector('#contact-search');
    let debounce = null;
    searchInput?.addEventListener('input', (e) => {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        searchQuery = e.target.value.trim();
        loadContacts();
      }, 300);
    });

    // Event: Kontakt anklicken
    container.querySelectorAll('.contact-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.dataset.id;
        const c = contacts.find(x => x.id === id);
        if (c) showDetail(c);
      });
    });

    // Event: Neu
    container.querySelector('#contact-add-btn')?.addEventListener('click', showCreateForm);
  }

  function showDetail(c) {
    const detail = container.querySelector('#contact-detail');
    if (!detail) return;
    detail.innerHTML = `
      <div class="card" style="margin-top:16px">
        <div style="display:flex;justify-content:space-between;align-items:start">
          <h3>${Utils.escapeHtml(c.name)}</h3>
          <div style="display:flex;gap:8px">
            <button class="btn btn-sm" id="contact-edit-btn">Bearbeiten</button>
            <button class="btn btn-sm btn-danger" id="contact-delete-btn">Loeschen</button>
          </div>
        </div>
        ${c.email ? `<p><strong>E-Mail:</strong> ${Utils.escapeHtml(c.email)}</p>` : ''}
        ${c.phone ? `<p><strong>Telefon:</strong> ${Utils.escapeHtml(c.phone)}</p>` : ''}
        ${c.notes ? `<p><strong>Notizen:</strong> ${Utils.escapeHtml(c.notes)}</p>` : ''}
        ${c.source ? `<p><strong>Quelle:</strong> ${Utils.escapeHtml(c.source)}</p>` : ''}
        ${c.last_interaction ? `<p><strong>Letzter Kontakt:</strong> ${Utils.escapeHtml(c.last_interaction)}</p>` : ''}
        ${c.tags && c.tags.length ? `<p><strong>Tags:</strong> ${c.tags.map(t => `<span class="badge">${Utils.escapeHtml(t)}</span>`).join(' ')}</p>` : ''}
      </div>
    `;
    detail.querySelector('#contact-delete-btn')?.addEventListener('click', async () => {
      if (!confirm('Kontakt wirklich loeschen?')) return;
      try {
        await Api.delete(`/contacts/${c.id}`);
        await loadContacts();
      } catch (e) {
        alert('Fehler beim Loeschen.');
      }
    });
    detail.querySelector('#contact-edit-btn')?.addEventListener('click', () => showEditForm(c));
  }

  function showCreateForm() {
    const detail = container.querySelector('#contact-detail');
    if (!detail) return;
    detail.innerHTML = `
      <div class="card" style="margin-top:16px">
        <h3>Neuer Kontakt</h3>
        <form id="contact-form">
          <div class="form-group"><label>Name *</label><input class="input" name="name" required></div>
          <div class="form-group"><label>E-Mail</label><input class="input" name="email" type="email"></div>
          <div class="form-group"><label>Telefon</label><input class="input" name="phone"></div>
          <div class="form-group"><label>Notizen</label><textarea class="input" name="notes" rows="3"></textarea></div>
          <div class="form-group"><label>Tags (kommagetrennt)</label><input class="input" name="tags"></div>
          <button type="submit" class="btn btn-primary">Speichern</button>
          <button type="button" class="btn" id="contact-cancel">Abbrechen</button>
        </form>
      </div>
    `;
    detail.querySelector('#contact-cancel')?.addEventListener('click', () => { detail.innerHTML = ''; });
    detail.querySelector('#contact-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const data = {
        name: fd.get('name'),
        email: fd.get('email') || null,
        phone: fd.get('phone') || null,
        notes: fd.get('notes') || null,
        tags: fd.get('tags') ? fd.get('tags').split(',').map(t => t.trim()).filter(Boolean) : [],
      };
      try {
        await Api.post('/contacts', data);
        await loadContacts();
      } catch (err) {
        alert('Fehler beim Speichern.');
      }
    });
  }

  function showEditForm(c) {
    const detail = container.querySelector('#contact-detail');
    if (!detail) return;
    detail.innerHTML = `
      <div class="card" style="margin-top:16px">
        <h3>Kontakt bearbeiten</h3>
        <form id="contact-form">
          <div class="form-group"><label>Name *</label><input class="input" name="name" value="${Utils.escapeHtml(c.name)}" required></div>
          <div class="form-group"><label>E-Mail</label><input class="input" name="email" type="email" value="${Utils.escapeHtml(c.email || '')}"></div>
          <div class="form-group"><label>Telefon</label><input class="input" name="phone" value="${Utils.escapeHtml(c.phone || '')}"></div>
          <div class="form-group"><label>Notizen</label><textarea class="input" name="notes" rows="3">${Utils.escapeHtml(c.notes || '')}</textarea></div>
          <div class="form-group"><label>Tags (kommagetrennt)</label><input class="input" name="tags" value="${(c.tags || []).join(', ')}"></div>
          <button type="submit" class="btn btn-primary">Speichern</button>
          <button type="button" class="btn" id="contact-cancel">Abbrechen</button>
        </form>
      </div>
    `;
    detail.querySelector('#contact-cancel')?.addEventListener('click', () => showDetail(c));
    detail.querySelector('#contact-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const data = {
        name: fd.get('name'),
        email: fd.get('email') || null,
        phone: fd.get('phone') || null,
        notes: fd.get('notes') || null,
        tags: fd.get('tags') ? fd.get('tags').split(',').map(t => t.trim()).filter(Boolean) : [],
      };
      try {
        await Api.patch(`/contacts/${c.id}`, data);
        await loadContacts();
      } catch (err) {
        alert('Fehler beim Speichern.');
      }
    });
  }

  async function render(c) {
    container = c;
    container.innerHTML = '<p class="empty-state">Lade Kontakte...</p>';
    await loadContacts();
  }

  return { render };
})();
