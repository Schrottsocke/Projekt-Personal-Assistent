/**
 * DualMind Dokumente View
 * Dokumenten-Eingang: Upload, OCR-Ergebnis, Drive-Ablage, Folgeaktionen.
 */
const DocumentsView = (() => {
  let documents = [];
  let loading = false;
  let container = null;
  let typeFilter = null;

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

  function renderHeader() {
    return `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">scanner</span> Dokumente</h2>
        <button class="btn btn-sm btn-primary" id="doc-upload-btn">
          <span class="material-symbols-outlined">upload_file</span> Hochladen
        </button>
      </div>
    `;
  }

  function renderUploadForm() {
    return `
      <div id="doc-upload-form" class="card" style="display:none;margin-bottom:16px">
        <h3>Dokument hochladen</h3>
        <p style="color:var(--text-secondary);margin-bottom:12px">
          Lade ein Bild oder PDF hoch. OCR und Analyse werden automatisch ausgefuehrt.
        </p>
        <input type="file" id="doc-file-input" accept="image/*,.pdf" style="margin-bottom:12px">
        <div style="display:flex;gap:8px">
          <button class="btn btn-primary" id="doc-submit-btn" disabled>Verarbeiten</button>
          <button class="btn btn-secondary" id="doc-cancel-btn">Abbrechen</button>
        </div>
        <div id="doc-upload-progress" style="display:none;margin-top:12px">
          <div class="spinner"></div>
          <span style="margin-left:8px">Dokument wird verarbeitet...</span>
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
      <div class="card doc-card" data-id="${doc.id}" style="margin-bottom:8px;cursor:pointer">
        <div style="display:flex;align-items:center;gap:12px">
          <span class="material-symbols-outlined" style="color:${meta.color};font-size:32px">${meta.icon}</span>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600">${doc.doc_type}${doc.sender ? ' – ' + doc.sender : ''}</div>
            <div style="color:var(--text-secondary);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              ${doc.summary || doc.filename}
            </div>
            <div style="display:flex;gap:12px;margin-top:4px;font-size:12px;color:var(--text-secondary)">
              ${doc.amount ? `<span>💶 ${doc.amount}</span>` : ''}
              <span>${formatDate(doc.scanned_at)}</span>
            </div>
          </div>
          ${doc.drive_link ? `<a href="${doc.drive_link}" target="_blank" class="btn-icon" title="In Drive oeffnen" onclick="event.stopPropagation()"><span class="material-symbols-outlined">open_in_new</span></a>` : ''}
        </div>
      </div>
    `;
  }

  function renderList() {
    if (loading) return '<div class="loading"><div class="spinner"></div></div>';
    if (!documents.length) {
      return `
        <div class="empty-state">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-secondary)">scanner</span>
          <p>Keine Dokumente vorhanden</p>
          <p style="font-size:13px;color:var(--text-secondary)">Lade ein Dokument hoch, um OCR und Analyse zu starten.</p>
        </div>
      `;
    }
    return documents.map(renderDocument).join('');
  }

  async function load() {
    loading = true;
    update();
    try {
      const params = new URLSearchParams();
      if (typeFilter) params.set('doc_type', typeFilter);
      const qs = params.toString();
      const data = await Api.request(`/documents${qs ? '?' + qs : ''}`);
      documents = data.items || [];
    } catch (err) {
      documents = [];
    } finally {
      loading = false;
    }
    update();
  }

  function update() {
    if (!container) return;
    container.innerHTML = `
      ${renderHeader()}
      ${renderUploadForm()}
      ${renderFilters()}
      <div class="doc-list">${renderList()}</div>
    `;
    bindEvents();
  }

  function bindEvents() {
    if (!container) return;

    // Upload toggle
    const uploadBtn = container.querySelector('#doc-upload-btn');
    const uploadForm = container.querySelector('#doc-upload-form');
    const fileInput = container.querySelector('#doc-file-input');
    const submitBtn = container.querySelector('#doc-submit-btn');
    const cancelBtn = container.querySelector('#doc-cancel-btn');

    uploadBtn?.addEventListener('click', () => {
      uploadForm.style.display = uploadForm.style.display === 'none' ? 'block' : 'none';
    });

    cancelBtn?.addEventListener('click', () => {
      uploadForm.style.display = 'none';
      fileInput.value = '';
      submitBtn.disabled = true;
    });

    fileInput?.addEventListener('change', () => {
      submitBtn.disabled = !fileInput.files.length;
    });

    submitBtn?.addEventListener('click', async () => {
      const file = fileInput.files[0];
      if (!file) return;
      const progress = container.querySelector('#doc-upload-progress');
      progress.style.display = 'flex';
      submitBtn.disabled = true;

      try {
        const formData = new FormData();
        formData.append('file', file);

        const token = Api.getToken();
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch('/documents/upload', {
          method: 'POST',
          headers,
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }

        Toast.show('Dokument erfolgreich verarbeitet', 'success');
        uploadForm.style.display = 'none';
        fileInput.value = '';
        await load();
      } catch (err) {
        Toast.show(err.message || 'Upload fehlgeschlagen');
      } finally {
        progress.style.display = 'none';
        submitBtn.disabled = false;
      }
    });

    // Type filters
    container.querySelectorAll('[data-doc-type]').forEach(btn => {
      btn.addEventListener('click', () => {
        typeFilter = btn.dataset.docType || null;
        load();
      });
    });
  }

  async function render(el) {
    container = el;
    typeFilter = null;
    await load();
  }

  return { render };
})();
