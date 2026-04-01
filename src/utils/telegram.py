"""Telegram-Hilfsfunktionen: Markdown-Escaping und Nachrichtenaufteilung."""

# Telegram-Nachrichtenlimit (Zeichen)
MAX_MESSAGE_LENGTH = 4096


def escape_md(text: str) -> str:
    """Maskiert Sonderzeichen fuer Telegram MarkdownV1 (* _ ` [)."""
    if not text:
        return ""
    for char in ("*", "_", "`", "["):
        text = text.replace(char, f"\\{char}")
    return text


def split_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Teilt einen langen Text in Telegram-kompatible Chunks.

    Versucht an Zeilenumbruechen zu trennen, faellt auf harte Trennung zurueck.
    """
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Letzten Zeilenumbruch vor dem Limit finden
        split_pos = text.rfind("\n", 0, limit)
        if split_pos == -1 or split_pos == 0:
            # Kein Zeilenumbruch → am Leerzeichen trennen
            split_pos = text.rfind(" ", 0, limit)
        if split_pos == -1 or split_pos == 0:
            # Notfall: hart am Limit trennen
            split_pos = limit
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")
    return chunks
