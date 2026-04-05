/**
 * Feedback View – Bug-Reports und UX-Bewertungen fuer Beta-Tester.
 * Issue #728: Tester-Feedback-Workflow.
 */
const FeedbackView = (() => {

  let _mode = 'list'; // 'list' | 'bug' | 'ux'

  async function render(container) {
    _mode = 'list';
    container.innerHTML = `
      <div class="view-header">
        <h2>Feedback</h2>
        <div class="header-actions" style="display:flex;gap:8px">
          <button class="btn btn-primary btn-sm" onclick="FeedbackView.showBugForm()">
            <span class="material-symbols-outlined">bug_report</span> Bug melden
          </button>
          <button class="btn btn-secondary btn-sm" onclick="FeedbackView.showUxForm()">
            <span class="material-symbols-outlined">star</span> UX bewerten
          </button>
        </div>
      </div>
      <div id="feedback-content"><p class="text-muted">Lade Feedback...</p></div>
    `;
    await loadList();
  }

  async function loadList() {
    const el = document.getElementById('feedback-content');
    if (!el) return;
    try {
      const items = await API.get('/feedback');
      if (!items || items.length === 0) {
        el.innerHTML = '<p class="text-muted">Noch kein Feedback vorhanden.</p>';
        return;
      }
      el.innerHTML = items.map(item => {
        const icon = item.feedback_type === 'bug' ? 'bug_report' : 'star';
        const color = item.feedback_type === 'bug' ? 'var(--error)' : 'var(--primary)';
        const title = item.title || item.area || 'UX-Bewertung';
        const badge = `<span class="badge" style="font-size:0.7rem">${item.triage_status}</span>`;
        return `
          <div class="card" style="margin-bottom:8px;padding:12px">
            <div style="display:flex;align-items:center;gap:8px">
              <span class="material-symbols-outlined" style="color:${color}">${icon}</span>
              <strong style="flex:1">${title}</strong>
              ${badge}
            </div>
            <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:4px">
              ${item.user_key} &middot; ${new Date(item.created_at).toLocaleDateString('de-DE')}
              ${item.severity ? ' &middot; ' + item.severity : ''}
            </div>
          </div>`;
      }).join('');
    } catch (e) {
      el.innerHTML = '<p class="text-muted">Fehler beim Laden.</p>';
    }
  }

  function showBugForm() {
    const el = document.getElementById('feedback-content');
    if (!el) return;
    _mode = 'bug';
    el.innerHTML = `
      <form id="bug-form" class="form-stack" style="gap:12px">
        <h3>Bug melden</h3>
        <input name="title" placeholder="Kurzer Titel *" required class="input" maxlength="200">
        <select name="area" class="input">
          <option value="">Bereich waehlen...</option>
          <option value="dashboard">Dashboard</option>
          <option value="shopping">Einkauf</option>
          <option value="calendar">Kalender</option>
          <option value="tasks">Aufgaben</option>
          <option value="finance">Finanzen</option>
          <option value="documents">Dokumente</option>
          <option value="chat">Chat</option>
          <option value="other">Sonstiges</option>
        </select>
        <textarea name="expected" placeholder="Erwartetes Verhalten" class="input" rows="2"></textarea>
        <textarea name="actual" placeholder="Tatsaechliches Verhalten" class="input" rows="2"></textarea>
        <textarea name="steps" placeholder="Schritte zum Reproduzieren" class="input" rows="3"></textarea>
        <input name="device" placeholder="Geraet / Browser" class="input">
        <select name="severity" class="input">
          <option value="">Schweregrad...</option>
          <option value="low">Niedrig</option>
          <option value="medium">Mittel</option>
          <option value="high">Hoch</option>
          <option value="critical">Kritisch</option>
        </select>
        <div style="display:flex;gap:8px">
          <button type="submit" class="btn btn-primary">Absenden</button>
          <button type="button" class="btn btn-secondary" onclick="FeedbackView.backToList()">Abbrechen</button>
        </div>
      </form>`;
    document.getElementById('bug-form').addEventListener('submit', submitBug);
  }

  function showUxForm() {
    const el = document.getElementById('feedback-content');
    if (!el) return;
    _mode = 'ux';
    const ratingRow = (name, label) => `
      <div style="display:flex;align-items:center;justify-content:space-between">
        <span>${label}</span>
        <div class="rating-group" style="display:flex;gap:4px">
          ${[1,2,3,4,5].map(n => `<button type="button" class="btn btn-sm rating-btn" data-name="${name}" data-val="${n}" onclick="FeedbackView.setRating(this)">${n}</button>`).join('')}
        </div>
      </div>`;
    el.innerHTML = `
      <form id="ux-form" class="form-stack" style="gap:12px">
        <h3>UX bewerten</h3>
        <select name="area" class="input">
          <option value="">Bereich waehlen...</option>
          <option value="overall">Gesamteindruck</option>
          <option value="dashboard">Dashboard</option>
          <option value="shopping">Einkauf</option>
          <option value="calendar">Kalender</option>
          <option value="navigation">Navigation</option>
          <option value="onboarding">Onboarding</option>
        </select>
        ${ratingRow('rating_clarity', 'Verstaendlichkeit')}
        ${ratingRow('rating_speed', 'Geschwindigkeit')}
        ${ratingRow('rating_trust', 'Vertrauen')}
        ${ratingRow('rating_mobile_comfort', 'Mobiler Komfort')}
        <textarea name="comment" placeholder="Kommentar (optional)" class="input" rows="3"></textarea>
        <div style="display:flex;gap:8px">
          <button type="submit" class="btn btn-primary">Absenden</button>
          <button type="button" class="btn btn-secondary" onclick="FeedbackView.backToList()">Abbrechen</button>
        </div>
      </form>`;
    document.getElementById('ux-form').addEventListener('submit', submitUx);
  }

  const _ratings = {};

  function setRating(btn) {
    const name = btn.dataset.name;
    const val = parseInt(btn.dataset.val);
    _ratings[name] = val;
    btn.parentElement.querySelectorAll('.rating-btn').forEach(b => {
      b.classList.toggle('btn-primary', parseInt(b.dataset.val) <= val);
      b.classList.toggle('btn-secondary', parseInt(b.dataset.val) > val);
    });
  }

  async function submitBug(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {};
    for (const [k, v] of fd.entries()) { if (v) data[k] = v; }
    try {
      await API.post('/feedback/bugs', data);
      Toast.show('Bug-Report gesendet!');
      await backToList();
    } catch (err) {
      Toast.show('Fehler beim Senden', 'error');
    }
  }

  async function submitUx(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = { ..._ratings };
    const area = fd.get('area');
    const comment = fd.get('comment');
    if (area) data.area = area;
    if (comment) data.comment = comment;
    try {
      await API.post('/feedback/ux', data);
      Toast.show('UX-Bewertung gesendet!');
      Object.keys(_ratings).forEach(k => delete _ratings[k]);
      await backToList();
    } catch (err) {
      Toast.show('Fehler beim Senden', 'error');
    }
  }

  async function backToList() {
    _mode = 'list';
    const container = document.getElementById('view-container');
    if (container) await render(container);
  }

  return { render, showBugForm, showUxForm, setRating, backToList };
})();
