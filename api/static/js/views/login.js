/**
 * Login View – User selection + password
 */
const LoginView = (() => {
  let selectedUser = null;

  function render(container) {
    container.innerHTML = `
      <div class="login-container">
        <div class="login-title">DualMind</div>
        <div class="login-subtitle">Melde dich an, um fortzufahren</div>

        <div class="user-select">
          <button class="user-btn" data-user="taake" onclick="LoginView.selectUser('taake')">
            <div class="user-avatar">T</div>
            <span>Taake</span>
          </button>
          <button class="user-btn" data-user="nina" onclick="LoginView.selectUser('nina')">
            <div class="user-avatar">N</div>
            <span>Nina</span>
          </button>
        </div>

        <div class="login-form hidden" id="login-form">
          <div class="password-wrapper">
            <input type="password" id="login-password" placeholder="Passwort eingeben"
                   onkeydown="if(event.key==='Enter') LoginView.doLogin()">
            <button class="password-toggle" onclick="LoginView.togglePassword()" type="button">
              &#128065;
            </button>
          </div>
          <div class="login-error hidden" id="login-error"></div>
          <button class="btn btn-primary" style="width:100%" onclick="LoginView.doLogin()" id="login-btn">
            Anmelden
          </button>
        </div>
      </div>
    `;
    selectedUser = null;
  }

  function selectUser(user) {
    selectedUser = user;
    document.querySelectorAll('.user-btn').forEach(btn => {
      btn.classList.toggle('selected', btn.dataset.user === user);
    });
    const form = document.getElementById('login-form');
    form.classList.remove('hidden');
    document.getElementById('login-password').focus();
  }

  function togglePassword() {
    const input = document.getElementById('login-password');
    input.type = input.type === 'password' ? 'text' : 'password';
  }

  async function doLogin() {
    if (!selectedUser) return;

    const password = document.getElementById('login-password').value;
    if (!password) return;

    const btn = document.getElementById('login-btn');
    const errorEl = document.getElementById('login-error');
    errorEl.classList.add('hidden');
    btn.disabled = true;
    btn.textContent = 'Anmelden…';

    try {
      await Api.login(selectedUser, password);
      Router.navigate('#/dashboard');
    } catch (err) {
      errorEl.textContent = err.message || 'Anmeldung fehlgeschlagen';
      errorEl.classList.remove('hidden');
      btn.disabled = false;
      btn.textContent = 'Anmelden';
    }
  }

  return { render, selectUser, togglePassword, doLogin };
})();
