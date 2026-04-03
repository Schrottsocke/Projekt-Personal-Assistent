/**
 * DualMind Dokumente View
 * Dokumenten-Scanner: Upload, Kamera, Multi-Page, OCR, Detail-Ansicht, Folgeaktionen.
 */
const DocumentsView = (() => {
  let documents = [];
  let loading = false;
  let container = null;
  let typeFilter = null;
  let currentDetail = null;
  let selectedFiles = [];

  const DOC_TYPES = {
    'Rechnung': { icon: 'receipt_long', color: 'var(--accent)' },
    'Brief': { icon: 'mail', color: 'var(--info, #42a5f5)' },
    'Vertrag': { icon: 'description', color: 'var(--warning)' },
    'Arztbrief': { icon: 'medical_information', color: 'var(--error)' },
    'Sonstiges': { icon: 'article', color: 'var(--text-secondary)' },
  };

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
  }

  // ── List View ──

  function renderHeader() {
    return `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">document_scanner</span> Dokumente</h2>
        <button class="btn btn-sm btn-primary" id="doc-upload-btn">
          <span class="material-symbols-outlined">add</span> Neu
        </button>
      </div>
    `;
  }

  function renderUploadForm() {
    return `
      <div id="doc-upload-form" class="card doc-upload-card" style="display:none">
        <h3 style="margin-bottom:4px">Dokument scannen</h3>
        <p style="color:var(--text-secondary);font-size:13px;margin-bottom:12px">
          Lade Bilder oder PDFs hoch. OCR und Analyse laufen automatisch.
        </p>

        <div class="doc-capture-row">
          <label class="doc-capture-btn" id="doc-camera-label">
            <span class="material-symbols-outlined">photo_camera</span>
            <span>Kamera</span>
            <input type="file" accept="image/*" capture="environment" id="doc-camera-input" hidden>
          </label>
          <label class="doc-capture-btn" id="doc-file-label">
            <span class="material-symbols-outlined">upload_file</span>
            <span>Datei</span>
            <input type="file" accept="image/*,.pdf" multiple id="doc-file-input" hidden>
          </label>
        </div>

        <div id="doc-preview-area" class="doc-preview-area" style="display:none"></div>

        <div style="display:flex;gap:8px;margin-top:12px">
          <button class="btn btn-primary" id="doc-submit-btn" disabled>
            <span class="material-symbols-outlined" style="font-size:18px">play_arrow</span> Verarbeiten
          </button>
          <button class="btn btn-secondary" id="doc-cancel-btn">Abbrechen</button>
        </div>

        <div id="doc-upload-progress" class="doc-progress" style="display:none">
          <div class="spinner"></div>
          <div class="doc-progress-text">
            <span id="doc-progress-label">Dokument wird verarbeitet...</span>
            <span id="doc-progress-step" style="font-size:12px;color:var(--text-secondary)">OCR und Analyse</span>
          </div>
        </div>
      </div>
    `;
  }

  function renderFilters() {
    const types = Object.keys(DOC_TYPES);
    return `
      <div class="notification-filter-row" style="margin-bottom:12px">
        <button class="filter-chip ${!typeFilter ? 'active' : ''}" data-doc-type="">Alle</button>
        ${types.map(t => `
          <button class="filter-chip ${typeFilter === t ? 'active' : ''}" data-doc-type="${t}">${t}</button>
        `).join('')}
      </div>
    `;
  }

  function renderDocument(doc) {
    const meta = DOC_TYPES[doc.doc_type] || DOC_TYPES['Sonstiges'];
    return `
      <div class="card doc-card" data-id="${doc.id}">
        <div style="display:flex;align-items:center;gap:12px">
          <span class="material-symbols-outlined" style="color:${meta.color};font-size:32px">${meta.icon}</span>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600">${doc.doc_type}${doc.sender ? ' – ' + doc.sender : ''}</div>
            <div style="color:var(--text-secondary);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              ${doc.summary || doc.filename}
            </div>
            <div style="display:flex;gap:12px;margin-top:4px;font-size:12px;color:var(--text-secondary)">
              ${doc.amount ? `<span style="color:var(--accent);font-weight:500">${doc.amount}</span>` : ''}
              <span>${formatDate(doc.scanned_at)}</span>
            </div>
          </div>
          <span class="material-symbols-outlined" style="color:var(--text-secondary);font-size:20px">chevron_right</span>
        </div>
      </div>
    `;
  }

  function renderList() {
    if (loading) return '<div class="loading"><div class="spinner"></div></div>';
    if (!documents.length) {
      return `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-secondary)">document_scanner</span>
          <p>Keine Dokumente vorhanden</p>
          <p style="font-size:13px;color:var(--text-secondary)">Scanne dein erstes Dokument per Kamera oder Datei-Upload.</p>
        </div>
      `;
    }
    return documents.map(renderDocument).join('');
  }

  // ── Detail View ──

  function renderDetail(doc) {
    const meta = DOC_TYPES[doc.doc_type] || DOC_TYPES['Sonstiges'];
    const ocrPreview = doc.ocr_text
      ? doc.ocr_text.substring(0, 2000)
      : 'Kein OCR-Text verfuegbar.';

    return `
      <div class="doc-detail">
        <button class="doc-back-btn" id="doc-back-btn">
          <span class="material-symbols-outlined">arrow_back</span> Zurueck
        </button>

        <div class="card" style="margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            <span class="material-symbols-outlined" style="color:${meta.color};font-size:40px">${meta.icon}</span>
            <div>
              <h3 style="margin:0">${doc.doc_type}${doc.sender ? ' – ' + doc.sender : ''}</h3>
              <div style="color:var(--text-secondary);font-size:13px">${formatDate(doc.scanned_at)} · ${doc.filename}</div>
            </div>
          </div>

          ${doc.summary ? `<p style="margin-bottom:8px">${doc.summary}</p>` : ''}

          <div class="doc-detail-meta">
            ${doc.amount ? `<div class="doc-meta-chip"><span class="material-symbols-outlined">payments</span> ${doc.amount}</div>` : ''}
            ${doc.sender ? `<div class="doc-meta-chip"><span class="material-symbols-outlined">person</span> ${doc.sender}</div>` : ''}
            ${doc.drive_link ? `<a href="${doc.drive_link}" target="_blank" class="doc-meta-chip doc-meta-link"><span class="material-symbols-outlined">cloud</span> In Drive oeffnen</a>` : ''}
          </div>
        </div>

        <div class="card" style="margin-bottom:12px">
          <h4 style="margin-bottom:8px;display:flex;align-items:center;gap:6px">
            <span class="material-symbols-outlined" style="font-size:20px">text_snippet</span> Erkannter Text
          </h4>
          <pre class="doc-ocr-text">${escapeHtml(ocrPreview)}</pre>
        </div>

        <div class="card doc-actions-card">
          <h4 style="margin-bottom:10px;display:flex;align-items:center;gap:6px">
            <span class="material-symbols-outlined" style="font-size:20px">bolt</span> Aktionen
          </h4>
          <div class="doc-actions-row">
            <button class="btn btn-secondary doc-action-btn" data-action="create_task" data-doc-id="${doc.id}">
              <span class="material-symbols-outlined">add_task</span> Aufgabe erstellen
            </button>
            <button class="btn btn-secondary doc-action-btn" data-action="save_memory" data-doc-id="${doc.id}">
              <span class="material-symbols-outlined">psychology</span> Merken
            </button>
            <button class="btn btn-secondary doc-action-btn" data-action="draft_email" data-doc-id="${doc.id}">
              <span class="material-symbols-outlined">forward_to_inbox</span> E-Mail-Entwurf
            </button>
          </div>
          <div id="doc-action-result" style="display:none;margin-top:12px"></div>
        </div>
      </div>
    `;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Data Loading ──

  async function load() {
    loading = true;
    update();
    try {
      const params = new URLSearchParams();
      if (typeFilter) params.set('doc_type', typeFilter);
      const qs = params.toString();
      const data = await Api.request(`/documents${qs ? '?' + qs : ''}`);
      documents = Array.isArray(data) ? data : (data.items || []);
    } catch (err) {
      documents = [];
    } finally {
      loading = false;
    }
    update();
  }

  async function loadDetail(docId) {
    try {
      currentDetail = await Api.request(`/documents/${docId}`);
    } catch (err) {
      Toast.show('Dokument konnte nicht geladen werden', 'error');
      currentDetail = null;
    }
    update();
  }

  // ── Rendering ──

  function update() {
    if (!container) return;

    if (currentDetail) {
      container.innerHTML = renderDetail(currentDetail);
      bindDetailEvents();
    } else {
      container.innerHTML = `
        ${renderHeader()}
        ${renderUploadForm()}
        ${renderFilters()}
        <div class="doc-list">${renderList()}</div>
      `;
      bindListEvents();
    }
  }

  // ── Upload Logic ──

  function updatePreviewArea() {
    const area = container.querySelector('#doc-preview-area');
    const submitBtn = container.querySelector('#doc-submit-btn');
    if (!area) return;

    if (!selectedFiles.length) {
      area.style.display = 'none';
      if (submitBtn) submitBtn.disabled = true;
      return;
    }

    area.style.display = 'flex';
    if (submitBtn) submitBtn.disabled = false;

    area.innerHTML = selectedFiles.map((f, i) => `
      <div class="doc-preview-item">
        <span class="material-symbols-outlined" style="font-size:24px;color:var(--text-secondary)">
          ${f.type.startsWith('image/') ? 'image' : 'picture_as_pdf'}
        </span>
        <span class="doc-preview-name">${f.name}</span>
        <button class="doc-preview-remove" data-idx="${i}" title="Entfernen">&times;</button>
      </div>
    `).join('');

    // Remove-Buttons
    area.querySelectorAll('.doc-preview-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.target.dataset.idx);
        selectedFiles.splice(idx, 1);
        updatePreviewArea();
      });
    });
  }

  async function handleUpload() {
    if (!selectedFiles.length) return;

    const progress = container.querySelector('#doc-upload-progress');
    const submitBtn = container.querySelector('#doc-submit-btn');
    const progressLabel = container.querySelector('#doc-progress-label');
    const progressStep = container.querySelector('#doc-progress-step');

    progress.style.display = 'flex';
    submitBtn.disabled = true;
    progressLabel.textContent = 'Dokument wird verarbeitet...';
    progressStep.textContent = 'OCR, Analyse und PDF-Erstellung';

    try {
      let result;
      if (selectedFiles.length === 1) {
        result = await Api.uploadFile(selectedFiles[0], '/documents/upload');
      } else {
        result = await Api.uploadFiles(selectedFiles, '/documents/upload-multi');
      }

      Toast.show(`${result.doc_type} erfolgreich verarbeitet`, 'success');

      // Upload-Form zuruecksetzen
      const uploadForm = container.querySelector('#doc-upload-form');
      if (uploadForm) uploadForm.style.display = 'none';
      selectedFiles = [];

      // Detail anzeigen
      currentDetail = result;
      update();
    } catch (err) {
      Toast.show(err.message || 'Verarbeitung fehlgeschlagen', 'error');
    } finally {
      if (progress) progress.style.display = 'none';
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  // ── Event Binding ──

  function bindListEvents() {
    if (!container) return;

    // Upload-Toggle
    const uploadBtn = container.querySelector('#doc-upload-btn');
    const uploadForm = container.querySelector('#doc-upload-form');
    const cameraInput = container.querySelector('#doc-camera-input');
    const fileInput = container.querySelector('#doc-file-input');
    const submitBtn = container.querySelector('#doc-submit-btn');
    const cancelBtn = container.querySelector('#doc-cancel-btn');

    uploadBtn?.addEventListener('click', () => {
      uploadForm.style.display = uploadForm.style.display === 'none' ? 'block' : 'none';
      selectedFiles = [];
      updatePreviewArea();
    });

    cancelBtn?.addEventListener('click', () => {
      uploadForm.style.display = 'none';
      selectedFiles = [];
      if (fileInput) fileInput.value = '';
      if (cameraInput) cameraInput.value = '';
    });

    // Kamera-Aufnahme
    cameraInput?.addEventListener('change', () => {
      if (cameraInput.files.length) {
        selectedFiles.push(...Array.from(cameraInput.files));
        cameraInput.value = '';
        updatePreviewArea();
      }
    });

    // Datei-Auswahl (multiple)
    fileInput?.addEventListener('change', () => {
      if (fileInput.files.length) {
        selectedFiles.push(...Array.from(fileInput.files));
        fileInput.value = '';
        updatePreviewArea();
      }
    });

    // Verarbeiten
    submitBtn?.addEventListener('click', handleUpload);

    // Type-Filter
    container.querySelectorAll('[data-doc-type]').forEach(btn => {
      btn.addEventListener('click', () => {
        typeFilter = btn.dataset.docType || null;
        load();
      });
    });

    // Dokument-Cards -> Detail
    container.querySelectorAll('.doc-card[data-id]').forEach(card => {
      card.addEventListener('click', () => {
        const docId = card.dataset.id;
        loadDetail(docId);
      });
    });
  }

  function bindDetailEvents() {
    if (!container) return;

    // Zurueck
    container.querySelector('#doc-back-btn')?.addEventListener('click', () => {
      currentDetail = null;
      load();
    });

    // Action-Buttons
    container.querySelectorAll('.doc-action-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const action = btn.dataset.action;
        const docId = btn.dataset.docId;
        const resultArea = container.querySelector('#doc-action-result');

        btn.disabled = true;
        btn.querySelector('.material-symbols-outlined').textContent = 'hourglass_empty';

        try {
          const res = await Api.post(`/documents/${docId}/actions`, { action });

          if (action === 'create_task') {
            Toast.show('Aufgabe erstellt', 'success');
            if (resultArea) {
              resultArea.style.display = 'block';
              resultArea.innerHTML = `<div class="badge badge-success">Aufgabe erstellt</div>`;
            }
          } else if (action === 'save_memory') {
            Toast.show('In Erinnerung gespeichert', 'success');
            if (resultArea) {
              resultArea.style.display = 'block';
              resultArea.innerHTML = `<div class="badge badge-success">Gespeichert</div>`;
            }
          } else if (action === 'draft_email') {
            Toast.show('E-Mail-Entwurf erstellt', 'success');
            if (resultArea && res.draft) {
              resultArea.style.display = 'block';
              resultArea.innerHTML = `
                <div class="doc-email-draft">
                  <div style="font-weight:600;margin-bottom:4px">Betreff: ${escapeHtml(res.draft.subject)}</div>
                  <pre style="white-space:pre-wrap;font-size:13px;color:var(--text-secondary)">${escapeHtml(res.draft.body)}</pre>
                </div>
              `;
            }
          }
        } catch (err) {
          Toast.show(err.message || 'Aktion fehlgeschlagen', 'error');
        } finally {
          btn.disabled = false;
          const icons = { create_task: 'add_task', save_memory: 'psychology', draft_email: 'forward_to_inbox' };
          btn.querySelector('.material-symbols-outlined').textContent = icons[action] || 'bolt';
        }
      });
    });
  }

  // ── Public API ──

  async function render(el) {
    container = el;
    typeFilter = null;
    currentDetail = null;
    selectedFiles = [];
    await load();
  }

  return { render };
})();
