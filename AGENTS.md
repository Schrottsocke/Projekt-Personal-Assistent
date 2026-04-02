AGENTS.md — Produktkontext und Architekturleitplanken
Diese Datei beschreibt den fachlichen Kontext des Projekts sowie produktbezogene Leitplanken fuer Coding Agents.
Arbeitsmodus, Sessionregeln, GitHub-Flow, Stop-Regeln und Claude-spezifisches Verhalten stehen ausschliesslich in `CLAUDE.md`.
Produktverstaendnis
DualMind ist ein produktiv nutzbarer persoenlicher Assistent, keine Demo-Oberflaeche.
Neue Features sollen alltagstauglich, robust und plattformuebergreifend nutzbar sein.
WebApp, iOS und Android sollen moeglichst dieselbe fachliche Logik und dieselben Nutzerpraeferenzen verwenden.
Der Nutzer soll zentrale Assistentenfunktionen nicht nur im Chat, sondern auch ueber eine klare App-Oberflaeche steuern koennen.
Informationsarchitektur
Home ist das Dashboard.
Das Dashboard ist modular und widget-basiert.
Navigation ist nutzerkonfigurierbar.
Tasks, Kalender und Meal Plan sind standardmaessig aktiviert.
Auf kleinen Screens duerfen nicht beliebig viele Haupt-Tabs gleichzeitig sichtbar sein; zusaetzliche aktive Bereiche sollen ueber Overflow oder „Mehr“ erreichbar sein.
Fokus-/Heute-Ansichten sind reduzierte Varianten des Dashboards und kein separates zweites Dashboard-System.
Produktregeln nach Bereich
Dashboard
Widgets sollen aktivierbar, deaktivierbar und umsortierbar sein.
Kompakte Fokus-/Heute-Ansichten sollen nur die wichtigsten Tagespunkte priorisieren.
Dashboard-Varianten sollen auf denselben Daten- und Preference-Strukturen aufbauen.
Chat
Text ist das kanonische Nachrichtenformat.
Voice ist ein alternativer Eingabekanal und wird zu Text transkribiert.
Chat-Logik soll nicht plattformabhaengig auseinanderlaufen.
Telegram, WebApp und spaetere Mobile-Apps sollen dieselben fachlichen Chat-Faehigkeiten verwenden.
Inbox und Notifications
Inbox ist fuer pruef- und uebernehmbare Vorschlaege.
Notifications sind fuer Hinweise, Warnungen, Erinnerungen und Statusaenderungen.
Diese beiden Konzepte duerfen fachlich nicht vermischt werden.
Dokumente
Dokumentverarbeitung ist ein echter Nutzerfluss: neu -> analysiert -> Aktion vorgeschlagen -> abgelegt.
Dokumente sollen nachvollziehbare Status, Extraktionen und Folgeaktionen haben.
Dokumente sind keine reine Debug- oder Admin-Ansicht.
Kontakte und Follow-ups
Kontakte dienen als leichte Kontextschicht fuer E-Mail, Kalender, Erinnerungen und Vorschlaege.
Kein vollwertiges CRM aufbauen.
Follow-ups sollen offene Rueckmeldungen und Zusagen unterstuetzen, nicht komplexe Sales-Prozesse.
Wetter und Mobility
Wetter ist Kontext fuer Tagesplanung, nicht nur eine isolierte Einzelabfrage.
Mobility soll proaktiv mit Kalender- und Wetterkontext zusammenarbeiten.
Das Ziel ist Assistenz im Alltag, nicht der Bau einer vollstaendigen Navigations- oder Wetter-App.
Preferences
Nutzerpraeferenzen sind plattformuebergreifend zu denken.
Theme, Schriftgroesse, Navigation, Fokus, Quiet Hours, TTS und aehnliche Einstellungen sollen als zusammenhaengendes Preferences-Modell behandelt werden.
Serverseitige Speicherung ist die bevorzugte Richtung; lokaler Cache ist nur Fallback.
UX-Leitplanken
Jede produktive Ansicht braucht Loading-, Empty- und Error-States.
Keine toten Platzhalter oder rein visuellen Demo-Elemente in produktiven Flows.
Mobile Nutzbarkeit immer mitdenken.
Bestehende Muster konsistent halten, statt fuer jedes neue Feature eine neue Interaktionslogik einzufuehren.
Architekturleitplanken
Bestehende Models, Services, Provider und API-Vertraege bevorzugt wiederverwenden.
Neue Strukturen nur einfuehren, wenn vorhandene Strukturen fachlich nicht passen.
Neue Features sollen nach Moeglichkeit an bestehende Bausteine andocken, insbesondere Dashboard, Inbox, Notifications, Preferences, Kontakte und Dokumente.
Backend-Erweiterungen sollen generisch und wiederverwendbar modelliert werden.
Relevante Bereiche im Repo
`app/` — Flutter-App / WebApp-Client
`api/` — FastAPI-Backend und REST-Endpunkte
`src/` — Kernlogik und Services
`memory/` — projektbezogene Dokumentation und Erkenntnisse
`docs/` — Playbooks und ergänzende Projektdokumentation
