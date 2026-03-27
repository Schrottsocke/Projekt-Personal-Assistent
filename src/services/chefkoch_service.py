"""
Chefkoch Service: Sucht Rezepte über die öffentliche Chefkoch.de API v2.
Kein API-Key erforderlich – immer verfügbar.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

CHEFKOCH_API_BASE = "https://api.chefkoch.de/v2"

# Schwierigkeitsgrade laut Chefkoch-API (int 1–4)
_DIFFICULTY_LABELS = {
    1: "Einfach",
    2: "Normal",
    3: "Anspruchsvoll",
    4: "Profi",
}

# Anfrage-Header, die einen normalen Browser imitieren
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class ChefkochService:
    """
    Async-Service für die Chefkoch.de Rezept-API v2.

    Kein API-Key erforderlich. Alle Methoden sind async und
    verwenden httpx für HTTP-Requests.
    """

    available = True  # Kein optionaler API-Key nötig

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    async def search_recipes(self, query: str, limit: int = 3) -> list[dict]:
        """
        Sucht Rezepte auf Chefkoch.de.

        Args:
            query: Suchbegriff (z.B. "Spaghetti Carbonara").
            limit: Maximale Anzahl an Ergebnissen (Standard: 3).

        Returns:
            Liste von Such-Ergebnis-Dicts. Jedes enthält einen ``item``-Key
            mit den eigentlichen Rezeptdaten. Bei Fehler leere Liste.
        """
        url = f"{CHEFKOCH_API_BASE}/search/recipes"
        params = {"query": query, "limit": limit, "offset": 0}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params, headers=_HEADERS)
                resp.raise_for_status()
                return resp.json().get("results", [])
        except httpx.HTTPStatusError as e:
            logger.error(
                "Chefkoch search HTTP-Fehler %s für '%s': %s",
                e.response.status_code,
                query,
                e,
            )
        except Exception as e:
            logger.error("Chefkoch search Fehler für '%s': %s", query, e)
        return []

    async def get_recipe(self, recipe_id: str) -> dict | None:
        """
        Ruft ein einzelnes Rezept anhand seiner ID ab.

        Args:
            recipe_id: Numerische Chefkoch-Rezept-ID.

        Returns:
            Rezept-Dict oder None bei Fehler.
        """
        url = f"{CHEFKOCH_API_BASE}/recipes/{recipe_id}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=_HEADERS)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Chefkoch get_recipe HTTP-Fehler %s für ID '%s': %s",
                e.response.status_code,
                recipe_id,
                e,
            )
        except Exception as e:
            logger.error("Chefkoch get_recipe Fehler für ID '%s': %s", recipe_id, e)
        return None

    def format_recipe_short(self, recipe: dict) -> str:
        """
        Formatiert einen Suchtreffer (``item``-Sub-Dict) als kurze
        Telegram-Nachricht im Markdown-Format.

        Args:
            recipe: Das ``item``-Objekt aus einem Such-Ergebnis-Dict.

        Returns:
            Formatierter Markdown-String.
        """
        title = recipe.get("title", "Unbekanntes Rezept")
        recipe_id = recipe.get("id", "")

        # Schwierigkeitsgrad
        difficulty_int = recipe.get("difficulty", 0)
        difficulty = _DIFFICULTY_LABELS.get(difficulty_int, "Unbekannt")

        # Bewertung als Sterne
        rating_value = recipe.get("rating", {}).get("rating", 0.0)
        stars = _rating_to_stars(rating_value)

        # Zeiten (Minuten)
        prep_time = recipe.get("preparationTime", 0) or 0
        cook_time = recipe.get("cookingTime", 0) or 0
        time_parts = []
        if prep_time:
            time_parts.append(f"Vorbereitung: {prep_time} Min.")
        if cook_time:
            time_parts.append(f"Kochen: {cook_time} Min.")
        time_str = " | ".join(time_parts) if time_parts else "Keine Zeitangabe"

        # Chefkoch-URL
        url = f"https://www.chefkoch.de/rezepte/{recipe_id}/"

        lines = [
            f"*{_escape_md(title)}*",
            f"Schwierigkeit: {difficulty}  |  Bewertung: {stars}",
            f"Zeit: {time_str}",
            f"[Zum Rezept]({url})",
        ]
        return "\n".join(lines)

    def format_recipe_full(self, recipe: dict) -> str:
        """
        Formatiert ein vollständiges Rezept (Rückgabe von ``get_recipe``)
        als ausführliche Telegram-Nachricht im Markdown-Format.

        Die Ausgabe wird auf ~4000 Zeichen begrenzt (Telegram-Limit).

        Args:
            recipe: Vollständiges Rezept-Dict von der API.

        Returns:
            Formatierter Markdown-String.
        """
        title = recipe.get("title", "Unbekanntes Rezept")
        subtitle = recipe.get("subtitle", "")
        recipe_id = recipe.get("id", "")
        servings = recipe.get("servings", 0)
        url = f"https://www.chefkoch.de/rezepte/{recipe_id}/"

        # Kopf
        lines = [f"*{_escape_md(title)}*"]
        if subtitle:
            lines.append(f"_{_escape_md(subtitle)}_")
        lines.append("")

        if servings:
            lines.append(f"Portionen: {servings}")
            lines.append("")

        # Zutaten
        ingredient_groups = recipe.get("ingredientGroups", [])
        all_ingredients: list[str] = []
        for group in ingredient_groups:
            group_name = group.get("name", "")
            if group_name:
                all_ingredients.append(f"*{_escape_md(group_name)}*")
            for ing in group.get("ingredients", []):
                amount = ing.get("amount", "")
                unit = ing.get("unit", "")
                name = ing.get("name", "")
                quantity = " ".join(filter(None, [str(amount) if amount else "", unit])).strip()
                ingredient_line = f"• {quantity} {name}".strip() if quantity else f"• {name}"
                all_ingredients.append(ingredient_line)

        if all_ingredients:
            lines.append("*Zutaten:*")
            lines.extend(all_ingredients)
            lines.append("")

        # Anleitung
        instructions = recipe.get("instructions", "") or ""
        if instructions:
            lines.append("*Zubereitung:*")
            if len(instructions) > 1500:
                instructions = instructions[:1497] + "..."
            lines.append(instructions)
            lines.append("")

        # Quelle
        lines.append(f"[Vollständiges Rezept auf Chefkoch]({url})")

        text = "\n".join(lines)

        # Auf 4000 Zeichen kürzen, falls nötig
        if len(text) > 4000:
            cutoff = text[:3990]
            # An einem Zeilenumbruch kürzen, um kein halbes Wort zu schneiden
            last_newline = cutoff.rfind("\n")
            if last_newline > 0:
                cutoff = cutoff[:last_newline]
            text = cutoff + f"\n\n[Vollständiges Rezept]({url})"

        return text

    async def search_and_format(self, query: str) -> str:
        """
        Sucht Rezepte und gibt eine fertig formatierte Telegram-Nachricht zurück.

        Args:
            query: Suchbegriff.

        Returns:
            Formatierter Markdown-String mit bis zu 3 Rezepten oder
            einer Hinweis-Nachricht bei keinem Ergebnis.
        """
        results = await self.search_recipes(query, limit=3)

        if not results:
            return (
                f"Keine Rezepte gefunden für: *{_escape_md(query)}*\n\n"
                "Tipps:\n"
                "• Andere Schreibweise versuchen\n"
                "• Weniger spezifische Begriffe nutzen\n"
                "• Direkt auf [chefkoch.de](https://www.chefkoch.de) suchen"
            )

        header = f"Rezepte für *{_escape_md(query)}*:\n\n"
        recipe_blocks: list[str] = []

        for result in results:
            item = result.get("item", {})
            if item:
                recipe_blocks.append(self.format_recipe_short(item))

        return header + "\n\n---\n\n".join(recipe_blocks)


# ------------------------------------------------------------------
# Hilfsfunktionen (modulprivat)
# ------------------------------------------------------------------


def _rating_to_stars(rating: float) -> str:
    """Wandelt einen Dezimalwert (0–5) in eine Sterne-Darstellung um."""
    if not rating:
        return "☆☆☆☆☆"
    full = int(round(rating))
    full = max(0, min(5, full))
    return "★" * full + "☆" * (5 - full)


def _escape_md(text: str) -> str:
    """
    Maskiert Sonderzeichen für Telegram MarkdownV1.
    (Betrifft vor allem * _ ` [)
    """
    if not text:
        return ""
    for char in ("*", "_", "`", "["):
        text = text.replace(char, f"\\{char}")
    return text
