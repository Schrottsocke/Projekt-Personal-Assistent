"""
SQLAlchemy Datenbankmodelle und Session-Management.
Speichert: Notizen, Erinnerungen, User-Profile, Konversations-History, Proposals.
"""

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import (
    create_engine,
    event,
    text as sa_text,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Date,
    Float,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), unique=True, nullable=False)
    is_onboarded = Column(Boolean, default=False)
    nickname = Column(String(100), nullable=True)
    communication_style = Column(String(50), default="casual")
    interests = Column(Text, nullable=True)
    chat_id = Column(String(50), nullable=True)  # Telegram Chat-ID für Proaktive Nachrichten
    # Trust-System: Komma-getrennte Proposal-Typen die auto-approved werden
    auto_approve_types = Column(Text, default="timer_create")
    # Persönlichkeitsprofil (Onboarding 2.0)
    work_start = Column(String(10), nullable=True)  # z.B. "09:00"
    work_end = Column(String(10), nullable=True)  # z.B. "18:00"
    quiet_start = Column(String(10), nullable=True)  # z.B. "22:00"
    quiet_end = Column(String(10), nullable=True)  # z.B. "07:00"
    focus_time = Column(String(20), nullable=True)  # "morgen" / "mittag" / "abend"
    week_structure = Column(Text, nullable=True)  # Freitext
    # Fokus-Modus: bis wann aktiv (None = kein Fokus-Modus)
    focus_mode_until = Column(DateTime, nullable=True)
    # TTS: Sprachantworten aktiviert (opt-in)
    tts_enabled = Column(Boolean, default=False)
    # Spotify: OAuth2-Token als JSON
    spotify_token_json = Column(Text, nullable=True)
    # Feature-Marketplace: aktivierte/deaktivierte Features als JSON {"calendar": true, ...}
    enabled_features = Column(Text, nullable=True)
    # User Preferences: JSON-Blob fuer Nav, Dashboard-Widgets, Appearance etc.
    preferences_json = Column(Text, nullable=True)
    # Password hash fuer Test-User mit Passwort-Auth (PBKDF2-SHA256)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    chat_id = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    remind_at = Column(DateTime, nullable=False)
    is_sent = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Proposal(Base):
    """
    Vorschlag zur manuellen Genehmigung (Human-in-the-Loop).
    Status: pending → approved/rejected
    """

    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True)
    proposal_type = Column(String(50), nullable=False)  # calendar_create, reminder_create, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False)  # JSON-kodierte Aktionsparameter
    user_key = Column(String(50), nullable=False)  # Für wen ist der Vorschlag
    created_by = Column(String(50), nullable=False)  # 'user', 'bot_taake', 'bot_nina', 'ai'
    status = Column(String(20), default="pending")  # pending, approved, rejected
    telegram_message_id = Column(String(50), nullable=True)  # Für späteres Editieren
    telegram_chat_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    decided_at = Column(DateTime, nullable=True)


class Task(Base):
    """Aufgaben/To-Do mit Status-Tracking und Cross-Bot-Zuweisung."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)  # Besitzer der Aufgabe
    assigned_by = Column(String(50), nullable=True)  # user_key des Zuweisers (cross-bot)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(10), default="medium")  # high / medium / low
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="open")  # open / in_progress / done
    recurrence = Column(String(20), nullable=True)  # daily / weekly / monthly / None
    last_completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class MemoryFact(Base):
    """
    Gespeicherte Fakten aus Gesprächen mit Bestätigungs-Tracking.
    Inspiriert vom JARVIS Continuous-Learning / Instinct-System.
    Fakten die öfter extrahiert oder bestätigt werden, bekommen höhere Konfidenz.
    """

    __tablename__ = "memory_facts"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    confirmation_count = Column(Integer, default=1)  # Wie oft wurde dieser Fakt extrahiert
    last_used = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' oder 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ShoppingItem(Base):
    """Einkaufsliste-Eintrag. Eine Liste pro User (kein separates Listen-Model)."""

    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    quantity = Column(String(50), nullable=True)  # z.B. "500", "2", "1 Bund"
    unit = Column(String(30), nullable=True)  # z.B. "g", "Stück", "ml"
    category = Column(String(50), nullable=True)  # z.B. "Gemüse", "Milchprodukte"
    checked = Column(Boolean, default=False)
    source = Column(String(100), nullable=True)  # z.B. "chefkoch:12345" oder "manual"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ScannedDocument(Base):
    """Gespeichertes Scan-Ergebnis für die /dokumente-Historie."""

    __tablename__ = "scanned_documents"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    doc_type = Column(String(100), nullable=False)  # Rechnung, Brief, etc.
    filename = Column(String(200), nullable=False)  # YYYY-MM-DD_Typ.pdf
    drive_link = Column(String(500), nullable=True)  # Drive webViewLink
    drive_file_id = Column(String(100), nullable=True)  # Drive File-ID
    summary = Column(Text, nullable=True)
    sender = Column(String(200), nullable=True)
    amount = Column(String(50), nullable=True)  # Betrag falls Rechnung
    ocr_text = Column(Text, nullable=True)  # Vollstaendiger OCR-Text
    category = Column(String(50), nullable=True)  # rechnung, vertrag, garantie, kassenbon, brief
    deadline = Column(Date, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    storage_location = Column(String(20), nullable=True)  # local, google_drive, server
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SavedRecipe(Base):
    """Gespeichertes / favorisiertes Rezept (aus Chefkoch-Suche)."""

    __tablename__ = "saved_recipes"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    chefkoch_id = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    image_url = Column(String(500), nullable=True)
    servings = Column(Integer, default=4)
    prep_time = Column(Integer, default=0)  # Minuten
    cook_time = Column(Integer, default=0)  # Minuten
    difficulty = Column(String(50), nullable=True)
    ingredients_json = Column(Text, nullable=True)  # JSON-Array
    is_favorite = Column(Boolean, default=False)
    source_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MealPlanEntry(Base):
    """Wochenplan-Eintrag: Rezept zu Tag + Mahlzeit."""

    __tablename__ = "meal_plan_entries"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    planned_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    recipe_chefkoch_id = Column(String(50), nullable=True)
    recipe_title = Column(String(300), nullable=False)
    recipe_image_url = Column(String(500), nullable=True)
    meal_type = Column(String(20), default="dinner")  # breakfast|lunch|dinner
    servings = Column(Integer, default=4)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class NotificationEvent(Base):
    """Benachrichtigungsereignis mit Kanal- und Referenz-Tracking.

    Ersetzt das alte Notification-Model. Enthaelt Rueckwaertskompatibilitaetsfelder
    (user_key, title, status, link) fuer bestehenden Code.
    """

    __tablename__ = "notification_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True)
    # Rueckwaertskompatibilitaet: user_key fuer bestehenden NotificationService
    user_key = Column(String(50), nullable=True)
    type = Column(String(30), nullable=False)  # reminder, follow_up, document, inbox, weather, system
    title = Column(String(300), nullable=True)
    reference_id = Column(Integer, nullable=True)
    reference_type = Column(String(50), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), default="new")  # new, read, completed, hidden
    link = Column(String(500), nullable=True)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    channel = Column(String(10), default="inapp")  # push, email, inapp
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


# Rueckwaertskompatibilitaet: Alias fuer bestehenden Code
Notification = NotificationEvent


class NotificationPreference(Base):
    """Benachrichtigungseinstellungen pro User und Kategorie."""

    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    category = Column(String(50), nullable=False)
    push_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    quiet_start = Column(String(5), default="22:00")  # HH:MM
    quiet_end = Column(String(5), default="07:00")  # HH:MM

    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_notification_pref_user_category"),)


class ShiftType(Base):
    """Diensttyp-Definition (z.B. Fruhdienst, Spaetdienst)."""

    __tablename__ = "shift_types"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    short_name = Column(String(10), nullable=False)
    color = Column(String(7), default="#7c4dff")
    start_time = Column(String(5), nullable=True)  # HH:MM
    end_time = Column(String(5), nullable=True)  # HH:MM
    break_minutes = Column(Integer, default=0)
    category = Column(String(20), default="work")  # work/free/vacation/special
    default_note = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ShiftEntry(Base):
    """Diensteintrag: Zuweisung eines Diensttyps zu einem Datum mit Soll/Ist-Tracking."""

    __tablename__ = "shift_entries"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    shift_type_id = Column(Integer, nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Soll-Zeiten (Override von ShiftType-Defaults, nullable)
    planned_start = Column(String(5), nullable=True)  # HH:MM
    planned_end = Column(String(5), nullable=True)  # HH:MM
    break_minutes = Column(Integer, nullable=True)  # Override ShiftType-Default

    # Ist-Zeiten
    actual_start = Column(String(5), nullable=True)  # HH:MM
    actual_end = Column(String(5), nullable=True)  # HH:MM
    actual_break_minutes = Column(Integer, nullable=True)

    # Berechnete Dauern (auf Write berechnet)
    planned_duration_minutes = Column(Integer, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)
    delta_minutes = Column(Integer, nullable=True)  # actual - planned

    # Bestaetigungsstatus
    confirmation_status = Column(String(20), default="pending")  # pending/confirmed/deviation/cancelled
    confirmation_source = Column(String(20), nullable=True)  # bot/manual/web/auto
    confirmation_timestamp = Column(DateTime, nullable=True)
    deviation_note = Column(String(500), nullable=True)

    # Reminder-Tracking
    reminder_sent = Column(Boolean, default=False)
    reminder_count = Column(Integer, default=0)
    next_reminder_at = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Produktlinien-Models: Finance, Inventory, Family
# ---------------------------------------------------------------------------


class Transaction(Base):
    """Finanztransaktion (Import, manuell oder Scan)."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="EUR")
    category = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    source = Column(String(10), default="manual")  # csv, manual, scan
    raw_text = Column(Text, nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Budget(Base):
    """Monatsbudget pro Kategorie."""

    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    category = Column(String(50), nullable=False)
    monthly_limit = Column(Float, nullable=False)
    alert_threshold = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Contract(Base):
    """Laufender Vertrag mit Kuendigungsfrist-Tracking."""

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    provider = Column(String(200), nullable=True)
    category = Column(String(50), nullable=True)
    amount = Column(Float, nullable=False)
    interval = Column(String(20), default="monthly")  # monthly, yearly, quarterly
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    cancellation_days = Column(Integer, nullable=True)
    cancellation_deadline = Column(Date, nullable=True)
    next_billing = Column(Date, nullable=True)
    status = Column(String(20), default="active", index=True)  # active, cancelled, expired
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))


class FinanceInvoice(Base):
    """Privatkunden-Rechnung (nicht zu verwechseln mit Kleinunternehmer-Rechnungen)."""

    __tablename__ = "finance_invoices"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=True)
    recipient = Column(String(200), nullable=False)
    recipient_address = Column(Text, nullable=True)
    issue_date = Column(Date, nullable=True)
    total = Column(Float, nullable=False)
    tax_rate = Column(Float, nullable=True)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), default="open", index=True)  # open, paid, overdue
    payment_date = Column(Date, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))


class InvoiceItem(Base):
    """Position einer Privatkunden-Rechnung."""

    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("finance_invoices.id"), nullable=False, index=True)
    description = Column(String(300), nullable=False)
    quantity = Column(Float, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)


class HouseholdDocument(Base):
    """Haushalts-Dokument (Rechnung, Garantie, Versicherung, Beleg)."""

    __tablename__ = "household_documents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    category = Column(String(50), nullable=True)  # invoice, warranty, insurance, receipt, other
    file_path = Column(String(500), nullable=True)
    ocr_text = Column(Text, nullable=True)
    deadline_date = Column(Date, nullable=True)
    issuer = Column(String(200), nullable=True)
    amount = Column(Float, nullable=True)
    linked_inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))


class BudgetCategory(Base):
    """Budget-Kategorie mit monatlichem Limit."""

    __tablename__ = "budget_categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    monthly_limit = Column(Float, nullable=False)
    color = Column(String(20), nullable=True)
    icon = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class HouseholdWorkspace(Base):
    """Haushalt / geteilter Workspace fuer Family-Features."""

    __tablename__ = "household_workspaces"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class WorkspaceMember(Base):
    """Mitgliedschaft in einem Workspace mit Rollenmodell."""

    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("household_workspaces.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    role = Column(String(20), default="viewer")  # admin, editor, viewer
    invited_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    accepted_at = Column(DateTime, nullable=True)


class Routine(Base):
    """Wiederkehrende Aufgabe im Haushalt."""

    __tablename__ = "routines"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("household_workspaces.id"), nullable=False)
    name = Column(String(200), nullable=False)
    interval = Column(String(20), default="weekly")  # daily, weekly, monthly
    assignee_strategy = Column(String(20), default="fixed")  # fixed, rotation
    current_assignee_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RoutineCompletion(Base):
    """Erledigungsnachweis fuer eine Routine."""

    __tablename__ = "routine_completions"

    id = Column(Integer, primary_key=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=False)
    completed_by = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    photo_url = Column(String(500), nullable=True)


class InventoryItem(Base):
    """Gegenstand im Haushaltsinventar."""

    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("household_workspaces.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    room = Column(String(100), nullable=True)
    box_label = Column(String(100), nullable=True)
    photo_url = Column(String(500), nullable=True)
    value = Column(Float, nullable=True)
    purchase_date = Column(Date, nullable=True)
    receipt_doc_id = Column(Integer, ForeignKey("scanned_documents.id"), nullable=True)
    serial_number = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))


class TestUserInvitation(Base):
    """Einladung fuer Testuser mit sicherem Token-Hash."""

    __tablename__ = "test_user_invitations"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    email = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    note = Column(String, nullable=True)
    token_hash = Column(String, nullable=False, unique=True)
    invited_by_user_id = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, accepted, expired, revoked
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Warranty(Base):
    """Garantie-Eintrag mit Ablauf-Tracking."""

    __tablename__ = "warranties"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    purchase_date = Column(Date, nullable=True)
    warranty_end = Column(Date, nullable=True)
    vendor = Column(String(200), nullable=True)
    receipt_doc_id = Column(Integer, ForeignKey("scanned_documents.id"), nullable=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Engine & Session Setup
_engine = None
_SessionLocal = None
_init_lock = threading.Lock()


def _set_sqlite_pragmas(dbapi_conn, connection_record):
    """SQLite-Pragmas bei jeder neuen Connection setzen."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def init_db():
    global _engine, _SessionLocal

    # Guard: idempotent – bei bereits initialisierter DB nichts tun
    if _engine is not None:
        return

    with _init_lock:
        # Double-check nach Lock-Erwerb
        if _engine is not None:
            return

        is_sqlite = "sqlite" in settings.DATABASE_URL

        connect_args = {"check_same_thread": False} if is_sqlite else {}
        pool_kwargs = {}
        if is_sqlite:
            # StaticPool ist für SQLite-Threads nicht geeignet;
            # stattdessen QueuePool mit sinnvollen Limits
            pool_kwargs = {"pool_size": 5, "max_overflow": 10, "pool_pre_ping": True}

        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            **pool_kwargs,
        )

        # WAL-Modus und busy_timeout für jede SQLite-Connection
        if is_sqlite:
            event.listen(_engine, "connect", _set_sqlite_pragmas)

        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, expire_on_commit=False)

        # Tabellen erstellen
        Base.metadata.create_all(bind=_engine)

        # Migrations: neue Spalten zu bestehenden Tabellen hinzufügen (SQLite)
        if is_sqlite:
            with _engine.connect() as conn:
                from sqlalchemy.exc import OperationalError

                for col_sql in [
                    "ALTER TABLE user_profiles ADD COLUMN focus_mode_until DATETIME",
                    "ALTER TABLE user_profiles ADD COLUMN tts_enabled BOOLEAN DEFAULT 0",
                    "ALTER TABLE user_profiles ADD COLUMN spotify_token_json TEXT",
                    "ALTER TABLE user_profiles ADD COLUMN enabled_features TEXT",
                    "ALTER TABLE user_profiles ADD COLUMN preferences_json TEXT",
                    "ALTER TABLE tasks ADD COLUMN recurrence VARCHAR(20)",
                    "ALTER TABLE tasks ADD COLUMN last_completed_at DATETIME",
                    "ALTER TABLE scanned_documents ADD COLUMN ocr_text TEXT",
                    # Shift-Tracking: Soll/Ist-Zeiten + Bestaetigungsstatus
                    "ALTER TABLE shift_entries ADD COLUMN planned_start VARCHAR(5)",
                    "ALTER TABLE shift_entries ADD COLUMN planned_end VARCHAR(5)",
                    "ALTER TABLE shift_entries ADD COLUMN break_minutes INTEGER",
                    "ALTER TABLE shift_entries ADD COLUMN actual_start VARCHAR(5)",
                    "ALTER TABLE shift_entries ADD COLUMN actual_end VARCHAR(5)",
                    "ALTER TABLE shift_entries ADD COLUMN actual_break_minutes INTEGER",
                    "ALTER TABLE shift_entries ADD COLUMN planned_duration_minutes INTEGER",
                    "ALTER TABLE shift_entries ADD COLUMN actual_duration_minutes INTEGER",
                    "ALTER TABLE shift_entries ADD COLUMN delta_minutes INTEGER",
                    "ALTER TABLE shift_entries ADD COLUMN confirmation_status VARCHAR(20) DEFAULT 'pending'",
                    "ALTER TABLE shift_entries ADD COLUMN confirmation_source VARCHAR(20)",
                    "ALTER TABLE shift_entries ADD COLUMN confirmation_timestamp DATETIME",
                    "ALTER TABLE shift_entries ADD COLUMN deviation_note VARCHAR(500)",
                    "ALTER TABLE shift_entries ADD COLUMN reminder_sent BOOLEAN DEFAULT 0",
                    "ALTER TABLE shift_entries ADD COLUMN reminder_count INTEGER DEFAULT 0",
                    "ALTER TABLE shift_entries ADD COLUMN next_reminder_at DATETIME",
                    # Auth: Passwort-Hash fuer DB-Login
                    "ALTER TABLE user_profiles ADD COLUMN password_hash VARCHAR",
                    # ScannedDocument: Produktlinien-Erweiterung
                    "ALTER TABLE scanned_documents ADD COLUMN category VARCHAR(50)",
                    "ALTER TABLE scanned_documents ADD COLUMN deadline DATE",
                    "ALTER TABLE scanned_documents ADD COLUMN ocr_confidence FLOAT",
                    "ALTER TABLE scanned_documents ADD COLUMN storage_location VARCHAR(20)",
                ]:
                    try:
                        conn.execute(sa_text(col_sql))
                        conn.commit()
                    except OperationalError as e:
                        if "duplicate column name" in str(e).lower():
                            logger.debug("Migration übersprungen (Spalte existiert bereits): %s", e)
                        else:
                            logger.warning("Migration fehlgeschlagen: %s", e)
                            raise

        # Data-Fix: Chefkoch-Bild-URLs reparieren (crop-Prefix + Proxy-Umstellung)
        with _engine.connect() as conn:
            for fix_sql in [
                "UPDATE saved_recipes SET image_url = REPLACE(image_url, '/400x300/', '/crop-400x300/') WHERE image_url LIKE '%/400x300/%' AND image_url NOT LIKE '%/crop-400x300/%'",
                "UPDATE meal_plan_entries SET recipe_image_url = REPLACE(recipe_image_url, '/400x300/', '/crop-400x300/') WHERE recipe_image_url LIKE '%/400x300/%' AND recipe_image_url NOT LIKE '%/crop-400x300/%'",
                "UPDATE saved_recipes SET image_url = REPLACE(image_url, 'https://img.chefkoch-cdn.de', '/recipes/img-proxy') WHERE image_url LIKE 'https://img.chefkoch-cdn.de%'",
                "UPDATE meal_plan_entries SET recipe_image_url = REPLACE(recipe_image_url, 'https://img.chefkoch-cdn.de', '/recipes/img-proxy') WHERE recipe_image_url LIKE 'https://img.chefkoch-cdn.de%'",
            ]:
                result = conn.execute(sa_text(fix_sql))
                if result.rowcount:
                    logger.info("Bild-URL-Fix: %d Zeilen aktualisiert (%s)", result.rowcount, fix_sql.split()[1])
            conn.commit()

        logger.info(f"Datenbank initialisiert: {settings.DATABASE_URL}")


def prune_conversation_history(days: int = 30) -> int:
    """Löscht Conversation-History-Einträge älter als 'days' Tage.
    Returns: Anzahl gelöschter Zeilen."""

    if _engine is None:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with _engine.connect() as conn:
        result = conn.execute(
            sa_text("DELETE FROM conversation_history WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        conn.commit()
        return result.rowcount


def get_db():
    """Gibt einen Session-Factory-Context-Manager zurück."""
    if _SessionLocal is None:
        init_db()
    if _SessionLocal is None:
        raise RuntimeError("Datenbank konnte nicht initialisiert werden. Prüfe DATABASE_URL in der Konfiguration.")
    return _session_context


@contextmanager
def _session_context():
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
