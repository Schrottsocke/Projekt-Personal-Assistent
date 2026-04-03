/**
 * Issues View – GitHub Issue-Liste + Erstellung
 * #458: Timeout, Retry mit Backoff, Error-Klassifikation
 */
const IssuesView = (() => {
  let labels = [];
  let submitting = false;

  const RETRY_DELAYS = [1000, 3000, 10000];

  /* ---------- Error Classification ---------- */

  function classifyError(err) {
    const msg = err.message || '';
    if (msg.includes('401') || msg.includes('Session abgelaufen')) {
      return { type: 'auth', message: 'Authentifizierung fehlgeschlagen. Bitte erneut einloggen.', icon: 'lock' };
    }
    if (msg.includes('403') || msg.toLowerCase().includes('rate')) {
      return { type: 'rate_limit', message: 'API-Rate-Limit erreicht. Bitte warte einen Moment.', icon: 'schedule' };
    }
    if (msg.includes('Zeitüberschreitung') || err.name === 'AbortError') {
      return { type: 'timeout', message: 'Zeitüberschreitung – der Server hat nicht rechtzeitig geantwortet.', icon: 'timer_off' };
    }
    if (msg.includes('5') && /HTTP 5\d\d/.test(msg)) {
      return { type: 'server', message: 'Serverfehler – bitte später erneut versuchen.', icon: 'cloud_off' };
    }
    if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('network')) {
      return { type: 'network', message: 'Keine Verbindung zum Server. Prüfe deine Internetverbindung.', icon: 'wifi_off' };
    }
    return { type: 'unknown', message: msg || 'Ein unbekannter Fehler ist aufgetreten.', icon: 'error' };
  }

  /* ---------- Retry with Backoff ---------- */

  async function withRetry(fn) {
    let lastError;
    for (let attempt = 0; attempt <= RETRY_DELAYS.length; attempt++) {
      try {
        return await fn();
      } catch (err) {
        lastError = err;
        const classified = classifyError(err);
        // Don't retry auth errors
        if (classified.type === 'auth') throw err;
        // Don't retry if we've exhausted retries
        if (attempt >= RETRY_DELAYS.length) throw err;
        // Wait before next attempt
        await new Promise(r => setTimeout(r, RETRY_DELAYS[attempt]));
      }
    }
    throw lastError;
  }

  /* ---------- Render ---------- */

  async function render(container) {
    container.innerHTML = `
      <a class="view-back" href="#/profile"><span class="material-symbols-outlined mi-sm">arrow_back</span> Profil</a>
      <div class="section-header"><span class="section-icon material-symbols-outlined">bug_report</span> Offene Issues</div>
      <div id="issue-list"><div class="loading"><div class="spinner"></div> Issues laden&hellip;</div></div>
      <div class="section-header mt-16"><span class="section-icon material-symbols-outlined">add_circle</span> Neues Issue erstellen</div>
      <div id="issue-form-area"><div class="loading"><div class="spinner"></div> Labels laden&hellip;</div></div>
      <div id="issue-result"></div>
    `;

    // Load issues and labels in parallel with independent error handling
    const [issuesResult, labelsResult] = await Promise.allSettled([
      withRetry(() => Api.getGitHubIssues()),
      withRetry(() => Api.getGitHubLabels()),
    ]);

    // Handle labels result
    const labelsEl = document.getElementById('issue-form-area');
    if (labelsResult.status === 'fulfilled') {
      labels = labelsResult.value;
      renderForm();
    } else {
      renderSectionError(labelsEl, labelsResult.reason, 'Labels');
    }

    // Handle issues result
    const issuesEl = document.getElementById('issue-list');
    if (issuesResult.status === 'fulfilled') {
      renderIssueList(issuesEl, issuesResult.value);
    } else {
      renderSectionError(issuesEl, issuesResult.reason, 'Issues');
    }
  }

  /* ---------- Error State Rendering ---------- */

  function renderSectionError(el, err, section) {
    const classified = classifyError(err);
    el.innerHTML = `
      <div class="error-state">
        <span class="material-symbols-outlined" style="font-size:2rem;color:var(--error);margin-bottom:8px">${classified.icon}</span>
        <p>${escapeHtml(classified.message)}</p>
        <button class="btn btn-primary btn-sm" onclick="IssuesView.reload()">
          <span class="material-symbols-outlined mi-sm">refresh</span> Erneut versuchen
        </button>
      </div>
    `;
  }

  function reload() {
    const container = document.getElementById('view-container');
    if (container) render(container);
  }

  /* ---------- Issue List ---------- */

  function renderIssueList(el, issues) {
    if (issues.length === 0) {
      el.innerHTML = '<div class="empty-state">Keine offenen Issues</div>';
      return;
    }
    el.innerHTML = issues.map(iss => `
      <a href="${escapeHtml(iss.html_url)}" target="_blank" rel="noopener" class="card issue-item">
        <div class="flex-between">
          <span class="issue-number">#${iss.number}</span>
          <span class="issue-date">${formatIssueDate(iss.created_at)}</span>
        </div>
        <div class="issue-title">${escapeHtml(iss.title)}</div>
        ${iss.labels.length ? `<div class="issue-labels">${iss.labels.map(l => renderLabelBadge(l)).join('')}</div>` : ''}
      </a>
    `).join('');
  }

  function formatIssueDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function renderLabelBadge(labelName) {
    const labelData = labels.find(l => l.name === labelName);
    if (labelData && labelData.color && /^[0-9a-fA-F]{6}$/.test(labelData.color)) {
      const bg = `#${labelData.color}33`;
      const fg = `#${labelData.color}`;
      return `<span class="badge" style="background:${bg};color:${fg}">${escapeHtml(labelName)}</span>`;
    }
    return `<span class="badge badge-accent">${escapeHtml(labelName)}</span>`;
  }

  /* ---------- Labels + Form ---------- */

  function groupLabels(prefix) {
    return labels.filter(l => l.name.startsWith(prefix));
  }

  function typeLabels() {
    const types = ['bug', 'enhancement', 'task', 'documentation', 'incident', 'refactoring', 'quality'];
    return labels.filter(l => types.includes(l.name));
  }

  function renderForm() {
    const area = document.getElementById('issue-form-area');
    const priorities = groupLabels('P');
    const areas = groupLabels('area/');
    const types = typeLabels();

    area.innerHTML = `
      <div class="card">
        <div class="input-group">
          <label for="issue-title">Titel *</label>
          <input type="text" id="issue-title" placeholder="Kurze Beschreibung des Issues"
                 maxlength="256" onkeydown="if(event.key==='Enter') IssuesView.submit()">
        </div>

        <div class="input-group">
          <label for="issue-type">Typ</label>
          <select id="issue-type">
            <option value="">– keiner –</option>
            ${types.map(l => `<option value="${escapeHtml(l.name)}">${escapeHtml(l.name)}</option>`).join('')}
          </select>
        </div>

        <div class="input-group">
          <label for="issue-priority">Priorität</label>
          <select id="issue-priority">
            <option value="">– keine –</option>
            ${priorities.map(l => `<option value="${escapeHtml(l.name)}">${escapeHtml(l.name)}</option>`).join('')}
          </select>
        </div>

        ${areas.length ? `
        <div class="input-group">
          <label>Bereich</label>
          <div class="label-chips" id="issue-areas">
            ${areas.map(l => `
              <label class="chip">
                <input type="checkbox" value="${escapeHtml(l.name)}">
                <span>${escapeHtml(l.name.replace('area/', ''))}</span>
              </label>
            `).join('')}
          </div>
        </div>
        ` : ''}

        <div class="input-group">
          <label for="issue-body">Beschreibung</label>
          <textarea id="issue-body" rows="6" placeholder="Details, Schritte, Kontext&hellip;"></textarea>
        </div>

        <button class="btn btn-primary" id="issue-submit-btn" onclick="IssuesView.submit()">
          Issue erstellen
        </button>
      </div>
    `;
  }

  async function submit() {
    if (submitting) return;
    const title = document.getElementById('issue-title').value.trim();
    if (!title) {
      document.getElementById('issue-title').focus();
      return;
    }

    const body = document.getElementById('issue-body').value.trim();
    const selectedLabels = [];

    const typeEl = document.getElementById('issue-type');
    if (typeEl.value) selectedLabels.push(typeEl.value);

    const prioEl = document.getElementById('issue-priority');
    if (prioEl.value) selectedLabels.push(prioEl.value);

    const areaChecks = document.querySelectorAll('#issue-areas input:checked');
    areaChecks.forEach(cb => selectedLabels.push(cb.value));

    const btn = document.getElementById('issue-submit-btn');
    submitting = true;
    btn.disabled = true;
    btn.textContent = 'Wird erstellt\u2026';

    const resultEl = document.getElementById('issue-result');
    resultEl.innerHTML = '';

    try {
      const issue = await Api.createGitHubIssue({ title, body, labels: selectedLabels });
      resultEl.innerHTML = `
        <div class="card" style="border-left: 3px solid var(--success)">
          <div class="flex-between">
            <strong>#${issue.number}</strong>
            <span class="badge badge-success">Erstellt</span>
          </div>
          <p style="margin: 8px 0">${escapeHtml(issue.title)}</p>
          ${issue.labels.length ? `<div style="margin-bottom:8px">${issue.labels.map(l => `<span class="badge badge-accent">${escapeHtml(l)}</span>`).join(' ')}</div>` : ''}
          <a href="${escapeHtml(issue.html_url)}" target="_blank" rel="noopener" class="btn btn-sm btn-secondary">
            Auf GitHub oeffnen <span class="material-symbols-outlined mi-sm">open_in_new</span>
          </a>
        </div>
      `;
      // Formular zuruecksetzen
      document.getElementById('issue-title').value = '';
      document.getElementById('issue-body').value = '';
      document.getElementById('issue-type').value = '';
      document.getElementById('issue-priority').value = '';
      document.querySelectorAll('#issue-areas input:checked').forEach(cb => { cb.checked = false; });
      // Issue-Liste aktualisieren
      try {
        const issues = await withRetry(() => Api.getGitHubIssues());
        renderIssueList(document.getElementById('issue-list'), issues);
      } catch (_) { /* list refresh is best-effort */ }
    } catch (err) {
      const classified = classifyError(err);
      resultEl.innerHTML = `
        <div class="card" style="border-left: 3px solid var(--error)">
          <span class="material-symbols-outlined" style="color:var(--error);vertical-align:middle">${classified.icon}</span>
          <strong> Fehler</strong>
          <p>${escapeHtml(classified.message)}</p>
        </div>
      `;
    } finally {
      submitting = false;
      btn.disabled = false;
      btn.textContent = 'Issue erstellen';
    }
  }

  return { render, submit, reload };
})();
