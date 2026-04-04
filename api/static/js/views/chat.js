/**
 * Chat View – History, Send, Voice Input, Quick Actions, Message States
 */
const ChatView = (() => {
  let sending = false;
  let lastMessage = '';
  let lastUserBubble = null;
  let pendingController = null;
  let slowTimer = null;

  // Voice recording state
  let mediaRecorder = null;
  let audioChunks = [];
  let recording = false;
  let recordingTimer = null;
  let recordingSeconds = 0;
  const MAX_RECORDING_SECONDS = 120;

  // Fallback-Vorschlaege falls der Endpoint nicht erreichbar ist
  const FALLBACK_ACTIONS = [
    { label: 'Briefing', message: 'Gib mir ein Briefing', icon: 'wb_sunny' },
    { label: 'Offene Aufgaben', message: 'Zeig mir offene Aufgaben', icon: 'check_circle' },
    { label: 'Tagesplan', message: 'Was steht heute an?', icon: 'calendar_month' },
    { label: 'Einkaufsliste', message: 'Zeig die Einkaufsliste', icon: 'shopping_cart' },
  ];

  async function render(container) {
    container.innerHTML = `
      <div class="chat-container">
        <div class="chat-messages" id="chat-messages">
          <div class="loading"><div class="spinner"></div> Nachrichten laden…</div>
        </div>
        <div class="chat-quick-actions" id="chat-quick-actions"></div>
        <div class="chat-input-area">
          <input type="text" id="chat-input" placeholder="Nachricht schreiben…"
                 onkeydown="if(event.key==='Enter' && !event.shiftKey) ChatView.send()">
          <button class="btn btn-icon" id="chat-mic-btn" onclick="ChatView.toggleRecording()" title="Sprachnachricht">
            <span class="material-symbols-outlined">mic</span>
          </button>
          <button class="btn btn-primary btn-icon" onclick="ChatView.send()" id="chat-send-btn">
            <span class="material-symbols-outlined">send</span>
          </button>
        </div>
      </div>
    `;

    // Quick action click handler
    document.getElementById('chat-quick-actions').addEventListener('click', (e) => {
      const chip = e.target.closest('.quick-action');
      if (chip && !sending) send(chip.dataset.msg);
    });

    // Dynamische Vorschlaege laden
    loadSuggestions();

    await loadHistory();

    // Chat-Prefill (z.B. von Memory-View)
    const prefill = sessionStorage.getItem('dm_chat_prefill');
    if (prefill) {
      sessionStorage.removeItem('dm_chat_prefill');
      const input = document.getElementById('chat-input');
      if (input) {
        input.value = prefill;
        input.focus();
      }
    }
  }

  const CHAT_CACHE_KEY = 'dm_cache_chat_history';

  async function loadHistory() {
    const el = document.getElementById('chat-messages');
    try {
      const messages = await Api.getChatHistory(50);
      if (messages.length === 0) {
        el.innerHTML = '<div class="empty-state chat-empty">Schreib mir etwas!</div>';
        return;
      }
      OfflineQueue.saveCache(CHAT_CACHE_KEY, messages);
      renderMessages(messages);
    } catch (err) {
      // Offline fallback: show cached history
      if (err.isOffline || (typeof OfflineQueue !== 'undefined' && !OfflineQueue.isOnline())) {
        const cached = OfflineQueue.loadCache(CHAT_CACHE_KEY);
        if (cached && cached.data && cached.data.length > 0) {
          renderMessages(cached.data);
          const ts = new Date(cached.ts).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
          el.insertAdjacentHTML('afterbegin',
            `<div class="offline-cache-banner">
              <span class="material-symbols-outlined mi-sm">cloud_off</span>
              Offline \u2014 Verlauf von ${ts}
            </div>`);
          return;
        }
      }
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
      const content = escapeHtml(m.content);

      return `
        <div class="chat-bubble ${m.role} ${groupClass} msg-sent">
          <div class="bubble-content">${content}</div>
          ${time ? `<div class="chat-time${hideTime ? ' grouped-time' : ''}">${time}</div>` : ''}
        </div>
      `;
    }).join('');

    // Apply expandable to long history messages
    el.querySelectorAll('.chat-bubble.assistant').forEach(applyExpandable);
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

  function setQuickActionsVisible(visible) {
    const qa = document.getElementById('chat-quick-actions');
    if (qa) qa.style.display = visible ? '' : 'none';
  }

  async function loadSuggestions() {
    const qa = document.getElementById('chat-quick-actions');
    if (!qa) return;
    try {
      const suggestions = await Api.getChatSuggestions();
      const items = (suggestions && suggestions.length > 0) ? suggestions : FALLBACK_ACTIONS;
      renderSuggestionChips(items);
    } catch {
      renderSuggestionChips(FALLBACK_ACTIONS);
    }
  }

  function renderSuggestionChips(items) {
    const qa = document.getElementById('chat-quick-actions');
    if (!qa) return;
    qa.innerHTML = items.map(a => `<button class="chip quick-action chat-suggestion-chip" data-msg="${escapeHtml(a.message)}"><span class="material-symbols-outlined mi-sm">${escapeHtml(a.icon || 'lightbulb')}</span> ${escapeHtml(a.label)}</button>`).join('');
  }

  async function send(retryMsg) {
    if (sending) return;
    const input = document.getElementById('chat-input');
    const message = retryMsg || (input ? input.value.trim() : '');
    if (!message) return;

    // Offline check – queue message for later delivery
    if (typeof OfflineQueue !== 'undefined' && !OfflineQueue.isOnline()) {
      OfflineQueue.enqueueChatSend(message);
      if (!retryMsg && input) input.value = '';
      // Show queued message in UI
      const messagesEl = document.getElementById('chat-messages');
      if (messagesEl) {
        const empty = messagesEl.querySelector('.empty-state');
        if (empty) empty.remove();
        const qBubble = document.createElement('div');
        qBubble.className = 'chat-bubble user msg-queued';
        qBubble.innerHTML = `<div class="bubble-content">${escapeHtml(message)}</div><span class="msg-status"><span class="material-symbols-outlined mi-sm">schedule_send</span> wird gesendet wenn online</span>`;
        messagesEl.appendChild(qBubble);
        scrollToBottom();
      }
      return;
    }

    if (!retryMsg) input.value = '';
    lastMessage = message;
    sending = true;
    setQuickActionsVisible(false);

    const messagesEl = document.getElementById('chat-messages');
    if (!messagesEl) return;

    // Remove empty state if present
    const empty = messagesEl.querySelector('.empty-state');
    if (empty) empty.remove();

    // Add user message with sending state (only if not a retry)
    let userBubble;
    if (!retryMsg) {
      userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user msg-sending';
      userBubble.innerHTML = `<div class="bubble-content">${escapeHtml(message)}</div><span class="msg-status"><span class="spinner-tiny"></span></span>`;
      messagesEl.appendChild(userBubble);
      lastUserBubble = userBubble;
    } else {
      userBubble = lastUserBubble;
      if (userBubble) {
        userBubble.className = 'chat-bubble user msg-sending';
        const statusEl = userBubble.querySelector('.msg-status');
        if (statusEl) statusEl.innerHTML = '<span class="spinner-tiny"></span>';
      }
    }

    // Add typing indicator with animated dots
    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.innerHTML = '<span class="typing-dots"><span></span><span></span><span></span></span> Denkt nach\u2026';
    messagesEl.appendChild(typing);
    scrollToBottom();

    // Slow-response hint after 15s
    slowTimer = setTimeout(() => {
      if (typing.parentNode) {
        typing.innerHTML = 'Dauert l\u00e4nger als erwartet\u2026 <button class="btn btn-sm" onclick="ChatView.cancelPending()">Abbrechen</button>';
      }
    }, 15000);

    const sendBtn = document.getElementById('chat-send-btn');
    sendBtn.disabled = true;

    try {
      // Streaming response
      const responseBubble = document.createElement('div');
      responseBubble.className = 'chat-bubble assistant';
      responseBubble.innerHTML = '<div class="bubble-content"></div>';
      let firstToken = true;
      let fullResponse = '';
      let streamDone = false;

      await Api.sendMessageStream(
        message,
        null,
        (token) => {
          if (firstToken) {
            typing.remove();
            messagesEl.appendChild(responseBubble);
            firstToken = false;
          }
          fullResponse += token;
          responseBubble.querySelector('.bubble-content').textContent = fullResponse;
          scrollToBottom();
        },
        () => {
          streamDone = true;
          if (!firstToken) {
            responseBubble.querySelector('.bubble-content').textContent = fullResponse;
            applyExpandable(responseBubble);
          }
          // Mark user bubble as sent
          markUserBubble(userBubble, 'sent');
        },
        (error) => {
          if (firstToken) {
            typing.textContent = 'Streaming fehlgeschlagen, versuche erneut\u2026';
            Api.sendMessage(message).then((result) => {
              typing.remove();
              const assistantBubble = document.createElement('div');
              assistantBubble.className = 'chat-bubble assistant';
              assistantBubble.innerHTML = `<div class="bubble-content">${escapeHtml(result.response)}</div>`;
              messagesEl.appendChild(assistantBubble);
              applyExpandable(assistantBubble);
              markUserBubble(userBubble, 'sent');
              scrollToBottom();
            }).catch((fallbackErr) => {
              typing.remove();
              markUserBubble(userBubble, 'failed');
              scrollToBottom();
            });
          } else {
            responseBubble.querySelector('.bubble-content').innerHTML = escapeHtml(fullResponse) +
              `<br><span style="color:var(--error)">Stream abgebrochen: ${escapeHtml(error)}</span>`;
            markUserBubble(userBubble, 'sent');
          }
        }
      );

      if (firstToken && !streamDone) {
        typing.remove();
      }
    } catch (err) {
      const typingEl = document.querySelector('.typing-indicator');
      if (typingEl) typingEl.remove();
      markUserBubble(userBubble, 'failed');
      scrollToBottom();
    } finally {
      if (slowTimer) { clearTimeout(slowTimer); slowTimer = null; }
      sending = false;
      pendingController = null;
      sendBtn.disabled = false;
      setQuickActionsVisible(true);
      loadSuggestions();
      if (input) input.focus();
    }
  }

  function markUserBubble(bubble, state) {
    if (!bubble) return;
    bubble.className = `chat-bubble user msg-${state}`;
    const statusEl = bubble.querySelector('.msg-status');
    if (!statusEl) return;
    if (state === 'sent') {
      statusEl.innerHTML = '<span class="material-symbols-outlined msg-check">done</span>';
    } else if (state === 'failed') {
      statusEl.innerHTML = '<span class="material-symbols-outlined msg-error-icon">error</span> <button class="btn btn-sm msg-retry-btn" onclick="ChatView.retry()">Erneut senden</button>';
    }
  }

  function applyExpandable(bubble) {
    if (!bubble) return;
    // Defer to next frame so layout is computed
    requestAnimationFrame(() => {
      const content = bubble.querySelector('.bubble-content');
      if (content && content.scrollHeight > 200) {
        bubble.classList.add('expandable', 'collapsed');
        const toggle = document.createElement('button');
        toggle.className = 'btn btn-sm expand-toggle';
        toggle.textContent = 'Mehr anzeigen';
        toggle.onclick = () => {
          bubble.classList.toggle('collapsed');
          toggle.textContent = bubble.classList.contains('collapsed') ? 'Mehr anzeigen' : 'Weniger';
          scrollToBottom();
        };
        bubble.appendChild(toggle);
      }
    });
  }

  function cancelPending() {
    const typing = document.querySelector('.typing-indicator');
    if (typing) typing.remove();
    sending = false;
    const sendBtn = document.getElementById('chat-send-btn');
    if (sendBtn) sendBtn.disabled = false;
    if (slowTimer) { clearTimeout(slowTimer); slowTimer = null; }
    setQuickActionsVisible(true);
  }

  function retry() {
    if (!lastMessage) return;
    // Remove retry button from failed bubble, keep the bubble
    if (lastUserBubble) {
      const retryBtn = lastUserBubble.querySelector('.msg-retry-btn');
      if (retryBtn) retryBtn.remove();
      const errIcon = lastUserBubble.querySelector('.msg-error-icon');
      if (errIcon) errIcon.remove();
    }
    send(lastMessage);
  }

  // ── Voice Recording ──────────────────────────────────

  async function toggleRecording() {
    if (recording) {
      stopRecording();
    } else {
      await startRecording();
    }
  }

  async function startRecording() {
    const micBtn = document.getElementById('chat-mic-btn');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Choose best available MIME type
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : '';

      const options = mimeType ? { mimeType } : {};
      mediaRecorder = new MediaRecorder(stream, options);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach(t => t.stop());
        clearRecordingTimer();
        setRecordingUI(false);

        if (audioChunks.length === 0) return;

        const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
        audioChunks = [];

        // Show transcription status
        const input = document.getElementById('chat-input');
        const origPlaceholder = input.placeholder;
        input.placeholder = 'Wird transkribiert\u2026';
        input.disabled = true;

        try {
          const result = await Api.transcribeVoice(blob);
          input.disabled = false;
          input.placeholder = origPlaceholder;
          if (result.transcription) {
            send(result.transcription);
          }
        } catch (err) {
          input.disabled = false;
          input.placeholder = origPlaceholder;
          showToast(err.message || 'Transkription fehlgeschlagen', 'error');
        }
      };

      mediaRecorder.start();
      recording = true;
      setRecordingUI(true);
      startRecordingTimer();

    } catch (err) {
      if (err.name === 'NotAllowedError') {
        showToast('Mikrofonzugriff verweigert. Bitte erlaube den Zugriff in den Browsereinstellungen.', 'error');
      } else {
        showToast('Mikrofon konnte nicht gestartet werden.', 'error');
      }
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    recording = false;
  }

  function setRecordingUI(isRecording) {
    const micBtn = document.getElementById('chat-mic-btn');
    if (!micBtn) return;
    if (isRecording) {
      micBtn.classList.add('recording');
      micBtn.querySelector('.material-symbols-outlined').textContent = 'stop_circle';
      micBtn.title = 'Aufnahme stoppen';
    } else {
      micBtn.classList.remove('recording');
      micBtn.querySelector('.material-symbols-outlined').textContent = 'mic';
      micBtn.title = 'Sprachnachricht';
      // Remove recording indicator
      const indicator = document.querySelector('.recording-indicator');
      if (indicator) indicator.remove();
    }
  }

  function startRecordingTimer() {
    recordingSeconds = 0;
    const micBtn = document.getElementById('chat-mic-btn');
    // Add timer indicator after mic button
    const indicator = document.createElement('span');
    indicator.className = 'recording-indicator';
    indicator.textContent = '0:00';
    micBtn.parentNode.insertBefore(indicator, micBtn.nextSibling);

    recordingTimer = setInterval(() => {
      recordingSeconds++;
      const mins = Math.floor(recordingSeconds / 60);
      const secs = String(recordingSeconds % 60).padStart(2, '0');
      indicator.textContent = `${mins}:${secs}`;
      if (recordingSeconds >= MAX_RECORDING_SECONDS) {
        stopRecording();
      }
    }, 1000);
  }

  function clearRecordingTimer() {
    if (recordingTimer) {
      clearInterval(recordingTimer);
      recordingTimer = null;
    }
    recordingSeconds = 0;
  }

  function showToast(message, type) {
    // Use existing toast if available, otherwise alert
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
    } else {
      const toast = document.createElement('div');
      toast.className = `toast toast-${type || 'info'}`;
      toast.textContent = message;
      document.body.appendChild(toast);
      setTimeout(() => toast.classList.add('show'), 10);
      setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }, 3000);
    }
  }

  return { render, send, cancelPending, retry, toggleRecording };
})();
