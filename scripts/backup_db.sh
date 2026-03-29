#!/usr/bin/env bash
# SQLite-Backup-Script fuer DualMind Personal Assistant
#
# Nutzung:
#   ./scripts/backup_db.sh              # Einmaliges Backup
#   ./scripts/backup_db.sh --install    # Crontab-Eintrag erstellen (taeglich 03:00)
#
# Aufbewahrung: 7 Tage (aeltere Backups werden automatisch geloescht)

set -euo pipefail

# ── Konfiguration ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="${PROJECT_DIR}/data/assistant.db"
BACKUP_DIR="${PROJECT_DIR}/data/backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/assistant_${TIMESTAMP}.db"

# ── Funktionen ──
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

do_backup() {
    # Backup-Verzeichnis erstellen
    mkdir -p "$BACKUP_DIR"

    # Pruefen ob DB existiert
    if [ ! -f "$DB_PATH" ]; then
        log "WARN: Datenbank nicht gefunden: $DB_PATH"
        log "Ueberspringe Backup (erstmalige Installation?)"
        exit 0
    fi

    # SQLite Online-Backup (sicher waehrend laufender Operationen)
    if command -v sqlite3 &>/dev/null; then
        log "Starte SQLite Online-Backup..."
        sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
    else
        log "sqlite3 nicht verfuegbar, verwende cp..."
        cp "$DB_PATH" "$BACKUP_FILE"
    fi

    # Integritaetscheck
    if command -v sqlite3 &>/dev/null; then
        INTEGRITY=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" 2>&1)
        if [ "$INTEGRITY" = "ok" ]; then
            log "Integritaetscheck: OK"
        else
            log "WARNUNG: Integritaetscheck fehlgeschlagen: $INTEGRITY"
        fi
    fi

    # Backup-Groesse anzeigen
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup erstellt: $BACKUP_FILE ($SIZE)"

    # Alte Backups loeschen
    DELETED=$(find "$BACKUP_DIR" -name "assistant_*.db" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    if [ "$DELETED" -gt 0 ]; then
        log "Alte Backups geloescht: $DELETED (aelter als $RETENTION_DAYS Tage)"
    fi

    log "Backup abgeschlossen."
}

install_cron() {
    CRON_CMD="0 3 * * * $SCRIPT_DIR/backup_db.sh >> ${PROJECT_DIR}/logs/backup.log 2>&1"

    # Pruefen ob bereits installiert
    if crontab -l 2>/dev/null | grep -q "backup_db.sh"; then
        log "Crontab-Eintrag existiert bereits."
        return 0
    fi

    # Hinzufuegen
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    log "Crontab installiert: taeglich 03:00 Uhr"
    log "Logs: ${PROJECT_DIR}/logs/backup.log"
}

# ── Main ──
case "${1:-}" in
    --install)
        install_cron
        ;;
    *)
        do_backup
        ;;
esac
