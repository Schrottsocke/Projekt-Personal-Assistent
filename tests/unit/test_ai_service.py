"""Unit-Tests für AIService: Intent-Erkennung, Fallback, Error-Handling."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def ai_service():
    """Erzeugt eine AIService-Instanz mit gemocktem OpenAI-Client."""
    with patch("src.services.ai_service.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        MockOpenAI.return_value = mock_client

        with patch("src.services.ai_service.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = "fake-key"
            mock_settings.OPENROUTER_BASE_URL = "https://fake.api"
            mock_settings.AI_MODEL_INTENT = "test-intent-model"
            mock_settings.AI_MODEL_CHAT = "test-chat-model"
            mock_settings.AI_MODEL_FALLBACK_NVIDIA = "nvidia_fallback"
            mock_settings.TIMEZONE = "Europe/Berlin"
            mock_settings.GROQ_API_KEY = None
            mock_settings.NVIDIA_API_KEY = None

            from src.services.ai_service import AIService

            svc = AIService.__new__(AIService)
            svc._client = mock_client
            svc._model_intent = "test-intent-model"
            svc._model_chat = "test-chat-model"
            svc._fallback_nvidia = "nvidia_fallback"

            import pytz

            svc.tz = pytz.timezone("Europe/Berlin")
            svc._intelligence = None
            svc._web_search = None
            svc._groq_client = None
            svc._nvidia_client = None
            svc._nvidia_model = None

    return svc


class TestDetectIntent:
    """Tests für die Intent-Erkennung."""

    @pytest.mark.asyncio
    async def test_detect_intent_returns_calendar_read(self, ai_service):
        """Intent-Erkennung gibt calendar_read zurück bei Termin-Frage."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"intent": "calendar_read"}'

        ai_service._client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.services.ai_service.get_enabled_intents", return_value=["calendar_read", "chat"]):
            result = await ai_service._detect_intent("Welche Termine habe ich heute Nachmittag?", "taake")

        assert result.get("intent") == "calendar_read"

    @pytest.mark.asyncio
    async def test_detect_intent_returns_chat_as_default(self, ai_service):
        """Bei normaler Konversation wird chat erkannt."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"intent": "chat"}'

        ai_service._client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.services.ai_service.get_enabled_intents", return_value=["chat"]):
            result = await ai_service._detect_intent("Hallo, wie geht es dir?", "taake")

        assert result.get("intent") == "chat"


class TestComplete:
    """Tests für den _complete-Aufruf mit Fallback."""

    @pytest.mark.asyncio
    async def test_complete_returns_response(self, ai_service):
        """Erfolgreicher _complete-Aufruf gibt Text zurück."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test-Antwort"

        ai_service._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [{"role": "user", "content": "Hallo"}]
        # Call the underlying logic directly (bypass tenacity retry for unit test)
        result = await ai_service._complete.__wrapped__(ai_service, messages)

        assert result == "Test-Antwort"

    @pytest.mark.asyncio
    async def test_complete_falls_back_on_error(self, ai_service):
        """Bei Fehler im Primärmodell wird das Fallback-Modell verwendet."""
        from openai import APITimeoutError

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Fallback-Antwort"

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("model") == "test-chat-model":
                raise APITimeoutError(request=MagicMock())
            return mock_response

        ai_service._client.chat.completions.create = mock_create

        messages = [{"role": "user", "content": "Hallo"}]
        result = await ai_service._complete.__wrapped__(ai_service, messages)

        assert result == "Fallback-Antwort"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_complete_raises_when_all_models_fail(self, ai_service):
        """Wenn alle Modelle fehlschlagen, wird eine Exception geworfen."""
        from openai import APITimeoutError

        async def mock_create(**kwargs):
            raise APITimeoutError(request=MagicMock())

        ai_service._client.chat.completions.create = mock_create

        messages = [{"role": "user", "content": "Hallo"}]
        with pytest.raises(APITimeoutError):
            await ai_service._complete.__wrapped__(ai_service, messages)


class TestProcessMessage:
    """Tests für die Hauptfunktion process_message."""

    @pytest.mark.asyncio
    async def test_process_message_delegates_to_chat(self, ai_service):
        """process_message delegiert an den Chat-Handler bei Intent 'chat'."""
        ai_service._detect_intent = AsyncMock(return_value={"intent": "chat"})
        ai_service._handle_chat = AsyncMock(return_value="Chat-Antwort")

        with patch("src.services.ai_service.is_enabled", return_value=True):
            result = await ai_service.process_message(
                message="Hallo",
                user_key="taake",
                chat_id=12345,
                bot=MagicMock(),
            )

        assert result == "Chat-Antwort"

    @pytest.mark.asyncio
    async def test_process_message_feature_gate_fallback(self, ai_service):
        """Deaktiviertes Feature fällt auf Chat-Handler zurück."""
        ai_service._detect_intent = AsyncMock(return_value={"intent": "calendar_read"})
        ai_service._handle_chat = AsyncMock(return_value="Chat-Fallback")
        ai_service._feature_enabled = MagicMock(return_value=False)

        result = await ai_service.process_message(
            message="Was habe ich heute?",
            user_key="taake",
            chat_id=12345,
            bot=MagicMock(),
        )

        assert result == "Chat-Fallback"
