/**
 * CameraCapture – Reusable camera component for PWA
 * Uses MediaDevices API with rear camera preference.
 * Returns File/Blob via callback. Falls back to file picker.
 *
 * Usage:
 *   CameraCapture.open({ onCapture(file) { ... }, onCancel() { ... } });
 */
const CameraCapture = (() => {
  let stream = null;
  let overlayEl = null;
  let capturedBlob = null;
  let onCaptureCallback = null;
  let onCancelCallback = null;

  function open(opts = {}) {
    onCaptureCallback = opts.onCapture || null;
    onCancelCallback = opts.onCancel || null;
    capturedBlob = null;
    showOverlay();
    startCamera();
  }

  function showOverlay() {
    if (overlayEl) overlayEl.remove();
    overlayEl = document.createElement('div');
    overlayEl.className = 'camera-overlay';
    overlayEl.innerHTML = `
      <div class="camera-header">
        <button class="btn-icon camera-close-btn" id="camera-close">
          <span class="material-symbols-outlined">close</span>
        </button>
        <span class="camera-title">Foto aufnehmen</span>
        <span></span>
      </div>
      <div class="camera-viewfinder" id="camera-viewfinder">
        <video id="camera-video" autoplay playsinline muted></video>
        <div class="camera-loading" id="camera-loading">
          <span class="material-symbols-outlined spin">hourglass_empty</span>
          <span>Kamera wird gestartet...</span>
        </div>
      </div>
      <div class="camera-preview" id="camera-preview" style="display:none">
        <img id="camera-preview-img" />
      </div>
      <div class="camera-controls" id="camera-controls">
        <button class="btn btn-secondary camera-gallery-btn" id="camera-gallery" title="Aus Galerie">
          <span class="material-symbols-outlined">photo_library</span>
        </button>
        <button class="camera-shutter-btn" id="camera-shutter" title="Aufnehmen">
          <span class="camera-shutter-ring"></span>
        </button>
        <span style="width:48px"></span>
      </div>
      <div class="camera-confirm-controls" id="camera-confirm" style="display:none">
        <button class="btn btn-secondary" id="camera-retake">
          <span class="material-symbols-outlined mi-sm">replay</span> Nochmal
        </button>
        <button class="btn btn-primary" id="camera-use">
          <span class="material-symbols-outlined mi-sm">check</span> Verwenden
        </button>
      </div>
      <input type="file" id="camera-file-input" accept="image/*" capture="environment" style="display:none" />
      <canvas id="camera-canvas" style="display:none"></canvas>
    `;
    document.body.appendChild(overlayEl);

    document.getElementById('camera-close').onclick = cancel;
    document.getElementById('camera-shutter').onclick = capture;
    document.getElementById('camera-retake').onclick = retake;
    document.getElementById('camera-use').onclick = confirmCapture;
    document.getElementById('camera-gallery').onclick = openGallery;
    document.getElementById('camera-file-input').onchange = handleFileSelect;
  }

  async function startCamera() {
    const video = document.getElementById('camera-video');
    const loading = document.getElementById('camera-loading');
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
      });
      video.srcObject = stream;
      await video.play();
      if (loading) loading.style.display = 'none';
    } catch (err) {
      console.warn('Camera access denied or unavailable:', err.message);
      if (loading) {
        loading.innerHTML = `
          <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted)">no_photography</span>
          <span style="margin-top:8px;text-align:center">Kamera nicht verfügbar.<br>Nutze den Galerie-Button unten.</span>
        `;
      }
    }
  }

  function capture() {
    const video = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    if (!video || !video.videoWidth) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(blob => {
      if (!blob) return;
      capturedBlob = blob;
      showPreview(URL.createObjectURL(blob));
    }, 'image/jpeg', 0.9);
  }

  function showPreview(src) {
    const viewfinder = document.getElementById('camera-viewfinder');
    const preview = document.getElementById('camera-preview');
    const controls = document.getElementById('camera-controls');
    const confirm = document.getElementById('camera-confirm');
    const img = document.getElementById('camera-preview-img');

    if (viewfinder) viewfinder.style.display = 'none';
    if (preview) { preview.style.display = 'flex'; img.src = src; }
    if (controls) controls.style.display = 'none';
    if (confirm) confirm.style.display = 'flex';

    stopStream();
  }

  function retake() {
    capturedBlob = null;
    const viewfinder = document.getElementById('camera-viewfinder');
    const preview = document.getElementById('camera-preview');
    const controls = document.getElementById('camera-controls');
    const confirm = document.getElementById('camera-confirm');

    if (viewfinder) viewfinder.style.display = 'flex';
    if (preview) preview.style.display = 'none';
    if (controls) controls.style.display = 'flex';
    if (confirm) confirm.style.display = 'none';

    startCamera();
  }

  function confirmCapture() {
    if (!capturedBlob) return;
    const file = new File([capturedBlob], `scan_${Date.now()}.jpg`, { type: 'image/jpeg' });
    cleanup();
    if (onCaptureCallback) onCaptureCallback(file);
  }

  function openGallery() {
    const input = document.getElementById('camera-file-input');
    if (input) input.click();
  }

  function handleFileSelect(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    capturedBlob = file;
    showPreview(URL.createObjectURL(file));
  }

  function cancel() {
    cleanup();
    if (onCancelCallback) onCancelCallback();
  }

  function stopStream() {
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
  }

  function cleanup() {
    stopStream();
    if (overlayEl) { overlayEl.remove(); overlayEl = null; }
    capturedBlob = null;
  }

  return { open };
})();
