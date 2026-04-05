/**
 * Mehr-Menue – Zugang zu allen sekundaeren Features.
 * Einfache vertikale Liste mit Icons und Beschreibungen.
 */
const MehrView = (() => {
  const SECTIONS = [
    {
      label: 'Konto',
      items: [
        { id: 'profile', icon: 'person', label: 'Profil & Einstellungen', route: '#/profile', desc: 'Theme, Benachrichtigungen, Konto' },
      ],
    },
    {
      label: 'Finanzen & Haushalt',
      items: [
        { id: 'finance', icon: 'account_balance', label: 'Finanzen', route: '#/finance', desc: 'Transaktionen, Budgets, Vertraege' },
        { id: 'invoices', icon: 'receipt_long', label: 'Rechnungen', route: '#/invoices', desc: 'Rechnungen erstellen und verwalten' },
        { id: 'inventory', icon: 'inventory_2', label: 'Inventar', route: '#/inventory', desc: 'Gegenstaende, Garantien, Dokumente' },
        { id: 'family', icon: 'group', label: 'Familie', route: '#/family', desc: 'Listen, Aufgaben, Routinen teilen' },
      ],
    },
    {
      label: 'Werkzeuge',
      items: [
        { id: 'documents', icon: 'scanner', label: 'Dokumente', route: '#/documents', desc: 'Scannen, OCR, Ablage' },
        { id: 'drive', icon: 'folder', label: 'Drive', route: '#/drive', desc: 'Dateien und Uploads' },
        { id: 'email', icon: 'mail', label: 'E-Mail', route: '#/email', desc: 'Gmail Posteingang' },
        { id: 'contacts', icon: 'contacts', label: 'Kontakte', route: '#/contacts', desc: 'Adressbuch verwalten' },
        { id: 'templates', icon: 'library_books', label: 'Vorlagen', route: '#/templates', desc: 'Einkauf, Aufgaben, Routinen' },
        { id: 'shifts', icon: 'work', label: 'Schichtplaner', route: '#/shifts', desc: 'Diensttypen und Kalender' },
      ],
    },
    {
      label: 'Erweitert',
      items: [
        { id: 'automation', icon: 'smart_toy', label: 'Automation', route: '#/automation', desc: 'Wenn-Dann-Regeln' },
        { id: 'memory', icon: 'psychology', label: 'Gedaechtnis', route: '#/memory', desc: 'Was der Assistent sich merkt' },
        { id: 'notification-center', icon: 'notifications_active', label: 'Benachrichtigungen', route: '#/notification-center', desc: 'Alle Benachrichtigungen verwalten' },
        { id: 'gdpr', icon: 'shield', label: 'Datenschutz', route: '#/gdpr', desc: 'DSGVO, Datenexport, Follow-ups' },
        { id: 'weather', icon: 'cloud', label: 'Wetter', route: '#/weather', desc: 'Vorhersage und Details' },
        { id: 'mobility', icon: 'route', label: 'Mobilitaet', route: '#/mobility', desc: 'Reisezeiten und Routen' },
        { id: 'issues', icon: 'bug_report', label: 'Issues', route: '#/issues', desc: 'GitHub Bug-Tracker' },
        { id: 'test-user-admin', icon: 'admin_panel_settings', label: 'Testuser', route: '#/test-user-admin', desc: 'Einladungen verwalten' },
      ],
    },
  ];

  function render(container) {
    container.innerHTML = `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">menu</span> Mehr</h2>
      </div>
      ${SECTIONS.map(section => `
        <div class="mehr-section">
          <div class="mehr-section-label">${section.label}</div>
          ${section.items.map(item => `
            <a class="mehr-item" href="${item.route}">
              <div class="mehr-item-icon">
                <span class="material-symbols-outlined">${item.icon}</span>
              </div>
              <div class="mehr-item-content">
                <div class="mehr-item-label">${item.label}</div>
                <div class="mehr-item-desc">${item.desc}</div>
              </div>
              <span class="material-symbols-outlined mehr-item-arrow">chevron_right</span>
            </a>
          `).join('')}
        </div>
      `).join('')}
    `;
  }

  return { render };
})();
