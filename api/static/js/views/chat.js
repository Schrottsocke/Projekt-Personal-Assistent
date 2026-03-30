/**
 * Chat View – History, Send, Auto-Scroll
 */
const ChatView = (() => {
  let sending = false;

  async function render(container) {
    container.innerHTML = `
      <div class="chat-container">
        <div class="chat-messages" id="chat-messages">
          <div class="loading"><div class="spinner"></div> Nachrichten laden…</div>
        </div>
        <div class="chat-input-area">
          <input type="text" id="chat-input" placeholder="Nachricht schreiben…"
                 onkeydown="if(event.key==='Enter' && !event.shiftKey) ChatView.send()">
          <button class="btn btn-primary btn-icon" onclick="ChatView.send()" id="chat-send-btn">
            &#10148;
          </button>
        </div>
      </div>
    `;

    await loadHistory();
  }

  async function loadHistory() {
    const el = document.getElementById('chat-messages');
    try {
      const messages = await Api.getChatHistory(50);
      if (messages.length === 0) {
        el.innerHTML = '<div class="empty-state" style="margin-top:40%">Schreib mir etwas!</div>';
        return;
      }
      renderMessages(messages);
    } catch (err) {
      el.innerHTML = `<div class="error-state"><p>${err.message}</p>
        <button class="btn btn-secondary" onclick="ChatView.render(document.getElementById('view-container'))">Erneut versuchen</button>
      </div>`;
    }
  }

  function renderMessages(messages) {
    const el = document.getElementById('chat-messages');
    if (!el) return;

    el.innerHTML = messages.map(m => {
      const time = m.created_at ? formatMessageTime(m.created_at) : '';
      return `
        <div class="chat-bubble ${m.role}">
          ${escapeHtml(m.content)}
          ${time ? `<div class="chat-time">${time}</div>` : ''}
        </div>
      `;
    }).join('');

    scrollToBottom();
  }

  function formatMessageTime(iso) {
    const d = new Date(iso);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const time = d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    if (isToday) return time;
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) + ' ' + time;
  }

  function scrollToBottom() {
    const el = document.getElementById('chat-messages');
    if (el) el.scrollTop = el.scrollHeight;
  }

  async function send() {
    if (sending) return;
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    sending = true;

    const messagesEl = document.getElementById('chat-messages');

    // Remove empty state if present
    const empty = messagesEl.querySelector('.empty-state');
    if (empty) empty.remove();

    // Add user message
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user';
    userBubble.textContent = message;
    messagesEl.appendChild(userBubble);

    // Add typing indicator
    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.textContent = 'Denkt nach…';
    messagesEl.appendChild(typing);
    scrollToBottom();

    const sendBtn = document.getElementById('chat-send-btn');
    sendBtn.disabled = true;

    try {
      const result = await Api.sendMessage(message);
      typing.remove();

      const assistantBubble = document.createElement('div');
      assistantBubble.className = 'chat-bubble assistant';
      assistantBubble.textContent = result.response;
      messagesEl.appendChild(assistantBubble);
      scrollToBottom();
    } catch (err) {
      typing.remove();
      const errorBubble = document.createElement('div');
      errorBubble.className = 'chat-bubble assistant';
      errorBubble.innerHTML = `<span style="color:var(--error)">Fehler: ${escapeHtml(err.message)}</span>`;
      messagesEl.appendChild(errorBubble);
      scrollToBottom();
    } finally {
      sending = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  return { render, send };
})();
