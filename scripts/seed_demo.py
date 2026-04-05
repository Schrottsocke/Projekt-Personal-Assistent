#!/usr/bin/env python3
"""
Seed-Skript: Demo-Haushalt "Familie Beispiel" mit realistischen Testdaten.

Deterministisch und reproduzierbar – laeuft idempotent (loescht alte Demo-Daten zuerst).
Kein PII – alle Daten sind fiktiv.

Usage:
    python scripts/seed_demo.py
"""

import json
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Projekt-Root in sys.path einfuegen
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.database import (
    Base,
    Budget,
    BudgetCategory,
    Contract,
    FinanceInvoice,
    HouseholdDocument,
    InvoiceItem,
    InventoryItem,
    ShoppingItem,
    Task,
    Transaction,
    UserProfile,
    get_db,
    init_db,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Demo-User Keys ─────────────────────────────────────────────────────────
DEMO_USERS = [
    {
        "user_key": "demo_max",
        "nickname": "Max Beispiel",
        "communication_style": "casual",
        "is_onboarded": True,
        "work_start": "08:00",
        "work_end": "17:00",
        "quiet_start": "22:00",
        "quiet_end": "07:00",
        "focus_time": "morgen",
    },
    {
        "user_key": "demo_lisa",
        "nickname": "Lisa Beispiel",
        "communication_style": "casual",
        "is_onboarded": True,
        "work_start": "09:00",
        "work_end": "18:00",
        "quiet_start": "23:00",
        "quiet_end": "07:00",
        "focus_time": "abend",
    },
    {
        "user_key": "demo_finn",
        "nickname": "Finn Beispiel",
        "communication_style": "casual",
        "is_onboarded": True,
    },
]

# ── Reference date for deterministic data ──────────────────────────────────
TODAY = date.today()
NOW = datetime.now(timezone.utc)


def _date_ago(days: int) -> date:
    return TODAY - timedelta(days=days)


def _dt_ago(days: int, hour: int = 12) -> datetime:
    return datetime(TODAY.year, TODAY.month, TODAY.day, hour, 0, tzinfo=timezone.utc) - timedelta(days=days)


def _date_future(days: int) -> date:
    return TODAY + timedelta(days=days)


# ── Cleanup ────────────────────────────────────────────────────────────────

def cleanup_demo_data(db):
    """Loescht alle Demo-Daten (user_key LIKE 'demo_%')."""
    demo_keys = [u["user_key"] for u in DEMO_USERS]

    # Reihenfolge beachten (ForeignKey-Constraints)
    profiles = db.query(UserProfile).filter(UserProfile.user_key.in_(demo_keys)).all()
    demo_user_ids = [p.id for p in profiles]

    if demo_user_ids:
        # Invoice items via invoice
        invoices = db.query(FinanceInvoice).filter(FinanceInvoice.user_id.in_(demo_user_ids)).all()
        invoice_ids = [inv.id for inv in invoices]
        if invoice_ids:
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
        db.query(FinanceInvoice).filter(FinanceInvoice.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(Transaction).filter(Transaction.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(Contract).filter(Contract.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(Budget).filter(Budget.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(BudgetCategory).filter(BudgetCategory.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(HouseholdDocument).filter(HouseholdDocument.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(InventoryItem).filter(InventoryItem.user_id.in_(demo_user_ids)).delete(synchronize_session=False)

    for key in demo_keys:
        db.query(Task).filter(Task.user_key == key).delete(synchronize_session=False)
        db.query(ShoppingItem).filter(ShoppingItem.user_key == key).delete(synchronize_session=False)

    db.query(UserProfile).filter(UserProfile.user_key.in_(demo_keys)).delete(synchronize_session=False)
    db.flush()
    logger.info("Alte Demo-Daten geloescht.")


# ── Seed functions ─────────────────────────────────────────────────────────

def seed_users(db) -> dict[str, int]:
    """Erstellt Demo-User und gibt {user_key: user_id} zurueck."""
    user_ids = {}
    for u in DEMO_USERS:
        profile = UserProfile(**u)
        db.add(profile)
        db.flush()
        user_ids[u["user_key"]] = profile.id
        logger.info("User erstellt: %s (id=%d)", u["user_key"], profile.id)
    return user_ids


def seed_transactions(db, user_ids: dict[str, int]):
    """Erstellt 30 realistische Transaktionen ueber die letzten 60 Tage."""
    max_id = user_ids["demo_max"]
    lisa_id = user_ids["demo_lisa"]

    transactions = [
        # Max – Gehalt und Ausgaben
        (max_id, _dt_ago(58), 2850.00, "Gehalt", "Gehalt Dezember", "manual"),
        (max_id, _dt_ago(55), -45.90, "Lebensmittel", "Wocheneinkauf REWE", "manual"),
        (max_id, _dt_ago(52), -12.99, "Streaming", "Netflix Abo", "manual"),
        (max_id, _dt_ago(50), -89.00, "Versicherung", "Haftpflichtversicherung", "manual"),
        (max_id, _dt_ago(47), -35.50, "Lebensmittel", "Wocheneinkauf Edeka", "manual"),
        (max_id, _dt_ago(44), -28.00, "Restaurant", "Abendessen Pizza", "manual"),
        (max_id, _dt_ago(40), -65.00, "Kleidung", "Winterjacke Sale", "manual"),
        (max_id, _dt_ago(37), -52.30, "Lebensmittel", "Grosseinkauf Lidl", "manual"),
        (max_id, _dt_ago(33), -15.00, "Freizeit", "Kino Tickets", "manual"),
        (max_id, _dt_ago(30), 2850.00, "Gehalt", "Gehalt Januar", "manual"),
        (max_id, _dt_ago(28), -750.00, "Miete", "Miete Februar", "manual"),
        (max_id, _dt_ago(25), -48.70, "Lebensmittel", "Wocheneinkauf REWE", "manual"),
        (max_id, _dt_ago(22), -9.99, "Streaming", "Spotify Family", "manual"),
        (max_id, _dt_ago(18), -120.00, "Auto", "Tankfuellung", "manual"),
        (max_id, _dt_ago(14), -38.50, "Lebensmittel", "Wocheneinkauf Aldi", "manual"),
        (max_id, _dt_ago(10), -22.00, "Gesundheit", "Apotheke", "manual"),
        (max_id, _dt_ago(7), -43.80, "Lebensmittel", "Wocheneinkauf REWE", "manual"),
        (max_id, _dt_ago(3), -55.00, "Haushalt", "Staubsauger-Beutel und Reiniger", "manual"),
        (max_id, _dt_ago(1), -18.50, "Restaurant", "Mittagessen Kantine", "manual"),
        # Lisa – Gehalt und Ausgaben
        (lisa_id, _dt_ago(58), 2400.00, "Gehalt", "Gehalt Dezember", "manual"),
        (lisa_id, _dt_ago(50), -32.00, "Lebensmittel", "Bio-Markt Einkauf", "manual"),
        (lisa_id, _dt_ago(45), -79.90, "Kleidung", "Schuhe online", "manual"),
        (lisa_id, _dt_ago(38), -14.99, "Streaming", "Disney+ Abo", "manual"),
        (lisa_id, _dt_ago(30), 2400.00, "Gehalt", "Gehalt Januar", "manual"),
        (lisa_id, _dt_ago(26), -42.50, "Lebensmittel", "Wocheneinkauf Bio-Markt", "manual"),
        (lisa_id, _dt_ago(20), -180.00, "Bildung", "Online-Kurs Fotografie", "manual"),
        (lisa_id, _dt_ago(15), -25.00, "Freizeit", "Yoga-Kurs", "manual"),
        (lisa_id, _dt_ago(8), -56.30, "Lebensmittel", "Grosseinkauf dm + Edeka", "manual"),
        (lisa_id, _dt_ago(4), -35.00, "Geschenk", "Geburtstagsgeschenk Kollegin", "manual"),
        (lisa_id, _dt_ago(0), -19.90, "Haushalt", "Kerzen und Deko", "manual"),
    ]

    for user_id, dt, amount, category, description, source in transactions:
        db.add(Transaction(
            user_id=user_id, date=dt, amount=amount, currency="EUR",
            category=category, description=description, source=source,
        ))
    db.flush()
    logger.info("%d Transaktionen erstellt.", len(transactions))


def seed_contracts(db, user_ids: dict[str, int]):
    """Erstellt 2 laufende Vertraege."""
    max_id = user_ids["demo_max"]

    contracts = [
        Contract(
            user_id=max_id, name="Mobilfunk Tarif L", provider="Telekom",
            category="Telekommunikation", amount=29.99, interval="monthly",
            start_date=_date_ago(365), end_date=_date_future(365),
            cancellation_days=90, status="active",
            notes="24-Monats-Vertrag, 10 GB Daten",
        ),
        Contract(
            user_id=max_id, name="Haftpflichtversicherung", provider="HUK-COBURG",
            category="Versicherung", amount=89.00, interval="yearly",
            start_date=_date_ago(730), cancellation_days=30,
            status="active", notes="Familien-Haftpflicht",
        ),
    ]
    for c in contracts:
        db.add(c)
    db.flush()
    logger.info("%d Vertraege erstellt.", len(contracts))


def seed_invoices(db, user_ids: dict[str, int]):
    """Erstellt 4 Rechnungen mit Positionen."""
    max_id = user_ids["demo_max"]

    invoice_data = [
        {
            "user_id": max_id, "invoice_number": "RE-2026-001",
            "recipient": "Hausverwaltung Sonnenberg", "issue_date": _date_ago(30),
            "total": 85.00, "due_date": _date_ago(0), "status": "paid",
            "payment_date": _date_ago(5), "notes": "Nebenkostenabrechnung",
            "items": [
                ("Nebenkostenabrechnung 2025", 1, 85.00),
            ],
        },
        {
            "user_id": max_id, "invoice_number": "RE-2026-002",
            "recipient": "Stadtwerke Musterstadt", "issue_date": _date_ago(14),
            "total": 128.50, "due_date": _date_future(14), "status": "open",
            "notes": "Strom-Jahresabrechnung",
            "items": [
                ("Stromverbrauch 2025 Nachzahlung", 1, 98.50),
                ("Neue Abschlagsberechnung Anpassung", 1, 30.00),
            ],
        },
        {
            "user_id": max_id, "invoice_number": "RE-2026-003",
            "recipient": "Zahnarztpraxis Dr. Zahn", "issue_date": _date_ago(45),
            "total": 180.00, "due_date": _date_ago(15), "status": "overdue",
            "notes": "Zahnreinigung und Kontrolluntersuchung",
            "items": [
                ("Professionelle Zahnreinigung", 1, 120.00),
                ("Kontrolluntersuchung Eigenanteil", 1, 60.00),
            ],
        },
        {
            "user_id": max_id, "invoice_number": "RE-2026-004",
            "recipient": "KFZ-Werkstatt Motorfix", "issue_date": _date_ago(7),
            "total": 345.80, "due_date": _date_future(21), "status": "open",
            "notes": "Inspektion und Oelwechsel",
            "items": [
                ("Inspektion nach Herstellervorgabe", 1, 189.00),
                ("Motoroel 5W30 (5L)", 1, 56.80),
                ("Oelfilter", 1, 18.00),
                ("Bremsfl\u00fcssigkeit pruefen + nachfuellen", 1, 82.00),
            ],
        },
    ]

    for inv_data in invoice_data:
        items = inv_data.pop("items")
        invoice = FinanceInvoice(**inv_data)
        db.add(invoice)
        db.flush()
        for desc, qty, price in items:
            db.add(InvoiceItem(
                invoice_id=invoice.id, description=desc,
                quantity=qty, unit_price=price, total=qty * price,
            ))
    db.flush()
    logger.info("%d Rechnungen erstellt.", len(invoice_data))


def seed_budgets(db, user_ids: dict[str, int]):
    """Erstellt Budget-Kategorien."""
    max_id = user_ids["demo_max"]

    categories = [
        ("Lebensmittel", 400.00, "#4caf50", "restaurant"),
        ("Miete", 750.00, "#f44336", "home"),
        ("Freizeit", 150.00, "#ff9800", "sports_esports"),
        ("Auto", 200.00, "#2196f3", "directions_car"),
        ("Kleidung", 100.00, "#9c27b0", "checkroom"),
    ]
    for name, limit_val, color, icon in categories:
        db.add(BudgetCategory(
            user_id=max_id, name=name, monthly_limit=limit_val,
            color=color, icon=icon,
        ))
    db.flush()
    logger.info("%d Budget-Kategorien erstellt.", len(categories))


def seed_documents(db, user_ids: dict[str, int]):
    """Erstellt 4 Beispiel-Dokumente mit OCR-Metadaten."""
    max_id = user_ids["demo_max"]

    documents = [
        HouseholdDocument(
            user_id=max_id, title="Nebenkostenabrechnung 2025",
            category="invoice", issuer="Hausverwaltung Sonnenberg",
            amount=85.00, deadline_date=_date_ago(0),
            ocr_text="Nebenkostenabrechnung fuer das Jahr 2025\nMieter: Familie Beispiel\nGesamt: 85,00 EUR\nFaellig bis: sofort",
        ),
        HouseholdDocument(
            user_id=max_id, title="KFZ-Versicherungsschein 2026",
            category="insurance", issuer="HUK-COBURG",
            amount=420.00, deadline_date=_date_future(330),
            ocr_text="Versicherungsschein Nr. KFZ-2026-88432\nFahrzeug: VW Golf VIII\nJahresbeitrag: 420,00 EUR\nGueltig bis: 31.12.2026",
        ),
        HouseholdDocument(
            user_id=max_id, title="Garantieschein Waschmaschine",
            category="warranty", issuer="Bosch Hausgeraete",
            amount=None, deadline_date=_date_future(540),
            ocr_text="Garantieschein\nProdukt: Bosch WAX32M00 Waschmaschine\nKaufdatum: 15.03.2025\nGarantie: 2 Jahre\nSerien-Nr: BSH-WM-2025-44821",
        ),
        HouseholdDocument(
            user_id=max_id, title="Mietvertrag Wohnung",
            category="other", issuer="Hausverwaltung Sonnenberg",
            amount=750.00,
            ocr_text="Mietvertrag\nVermieter: Sonnenberg Immobilien GmbH\nMieter: Max Beispiel\nKaltmiete: 750,00 EUR\nNebenkosten: 180,00 EUR\nBeginn: 01.04.2023",
        ),
    ]
    for doc in documents:
        db.add(doc)
    db.flush()
    logger.info("%d Dokumente erstellt.", len(documents))


def seed_inventory(db, user_ids: dict[str, int]):
    """Erstellt 12 Inventar-Gegenstaende ueber mehrere Raeume."""
    max_id = user_ids["demo_max"]

    items = [
        # Wohnzimmer
        ("Samsung OLED TV 55 Zoll", "Wohnzimmer", "Smart TV mit HDMI 2.1", 899.00, _date_ago(180), "SN-TV-55-2025"),
        ("IKEA Sofa Kivik 3-Sitzer", "Wohnzimmer", "Bezug: Grau, waschbar", 699.00, _date_ago(365), None),
        ("Sonos Beam Soundbar", "Wohnzimmer", "Dolby Atmos, WLAN", 449.00, _date_ago(90), "SN-SONOS-2025"),
        # Kueche
        ("Bosch WAX32M00 Waschmaschine", "Kueche", "8kg, 1600 U/min, Energieklasse A", 629.00, _date_ago(300), "BSH-WM-2025-44821"),
        ("Siemens Kuehlschrank", "Kueche", "No-Frost, 300L", 549.00, _date_ago(500), None),
        ("KitchenAid Kuechenmaschine", "Kueche", "Artisan 5KSM175, Rot", 479.00, _date_ago(150), "KA-ART-2025"),
        # Arbeitszimmer
        ("MacBook Pro 14 Zoll", "Arbeitszimmer", "M3 Pro, 18GB RAM, 512GB SSD", 1999.00, _date_ago(120), "C02FM123456"),
        ("Dell Monitor U2723QE", "Arbeitszimmer", "27 Zoll, 4K, USB-C Hub", 489.00, _date_ago(120), None),
        ("IKEA Bekant Schreibtisch", "Arbeitszimmer", "Hoehenverstellbar, 160x80cm", 549.00, _date_ago(400), None),
        # Schlafzimmer
        ("Emma One Matratze", "Schlafzimmer", "180x200cm, H3", 449.00, _date_ago(700), None),
        # Kinderzimmer
        ("LEGO Technic Bagger", "Kinderzimmer", "Modell 42121, ab 8 Jahre", 39.99, _date_ago(30), None),
        # Keller
        ("Bosch Akkuschrauber GSR 18V", "Keller", "2 Akkus, Koffer", 149.00, _date_ago(250), "BSH-GSR-2024"),
    ]

    for name, room, desc, value, purchase, serial in items:
        db.add(InventoryItem(
            user_id=max_id, name=name, room=room, description=desc,
            value=value, purchase_date=purchase, serial_number=serial,
        ))
    db.flush()
    logger.info("%d Inventar-Gegenstaende erstellt.", len(items))


def seed_tasks(db):
    """Erstellt Aufgaben: offene, erledigte, wiederkehrende."""
    tasks = [
        # Max – offene Aufgaben
        Task(user_key="demo_max", title="Nebenkostenabrechnung pruefen", priority="high",
             due_date=_dt_ago(-2), status="open"),
        Task(user_key="demo_max", title="Auto zur Inspektion bringen", priority="medium",
             due_date=_dt_ago(-7), status="open"),
        Task(user_key="demo_max", title="Geburtstag Oma – Geschenk besorgen", priority="high",
             due_date=_dt_ago(-14), status="open"),
        Task(user_key="demo_max", title="Steuererklärung 2025 vorbereiten", priority="low",
             due_date=_dt_ago(-60), status="open"),
        # Max – erledigte Aufgaben
        Task(user_key="demo_max", title="Waschmaschine entkalken", priority="low",
             status="done", last_completed_at=_dt_ago(5)),
        Task(user_key="demo_max", title="Muell rausbringen", priority="medium",
             status="done", recurrence="weekly", last_completed_at=_dt_ago(1)),
        # Lisa – offene Aufgaben
        Task(user_key="demo_lisa", title="Fotokurs Hausaufgabe abgeben", priority="high",
             due_date=_dt_ago(-3), status="open"),
        Task(user_key="demo_lisa", title="Kinderzimmer aufraumen", priority="medium",
             status="open"),
        # Lisa – erledigte
        Task(user_key="demo_lisa", title="Yoga-Matte bestellen", priority="low",
             status="done", last_completed_at=_dt_ago(10)),
        # Routinen (wiederkehrend)
        Task(user_key="demo_max", title="Wocheneinkauf planen", priority="medium",
             recurrence="weekly", status="open"),
        Task(user_key="demo_lisa", title="Blumen giessen", priority="low",
             recurrence="daily", status="open", last_completed_at=_dt_ago(1)),
    ]

    for t in tasks:
        db.add(t)
    db.flush()
    logger.info("%d Aufgaben erstellt.", len(tasks))


def seed_shopping(db):
    """Erstellt eine Einkaufsliste mit typischen Eintraegen."""
    items = [
        ("Milch", "1", "L", "Milchprodukte", False),
        ("Vollkornbrot", "1", "Stueck", "Backwaren", False),
        ("Bananen", "1", "Bund", "Obst", False),
        ("Tomaten", "500", "g", "Gemuese", False),
        ("Haehnchenbrust", "400", "g", "Fleisch", False),
        ("Olivenoel", "1", "Flasche", "Gewuerze", False),
        ("Joghurt Natur", "4", "Stueck", "Milchprodukte", True),  # schon abgehakt
        ("Eier", "10", "Stueck", "Basics", True),
        ("Spuelmittel", "1", "Flasche", "Haushalt", False),
        ("Aepfel", "1", "kg", "Obst", False),
    ]

    for name, qty, unit, category, checked in items:
        db.add(ShoppingItem(
            user_key="demo_max", name=name, quantity=qty, unit=unit,
            category=category, checked=checked, source="seed",
        ))
    db.flush()
    logger.info("%d Einkaufsliste-Eintraege erstellt.", len(items))


# ── Main ───────────────────────────────────────────────────────────────────

def run_seed():
    """Fuehrt das komplette Seeding durch."""
    init_db()

    with get_db()() as db:
        logger.info("=== Starte Demo-Seed ===")

        # 1. Alte Demo-Daten entfernen
        cleanup_demo_data(db)

        # 2. User erstellen
        user_ids = seed_users(db)

        # 3. Finanzdaten
        seed_transactions(db, user_ids)
        seed_contracts(db, user_ids)
        seed_invoices(db, user_ids)
        seed_budgets(db, user_ids)

        # 4. Dokumente
        seed_documents(db, user_ids)

        # 5. Inventar
        seed_inventory(db, user_ids)

        # 6. Aufgaben
        seed_tasks(db)

        # 7. Einkaufsliste
        seed_shopping(db)

        logger.info("=== Demo-Seed abgeschlossen ===")
        logger.info(
            "Erstellt: 3 User, 30 Transaktionen, 2 Vertraege, 4 Rechnungen, "
            "5 Budget-Kategorien, 4 Dokumente, 12 Inventar-Gegenstaende, "
            "11 Aufgaben, 10 Einkaufseintraege"
        )


if __name__ == "__main__":
    run_seed()
