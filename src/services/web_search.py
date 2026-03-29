"""
Web Search Service: Tavily (primär) mit DuckDuckGo-Fallback.
Liefert aufbereitete Suchergebnisse für den KI-Kontext.
"""

import logging
from config.settings import settings

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Sucht im Web und gibt KI-optimierte Snippets zurück.
    Verwendet Tavily wenn TAVILY_API_KEY gesetzt ist, sonst DuckDuckGo.
    """

    def __init__(self):
        self._tavily = None
        self._mode = "none"
        self._setup()

    def _setup(self):
        if settings.TAVILY_API_KEY:
            try:
                from tavily import TavilyClient

                self._tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
                self._mode = "tavily"
                logger.info("WebSearch: Tavily aktiv.")
                return
            except ImportError:
                logger.warning("tavily-python nicht installiert. Versuche DuckDuckGo...")

        try:
            from duckduckgo_search import DDGS

            self._mode = "duckduckgo"
            logger.info("WebSearch: DuckDuckGo aktiv.")
        except ImportError:
            logger.warning("Weder tavily noch duckduckgo-search installiert. Web-Suche deaktiviert.")
            self._mode = "none"

    @property
    def available(self) -> bool:
        return self._mode != "none"

    async def search(self, query: str, max_results: int = 4) -> list[dict]:
        """
        Führt eine Web-Suche durch.
        Returns: Liste von {"title": ..., "url": ..., "snippet": ...}
        """
        if self._mode == "tavily":
            return await self._search_tavily(query, max_results)
        elif self._mode == "duckduckgo":
            return await self._search_ddg(query, max_results)
        return []

    async def _search_tavily(self, query: str, max_results: int) -> list[dict]:
        try:
            import asyncio

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._tavily.search(
                    query=query,
                    max_results=max_results,
                    search_depth="basic",
                    include_answer=True,
                ),
            )
            results = []
            # Direkte KI-Antwort von Tavily (falls vorhanden)
            if response.get("answer"):
                results.append(
                    {
                        "title": "Zusammenfassung",
                        "url": "",
                        "snippet": response["answer"],
                    }
                )
            for r in response.get("results", [])[:max_results]:
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", "")[:400],
                    }
                )
            return results
        except Exception as e:
            logger.error(f"Tavily-Fehler: {e}. Versuche DuckDuckGo...")
            return await self._search_ddg(query, max_results)

    async def _search_ddg(self, query: str, max_results: int) -> list[dict]:
        try:
            import asyncio
            from duckduckgo_search import DDGS

            loop = asyncio.get_running_loop()

            def _run():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))

            hits = await loop.run_in_executor(None, _run)
            return [
                {
                    "title": h.get("title", ""),
                    "url": h.get("href", ""),
                    "snippet": h.get("body", "")[:400],
                }
                for h in hits
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo-Fehler: {e}")
            return []

    # Muster die auf Prompt-Injection-Versuche hindeuten.
    # Gefundene Zeilen werden durch einen Platzhalter ersetzt,
    # nicht still gelöscht, damit das LLM den Kontext nicht verliert.
    _INJECTION_PATTERNS = [
        "ignore previous instructions",
        "ignore all previous",
        "ignore the above",
        "disregard previous",
        "disregard all previous",
        "forget previous instructions",
        "new instructions:",
        "system prompt:",
        "you are now",
        "act as",
        "jailbreak",
        "ignoriere alle vorherigen",
        "ignoriere die obigen",
        "neue anweisungen:",
        "du bist jetzt",
        "vergiss alle",
    ]

    def _sanitize_snippet(self, text: str) -> str:
        """
        Entfernt bekannte Prompt-Injection-Muster aus einem Snippet.
        Arbeitet zeilenweise: verdächtige Zeilen werden markiert,
        nicht still gelöscht – so bleibt der Kontext erhalten und
        das LLM weiß, dass hier etwas entfernt wurde.
        """
        clean_lines = []
        for line in text.splitlines():
            line_lower = line.lower().strip()
            if any(pattern in line_lower for pattern in self._INJECTION_PATTERNS):
                clean_lines.append("[Inhalt aus Sicherheitsgründen entfernt]")
                logger.warning(f"Prompt-Injection-Versuch in Suchergebnis erkannt: {line[:80]!r}")
            else:
                clean_lines.append(line)
        return "\n".join(clean_lines)

    def format_for_prompt(self, results: list[dict]) -> str:
        """
        Formatiert Suchergebnisse als sicheren Kontext-Block für den LLM-Prompt.

        Wichtig: Die Ergebnisse werden in einen expliziten <search_results>-Block
        eingebettet. Das signalisiert dem Modell klar, dass es sich um externe,
        nicht vertrauenswürdige Daten handelt – keine Anweisungen.
        """
        if not results:
            return "Keine Suchergebnisse gefunden."
        lines = []
        for i, r in enumerate(results, 1):
            title = self._sanitize_snippet(r.get("title", ""))
            snippet = self._sanitize_snippet(r.get("snippet", ""))
            url = r.get("url", "")
            if url:
                lines.append(f"[{i}] {title}\n{snippet}\nQuelle: {url}")
            else:
                lines.append(f"[{i}] {title}\n{snippet}")
        return "\n\n".join(lines)
