"""
Feature-Katalog: Alle verfügbaren Features mit Metadaten.
Jedes Feature hat eine ID, Emoji, Name, Beschreibung,
zugehörige Intents, Commands und optionale Konfigurationsvoraussetzungen.
"""

from dataclasses import dataclass


@dataclass
class Feature:
    id: str
    emoji: str
    name: str
    description: str
    intents: list[str]
    commands: list[str]
    required_settings: list[str]  # Settings-Keys die gesetzt sein müssen
    default_enabled: bool = True


# Vollständiger Feature-Katalog
CATALOG: list[Feature] = [
    Feature(
        id="core",
        emoji="🧠",
        name="KI-Chat",
        description="Freie Konversation, Gedächtnis und Persönlichkeit",
        intents=["chat"],
        commands=[],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="calendar",
        emoji="📅",
        name="Kalender",
        description="Termine lesen und erstellen (Google Calendar)",
        intents=["calendar_read", "calendar_create"],
        commands=["kalender", "neu_termin"],
        required_settings=["GOOGLE_CREDENTIALS_PATH"],
        default_enabled=True,
    ),
    Feature(
        id="tasks",
        emoji="✅",
        name="Aufgaben",
        description="Task-Management mit Prioritäten und Cross-Bot-Zuweisung",
        intents=["task_create", "task_read", "task_complete"],
        commands=["tasks", "done"],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="reminders",
        emoji="⏰",
        name="Erinnerungen",
        description="Zeitgesteuerte Erinnerungen und Alarme",
        intents=["reminder_create"],
        commands=["erinnerung", "erinnerungen"],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="shopping",
        emoji="🛒",
        name="Einkaufsliste",
        description="Liste mit automatischen Kategorien und Chefkoch-Integration",
        intents=["shopping_add", "shopping_view", "shopping_recipe"],
        commands=["einkaufsliste", "einkauf"],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="recipes",
        emoji="🍳",
        name="Rezepte",
        description="Chefkoch-Rezeptsuche – Zutaten direkt auf die Einkaufsliste",
        intents=["recipe_search"],
        commands=["rezept"],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="email",
        emoji="📧",
        name="E-Mail (Gmail)",
        description="Posteingang lesen, KI-Aktionen erkennen, Entwürfe erstellen",
        intents=["email_read", "email_compose"],
        commands=["email", "email_connect", "email_aktionen"],
        required_settings=["GOOGLE_CREDENTIALS_PATH"],
        default_enabled=True,
    ),
    Feature(
        id="drive",
        emoji="💾",
        name="Google Drive",
        description="Dateien hochladen und durchsuchen",
        intents=["drive"],
        commands=["drive"],
        required_settings=["GOOGLE_CREDENTIALS_PATH"],
        default_enabled=True,
    ),
    Feature(
        id="websearch",
        emoji="🔍",
        name="Web-Suche",
        description="Wetter, Nachrichten, Preise – automatisch gesucht",
        intents=["web_search"],
        commands=[],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="weather",
        emoji="🌤",
        name="Wetter",
        description="Wetterabfragen via Web-Suche",
        intents=["web_search"],
        commands=[],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="mobility",
        emoji="🚗",
        name="Fahrzeit",
        description="Route und Abfahrtszeit berechnen (OpenRouteService)",
        intents=["mobility"],
        commands=["fahrzeit"],
        required_settings=["OPENROUTE_API_KEY"],
        default_enabled=True,
    ),
    Feature(
        id="documents",
        emoji="📄",
        name="Dokument-Scanner",
        description="Foto → OCR → durchsuchbares PDF → Drive-Upload → KI-Analyse",
        intents=[],
        commands=["scan", "dokumente"],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="tables",
        emoji="📊",
        name="Tabellen & Präsentationen",
        description="Excel- und PowerPoint-Dateien per KI erstellen und senden",
        intents=["table_create", "presentation_create"],
        commands=["tabelle", "praesentation"],
        required_settings=[],
        default_enabled=True,
    ),
    Feature(
        id="spotify",
        emoji="🎵",
        name="Spotify",
        description="Musik per Sprache steuern (benötigt Spotify Premium)",
        intents=["spotify"],
        commands=["spotify"],
        required_settings=["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"],
        default_enabled=False,
    ),
    Feature(
        id="smarthome",
        emoji="🏠",
        name="Smart Home",
        description="Home Assistant steuern (Licht, Heizung, Rollos)",
        intents=["smarthome"],
        commands=["smarthome"],
        required_settings=["HA_URL", "HA_TOKEN"],
        default_enabled=False,
    ),
    Feature(
        id="tts",
        emoji="🔊",
        name="Sprachausgabe",
        description="Bot antwortet zusätzlich als Sprachnachricht (gTTS)",
        intents=[],
        commands=["tts"],
        required_settings=[],
        default_enabled=False,
    ),
    Feature(
        id="finance",
        emoji="💰",
        name="Finanzhub",
        description="Ausgaben, Verträge, Budgets und Rechnungen verwalten",
        intents=[],
        commands=[],
        required_settings=[],
        default_enabled=False,
    ),
    Feature(
        id="inventory",
        emoji="📦",
        name="Haushaltsordner",
        description="Inventar, Garantien und Dokumente organisieren",
        intents=[],
        commands=[],
        required_settings=[],
        default_enabled=False,
    ),
    Feature(
        id="family",
        emoji="👨‍👩‍👧‍👦",
        name="Familien-Modus",
        description="Gemeinsamer Workspace mit Aufgaben-Rotation",
        intents=[],
        commands=[],
        required_settings=[],
        default_enabled=False,
    ),
]

# Schnell-Lookup: feature_id → Feature
CATALOG_MAP: dict[str, Feature] = {f.id: f for f in CATALOG}

# Intent → Feature-IDs (ein Intent kann zu mehreren Features gehören)
INTENT_TO_FEATURES: dict[str, list[str]] = {}
for _feat in CATALOG:
    for _intent in _feat.intents:
        INTENT_TO_FEATURES.setdefault(_intent, []).append(_feat.id)
