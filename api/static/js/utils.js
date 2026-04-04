/**
 * Shared utility functions for the DualMind web app.
 */
const Utils = (() => {
  function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  /**
   * Relative Zeitformatierung (deutsch): "Gerade eben", "vor 5 Min.", "Gestern", etc.
   */
  function formatTime(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Gerade eben';
    if (diff < 3600000) return `vor ${Math.floor(diff / 60000)} Min.`;
    if (diff < 86400000) return `vor ${Math.floor(diff / 3600000)} Std.`;
    if (diff < 172800000) return 'Gestern';
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
  }

  /**
   * Datum als dd.mm. formatieren.
   */
  function formatDateShort(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
  }

  return { escapeHtml, formatTime, formatDateShort };
})();

// Backward compatibility: global escapeHtml
function escapeHtml(str) { return Utils.escapeHtml(str); }
