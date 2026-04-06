# Konzept-Review Fixes — 2026-04-05

Umsetzung aller Findings aus `docs/konzept-review-2026-04-05.md`.

## Aenderungs-Uebersicht

| Batch | Commit-Message | Dateien | Aenderungen |
|---|---|---|---|
| **A** | `fix(css): light-mode visibility, reduced-motion, color-scheme auto-detect` | `app.css`, `app.js` | 8 Light-Mode-Selektoren gefixt, 23 hardcodierte Accent-Farben durch Tokens ersetzt, `prefers-reduced-motion` Reset, `prefers-color-scheme` Auto-Detection |
| **B** | `feat(pwa): complete manifest with PNG icons, shortcuts, screenshots` | `manifest.json`, `app.html`, `icons/`, `screenshots/` | PNG-Icons (192/512px + maskable), Manifest mit Shortcuts/Categories/Orientation, Placeholder-Screenshots, apple-touch-icon auf PNG |
| **C** | `fix(auth): exponential backoff for token refresh and offline queue` | `api.js`, `offlineQueue.js`, `sw.js` | Token-Refresh: 3 Retries (1s/2s/4s), OfflineQueue: Backoff 1.5s-12s, SW Cache auf v11 |
| **D** | `refactor(css): replace hardcoded values with design tokens` | `app.css` | 8 generische Spacing-Werte durch `--space-*` ersetzt, `:focus-visible` auf alle interaktiven Elemente erweitert |

## Detaillierte Aenderungen

### BATCH A — Kritische Blocker

**Neue CSS Custom Properties (`:root` + `[data-theme="light"]`):**
- `--accent-4` bis `--accent-50` (Opacity-Skala fuer Accent-Farbe)
- `--on-accent`, `--on-accent-muted`, `--on-accent-subtle`, `--on-accent-faint`
- `--on-accent-bg`, `--on-accent-bg-hover`
- Light-Theme: `--on-accent-bg` nutzt `rgba(0,0,0,...)` statt `rgba(255,255,255,...)`

**Gefixt (vorher unsichtbar in Light Mode):**
- `.toast-undo button` — weisser Text auf weissem Hintergrund
- `.spinner-tiny` — weisser Rahmen auf weissem Hintergrund
- `.offline-banner-btn` — weisser Text auf weissem Hintergrund
- `.offline-banner-spinner` — weisser Rahmen
- `.msg-check` — weisse Icons
- `.chat-bubble.user .chat-time` — weisse Zeitstempel
- `.login-spinner` — weisser Rahmen
- `.badge-muted` — hardcodiert weiss

**23 Accent-Farb-Stellen ersetzt:**
- `rgba(124, 77, 255, 0.XX)` → `var(--accent-XX)` in allen Selektoren
- Nur noch in `:root`-Definitionen als rgba-Werte vorhanden

**Accessibility:**
- `@media (prefers-reduced-motion: reduce)` — globaler Reset fuer alle Animationen
- `prefers-color-scheme` Auto-Detection in `app.js` mit `localStorage`-Override

### BATCH B — PWA-Manifest

**Neue Dateien:**
- `api/static/icons/icon-192.png` (192x192, generiert aus SVG)
- `api/static/icons/icon-512.png` (512x512)
- `api/static/icons/icon-maskable-512.png` (512x512, purpose: maskable)
- `api/static/screenshots/dashboard.png` (Platzhalter — TODO ersetzen)
- `api/static/screenshots/finance.png` (Platzhalter — TODO ersetzen)

**Manifest-Erweiterungen:**
- `orientation: portrait-primary`
- `categories: ["productivity", "utilities", "lifestyle"]`
- `lang: "de"`
- 4 Shortcuts: Dashboard, Einkauf, Chat, Finanzen
- 2 Screenshot-Eintraege (Platzhalter)
- Icons: 192px PNG, 512px PNG, maskable PNG, SVG

### BATCH C — Offline-Robustheit

**Token-Refresh (api.js):**
- Vorher: 1 Versuch, bei Fehler sofort Logout
- Nachher: Max 3 Retries mit 1s/2s/4s Backoff
- Nur bei Network-Error oder 502/503/504 → Retry
- Bei 401 vom Refresh-Endpoint → sofort Logout (Token ungueltig)

**OfflineQueue (offlineQueue.js):**
- Vorher: feste 2s Delay, max 3 Retries
- Nachher: Exponentiell 1.5s/3s/6s/12s, max 4 Retries

**Service Worker:**
- Cache-Version: `dualmind-v10` → `dualmind-v11`
- PNG-Icons zum Precache hinzugefuegt
- Scope `/app` verifiziert: korrekt fuer `/static/*`-Caching

### BATCH D — Design-Tokens

**Spacing-Tokens ersetzt:**
- `#view-container` padding: `20px` → `var(--space-5)`
- `.btn` padding: `10px 20px` → `var(--space-3) var(--space-5)`
- `input/textarea` padding: `10px 14px` → `var(--space-3) var(--space-4)`
- `select` padding: `10px 14px` → `var(--space-3) var(--space-4)`
- `.btn-sm` padding: `10px 14px` → `var(--space-3) var(--space-4)`
- `.card-title` margin: `8px` → `var(--space-2)`
- `.landing-cta` padding: `14px 36px` → `var(--space-4) var(--space-8)`

**Focus-Styles erweitert:**
- `input:focus-visible`, `textarea:focus-visible`
- `[role="button"]:focus-visible`
- `.nav-item:focus-visible`, `.card-clickable:focus-visible`
- `.chip:focus-visible`, `.tab:focus-visible`
- `input[type="checkbox/radio"]:focus-visible` (offset: 3px)
- `input[type="range"]:focus-visible` (offset: 4px)

**Breakpoints beibehalten:**
- 480px, 600px, 640px sind komponenten-spezifisch und funktional korrekt
- Konsolidierung auf 768px wuerde Issue-Labels, Shift-Reports und Kanban-Boards brechen

## Erledigte TODOs (Folge-Commit)

- [x] Service-Worker `SHELL_ASSETS`: 12 fehlende Views + 2 Components ergaenzt, Cache v12
- [x] Theme-Toggle: localStorage-Key auf `dm_theme` vereinheitlicht, Legacy-Migration, Sync mit Auto-Detection
- [x] Screenshots: realistische Mockups fuer Dashboard und Finanzen generiert (Pillow)
