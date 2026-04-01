/**
 * Issues View – GitHub Issue-Liste + Erstellung
 */
const IssuesView = (() => {
  let labels = [];
  let submitting = false;

  async function render(container) {
    container.innerHTML = `
      <a class="view-back" href="#/profile">&#8592; Profil</a>
      <div class="section-header"><span class="section-icon">&#128196;</span> Offene Issues</div>
      <div id="issue-list"><div class="loading"><div class="spinner"></div> Issues laden&hellip;</div></div>
      <div class="section-header mt-16"><span class="section-icon">&#10133;</span> Neues Issue erstellen</div>
      <div id="issue-form-area"><div class="loading"><div class="spinner"></div> Labels laden&hellip;</div></div>
      <div id="issue-result"></div>
    `;
    await loadLabels();
    await loadIssues();
  }

  /* ---------- Issue List ---------- */

  async function loadIssues() {
    const el = document.getElementById('issue-list');
    try {
      const issues = await Api.getGitHubIssues();
      renderIssueList(el, issues);
    } catch (err) {
      el.innerHTML = `
        <div class="error-state">
          <p>${escapeHtml(err.message)}</p>
          <button class="btn btn-primary btn-sm" onclick="IssuesView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

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
    if (labelData && labelData.color) {
      const bg = `#${labelData.color}33`;
      const fg = `#${labelData.color}`;
      return `<span class="badge" style="background:${bg};color:${fg}">${escapeHtml(labelName)}</span>`;
    }
    return `<span class="badge badge-accent">${escapeHtml(labelName)}</span>`;
  }

  /* ---------- Labels + Form ---------- */

  async function loadLabels() {
    const area = document.getElementById('issue-form-area');
    try {
      labels = await Api.getGitHubLabels();
      renderForm();
    } catch (err) {
      area.innerHTML = `
        <div class="error-state">
          <p>${escapeHtml(err.message)}</p>
          <button class="btn btn-primary btn-sm" onclick="IssuesView.render(document.getElementById('view-container'))">Erneut versuchen</button>
        </div>
      `;
    }
  }

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
            Auf GitHub oeffnen &#8599;
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
      await loadIssues();
    } catch (err) {
      resultEl.innerHTML = `
        <div class="card" style="border-left: 3px solid var(--error)">
          <strong>Fehler</strong>
          <p>${escapeHtml(err.message)}</p>
        </div>
      `;
    } finally {
      submitting = false;
      btn.disabled = false;
      btn.textContent = 'Issue erstellen';
    }
  }

  return { render, submit };
})();
