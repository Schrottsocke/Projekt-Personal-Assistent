/**
 * Login View – Landing Page + Login Card
 */
const LoginView = (() => {

  function render(container) {
    // Remove default view-container padding for full-width landing
    container.style.padding = '0';

    container.innerHTML = `
      <div class="landing-page">

        <!-- Hero Section -->
        <section class="landing-hero">
          <div class="landing-logo-icon">
            <span class="material-symbols-outlined">psychology</span>
          </div>
          <div class="landing-logo">DualMind</div>
          <p class="landing-tagline">
            Dein persoenlicher Assistent fuer Haushalt, Finanzen, Dokumente und Familie &ndash;
            DSGVO-konform und selbst gehostet.
          </p>
          <button class="landing-cta" onclick="LoginView.scrollToLogin()">
            Beta-Zugang
            <span class="material-symbols-outlined" style="font-size:1.125rem">arrow_downward</span>
          </button>
          <div class="landing-beta-badge">Einladungs-Beta &middot; Begrenzte Plaetze</div>
        </section>

        <!-- Features Section -->
        <section class="landing-features">
          <h2 class="landing-features-title">Was DualMind kann</h2>
          <div class="landing-features-grid">

            <div class="feature-card">
              <div class="feature-card-icon">
                <span class="material-symbols-outlined">account_balance</span>
              </div>
              <div class="feature-card-title">Finanzen &amp; Budgets</div>
              <div class="feature-card-desc">Einnahmen, Ausgaben und Budgets im Blick &ndash; mit automatischer Kategorisierung und Monatsberichten.</div>
            </div>

            <div class="feature-card">
              <div class="feature-card-icon">
                <span class="material-symbols-outlined">document_scanner</span>
              </div>
              <div class="feature-card-title">Dokumente &amp; OCR-Scan</div>
              <div class="feature-card-desc">Rechnungen, Vertraege und Belege scannen, durchsuchen und sicher archivieren.</div>
            </div>

            <div class="feature-card">
              <div class="feature-card-icon">
                <span class="material-symbols-outlined">inventory_2</span>
              </div>
              <div class="feature-card-title">Inventar &amp; Garantien</div>
              <div class="feature-card-desc">Geraete und Anschaffungen verwalten mit Garantie-Erinnerungen und Kaufbelegen.</div>
            </div>

            <div class="feature-card">
              <div class="feature-card-icon">
                <span class="material-symbols-outlined">group</span>
              </div>
              <div class="feature-card-title">Familie &amp; Aufgaben</div>
              <div class="feature-card-desc">Aufgaben verteilen, Termine koordinieren und den Familienalltag gemeinsam organisieren.</div>
            </div>

            <div class="feature-card">
              <div class="feature-card-icon">
                <span class="material-symbols-outlined">shield</span>
              </div>
              <div class="feature-card-title">DSGVO-konform &amp; selbst gehostet</div>
              <div class="feature-card-desc">Alle Daten bleiben auf deinem Server. Kein Cloud-Zwang, volle Kontrolle, europaeischer Datenschutz.</div>
            </div>

          </div>
        </section>

        <!-- Login Section -->
        <section class="login-section" id="login-section">
          <div class="login-card" id="login-card">
            <div class="login-card-logo">
              <div class="login-card-logo-text">DualMind</div>
              <div class="login-card-subtitle">Melde dich an, um fortzufahren</div>
            </div>

            <form id="login-form" onsubmit="LoginView.doLogin(event)" novalidate>
              <div class="login-error hidden" id="login-error" role="alert" aria-live="assertive"></div>

              <div class="login-field">
                <label for="login-email">E-Mail oder Benutzername</label>
                <input type="email" id="login-email" autocomplete="username"
                       aria-label="E-Mail oder Benutzername" placeholder="name@beispiel.de">
              </div>

              <div class="login-field">
                <label for="login-password">Passwort</label>
                <div class="password-wrapper">
                  <input type="password" id="login-password" autocomplete="current-password"
                         aria-label="Passwort" placeholder="Passwort eingeben">
                  <button class="password-toggle" type="button" onclick="LoginView.togglePassword()"
                          aria-label="Passwort anzeigen/verbergen">
                    <span class="material-symbols-outlined" id="pw-toggle-icon">visibility</span>
                  </button>
                </div>
              </div>

              <div class="login-options">
                <label class="login-remember">
                  <input type="checkbox" id="login-remember">
                  Angemeldet bleiben
                </label>
                <a href="#reset" class="login-forgot">Passwort vergessen?</a>
              </div>

              <button type="submit" class="login-submit" id="login-btn">
                Anmelden
              </button>
            </form>
          </div>
        </section>

        <!-- Footer -->
        <footer class="landing-footer">
          DualMind Beta <span>&middot;</span> DSGVO-konform <span>&middot;</span> Wittenfoerden, DE
        </footer>

      </div>
    `;

    // No autofocus on mobile to avoid keyboard pop-up
    if (window.innerWidth >= 768) {
      const emailInput = document.getElementById('login-email');
      if (emailInput) emailInput.focus();
    }
  }

  function scrollToLogin() {
    const section = document.getElementById('login-section');
    if (section) section.scrollIntoView({ behavior: 'smooth' });
  }

  function togglePassword() {
    const input = document.getElementById('login-password');
    const icon = document.getElementById('pw-toggle-icon');
    if (input.type === 'password') {
      input.type = 'text';
      icon.textContent = 'visibility_off';
    } else {
      input.type = 'password';
      icon.textContent = 'visibility';
    }
  }

  async function doLogin(e) {
    if (e) e.preventDefault();

    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    const btn = document.getElementById('login-btn');
    const errorEl = document.getElementById('login-error');
    const card = document.getElementById('login-card');

    const username = (emailInput.value || '').trim();
    const password = passwordInput.value;

    // Basic validation
    if (!username) {
      showError(errorEl, card, 'Bitte E-Mail oder Benutzername eingeben.');
      emailInput.classList.add('input-error');
      emailInput.focus();
      return;
    }
    if (!password) {
      showError(errorEl, card, 'Bitte Passwort eingeben.');
      passwordInput.classList.add('input-error');
      passwordInput.focus();
      return;
    }

    // Clear previous errors
    emailInput.classList.remove('input-error');
    passwordInput.classList.remove('input-error');
    errorEl.classList.add('hidden');

    // Loading state
    btn.disabled = true;
    btn.innerHTML = '<span class="login-spinner"></span> Anmelden…';

    try {
      await Api.login(username, password);

      // Restore padding before navigating
      const container = document.getElementById('view-container');
      if (container) container.style.padding = '';

      Router.navigate('#/dashboard');
    } catch (err) {
      showError(errorEl, card, err.message || 'Anmeldung fehlgeschlagen. Bitte versuche es erneut.');
      btn.disabled = false;
      btn.innerHTML = 'Anmelden';
    }
  }

  function showError(errorEl, card, message) {
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
    // Trigger shake animation
    card.classList.remove('shake');
    // Force reflow to restart animation
    void card.offsetWidth;
    card.classList.add('shake');
  }

  return { render, scrollToLogin, togglePassword, doLogin };
})();
