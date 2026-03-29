"""
google_auth_local.py – Google Calendar OAuth lokal ausführen
=============================================================
Dieses Skript LOKAL auf deinem PC ausführen (nicht auf dem Server).
Erstellt Token-Dateien die dann per scp auf den Server hochgeladen werden.

Voraussetzungen:
  pip install google-auth-oauthlib google-api-python-client

Ausführen:
  python deploy/google_auth_local.py

Dann die generierten Token-Dateien hochladen:
  scp data/google_token_taake.json assistant@DEINE_IP:~/projekt-personal-assistent/data/
  scp data/google_token_nina.json   assistant@DEINE_IP:~/projekt-personal-assistent/data/
  scp config/google_credentials.json assistant@DEINE_IP:~/projekt-personal-assistent/config/
"""

import sys
from pathlib import Path

# Projektpfad
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "config" / "google_credentials.json"
DATA_DIR = PROJECT_ROOT / "data"

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def authenticate(token_filename: str, user_label: str):
    """Startet den OAuth-Flow für einen Benutzer und speichert das Token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Fehler: google-auth-oauthlib nicht installiert.")
        print("Bitte ausführen: pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    token_path = DATA_DIR / token_filename

    if token_path.exists():
        overwrite = input(f"Token für {user_label} existiert bereits. Überschreiben? (j/n): ")
        if overwrite.lower() != "j":
            print(f"Übersprungen: {user_label}")
            return

    if not CREDENTIALS_PATH.exists():
        print(f"\nFehler: {CREDENTIALS_PATH} nicht gefunden.")
        print("Bitte credentials.json aus der Google Cloud Console herunterladen:")
        print("  1. console.cloud.google.com")
        print("  2. APIs & Services → Credentials")
        print("  3. OAuth 2.0 Client IDs → Download JSON")
        print(f"  4. Speichern als: {CREDENTIALS_PATH}")
        sys.exit(1)

    print(f"\n>>> Authentifizierung für {user_label}...")
    print("Ein Browser-Fenster öffnet sich. Bitte mit dem richtigen Google-Account anmelden.")
    input("Drücke Enter zum Starten...")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w") as f:
        f.write(creds.to_json())

    print(f"✅ Token gespeichert: {token_path}")


def main():
    print("=" * 60)
    print("  Google Calendar OAuth – Token-Generator")
    print("=" * 60)
    print()
    print("Für jeden Bot-Benutzer wird ein eigener Google-Account")
    print("benötigt (oder derselbe Account kann für beide verwendet werden).")
    print()

    # Taake
    authenticate("google_token_taake.json", "Taake")

    print()
    use_same = input("Denselben Google-Account für Nina verwenden? (j/n): ")
    if use_same.lower() == "j":
        import shutil

        src = DATA_DIR / "google_token_taake.json"
        dst = DATA_DIR / "google_token_nina.json"
        shutil.copy(src, dst)
        print(f"✅ Token kopiert: {dst}")
    else:
        authenticate("google_token_nina.json", "Nina")

    print()
    print("=" * 60)
    print("  Fertig! Jetzt Tokens auf Server hochladen:")
    print()
    print("  scp data/google_token_taake.json \\")
    print("      assistant@DEINE_IP:~/projekt-personal-assistent/data/")
    print()
    print("  scp data/google_token_nina.json \\")
    print("      assistant@DEINE_IP:~/projekt-personal-assistent/data/")
    print()
    print("  scp config/google_credentials.json \\")
    print("      assistant@DEINE_IP:~/projekt-personal-assistent/config/")
    print("=" * 60)


if __name__ == "__main__":
    main()
