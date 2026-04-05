/**
 * DualMind Testuser Admin View – Einladungsverwaltung fuer Admins
 */
const TestUserAdminView = (() => {
  let invitations = [];
  let statusFilter = '';
  let showCreateForm = false;

  // ── Helpers ─────────────────────────────────────────────────

  function esc(str) {
    return String(str || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[c]);
  }

  function showToast(msg, type) {
    if (typeof Toast !== 'undefined') Toast.show(msg, type);
  }

  function formatDate(dateStr) {
    if (!dateStr) return '\u2013';
    const d = new Date(dateStr);
    if (isNaN(d)) return dateStr;
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function statusBadge(s) {
    const map = {
      pending:  { label: 'Ausstehend', cls: 'badge-warning' },
      accepted: { label: 'Akzeptiert', cls: 'badge-success' },
      expired:  { label: 'Abgelaufen', cls: 'badge-error' },
      revoked:  { label: 'Widerrufen', cls: 'badge-muted' },
    };
    const m = map[s] || { label: esc(s), cls: '' };
    return `<span class="badge ${m.cls}">${m.label}</span>`;
  }

  // ── API ─────────────────────────────────────────────────────

  async function loadInvitations() {
    try {
      const params = statusFilter ? `?status=${statusFilter}` : '';
      const data = await Api.get(`/test-users/invitations${params}`);
      invitations = data.invitations || [];
    } catch (e) {
      showToast('Fehler beim Laden der Einladungen', 'error');
      invitations = [];
    }
  }

  async function createInvitation(email, displayName, note) {
    try {
      const body = { email };
      if (displayName) body.display_name = displayName;
      if (note) body.note = note;
      const result = await Api.post('/test-users/invitations', body);
      showToast('Einladung erstellt', 'success');
      showCreateForm = false;
      await loadInvitations();
      renderContent();
      // Show the invite token in a dialog
      if (result.invite_token) {
        showTokenDialog(result.invite_token, result.email);
      }
    } catch (e) {
      showToast(e.message || 'Fehler beim Erstellen', 'error');
    }
  }

  async function resendInvitation(id) {
    try {
      const result = await Api.post(`/test-users/invitations/${id}/resend`);
      showToast('Einladung erneut gesendet', 'success');
      await loadInvitations();
      renderContent();
      if (result.invite_token) {
        showTokenDialog(result.invite_token, result.email);
      }
    } catch (e) {
      showToast(e.message || 'Fehler beim erneuten Senden', 'error');
    }
  }

  async function revokeInvitation(id) {
    if (!confirm('Einladung wirklich widerrufen?')) return;
    try {
      await Api.delete(`/test-users/invitations/${id}`);
      showToast('Einladung widerrufen', 'success');
      await loadInvitations();
      renderContent();
    } catch (e) {
      showToast(e.message || 'Fehler beim Widerrufen', 'error');
    }
  }

  // ── Token Dialog ────────────────────────────────────────────

  function showTokenDialog(token, email) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal-card" style="max-width:500px">
        <div class="modal-header">
          <h3>Einladungstoken</h3>
          <button class="btn-icon" onclick="this.closest('.modal-overlay').remove()">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body" style="padding:1rem">
          <p>Einladung fuer <strong>${esc(email)}</strong> erstellt.</p>
          <p style="margin-top:0.5rem;font-size:0.85rem;color:var(--text-secondary)">
            Diesen Token einmalig an den Eingeladenen senden:
          </p>
          <div class="token-display" style="margin-top:0.75rem;padding:0.75rem;background:var(--bg-card);border-radius:8px;word-break:break-all;font-family:monospace;font-size:0.85rem">
            ${esc(token)}
          </div>
          <button class="btn btn-primary" style="margin-top:1rem;width:100%" onclick="navigator.clipboard.writeText('${esc(token)}');Toast.show('Token kopiert','success')">
            <span class="material-symbols-outlined mi-sm">content_copy</span> Token kopieren
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.remove();
    });
  }

  // ── Render ──────────────────────────────────────────────────

  function renderContent() {
    const content = document.getElementById('tua-content');
    if (!content) return;

    const filterHtml = `
      <div class="tua-filter" style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem">
        ${['', 'pending', 'accepted', 'expired', 'revoked'].map(s => {
          const label = s === '' ? 'Alle' : { pending: 'Ausstehend', accepted: 'Akzeptiert', expired: 'Abgelaufen', revoked: 'Widerrufen' }[s];
          const active = statusFilter === s ? 'active' : '';
          return `<button class="chip ${active}" onclick="TestUserAdminView.setFilter('${s}')">${label}</button>`;
        }).join('')}
      </div>
    `;

    const createFormHtml = showCreateForm ? `
      <div class="card" style="margin-bottom:1rem;padding:1rem">
        <h3 style="margin-bottom:0.75rem">Neue Einladung</h3>
        <form onsubmit="TestUserAdminView.handleCreate(event)">
          <div class="form-group">
            <label>E-Mail *</label>
            <input type="email" id="tua-email" class="form-input" required placeholder="test@example.com">
          </div>
          <div class="form-group">
            <label>Anzeigename</label>
            <input type="text" id="tua-display-name" class="form-input" placeholder="Max Mustermann">
          </div>
          <div class="form-group">
            <label>Notiz</label>
            <textarea id="tua-note" class="form-input" rows="2" placeholder="Optionale Notiz..."></textarea>
          </div>
          <div style="display:flex;gap:0.5rem;margin-top:0.75rem">
            <button type="submit" class="btn btn-primary">Einladung erstellen</button>
            <button type="button" class="btn btn-ghost" onclick="TestUserAdminView.toggleCreate()">Abbrechen</button>
          </div>
        </form>
      </div>
    ` : '';

    if (invitations.length === 0) {
      content.innerHTML = filterHtml + createFormHtml + `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:3rem;color:var(--text-secondary)">mail</span>
          <p>Keine Einladungen${statusFilter ? ' mit diesem Status' : ''} vorhanden</p>
        </div>
      `;
      return;
    }

    // Desktop: Table, Mobile: Cards
    const tableHtml = `
      <div class="tua-table-wrap desktop-only">
        <table class="data-table">
          <thead>
            <tr>
              <th>E-Mail</th>
              <th>Name</th>
              <th>Status</th>
              <th>Erstellt</th>
              <th>Gueltig bis</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            ${invitations.map(inv => `
              <tr>
                <td>${esc(inv.email)}</td>
                <td>${esc(inv.display_name || '\u2013')}</td>
                <td>${statusBadge(inv.status)}</td>
                <td>${formatDate(inv.created_at)}</td>
                <td>${formatDate(inv.expires_at)}</td>
                <td class="tua-actions">
                  ${inv.status === 'pending' || inv.status === 'expired' ? `
                    <button class="btn-icon" title="Erneut senden" onclick="TestUserAdminView.resend('${esc(inv.id)}')">
                      <span class="material-symbols-outlined">send</span>
                    </button>
                  ` : ''}
                  ${inv.status !== 'accepted' && inv.status !== 'revoked' ? `
                    <button class="btn-icon" title="Widerrufen" onclick="TestUserAdminView.revoke('${esc(inv.id)}')">
                      <span class="material-symbols-outlined">block</span>
                    </button>
                  ` : ''}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    const cardsHtml = `
      <div class="tua-cards mobile-only">
        ${invitations.map(inv => `
          <div class="card tua-card">
            <div class="tua-card-header">
              <div>
                <div class="tua-card-email">${esc(inv.email)}</div>
                ${inv.display_name ? `<div class="tua-card-name">${esc(inv.display_name)}</div>` : ''}
              </div>
              ${statusBadge(inv.status)}
            </div>
            ${inv.note ? `<div class="tua-card-note">${esc(inv.note)}</div>` : ''}
            <div class="tua-card-meta">
              <span>Erstellt: ${formatDate(inv.created_at)}</span>
              <span>Gueltig bis: ${formatDate(inv.expires_at)}</span>
            </div>
            <div class="tua-card-actions">
              ${inv.status === 'pending' || inv.status === 'expired' ? `
                <button class="btn btn-small btn-ghost" onclick="TestUserAdminView.resend('${esc(inv.id)}')">
                  <span class="material-symbols-outlined mi-sm">send</span> Erneut senden
                </button>
              ` : ''}
              ${inv.status !== 'accepted' && inv.status !== 'revoked' ? `
                <button class="btn btn-small btn-ghost" onclick="TestUserAdminView.revoke('${esc(inv.id)}')">
                  <span class="material-symbols-outlined mi-sm">block</span> Widerrufen
                </button>
              ` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;

    content.innerHTML = filterHtml + createFormHtml + tableHtml + cardsHtml;
  }

  async function render(container) {
    container.innerHTML = `
      <a class="view-back" href="#/mehr">
        <span class="material-symbols-outlined mi-sm">arrow_back</span> Mehr
      </a>
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">admin_panel_settings</span>
        Testuser-Verwaltung
      </div>
      <div style="margin-bottom:1rem">
        <button class="btn btn-primary" onclick="TestUserAdminView.toggleCreate()">
          <span class="material-symbols-outlined mi-sm">person_add</span> Neue Einladung
        </button>
      </div>
      <div id="tua-content">
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
      </div>
    `;
    await loadInvitations();
    renderContent();
  }

  // ── Public API ──────────────────────────────────────────────

  function setFilter(s) {
    statusFilter = s;
    loadInvitations().then(() => renderContent());
  }

  function toggleCreate() {
    showCreateForm = !showCreateForm;
    renderContent();
  }

  function handleCreate(e) {
    e.preventDefault();
    const email = document.getElementById('tua-email')?.value?.trim();
    const displayName = document.getElementById('tua-display-name')?.value?.trim();
    const note = document.getElementById('tua-note')?.value?.trim();
    if (!email) return;
    createInvitation(email, displayName, note);
  }

  return {
    render,
    setFilter,
    toggleCreate,
    handleCreate,
    resend: resendInvitation,
    revoke: revokeInvitation,
  };
})();
