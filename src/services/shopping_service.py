"""
Shopping Service: Einkaufsliste-Verwaltung.
Eine Liste pro User, optional geteilt mit Partner.
Integriert mit ChefkochService: Rezept-Zutaten direkt auf die Liste übernehmen.
"""

import logging
from collections import defaultdict

from src.services.database import ShoppingItem, get_db

logger = logging.getLogger(__name__)

# Keyword-basierte Kategorie-Zuordnung (lowercase)
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Obst": [
        "apfel",
        "birne",
        "banane",
        "orange",
        "zitrone",
        "limette",
        "erdbeere",
        "himbeere",
        "blaubeere",
        "traube",
        "kirsche",
        "pfirsich",
        "mango",
        "ananas",
        "melone",
        "kiwi",
        "pflaume",
        "weintraube",
        "mandarine",
    ],
    "Gemüse": [
        "tomate",
        "gurke",
        "paprika",
        "zwiebel",
        "knoblauch",
        "karotte",
        "möhre",
        "zucchini",
        "brokkoli",
        "blumenkohl",
        "spinat",
        "salat",
        "kopfsalat",
        "rucola",
        "lauch",
        "sellerie",
        "kürbis",
        "aubergine",
        "erbsen",
        "bohnen",
        "mais",
        "pilze",
        "champignon",
        "kartoffel",
        "süßkartoffel",
        "fenchel",
        "kohlrabi",
        "rote bete",
        "radieschen",
    ],
    "Milchprodukte": [
        "milch",
        "butter",
        "joghurt",
        "käse",
        "quark",
        "sahne",
        "schmand",
        "frischkäse",
        "mozzarella",
        "parmesan",
        "gouda",
        "emmentaler",
        "brie",
        "feta",
        "ricotta",
        "crème fraîche",
        "buttermilch",
        "kefir",
        "skyr",
    ],
    "Fleisch & Fisch": [
        "hähnchen",
        "hühnchen",
        "rind",
        "schwein",
        "lamm",
        "kalb",
        "hackfleisch",
        "steak",
        "schnitzel",
        "wurst",
        "speck",
        "schinken",
        "lachs",
        "thunfisch",
        "garnelen",
        "shrimps",
        "fisch",
        "forelle",
        "zander",
        "kabeljau",
        "dorade",
    ],
    "Brot & Backwaren": [
        "brot",
        "brötchen",
        "toast",
        "baguette",
        "croissant",
        "laugenbrezel",
        "knäckebrot",
        "mehl",
        "hefe",
        "backpulver",
    ],
    "Getränke": [
        "wasser",
        "saft",
        "cola",
        "bier",
        "wein",
        "kaffee",
        "tee",
        "limo",
        "limonade",
        "mineralwasser",
        "orangensaft",
        "apfelsaft",
        "smoothie",
        "milchmix",
    ],
    "Gewürze & Öle": [
        "salz",
        "pfeffer",
        "öl",
        "olivenöl",
        "essig",
        "senf",
        "ketchup",
        "mayo",
        "mayonnaise",
        "sojasoße",
        "zucker",
        "honig",
        "zimt",
        "paprikapulver",
        "curry",
        "chili",
        "thymian",
        "rosmarin",
        "basilikum",
        "oregano",
        "petersilie",
        "schnittlauch",
        "lorbeer",
        "muskat",
        "vanille",
    ],
    "Tiefkühl": ["tiefkühl", "tk-", "gefroren", "frozen", "eis", "eiscreme"],
    "Konserven & Trockenware": [
        "dose",
        "konserve",
        "nudeln",
        "pasta",
        "spaghetti",
        "penne",
        "reis",
        "linsen",
        "kichererbsen",
        "bohnen",
        "tomatenmark",
        "passierte tomaten",
        "kokosmilch",
        "müsli",
        "haferflocken",
        "cornflakes",
    ],
    "Haushalt": [
        "küchenrolle",
        "toilettenpapier",
        "spülmittel",
        "waschmittel",
        "reiniger",
        "müllbeutel",
        "folie",
        "backpapier",
        "schwamm",
    ],
}


def _categorize(name: str) -> str:
    """Bestimmt die Kategorie eines Einkaufsartikels anhand von Keywords."""
    name_lower = name.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return category
    return "Sonstiges"


_UNIT_ALIASES: dict[str, str] = {
    "gramm": "g",
    "kilogramm": "kg",
    "milliliter": "ml",
    "liter": "l",
    "stueck": "stk",
    "stück": "stk",
    "stk.": "stk",
    "packung": "pkg",
    "pkg.": "pkg",
    "bund": "bund",
    "dose": "dose",
    "dosen": "dose",
    "el": "el",
    "tl": "tl",
    "esslöffel": "el",
    "teelöffel": "tl",
    "essl.": "el",
    "teel.": "tl",
    "prise": "prise",
    "prisen": "prise",
}


def _normalize_unit(unit: str | None) -> str:
    """Normalisiert Einheiten für Duplikaterkennung."""
    if not unit:
        return ""
    u = unit.strip().lower()
    return _UNIT_ALIASES.get(u, u)


class ShoppingService:
    """
    Verwaltet die Einkaufsliste pro User.
    Eine Liste pro User — Items werden direkt mit user_key gespeichert.
    """

    async def add_item(
        self,
        user_key: str,
        name: str,
        quantity: str | None = None,
        unit: str | None = None,
        category: str | None = None,
        source: str | None = None,
    ) -> dict:
        """Fügt einen einzelnen Artikel zur Einkaufsliste hinzu."""
        if not category:
            category = _categorize(name)

        with get_db()() as session:
            item = ShoppingItem(
                user_key=user_key,
                name=name.strip(),
                quantity=quantity,
                unit=unit,
                category=category,
                source=source or "manual",
            )
            session.add(item)
            session.flush()
            result = {
                "id": item.id,
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "category": item.category,
                "checked": item.checked,
                "source": item.source,
                "created_at": item.created_at,
            }
        logger.debug(f"[{user_key}] Einkaufsartikel hinzugefügt: {name}")
        return result

    async def add_items_bulk(self, user_key: str, items: list[dict]) -> dict:
        """
        Fügt mehrere Artikel auf einmal hinzu. Erkennt Duplikate und
        addiert Mengen bei gleichem Namen und kompatibler Einheit.

        Args:
            items: Liste von Dicts mit keys: name, quantity (opt), unit (opt), source (opt)

        Returns:
            Dict mit ``added`` (neue Artikel) und ``merged`` (zusammengefuehrte).
        """
        added = 0
        merged = 0
        with get_db()() as session:
            # Bestehende unchecked Items laden fuer Duplikaterkennung
            existing = session.query(ShoppingItem).filter_by(user_key=user_key, checked=False).all()
            lookup: dict[tuple[str, str], ShoppingItem] = {}
            for ex in existing:
                key = (ex.name.lower().strip(), _normalize_unit(ex.unit))
                lookup[key] = ex

            for item_data in items:
                name = item_data.get("name", "").strip()
                if not name:
                    continue
                unit_raw = item_data.get("unit")
                norm_unit = _normalize_unit(unit_raw)
                key = (name.lower(), norm_unit)

                if key in lookup:
                    # Mengen numerisch addieren
                    ex_item = lookup[key]
                    new_qty = item_data.get("quantity")
                    if ex_item.quantity and new_qty:
                        try:
                            total = float(ex_item.quantity) + float(new_qty)
                            ex_item.quantity = str(int(total) if total == int(total) else round(total, 2))
                            merged += 1
                            continue
                        except (ValueError, TypeError):
                            pass  # Nicht-numerisch → neuen Eintrag anlegen

                category = item_data.get("category") or _categorize(name)
                item = ShoppingItem(
                    user_key=user_key,
                    name=name,
                    quantity=item_data.get("quantity"),
                    unit=unit_raw,
                    category=category,
                    source=item_data.get("source", "manual"),
                )
                session.add(item)
                # Neuen Eintrag auch im Lookup registrieren
                lookup[key] = item
                added += 1
        logger.info(f"[{user_key}] Einkauf bulk: {added} neu, {merged} zusammengefuehrt")
        return {"added": added, "merged": merged}

    async def add_items_from_recipe(self, user_key: str, recipe: dict, servings: int | None = None) -> dict:
        """
        Extrahiert Zutaten aus einem Chefkoch-Rezept und fügt sie zur Liste hinzu.

        Args:
            recipe: Vollständiges Rezept-Dict von ChefkochService.get_recipe()
            servings: Gewünschte Portionen. Mengen werden skaliert, wenn das
                      Rezept eine Original-Portionszahl enthält.

        Returns:
            Dict mit ``added`` und ``merged`` Counts.
        """
        recipe_id = recipe.get("id", "")
        source = f"chefkoch:{recipe_id}" if recipe_id else "chefkoch"

        # Skalierungsfaktor berechnen
        original_servings = recipe.get("servings")
        scale: float = 1.0
        if servings and original_servings:
            try:
                scale = servings / float(original_servings)
            except (ValueError, ZeroDivisionError):
                scale = 1.0

        items = []

        for group in recipe.get("ingredientGroups", []):
            for ing in group.get("ingredients", []):
                name = ing.get("name", "").strip()
                if not name:
                    continue
                amount = ing.get("amount", "")
                unit = ing.get("unit", "")

                # Menge skalieren wenn möglich
                scaled_amount = amount
                if amount and scale != 1.0:
                    try:
                        scaled_amount = round(float(amount) * scale, 2)
                        # Ganzzahlen ohne Dezimalstelle darstellen
                        if scaled_amount == int(scaled_amount):
                            scaled_amount = int(scaled_amount)
                    except (ValueError, TypeError):
                        scaled_amount = amount

                items.append(
                    {
                        "name": name,
                        "quantity": str(scaled_amount) if scaled_amount else None,
                        "unit": unit or None,
                        "source": source,
                    }
                )

        return await self.add_items_bulk(user_key, items)

    async def remove_item(self, user_key: str, item_id: int) -> bool:
        """Entfernt einen Artikel von der Einkaufsliste."""
        with get_db()() as session:
            item = session.query(ShoppingItem).filter_by(id=item_id, user_key=user_key).first()
            if not item:
                return False
            session.delete(item)
        return True

    async def check_item(self, user_key: str, item_id: int) -> bool:
        """Markiert einen Artikel als erledigt (oder hebt die Markierung auf)."""
        with get_db()() as session:
            item = session.query(ShoppingItem).filter_by(id=item_id, user_key=user_key).first()
            if not item:
                return False
            item.checked = not item.checked
        return True

    async def get_items(self, user_key: str, include_checked: bool = False) -> list[dict]:
        """
        Gibt alle Einkaufsartikel des Users zurück.

        Returns:
            Liste von Dicts mit id, name, quantity, unit, category, checked.
        """
        with get_db()() as session:
            query = session.query(ShoppingItem).filter_by(user_key=user_key)
            if not include_checked:
                query = query.filter_by(checked=False)
            items = query.order_by(ShoppingItem.category, ShoppingItem.name).all()
            return [
                {
                    "id": i.id,
                    "name": i.name,
                    "quantity": i.quantity,
                    "unit": i.unit,
                    "category": i.category,
                    "checked": i.checked,
                    "source": i.source,
                    "created_at": i.created_at,
                }
                for i in items
            ]

    async def clear_checked(self, user_key: str) -> int:
        """Löscht alle abgehakten Artikel. Gibt Anzahl der gelöschten Items zurück."""
        count = 0
        with get_db()() as session:
            items = session.query(ShoppingItem).filter_by(user_key=user_key, checked=True).all()
            count = len(items)
            for item in items:
                session.delete(item)
        logger.info(f"[{user_key}] {count} erledigte Einkaufsartikel gelöscht")
        return count

    async def clear_all(self, user_key: str) -> int:
        """Löscht die gesamte Einkaufsliste. Gibt Anzahl der gelöschten Items zurück."""
        count = 0
        with get_db()() as session:
            items = session.query(ShoppingItem).filter_by(user_key=user_key).all()
            count = len(items)
            for item in items:
                session.delete(item)
        logger.info(f"[{user_key}] Einkaufsliste geleert ({count} Artikel)")
        return count

    @staticmethod
    def format_list(items: list[dict]) -> str:
        """
        Formatiert die Einkaufsliste als Telegram-Markdown, gruppiert nach Kategorie.
        Erledigte Artikel werden durchgestrichen (via ~text~) angezeigt, falls include_checked.
        """
        if not items:
            return "🛒 Deine Einkaufsliste ist leer."

        # Gruppieren nach Kategorie
        by_category: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            by_category[item["category"]].append(item)

        lines = ["🛒 *Einkaufsliste*\n"]
        for category in sorted(by_category.keys()):
            lines.append(f"*{category}*")
            for item in by_category[category]:
                qty_parts = [p for p in [item.get("quantity"), item.get("unit")] if p]
                qty_str = " ".join(qty_parts)
                label = f"{qty_str} {item['name']}".strip() if qty_str else item["name"]
                checkbox = "✅" if item.get("checked") else "⬜"
                lines.append(f"  {checkbox} {label}")
            lines.append("")

        total = len(items)
        checked = sum(1 for i in items if i.get("checked"))
        lines.append(f"_({checked}/{total} erledigt)_")
        return "\n".join(lines)
