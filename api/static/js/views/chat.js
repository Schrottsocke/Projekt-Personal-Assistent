/**
 * Chat View – History, Send, Auto-Scroll
 */
const ChatView = (() => {
  let sending = false;
  let lastMessage = '';
  let pendingController = null;
  let slowTimer = null;

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
            <span class="material-symbols-outlined">send</span>
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
        el.innerHTML = '<div class="empty-state chat-empty">Schreib mir etwas!</div>';
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

    el.innerHTML = messages.map((m, i) => {
      const time = m.created_at ? formatMessageTime(m.created_at) : '';
      const prev = i > 0 ? messages[i - 1] : null;
      const next = i < messages.length - 1 ? messages[i + 1] : null;
      const sameAsPrev = prev && prev.role === m.role;
      const sameAsNext = next && next.role === m.role;

      let groupClass = '';
      if (sameAsPrev && sameAsNext) groupClass = 'group-middle';
      else if (sameAsPrev) groupClass = 'group-end';
      else if (sameAsNext) groupClass = 'group-start';

      const hideTime = sameAsNext;

      return `
        <div class="chat-bubble ${m.role} ${groupClass}">
          ${escapeHtml(m.content)}
          ${time ? `<div class="chat-time${hideTime ? ' grouped-time' : ''}">${time}</div>` : ''}
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

  async function send(retryMsg) {
    if (sending) return;
    const input = document.getElementById('chat-input');
    const message = retryMsg || input.value.trim();
    if (!message) return;

    if (!retryMsg) input.value = '';
    lastMessage = message;
    sending = true;

    const messagesEl = document.getElementById('chat-messages');

    // Remove empty state if present
    const empty = messagesEl.querySelector('.empty-state');
    if (empty) empty.remove();

    // Add user message (only if not a retry – retry already has the bubble)
    if (!retryMsg) {
      const userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user';
      userBubble.textContent = message;
      messagesEl.appendChild(userBubble);
    }

    // Add typing indicator
    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.textContent = 'Denkt nach…';
    messagesEl.appendChild(typing);
    scrollToBottom();

    // Slow-response hint after 15s
    slowTimer = setTimeout(() => {
      if (typing.parentNode) {
        typing.innerHTML = 'Dauert länger als erwartet… <button class="btn btn-sm" onclick="ChatView.cancelPending()">Abbrechen</button>';
      }
    }, 15000);

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
      errorBubble.innerHTML = `<span style="color:var(--error)">Fehler: ${escapeHtml(err.message)}</span>
        <button class="btn btn-sm" onclick="ChatView.retry()" style="margin-top:6px">Erneut versuchen</button>`;
      messagesEl.appendChild(errorBubble);
      scrollToBottom();
    } finally {
      if (slowTimer) { clearTimeout(slowTimer); slowTimer = null; }
      sending = false;
      pendingController = null;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  function cancelPending() {
    // The AbortController lives inside Api.request; we signal cancellation
    // by setting sending = false so the UI cleans up on the resulting error.
    // Since we can't reach the internal controller, we rely on the timeout
    // to eventually fire. For immediate UX, remove the indicator now.
    const typing = document.querySelector('.typing-indicator');
    if (typing) typing.remove();
    sending = false;
    const sendBtn = document.getElementById('chat-send-btn');
    if (sendBtn) sendBtn.disabled = false;
    if (slowTimer) { clearTimeout(slowTimer); slowTimer = null; }
  }

  function retry() {
    if (!lastMessage) return;
    // Remove the error bubble that contains the retry button
    const bubbles = document.querySelectorAll('.chat-bubble.assistant');
    const last = bubbles[bubbles.length - 1];
    if (last && last.querySelector('.btn')) last.remove();
    send(lastMessage);
  }

  return { render, send, cancelPending, retry };
})();
