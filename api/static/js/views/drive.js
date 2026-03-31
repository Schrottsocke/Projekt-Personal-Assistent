/**
 * Drive View – File List, Search, Upload
 */
const DriveView = (() => {
  let files = [];
  let connected = false;
  let searchTimer = null;
  let uploading = false;

  function formatSize(bytes) {
    if (!bytes) return '';
    const num = parseInt(bytes);
    if (isNaN(num)) return bytes;
    if (num < 1024) return num + ' B';
    if (num < 1048576) return (num / 1024).toFixed(1) + ' KB';
    return (num / 1048576).toFixed(1) + ' MB';
  }

  function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function fileIcon(mimeType) {
    if (!mimeType) return '&#128196;';
    if (mimeType.startsWith('image/')) return '&#128247;';
    if (mimeType.startsWith('video/')) return '&#127910;';
    if (mimeType.startsWith('audio/')) return '&#127925;';
    if (mimeType.includes('pdf')) return '&#128212;';
    if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return '&#128202;';
    if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '&#128202;';
    if (mimeType.includes('document') || mimeType.includes('word')) return '&#128196;';
    if (mimeType.includes('folder')) return '&#128193;';
    return '&#128196;';
  }

  async function render(container) {
    container.innerHTML = `
      <a class="view-back" href="#/dashboard">&#8592; Dashboard</a>
      <div class="section-header"><span class="section-icon">&#128193;</span> Drive</div>
      <div id="drive-status"></div>
      <div class="input-group mb-8">
        <input type="search" id="drive-search" placeholder="Dateien suchen…"
               oninput="DriveView.onSearch(this.value)">
      </div>
      <div id="drive-upload-area">
        <div class="upload-area">
          <input type="file" id="drive-file-input" class="hidden" onchange="DriveView.handleFileSelect()">
          <button class="btn btn-sm btn-secondary" onclick="document.getElementById('drive-file-input').click()" id="upload-btn">
            &#128228; Datei hochladen
          </button>
          <span id="upload-status" class="card-subtitle" style="margin-left:8px"></span>
        </div>
      </div>
      <div id="drive-list"><div class="loading"><div class="spinner"></div> Laden…</div></div>
    `;
    await loadFiles();
  }

  async function loadFiles(query) {
    try {
      const data = await Api.getDriveFiles(query);
      connected = data.connected !== false;
      files = data.files || [];
      renderStatus();
      renderFiles();
    } catch (err) {
      document.getElementById('drive-list').innerHTML = `
        <div class="error-state"><p>${escapeHtml(err.message)}</p>
          <button class="btn btn-secondary" onclick="DriveView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

  function renderStatus() {
    const el = document.getElementById('drive-status');
    if (!el) return;
    if (!connected) {
      el.innerHTML = `<div class="card" style="border-color:var(--warning)">
        <div class="flex-between">
          <span>&#9888; Google Drive nicht verbunden</span>
          <span class="badge badge-warning">Nicht verbunden</span>
        </div>
      </div>`;
    } else {
      el.innerHTML = '';
    }
  }

  function onSearch(query) {
    clearTimeout(searchTimer);
    if (!query.trim()) {
      loadFiles();
      return;
    }
    searchTimer = setTimeout(() => loadFiles(query.trim()), 400);
  }

  function renderFiles() {
    const el = document.getElementById('drive-list');
    if (!el) return;

    if (files.length === 0) {
      el.innerHTML = `<div class="empty-state">${connected ? 'Keine Dateien gefunden' : 'Drive nicht verbunden'}</div>`;
      return;
    }

    el.innerHTML = files.map(f => `
      <div class="file-item">
        <span class="file-icon">${fileIcon(f.mime_type)}</span>
        <div class="file-info">
          <div class="file-name">${escapeHtml(f.name)}</div>
          <div class="file-meta">
            ${f.size ? formatSize(f.size) : ''}
            ${f.modified_time ? ' &middot; ' + formatDate(f.modified_time) : ''}
          </div>
        </div>
        ${f.web_view_link ? `<a href="${escapeHtml(f.web_view_link)}" target="_blank" rel="noopener" class="btn btn-sm btn-secondary" title="Oeffnen">&#128279;</a>` : ''}
      </div>
    `).join('');
  }

  async function handleFileSelect() {
    const input = document.getElementById('drive-file-input');
    const file = input.files && input.files[0];
    if (!file || uploading) return;

    uploading = true;
    const statusEl = document.getElementById('upload-status');
    const btn = document.getElementById('upload-btn');
    if (statusEl) statusEl.textContent = `Hochladen: ${file.name}…`;
    if (btn) btn.disabled = true;

    try {
      const result = await Api.uploadFile(file);
      if (statusEl) statusEl.textContent = `"${result.name}" hochgeladen`;
      // Reload file list
      await loadFiles();
    } catch (err) {
      if (statusEl) statusEl.textContent = `Fehler: ${err.message}`;
    } finally {
      uploading = false;
      if (btn) btn.disabled = false;
      input.value = '';
    }
  }

  return { render, onSearch, handleFileSelect };
})();
