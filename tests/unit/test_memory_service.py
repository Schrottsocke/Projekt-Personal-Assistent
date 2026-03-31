"""Unit-Tests für BaseMemoryService und BotMemoryService."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def base_memory_service():
    """Erzeugt eine BaseMemoryService-Instanz mit gemocktem mem0-Backend."""
    from src.memory.base_memory_service import BaseMemoryService

    svc = BaseMemoryService()
    svc._memory = MagicMock()
    svc._available = True
    return svc


@pytest.fixture
def bot_memory_service():
    """Erzeugt eine BotMemoryService-Instanz mit gemocktem mem0 und DB."""
    from src.memory.memory_service import BotMemoryService

    svc = BotMemoryService()
    svc._memory = MagicMock()
    svc._available = True
    svc._db = None  # DB-Tests mocken das separat
    return svc


class TestAddMemory:
    """Tests für add_memory (BaseMemoryService)."""

    @pytest.mark.asyncio
    async def test_add_memory_calls_mem0(self, base_memory_service):
        """add_memory ruft mem0.add mit korrekten Parametern auf."""
        base_memory_service._memory.add = MagicMock(return_value={"results": [{"id": "123"}]})

        await base_memory_service.add_memory("taake", "User mag Kaffee")

        base_memory_service._memory.add.assert_called_once()
        call_kwargs = base_memory_service._memory.add.call_args
        assert call_kwargs[1]["user_id"] == "taake"

    @pytest.mark.asyncio
    async def test_add_memory_noop_when_unavailable(self, base_memory_service):
        """add_memory tut nichts, wenn der Service nicht verfügbar ist."""
        base_memory_service._available = False

        await base_memory_service.add_memory("taake", "Test")

        base_memory_service._memory.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_memory_handles_error(self, base_memory_service):
        """add_memory fängt Fehler ab, ohne eine Exception zu werfen."""
        base_memory_service._memory.add = MagicMock(side_effect=OSError("Connection failed"))

        # Sollte keine Exception werfen
        await base_memory_service.add_memory("taake", "Test")


class TestSearchMemories:
    """Tests für search_memories (BaseMemoryService)."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, base_memory_service):
        """search_memories gibt eine Liste von Ergebnissen zurück."""
        base_memory_service._memory.search = MagicMock(return_value={"results": [{"memory": "User mag Kaffee"}]})

        results = await base_memory_service.search_memories("taake", "Kaffee")

        assert len(results) == 1
        assert results[0]["memory"] == "User mag Kaffee"

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_unavailable(self, base_memory_service):
        """search_memories gibt leere Liste zurück, wenn Service nicht verfügbar."""
        base_memory_service._available = False

        results = await base_memory_service.search_memories("taake", "Kaffee")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_list_response(self, base_memory_service):
        """search_memories verarbeitet auch einfache Listen (nicht nur dicts)."""
        base_memory_service._memory.search = MagicMock(
            return_value=[{"memory": "Ergebnis 1"}, {"memory": "Ergebnis 2"}]
        )

        results = await base_memory_service.search_memories("taake", "query")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_handles_error(self, base_memory_service):
        """search_memories gibt leere Liste bei Fehler zurück."""
        base_memory_service._memory.search = MagicMock(side_effect=RuntimeError("Search failed"))

        results = await base_memory_service.search_memories("taake", "query")

        assert results == []


class TestUpsertFact:
    """Tests für upsert_fact (BotMemoryService)."""

    @pytest.mark.asyncio
    async def test_upsert_fact_no_db_is_noop(self, bot_memory_service):
        """upsert_fact tut nichts, wenn keine DB verfügbar ist."""
        bot_memory_service._db = None

        # Sollte keine Exception werfen
        await bot_memory_service.upsert_fact("taake", "User trinkt gerne Tee")

    @pytest.mark.asyncio
    async def test_upsert_fact_creates_new_fact(self, bot_memory_service):
        """upsert_fact erstellt einen neuen Fakt, wenn keiner existiert."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        bot_memory_service._db = MagicMock(return_value=mock_session)

        with patch("src.services.database.MemoryFact", MagicMock()) as MockFact:
            MockFact.return_value = MagicMock()
            await bot_memory_service.upsert_fact("taake", "Neuer Fakt")

        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_fact_increments_existing(self, bot_memory_service):
        """upsert_fact erhöht confirmation_count bei bestehendem Fakt."""
        existing_fact = MagicMock()
        existing_fact.confirmation_count = 1

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = existing_fact
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        bot_memory_service._db = MagicMock(return_value=mock_session)

        with patch.dict("sys.modules", {"src.services.database": MagicMock(MemoryFact=MagicMock)}):
            await bot_memory_service.upsert_fact("taake", "Bestehender Fakt")

        assert existing_fact.confirmation_count == 2


class TestGetAllMemories:
    """Tests für get_all_memories (BaseMemoryService)."""

    @pytest.mark.asyncio
    async def test_get_all_returns_results(self, base_memory_service):
        """get_all_memories gibt alle gespeicherten Erinnerungen zurück."""
        base_memory_service._memory.get_all = MagicMock(
            return_value={"results": [{"memory": "Fakt 1"}, {"memory": "Fakt 2"}]}
        )

        results = await base_memory_service.get_all_memories("taake")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_all_empty_when_unavailable(self, base_memory_service):
        """get_all_memories gibt leere Liste zurück, wenn Service nicht verfügbar."""
        base_memory_service._available = False

        results = await base_memory_service.get_all_memories("taake")

        assert results == []
