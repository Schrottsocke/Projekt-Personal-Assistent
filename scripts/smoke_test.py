#!/usr/bin/env python3
"""Smoke-Test: prueft ob alle Services importierbar und grundlegend initialisierbar sind.

Nutzung:
    python scripts/smoke_test.py          # Alle Services pruefen
    python scripts/smoke_test.py --quick  # Nur Imports pruefen (keine Init)

Exit-Code 0 = alle Tests bestanden, 1 = mindestens ein Fehler.
"""

import importlib
import sys
import os
from pathlib import Path

# Projektroot zum Pfad hinzufuegen
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Minimale Env-Vars setzen damit Settings nicht crasht
_DEFAULTS = {
    "BOT_TOKEN_TAAKE": "test:token",
    "BOT_TOKEN_NINA": "test:token",
    "TELEGRAM_USER_ID_TAAKE": "12345",
    "TELEGRAM_USER_ID_NINA": "12345",
    "OPENROUTER_API_KEY": "test-key",
    "API_SECRET_KEY": "a" * 32,
    "API_PASSWORD_TAAKE": "testpass",
    "API_PASSWORD_NINA": "testpass",
    "DATABASE_URL": "sqlite:///data/test_smoke.db",
}

for key, val in _DEFAULTS.items():
    os.environ.setdefault(key, val)


# ── Service-Module die importierbar sein muessen ──────────────────────
CORE_MODULES = [
    ("config.settings", "Settings"),
    ("src.services.database", "init_db"),
    ("src.services.ai_service", "AIService"),
    ("src.memory.base_memory_service", "BaseMemoryService"),
    ("src.memory.memory_service", "MemoryService"),
    ("src.services.task_service", "TaskService"),
    ("src.services.reminder_service", "ReminderService"),
    ("src.services.notes_service", "NotesService"),
    ("src.services.proposal_service", "ProposalService"),
    ("src.services.shopping_service", "ShoppingService"),
    ("src.services.document_service", "DocumentService"),
    ("src.services.rate_limiter", None),
]

OPTIONAL_MODULES = [
    ("src.services.calendar_service", "CalendarService"),
    ("src.services.email_service", "EmailService"),
    ("src.services.drive_service", "DriveService"),
    ("src.services.tts_service", "TTSService"),
    ("src.services.spotify_service", "SpotifyService"),
    ("src.services.smarthome_service", "SmartHomeService"),
    ("src.services.chefkoch_service", "ChefkochService"),
    ("src.services.weather_service", "WeatherService"),
    ("src.services.web_search", None),
    ("src.services.scanner_service", "ScannerService"),
    ("src.services.mobility_service", "MobilityService"),
    ("src.services.ocr_service", "OcrService"),
    ("src.services.pdf_service", "PdfService"),
    ("src.services.memory_service", None),
]

API_MODULES = [
    ("api.main", "app"),
    ("api.dependencies", None),
    ("api.auth.jwt_handler", None),
]

BOT_MODULES = [
    ("src.bots.base_bot", "BaseAssistantBot"),
    ("src.bots.taake_bot", "TaakeBot"),
    ("src.bots.nina_bot", "NinaBot"),
]

SCHEDULER_MODULES = [
    ("src.scheduler.scheduler", "AssistantScheduler"),
]

HANDLER_MODULES = [
    ("src.handlers.command_handlers", None),
    ("src.handlers.message_handlers", None),
    ("src.handlers.proposal_handlers", None),
    ("src.handlers.onboarding", None),
]


def check_import(module_path: str, class_name: str | None) -> tuple[bool, str]:
    """Versucht ein Modul zu importieren und optional eine Klasse daraus zu laden."""
    try:
        mod = importlib.import_module(module_path)
        if class_name and not hasattr(mod, class_name):
            return False, f"{module_path}: Klasse '{class_name}' nicht gefunden"
        return True, "OK"
    except Exception as exc:
        return False, f"{module_path}: {type(exc).__name__}: {exc}"


def run_smoke_tests(quick: bool = False) -> int:
    """Fuehrt alle Smoke-Tests aus. Gibt Exit-Code zurueck."""
    categories = [
        ("Core Services", CORE_MODULES),
        ("Optional Services", OPTIONAL_MODULES),
        ("API", API_MODULES),
        ("Bots", BOT_MODULES),
        ("Scheduler", SCHEDULER_MODULES),
        ("Handlers", HANDLER_MODULES),
    ]

    total = 0
    passed = 0
    failed = 0
    warnings = 0
    errors: list[str] = []

    for cat_name, modules in categories:
        print(f"\n{'=' * 60}")
        print(f"  {cat_name}")
        print(f"{'=' * 60}")

        is_optional = cat_name == "Optional Services"

        for module_path, class_name in modules:
            total += 1
            ok, msg = check_import(module_path, class_name)

            label = f"{module_path}"
            if class_name:
                label += f".{class_name}"

            if ok:
                passed += 1
                print(f"  [PASS] {label}")
            elif is_optional:
                warnings += 1
                print(f"  [WARN] {label} -- {msg}")
            else:
                failed += 1
                print(f"  [FAIL] {label} -- {msg}")
                errors.append(msg)

    # ── Zusammenfassung ──
    print(f"\n{'=' * 60}")
    print("  ERGEBNIS")
    print(f"{'=' * 60}")
    print(f"  Gesamt:    {total}")
    print(f"  Bestanden: {passed}")
    print(f"  Warnungen: {warnings}")
    print(f"  Fehler:    {failed}")

    if errors:
        print("\n  Fehlerdetails:")
        for err in errors:
            print(f"    - {err}")

    if failed > 0:
        print("\n  STATUS: FEHLGESCHLAGEN")
        return 1
    else:
        print("\n  STATUS: BESTANDEN")
        return 0


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    sys.exit(run_smoke_tests(quick=quick))
