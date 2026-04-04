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

  /**
   * Uhrzeit als HH:MM formatieren.
   */
  function formatClockTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }

  /**
   * Tageszeit-Begruessung (Morgen/Tag/Abend).
   */
  function getGreeting() {
    const h = new Date().getHours();
    if (h < 12) return 'Guten Morgen';
    if (h < 18) return 'Guten Tag';
    return 'Guten Abend';
  }

  /**
   * Ersten Buchstaben gross.
   */
  function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
  }

  return { escapeHtml, formatTime, formatDateShort, formatClockTime, getGreeting, capitalize };
})();

// Backward compatibility: global escapeHtml
function escapeHtml(str) { return Utils.escapeHtml(str); }
