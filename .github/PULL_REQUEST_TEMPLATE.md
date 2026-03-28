## Ziel / Problem

<!-- Was wird gelöst oder verbessert? Kurze Zusammenfassung. -->

Fixes #

## Betroffene Bereiche

<!-- Welche Teile des Systems sind betroffen? -->

- [ ] Bot (src/, main.py)
- [ ] API (api/)
- [ ] App (app/)
- [ ] Config (config/, .env.example)
- [ ] Deploy (deploy/, Dockerfile)
- [ ] Tests (tests/)
- [ ] CI/CD (.github/)
- [ ] Docs (docs/, *.md)

## Änderungen

<!-- Kurze Beschreibung der wichtigsten Änderungen. -->

-

## Verifikation

- [ ] `ruff check .` und `ruff format --check .` bestanden
- [ ] `pytest tests/ -v` bestanden
- [ ] Manuelle Prüfung durchgeführt (falls relevant)

## Risiken / Rollback

<!-- Gibt es Risiken? Wie kann die Änderung zurückgenommen werden? -->
<!-- Bei risikoarmen Änderungen: "Kein besonderes Risiko, Revert genügt." -->

## Checkliste

- [ ] PR richtet sich gegen `main`
- [ ] `Fixes #<issue>` in Beschreibung enthalten
- [ ] Keine `.env`, Secrets oder Tokens in der Änderung
- [ ] Änderung ist minimal und fokussiert
