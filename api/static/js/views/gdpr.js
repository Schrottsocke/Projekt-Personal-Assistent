/**
 * GDPR View – Datenschutz-Center (DSGVO)
 * Issue #720: Export, Account-Loeschung, Einwilligungen, Datenverarbeitung
 * Tabs: Datenschutz | Follow-ups
 */
const GdprView = (() => {
  let activeTab = 'datenschutz';

  // -- State: Datenschutz --
  let dataSummary = null;
  let consents = [];
  let processingLog = [];
  let exportUrl = null;
  let exportPolling = false;
  let deleteStep = 0; // 0=idle, 1=confirm input, 2=grace period shown
  let deleteConfirmText = '';

  // -- State: Follow-ups --
  let followups = [];
  let dueFollowups = [];
  let showCreateForm = false;

  // -- Data processing overview --
  const DATA_PROCESSING = [
    { category: 'Chat-Nachrichten', purpose: 'Assistenz & Konversation', retention: 'Bis zur Kontoloeschung', legal: 'Einwilligung' },
    { category: 'Kalender & Termine', purpose: 'Terminverwaltung & Erinnerungen', retention: 'Bis zur Kontoloeschung', legal: 'Vertragserfuellung' },
    { category: 'Dokumente & Scans', purpose: 'Dokumentenablage & -suche', retention: 'Bis zur Kontoloeschung', legal: 'Einwilligung' },
    { category: 'Finanzdaten', purpose: 'Budget-Tracking & Auswertung', retention: 'Bis zur Kontoloeschung', legal: 'Einwilligung' },
    { category: 'Einkaufslisten', purpose: 'Haushaltsverwaltung', retention: 'Bis zur Kontoloeschung', legal: 'Vertragserfuellung' },
    { category: 'Nutzungsstatistiken', purpose: 'Verbesserung des Dienstes', retention: '12 Monate', legal: 'Berechtigtes Interesse' },
  ];

  // -- Helpers --

  function esc(str) {
    return String(str || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
  }

  function showToast(msg, type) {
    if (typeof Toast !== 'undefined') Toast.show(msg, type);
  }

  function formatDate(iso) {
    if (!iso) return '\u2013';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function formatDatetime(iso) {
    if (!iso) return '\u2013';
    const d = new Date(iso);
    return d.toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function isOverdue(dueDateStr) {
    if (!dueDateStr) return false;
    const due = new Date(dueDateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return due < today;
  }

  function isDueToday(dueDateStr) {
    if (!dueDateStr) return false;
    const due = new Date(dueDateStr);
    const today = new Date();
    return (
      due.getFullYear() === today.getFullYear() &&
      due.getMonth() === today.getMonth() &&
      due.getDate() === today.getDate()
    );
  }

  function consentLabel(category) {
    const labels = {
      analytics: 'Analyse & Statistik',
      personalization: 'Personalisierung',
      email_notifications: 'E-Mail-Benachrichtigungen',
      data_sharing: 'Datenweitergabe',
    };
    return labels[category] || esc(category);
  }

  function followupStatusBadge(status, dueDate) {
    if (status === 'done') return '<span class="badge badge-success">Erledigt</span>';
    if (isOverdue(dueDate)) return '<span class="badge badge-error">\u00dcberf\u00e4llig</span>';
    if (isDueToday(dueDate)) return '<span class="badge badge-warning">Heute f\u00e4llig</span>';
    return '<span class="badge badge-accent">Offen</span>';
  }

  function refTypeBadge(refType) {
    if (!refType) return '';
    const map = {
      task: 'badge-accent',
      conversation: 'badge-muted',
      invoice: 'badge-warning',
      contract: 'badge-error',
      document: 'badge-success',
    };
    return `<span class="badge ${map[refType] || 'badge-muted'}">${esc(refType)}</span>`;
  }

  // -- Main Render --

  async function render(container) {
    deleteStep = 0;
    exportUrl = null;
    exportPolling = false;
    showCreateForm = false;
    deleteConfirmText = '';

    container.innerHTML = `
      <div class="section-header">
        <span class="section-icon material-symbols-outlined">security</span>
        Datenschutz-Center
      </div>
      <div class="tab-bar mb-16">
        <button class="tab-btn ${activeTab === 'datenschutz' ? 'active' : ''}"
          onclick="GdprView.switchTab('datenschutz')">
          <span class="material-symbols-outlined mi-sm">shield</span> Datenschutz
        </button>
        <button class="tab-btn ${activeTab === 'followups' ? 'active' : ''}"
          onclick="GdprView.switchTab('followups')">
          <span class="material-symbols-outlined mi-sm">event_upcoming</span> Follow-ups
        </button>
      </div>
      <div id="gdpr-tab-content">
        <div class="skeleton skeleton-card"></div>
        <div class="skeleton skeleton-card"></div>
      </div>
    `;

    if (activeTab === 'datenschutz') {
      await loadDatenschutzTab(container);
    } else {
      await loadFollowupsTab(container);
    }
  }

  // -- Datenschutz Tab --

  async function loadDatenschutzTab(container) {
    try {
      const [consentsRes, exportRes] = await Promise.all([
        Api.get('/gdpr/consents').catch(() => null),
        Api.get('/gdpr/data-export').catch(() => null),
      ]);
      consents = consentsRes && consentsRes.consents ? consentsRes.consents : {};
      processingLog = [];
      // Build data summary from export response
      if (exportRes && exportRes.data) {
        const categories = {};
        let total = 0;
        for (const [key, records] of Object.entries(exportRes.data)) {
          const count = Array.isArray(records) ? records.length : 0;
          if (count > 0) {
            categories[key] = count;
            total += count;
          }
        }
        dataSummary = { categories, total_records: total };
      } else {
        dataSummary = null;
      }
    } catch (e) {
      showToast('Fehler beim Laden der Datenschutzdaten', 'error');
      dataSummary = null;
      consents = {};
      processingLog = [];
    }
    renderDatenschutzTab(container);
  }

  function renderDatenschutzTab(container) {
    const tabContent = container.querySelector('#gdpr-tab-content');
    if (!tabContent) return;

    // Data summary
    let summaryHtml = '';
    if (dataSummary) {
      const cats = dataSummary.categories || {};
      const catRows = Object.entries(cats)
        .map(([k, v]) => `<div class="data-summary-row"><span class="data-summary-key">${esc(k)}</span><span class="badge badge-muted">${esc(String(v))}</span></div>`)
        .join('');
      summaryHtml = `
        <div class="card mb-16">
          <div class="card-title"><span class="material-symbols-outlined mi-sm">database</span> Meine Daten</div>
          <div class="data-summary-total mb-8">
            <strong>Gesamt:</strong> ${esc(String(dataSummary.total_records || 0))} Eintr\u00e4ge
          </div>
          ${catRows}
        </div>
      `;
    } else {
      summaryHtml = '';
    }

    // Datenschutzerklaerung (DSGVO)
    summaryHtml = `
      <div class="card mb-16">
        <div class="card-title"><span class="material-symbols-outlined mi-sm">gavel</span> Datenschutzerkl\u00e4rung</div>
        <div style="font-size:0.9rem;color:var(--text-secondary);line-height:1.6">
          <p class="mb-8"><strong>Verantwortlicher:</strong> Der Betreiber dieser DualMind-Instanz.</p>
          <p class="mb-8"><strong>Zweck der Datenverarbeitung:</strong> Bereitstellung eines pers\u00f6nlichen Assistenten f\u00fcr Aufgaben-, Termin-, Finanz- und Haushaltsverwaltung.</p>
          <p class="mb-8"><strong>Rechtsgrundlage:</strong> Art. 6 Abs. 1 lit. a (Einwilligung) und lit. b (Vertragserf\u00fcllung) DSGVO.</p>
          <p class="mb-8"><strong>Speicherung:</strong> Alle Daten werden ausschlie\u00dflich auf dem eigenen Server gespeichert. Es erfolgt keine Weitergabe an Dritte, sofern nicht ausdr\u00fccklich eingewilligt.</p>
          <p class="mb-8"><strong>Deine Rechte:</strong> Auskunft, Berichtigung, L\u00f6schung, Einschr\u00e4nkung, Daten\u00fcbertragbarkeit und Widerspruch gem\u00e4\u00df Art. 15\u201321 DSGVO.</p>
          <p><strong>Datenexport & L\u00f6schung:</strong> Du kannst jederzeit alle deine Daten exportieren oder dein Konto vollst\u00e4ndig l\u00f6schen \u2013 siehe unten.</p>
        </div>
      </div>
    ` + summaryHtml;

    // Export card with status polling
    const exportSection = `
      <div class="card mb-16 gdpr-export-card">
        <div class="card-title"><span class="material-symbols-outlined mi-sm">download</span> Meine Daten exportieren</div>
        <p class="text-muted mb-12">Exportiere alle deine pers\u00f6nlichen Daten als ZIP-Datei (DSGVO Art. 20).</p>
        <div id="gdpr-export-area">
          ${exportUrl
            ? `<a class="btn btn-secondary" href="${esc(exportUrl)}" download>
                <span class="material-symbols-outlined mi-sm">download</span> ZIP herunterladen
               </a>`
            : exportPolling
              ? `<div class="gdpr-export-polling">
                  <span class="material-symbols-outlined spin">hourglass_top</span>
                  <span>Export wird vorbereitet...</span>
                </div>`
              : `<button class="btn btn-primary" onclick="GdprView.requestExport()">
                  <span class="material-symbols-outlined mi-sm">cloud_download</span> Meine Daten exportieren
                 </button>`
          }
        </div>
      </div>
    `;

    // Consent management with individual revoke
    const CONSENT_CATEGORIES = ['analytics', 'personalization', 'email_notifications', 'data_sharing'];

    const consentRows = CONSENT_CATEGORIES.map(cat => {
      const granted = consents[cat] === true;
      return `
        <div class="consent-row">
          <div class="consent-info">
            <span class="consent-label">${consentLabel(cat)}</span>
          </div>
          <div class="consent-actions">
            <label class="toggle-switch">
              <input type="checkbox" id="consent-${esc(cat)}" ${granted ? 'checked' : ''}>
              <span class="toggle-slider"></span>
            </label>
            ${granted ? `<button class="btn btn-sm btn-danger gdpr-revoke-btn" onclick="GdprView.revokeConsent('${esc(cat)}')" title="Einwilligung widerrufen">
              <span class="material-symbols-outlined mi-sm">block</span>
            </button>` : ''}
          </div>
        </div>
      `;
    }).join('');

    const consentSection = `
      <div class="card mb-16">
        <div class="card-title"><span class="material-symbols-outlined mi-sm">tune</span> Einwilligungen verwalten</div>
        <p class="text-muted mb-8" style="font-size:0.85rem">Verwalte deine Einwilligungen zur Datenverarbeitung. Du kannst jede einzeln widerrufen.</p>
        <div id="consent-list">${consentRows}</div>
        <div class="mt-12">
          <button class="btn btn-primary" onclick="GdprView.saveConsents()">
            <span class="material-symbols-outlined mi-sm">save</span> Einwilligungen speichern
          </button>
        </div>
      </div>
    `;

    // Data processing overview table
    const processingOverview = `
      <div class="card mb-16">
        <div class="card-title"><span class="material-symbols-outlined mi-sm">info</span> Datenverarbeitungs-\u00dcbersicht</div>
        <p class="text-muted mb-8" style="font-size:0.85rem">Welche Daten werden wof\u00fcr und wie lange verarbeitet?</p>
        <div class="table-scroll">
          <table class="log-table gdpr-processing-table">
            <thead>
              <tr>
                <th>Datenkategorie</th>
                <th>Zweck</th>
                <th>Speicherdauer</th>
                <th>Rechtsgrundlage</th>
              </tr>
            </thead>
            <tbody>
              ${DATA_PROCESSING.map(dp => `
                <tr>
                  <td>${esc(dp.category)}</td>
                  <td class="text-muted">${esc(dp.purpose)}</td>
                  <td><span class="badge badge-muted">${esc(dp.retention)}</span></td>
                  <td class="text-muted">${esc(dp.legal)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Processing log
    const logRows = processingLog.length
      ? processingLog.map(entry => `
          <tr>
            <td class="log-timestamp">${formatDatetime(entry.timestamp)}</td>
            <td>${esc(entry.action)}</td>
            <td class="text-muted">${esc(entry.details || '\u2013')}</td>
          </tr>
        `).join('')
      : `<tr><td colspan="3" class="text-center text-muted">Keine Eintr\u00e4ge vorhanden.</td></tr>`;

    const logSection = `
      <div class="card mb-16">
        <div class="card-title"><span class="material-symbols-outlined mi-sm">history</span> Verarbeitungsprotokoll</div>
        <div class="table-scroll">
          <table class="log-table">
            <thead>
              <tr>
                <th>Zeitpunkt</th>
                <th>Aktion</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>${logRows}</tbody>
          </table>
        </div>
      </div>
    `;

    // Delete account danger zone with two-step confirmation
    const deleteZone = renderDeleteZone();

    tabContent.innerHTML = summaryHtml + exportSection + consentSection + processingOverview + logSection + deleteZone;
  }

  function renderDeleteZone() {
    if (deleteStep === 0) {
      return `
        <div class="card danger-zone mb-16">
          <div class="card-title text-danger">
            <span class="material-symbols-outlined mi-sm">delete_forever</span> Account l\u00f6schen
          </div>
          <p class="text-muted mb-8">
            Diese Aktion ist <strong>unwiderruflich</strong>. Alle deine Daten werden dauerhaft gel\u00f6scht.
          </p>
          <div class="gdpr-grace-notice mb-12">
            <span class="material-symbols-outlined mi-sm">schedule</span>
            <span>Nach der L\u00f6schung hast du <strong>7 Tage</strong> Zeit, den Vorgang r\u00fcckg\u00e4ngig zu machen. Danach werden alle Daten unwiderruflich entfernt.</span>
          </div>
          <button class="btn btn-danger" onclick="GdprView.startDeleteAccount()">
            <span class="material-symbols-outlined mi-sm">delete_forever</span> Account l\u00f6schen
          </button>
        </div>
      `;
    } else {
      return `
        <div class="card danger-zone mb-16">
          <div class="card-title text-danger">
            <span class="material-symbols-outlined mi-sm">warning</span> Account wirklich l\u00f6schen?
          </div>
          <p class="text-muted mb-8">
            Gib <strong>LOESCHEN</strong> ein, um die L\u00f6schung zu best\u00e4tigen.
          </p>
          <div class="gdpr-grace-notice mb-12">
            <span class="material-symbols-outlined mi-sm">info</span>
            <span>Dein Account wird f\u00fcr 7 Tage deaktiviert. In dieser Zeit kannst du dich erneut anmelden, um die L\u00f6schung abzubrechen. Nach Ablauf werden alle Daten endg\u00fcltig gel\u00f6scht.</span>
          </div>
          <div class="form-group mb-12">
            <input type="text" id="delete-confirm-input" class="input" placeholder='Tippe "LOESCHEN" zur Best\u00e4tigung'
              oninput="GdprView.onDeleteInputChange(this.value)" autocomplete="off" />
          </div>
          <div class="flex gap-8">
            <button class="btn btn-danger" id="gdpr-delete-confirm-btn" onclick="GdprView.confirmDeleteAccount()" disabled>
              <span class="material-symbols-outlined mi-sm">delete_forever</span> Endg\u00fcltig l\u00f6schen
            </button>
            <button class="btn btn-secondary" onclick="GdprView.cancelDeleteAccount()">
              Abbrechen
            </button>
          </div>
        </div>
      `;
    }
  }

  // -- Datenschutz Actions --

  async function requestExport() {
    exportPolling = true;
    const exportArea = document.getElementById('gdpr-export-area');
    if (exportArea) {
      exportArea.innerHTML = `
        <div class="gdpr-export-polling">
          <span class="material-symbols-outlined spin">hourglass_top</span>
          <span>Export wird vorbereitet...</span>
        </div>
      `;
    }

    try {
      const res = await Api.get('/gdpr/data-export');
      if (res && res.data) {
        // Create a downloadable JSON blob from the export data
        const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
        exportUrl = URL.createObjectURL(blob);
        exportPolling = false;
        _updateExportArea();
        showToast('Export bereit. Download-Link ist verf\u00fcgbar.', 'success');
      } else {
        exportPolling = false;
        _updateExportArea();
        showToast('Export fehlgeschlagen: keine Daten erhalten', 'error');
      }
    } catch (e) {
      exportPolling = false;
      _updateExportArea();
      showToast('Fehler beim Anfordern des Exports', 'error');
    }
  }

  function _updateExportArea() {
    const exportArea = document.getElementById('gdpr-export-area');
    if (!exportArea) return;
    if (exportUrl) {
      exportArea.innerHTML = `
        <a class="btn btn-secondary" href="${esc(exportUrl)}" download>
          <span class="material-symbols-outlined mi-sm">download</span> ZIP herunterladen
        </a>
      `;
    } else {
      exportArea.innerHTML = `
        <button class="btn btn-primary" onclick="GdprView.requestExport()">
          <span class="material-symbols-outlined mi-sm">cloud_download</span> Meine Daten exportieren
        </button>
      `;
    }
  }

  async function saveConsents() {
    const CONSENT_CATEGORIES = ['analytics', 'personalization', 'email_notifications', 'data_sharing'];
    const updates = CONSENT_CATEGORIES.map(cat => {
      const el = document.getElementById(`consent-${cat}`);
      return { category: cat, granted: el ? el.checked : false };
    });
    try {
      await Promise.all(updates.map(u => {
        if (u.granted) {
          return Api.post(`/gdpr/consents/${u.category}`, {});
        } else {
          return Api.delete(`/gdpr/consents/${u.category}`);
        }
      }));
      showToast('Einwilligungen gespeichert', 'success');
      const consentsRes = await Api.get('/gdpr/consents');
      consents = consentsRes && consentsRes.consents ? consentsRes.consents : {};
    } catch (e) {
      showToast('Fehler beim Speichern der Einwilligungen', 'error');
    }
  }

  async function revokeConsent(category) {
    if (!confirm(`Einwilligung f\u00fcr "${consentLabel(category)}" wirklich widerrufen?`)) return;
    try {
      await Api.delete(`/gdpr/consents/${category}`);
      showToast('Einwilligung widerrufen', 'success');
      const consentsRes = await Api.get('/gdpr/consents');
      consents = consentsRes && consentsRes.consents ? consentsRes.consents : {};
      // Re-render consent rows
      const container = { querySelector: (sel) => document.querySelector(sel) };
      renderDatenschutzTab(container);
    } catch (e) {
      showToast('Fehler beim Widerrufen', 'error');
    }
  }

  function startDeleteAccount() {
    deleteStep = 1;
    _replaceDangerZone();
  }

  function onDeleteInputChange(value) {
    deleteConfirmText = value;
    const btn = document.getElementById('gdpr-delete-confirm-btn');
    if (btn) {
      btn.disabled = value.trim() !== 'LOESCHEN';
    }
  }

  async function confirmDeleteAccount() {
    if (deleteConfirmText.trim() !== 'LOESCHEN') {
      showToast('Bitte "LOESCHEN" eingeben', 'error');
      return;
    }
    try {
      await Api.delete('/gdpr/account');
      showToast('Account zur L\u00f6schung vorgemerkt. Du hast 7 Tage, um dies r\u00fcckg\u00e4ngig zu machen.', 'success');
      deleteStep = 0;
      setTimeout(() => {
        Api.logout();
      }, 3000);
    } catch (e) {
      showToast('Fehler beim L\u00f6schen des Accounts: ' + (e.message || 'Unbekannter Fehler'), 'error');
    }
  }

  function cancelDeleteAccount() {
    deleteStep = 0;
    deleteConfirmText = '';
    _replaceDangerZone();
  }

  function _replaceDangerZone() {
    const zone = document.querySelector('.danger-zone');
    if (zone) {
      const div = document.createElement('div');
      div.innerHTML = renderDeleteZone();
      zone.replaceWith(div.firstElementChild);
    }
  }

  // -- Follow-ups Tab --

  async function loadFollowupsTab(container) {
    try {
      const [allRes, dueRes] = await Promise.all([
        Api.get('/followups/'),
        Api.get('/followups/due'),
      ]);
      followups = (allRes || []).slice().sort((a, b) => {
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return new Date(a.due_date) - new Date(b.due_date);
      });
      dueFollowups = dueRes || [];
    } catch (e) {
      showToast('Fehler beim Laden der Follow-ups', 'error');
      followups = [];
      dueFollowups = [];
    }
    renderFollowupsTab(container);
  }

  function renderFollowupsTab(container) {
    const tabContent = container.querySelector('#gdpr-tab-content');
    if (!tabContent) return;

    let dueSection = '';
    if (dueFollowups.length > 0) {
      const dueItems = dueFollowups.map(f => renderFollowupCard(f, true)).join('');
      dueSection = `
        <div class="card mb-16 due-followups-card">
          <div class="card-title text-warning">
            <span class="material-symbols-outlined mi-sm">notification_important</span>
            F\u00e4llige Follow-ups (${dueFollowups.length})
          </div>
          <div>${dueItems}</div>
        </div>
      `;
    }

    const createForm = showCreateForm ? renderCreateFollowupForm() : `
      <div class="mb-16">
        <button class="btn btn-primary" onclick="GdprView.toggleCreateForm()">
          <span class="material-symbols-outlined mi-sm">add</span> Follow-up erstellen
        </button>
      </div>
    `;

    let listHtml = '';
    if (followups.length === 0) {
      listHtml = `<div class="empty-state"><span class="material-symbols-outlined">event_upcoming</span><p>Keine Follow-ups vorhanden.</p></div>`;
    } else {
      listHtml = followups.map(f => renderFollowupCard(f, false)).join('');
    }

    tabContent.innerHTML = dueSection + createForm + `
      <div class="section-subheader mb-8">
        <span class="material-symbols-outlined mi-sm">list</span> Alle Follow-ups
      </div>
      <div id="followup-list">${listHtml}</div>
    `;
  }

  function renderFollowupCard(f, highlight) {
    const statusBadge = followupStatusBadge(f.status, f.due_date);
    const refBadge = refTypeBadge(f.reference_type);
    const isDone = f.status === 'done';
    const highlightClass = highlight ? 'followup-card-highlight' : '';

    return `
      <div class="card followup-card mb-8 ${highlightClass}" data-id="${esc(String(f.id))}">
        <div class="followup-header">
          <div class="followup-subject">${esc(f.subject)}</div>
          <div class="followup-badges">
            ${statusBadge}
            ${refBadge}
          </div>
        </div>
        <div class="followup-meta text-muted text-sm mt-4">
          <span class="material-symbols-outlined mi-xs">calendar_today</span>
          F\u00e4llig: ${formatDate(f.due_date)}
          ${f.reference_id ? `<span class="ml-8">Ref: #${esc(String(f.reference_id))}</span>` : ''}
        </div>
        <div class="followup-actions mt-8 flex gap-8">
          ${!isDone ? `<button class="btn btn-sm btn-primary" onclick="GdprView.markDone(${f.id})">
            <span class="material-symbols-outlined mi-sm">check_circle</span> Als erledigt
          </button>` : ''}
          <button class="btn btn-sm btn-danger" onclick="GdprView.deleteFollowup(${f.id})">
            <span class="material-symbols-outlined mi-sm">delete</span>
          </button>
        </div>
      </div>
    `;
  }

  function renderCreateFollowupForm() {
    return `
      <div class="card mb-16" id="followup-create-form">
        <div class="card-title">
          <span class="material-symbols-outlined mi-sm">add_task</span> Neues Follow-up
        </div>
        <div class="form-group mb-8">
          <label>Betreff</label>
          <input type="text" id="fu-subject" class="input" placeholder="Worum geht es?">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>F\u00e4lligkeitsdatum</label>
            <input type="date" id="fu-due-date" class="input">
          </div>
          <div class="form-group">
            <label>Referenztyp</label>
            <select id="fu-ref-type" class="input">
              <option value="">\u2013 kein \u2013</option>
              <option value="task">Aufgabe</option>
              <option value="conversation">Gespr\u00e4ch</option>
              <option value="invoice">Rechnung</option>
              <option value="contract">Vertrag</option>
              <option value="document">Dokument</option>
            </select>
          </div>
        </div>
        <div class="form-group mb-8">
          <label>Referenz-ID (optional)</label>
          <input type="number" id="fu-ref-id" class="input" placeholder="z.B. 42">
        </div>
        <div class="flex gap-8 mt-12">
          <button class="btn btn-primary" onclick="GdprView.createFollowup()">
            <span class="material-symbols-outlined mi-sm">save</span> Erstellen
          </button>
          <button class="btn btn-secondary" onclick="GdprView.toggleCreateForm()">
            Abbrechen
          </button>
        </div>
      </div>
    `;
  }

  // -- Follow-ups Actions --

  async function markDone(id) {
    try {
      await Api.patch(`/followups/${id}`, { status: 'done' });
      showToast('Follow-up als erledigt markiert', 'success');
      followups = followups.map(f => f.id === id ? { ...f, status: 'done' } : f);
      dueFollowups = dueFollowups.filter(f => f.id !== id);
      _rerenderFollowupsInPlace();
    } catch (e) {
      showToast('Fehler beim Aktualisieren des Follow-ups', 'error');
    }
  }

  async function deleteFollowup(id) {
    if (!confirm('Follow-up wirklich l\u00f6schen?')) return;
    try {
      await Api.delete(`/followups/${id}`);
      showToast('Follow-up gel\u00f6scht', 'success');
      followups = followups.filter(f => f.id !== id);
      dueFollowups = dueFollowups.filter(f => f.id !== id);
      _rerenderFollowupsInPlace();
    } catch (e) {
      showToast('Fehler beim L\u00f6schen des Follow-ups', 'error');
    }
  }

  function _rerenderFollowupsInPlace() {
    renderFollowupsTab({ querySelector: (sel) => document.querySelector(sel) });
  }

  async function createFollowup() {
    const subject = (document.getElementById('fu-subject') || {}).value || '';
    const dueDate = (document.getElementById('fu-due-date') || {}).value || '';
    const refType = (document.getElementById('fu-ref-type') || {}).value || '';
    const refIdRaw = (document.getElementById('fu-ref-id') || {}).value || '';
    const refId = refIdRaw ? parseInt(refIdRaw, 10) : null;

    if (!subject.trim()) {
      showToast('Bitte Betreff angeben', 'error');
      return;
    }
    if (!dueDate) {
      showToast('Bitte F\u00e4lligkeitsdatum angeben', 'error');
      return;
    }

    const payload = {
      subject: subject.trim(),
      due_date: dueDate,
      reference_type: refType || null,
      reference_id: refId,
    };

    try {
      const created = await Api.post('/followups/', payload);
      showToast('Follow-up erstellt', 'success');
      followups = [...followups, created].sort((a, b) => {
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return new Date(a.due_date) - new Date(b.due_date);
      });
      showCreateForm = false;
      _rerenderFollowupsInPlace();
    } catch (e) {
      showToast('Fehler beim Erstellen des Follow-ups', 'error');
    }
  }

  function toggleCreateForm() {
    showCreateForm = !showCreateForm;
    _rerenderFollowupsInPlace();
  }

  // -- Tab Switch --

  function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.textContent.toLowerCase().includes(tab === 'datenschutz' ? 'datenschutz' : 'follow'));
    if (activeBtn) activeBtn.classList.add('active');

    const tabContent = document.getElementById('gdpr-tab-content');
    if (!tabContent) return;
    tabContent.innerHTML = `<div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div>`;

    const container = { querySelector: (sel) => document.querySelector(sel) };
    if (tab === 'datenschutz') {
      loadDatenschutzTab(container);
    } else {
      loadFollowupsTab(container);
    }
  }

  // -- Public API --

  return {
    render,
    switchTab,
    // Datenschutz
    requestExport,
    saveConsents,
    revokeConsent,
    startDeleteAccount,
    confirmDeleteAccount,
    cancelDeleteAccount,
    onDeleteInputChange,
    // Follow-ups
    markDone,
    deleteFollowup,
    createFollowup,
    toggleCreateForm,
  };
})();
