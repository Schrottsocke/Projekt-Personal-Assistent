/**
 * DualMind Web App – Shared Utilities
 */

/**
 * Escape HTML special characters to prevent XSS.
 * Uses DOM textContent/innerHTML for reliable encoding.
 */
function escapeHtml(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
