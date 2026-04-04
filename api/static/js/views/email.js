/**
 * EmailView – Gmail Posteingang und E-Mail-Detailansicht.
 */
const EmailView = (() => {
  let emails = [];
  let selectedEmail = null;

  async function render(container) {
    container.innerHTML = `
      <a class="view-back" href="#/mehr"><span class="material-symbols-outlined mi-sm">arrow_back</span> Mehr</a>
      <div class="section-header"><span class="section-icon material-symbols-outlined">mail</span> E-Mail</div>
      <div id="email-content">
        <div class="skeleton skeleton-task"></div>
        <div class="skeleton skeleton-task"></div>
        <div class="skeleton skeleton-task"></div>
      </div>
    `;
    selectedEmail = null;
    await loadInbox();
  }

  async function loadInbox() {
    const el = document.getElementById('email-content');
    if (!el) return;
    try {
      emails = await Api.get('/email/inbox?limit=20');
      renderInbox();
    } catch (err) {
      if (err.status === 503 || err.isServiceDown) {
        el.innerHTML = `
          <div class="empty-state">
            <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-muted)">mail_lock</span>
            <p>Gmail nicht verbunden</p>
            <p class="card-subtitle">Verbinde Gmail in den Einstellungen, um E-Mails hier zu sehen.</p>
          </div>
        `;
      } else {
        el.innerHTML = `
          <div class="empty-state">
            <span class="material-symbols-outlined" style="font-size:48px;color:var(--error)">error</span>
            <p>${escapeHtml(err.message || 'Fehler beim Laden')}</p>
          </div>
        `;
      }
    }
  }

  function renderInbox() {
    const el = document.getElementById('email-content');
    if (!el) return;

    if (!emails || emails.length === 0) {
      el.innerHTML = `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-muted)">inbox</span>
          <p>Keine E-Mails</p>
        </div>
      `;
      return;
    }

    el.innerHTML = emails.map(mail => {
      const unreadCls = mail.is_unread ? ' email-unread' : '';
      const fromDisplay = _extractName(mail.from || 'Unbekannt');
      const dateDisplay = _formatEmailDate(mail.date);
      const subject = mail.subject || '(Kein Betreff)';
      const snippet = mail.snippet || '';
      return `
        <div class="card email-card${unreadCls}" data-id="${escapeHtml(mail.id)}" onclick="EmailView.showEmail('${escapeHtml(mail.id)}')">
          <div class="email-card-header">
            <span class="email-from">${escapeHtml(fromDisplay)}</span>
            <span class="email-date">${escapeHtml(dateDisplay)}</span>
          </div>
          <div class="email-subject">${escapeHtml(subject)}</div>
          <div class="email-snippet">${escapeHtml(snippet)}</div>
        </div>
      `;
    }).join('');
  }

  async function showEmail(id) {
    const el = document.getElementById('email-content');
    if (!el) return;

    el.innerHTML = `
      <div class="skeleton skeleton-task"></div>
      <div class="skeleton skeleton-task"></div>
    `;

    try {
      selectedEmail = await Api.get('/email/' + encodeURIComponent(id));
      renderDetail(selectedEmail);
    } catch (err) {
      el.innerHTML = `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--error)">error</span>
          <p>${escapeHtml(err.message || 'E-Mail konnte nicht geladen werden')}</p>
        </div>
      `;
    }
  }

  function renderDetail(email) {
    const el = document.getElementById('email-content');
    if (!el) return;

    const fromDisplay = escapeHtml(email.from || 'Unbekannt');
    const toDisplay = escapeHtml(email.to || '');
    const subject = escapeHtml(email.subject || '(Kein Betreff)');
    const dateDisplay = escapeHtml(_formatEmailDate(email.date));
    const body = escapeHtml(email.body || email.snippet || '');

    el.innerHTML = `
      <button class="btn btn-text email-back-btn" onclick="EmailView._backToInbox()">
        <span class="material-symbols-outlined mi-sm">arrow_back</span> Zurueck
      </button>
      <div class="card email-detail">
        <h3 class="email-detail-subject">${subject}</h3>
        <div class="email-detail-meta">
          <div><strong>Von:</strong> ${fromDisplay}</div>
          ${toDisplay ? `<div><strong>An:</strong> ${toDisplay}</div>` : ''}
          <div><strong>Datum:</strong> ${dateDisplay}</div>
        </div>
        <hr class="email-divider">
        <div class="email-detail-body">${body}</div>
      </div>
    `;
  }

  function _backToInbox() {
    selectedEmail = null;
    const el = document.getElementById('email-content');
    if (!el) return;
    renderInbox();
  }

  function _extractName(fromStr) {
    // "Name <email>" → "Name", else return as-is
    const match = fromStr.match(/^"?([^"<]+)"?\s*</);
    return match ? match[1].trim() : fromStr.replace(/<.*>/, '').trim() || fromStr;
  }

  function _formatEmailDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      const now = new Date();
      const isToday = d.toDateString() === now.toDateString();
      if (isToday) {
        return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
    } catch {
      return dateStr;
    }
  }

  return { render, showEmail, _backToInbox };
})();
