"""
Smart Home Integration via Home Assistant REST API.
Benötigt: HA_URL + HA_TOKEN in .env

Unterstützte Domains: light, switch, media_player, cover, climate, script, scene

Natürliche Sprache → HA-Service-Call:
  "Schalte das Licht aus"       → light.turn_off
  "Mach Licht im Wohnzimmer an" → light.turn_on (entity_id erkennen)
  "Heizung auf 22 Grad"         → climate.set_temperature
"""

import logging
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


class SmartHomeService:
    """
    Steuert Home Assistant Geräte über die REST API.
    Alle Methoden sind optional – wenn HA_URL/HA_TOKEN fehlen, bleibt der Service inaktiv.
    """

    def __init__(self):
        self._available = False
        self._base_url = ""
        self._headers = {}
        self._check_availability()

    def _check_availability(self):
        if not settings.HA_URL or not settings.HA_TOKEN:
            logger.info("SmartHomeService: HA_URL/HA_TOKEN nicht konfiguriert – deaktiviert.")
            return
        self._base_url = settings.HA_URL.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.HA_TOKEN}",
            "Content-Type": "application/json",
        }
        self._available = True
        logger.info(f"SmartHomeService: Home Assistant konfiguriert ({self._base_url}).")

    @property
    def available(self) -> bool:
        return self._available

    async def get_states(self, domain: str = "") -> list[dict]:
        """Gibt alle Entities (optional gefiltert nach Domain) zurück."""
        if not self._available:
            return []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/api/states",
                    headers=self._headers,
                )
                resp.raise_for_status()
                states = resp.json()
                if domain:
                    states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]
                return states
        except Exception as e:
            logger.error(f"HA-States-Fehler: {e}")
            return []

    async def call_service(
        self, domain: str, service: str, entity_id: str = "", extra: dict = None
    ) -> bool:
        """
        Ruft einen HA-Service auf.
        Beispiel: domain="light", service="turn_on", entity_id="light.wohnzimmer"
        """
        if not self._available:
            return False
        payload = {}
        if entity_id:
            payload["entity_id"] = entity_id
        if extra:
            payload.update(extra)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._base_url}/api/services/{domain}/{service}",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
                logger.info(f"HA-Service: {domain}.{service}({entity_id})")
                return True
        except Exception as e:
            logger.error(f"HA-Service-Fehler ({domain}.{service}): {e}")
            return False

    async def get_status_summary(self) -> str:
        """Gibt einen Überblick über den aktuellen Status zurück (für /smarthome)."""
        if not self._available:
            return "❌ Smart Home nicht konfiguriert. Bitte HA_URL und HA_TOKEN in .env setzen."

        try:
            states = await self.get_states()
            if not states:
                return "🏠 Home Assistant erreichbar, aber keine Entities gefunden."

            # Interessante Entities filtern
            lights_on = [s for s in states if s["entity_id"].startswith("light.") and s["state"] == "on"]
            switches_on = [s for s in states if s["entity_id"].startswith("switch.") and s["state"] == "on"]
            covers = [s for s in states if s["entity_id"].startswith("cover.")]
            climate = [s for s in states if s["entity_id"].startswith("climate.")]

            lines = ["🏠 *Smart Home Status*\n"]

            if lights_on:
                names = [s.get("attributes", {}).get("friendly_name", s["entity_id"]) for s in lights_on[:5]]
                lines.append(f"💡 Lichter an: {', '.join(names)}")
            else:
                lines.append("💡 Alle Lichter aus")

            if switches_on:
                names = [s.get("attributes", {}).get("friendly_name", s["entity_id"]) for s in switches_on[:3]]
                lines.append(f"🔌 Aktive Schalter: {', '.join(names)}")

            for c in climate[:2]:
                attrs = c.get("attributes", {})
                temp = attrs.get("current_temperature", "?")
                target = attrs.get("temperature", "?")
                name = attrs.get("friendly_name", c["entity_id"])
                lines.append(f"🌡️ {name}: {temp}°C (Ziel: {target}°C)")

            lines.append(f"\n_Gesamt: {len(states)} Entities_")
            return "\n".join(lines)

        except Exception as e:
            return f"❌ HA-Fehler: {e}"

    async def execute_command(self, command: str, entity_hint: str = "") -> str:
        """
        Führt einen natürlichsprachigen Befehl aus.
        command: z.B. "Licht an", "Heizung auf 22", "Rollos schließen"
        entity_hint: Raumname/Entity-Name zur Eingrenzung
        Returns: Statusmeldung
        """
        if not self._available:
            return "❌ Smart Home nicht konfiguriert."

        cmd = command.lower()

        # Licht
        if any(w in cmd for w in ["licht", "lampe", "beleuchtung"]):
            if any(w in cmd for w in ["aus", "off", "ausschalten", "deaktivieren"]):
                entity = self._find_entity_id("light", entity_hint)
                ok = await self.call_service("light", "turn_off", entity)
                return f"💡 Licht{'(e)' if not entity_hint else f' ({entity_hint})'} {'ausgeschaltet ✅' if ok else 'Fehler ❌'}"
            else:
                entity = self._find_entity_id("light", entity_hint)
                extra = {}
                # Helligkeit erkennen
                import re
                m = re.search(r"(\d+)\s*%", cmd)
                if m:
                    extra["brightness_pct"] = int(m.group(1))
                ok = await self.call_service("light", "turn_on", entity, extra or None)
                return f"💡 Licht{'(e)' if not entity_hint else f' ({entity_hint})'} {'eingeschaltet ✅' if ok else 'Fehler ❌'}"

        # Schalter / Steckdose
        if any(w in cmd for w in ["schalter", "steckdose", "switch"]):
            if any(w in cmd for w in ["aus", "off"]):
                entity = self._find_entity_id("switch", entity_hint)
                ok = await self.call_service("switch", "turn_off", entity)
                return f"🔌 {'Aus' if ok else 'Fehler ❌'}"
            else:
                entity = self._find_entity_id("switch", entity_hint)
                ok = await self.call_service("switch", "turn_on", entity)
                return f"🔌 {'An ✅' if ok else 'Fehler ❌'}"

        # Heizung / Thermostat
        if any(w in cmd for w in ["heizung", "thermostat", "temperatur", "grad", "°"]):
            import re
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:grad|°c|°)", cmd)
            if m:
                temp = float(m.group(1).replace(",", "."))
                entity = self._find_entity_id("climate", entity_hint)
                ok = await self.call_service("climate", "set_temperature", entity, {"temperature": temp})
                return f"🌡️ Temperatur auf {temp}°C gesetzt {'✅' if ok else '❌'}"
            return "❓ Bitte Temperatur angeben, z.B. _Heizung auf 22 Grad_"

        # Rollos / Jalousien
        if any(w in cmd for w in ["rollo", "jalousie", "rollladen", "cover"]):
            entity = self._find_entity_id("cover", entity_hint)
            if any(w in cmd for w in ["auf", "öffnen", "hoch", "open"]):
                ok = await self.call_service("cover", "open_cover", entity)
                return f"🪟 Rollo {'geöffnet ✅' if ok else 'Fehler ❌'}"
            else:
                ok = await self.call_service("cover", "close_cover", entity)
                return f"🪟 Rollo {'geschlossen ✅' if ok else 'Fehler ❌'}"

        # Szenen
        if any(w in cmd for w in ["szene", "scene", "modus"]):
            import re
            m = re.search(r"(?:szene|scene|modus)\s+(.+)", cmd)
            scene_name = m.group(1) if m else entity_hint
            entity = f"scene.{scene_name.lower().replace(' ', '_')}" if scene_name else ""
            ok = await self.call_service("scene", "turn_on", entity)
            return f"🎨 Szene aktiviert {'✅' if ok else '❌'}"

        return "❓ Befehl nicht erkannt. Beispiele: _Licht an_, _Heizung auf 22°_, _Rollos schließen_"

    def _find_entity_id(self, domain: str, hint: str) -> str:
        """Baut eine Entity-ID aus Domain + Hinweis (Raumname etc.)."""
        if not hint:
            return ""
        # Raumname zu entity_id konvertieren
        slug = hint.lower().replace(" ", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        return f"{domain}.{slug}"
