"""Tests für config/settings.py – Validierung, Defaults, BotConfig."""

from config.settings import Settings


class TestSettingsDefaults:
    """Prüft ob Defaults korrekt gesetzt sind."""

    def test_default_ai_models(self):
        assert Settings.AI_MODEL_INTENT != ""
        assert Settings.AI_MODEL_CHAT != ""

    def test_default_timezone(self, settings_fresh):
        assert settings_fresh.TIMEZONE == "Europe/Berlin"

    def test_default_memory_mode(self, settings_fresh):
        assert settings_fresh.MEMORY_MODE == "local"

    def test_default_api_port(self, settings_fresh):
        assert settings_fresh.API_PORT == 8000

    def test_default_token_expire_days(self, settings_fresh):
        assert settings_fresh.API_TOKEN_EXPIRE_DAYS == 30

    def test_default_conversation_history_days(self, settings_fresh):
        assert settings_fresh.CONVERSATION_HISTORY_DAYS == 30

    def test_default_calendar_cache_ttl(self, settings_fresh):
        assert settings_fresh.CALENDAR_CACHE_TTL_MINUTES == 5


class TestSettingsValidation:
    """Prüft die validate()-Methode."""

    def test_validate_passes_with_all_required(self, settings_fresh):
        errors = settings_fresh.validate()
        assert errors == []

    def test_validate_fails_without_bot_token(self, settings_fresh, monkeypatch):
        monkeypatch.setattr(settings_fresh, "BOT_TOKEN_TAAKE", "")
        errors = settings_fresh.validate()
        assert any("BOT_TOKEN_TAAKE" in e for e in errors)

    def test_validate_fails_without_openrouter_key(self, settings_fresh, monkeypatch):
        monkeypatch.setattr(settings_fresh, "OPENROUTER_API_KEY", "")
        errors = settings_fresh.validate()
        assert any("OPENROUTER_API_KEY" in e for e in errors)

    def test_validate_fails_with_empty_secret_key(self, settings_fresh, monkeypatch):
        monkeypatch.setattr(settings_fresh, "API_SECRET_KEY", "")
        errors = settings_fresh.validate()
        assert any("API_SECRET_KEY" in e for e in errors)

    def test_validate_fails_with_insecure_default_secret(self, settings_fresh, monkeypatch):
        monkeypatch.setattr(settings_fresh, "API_SECRET_KEY", "change-me-in-production-please")
        errors = settings_fresh.validate()
        assert any("API_SECRET_KEY" in e for e in errors)

    def test_validate_fails_with_short_secret(self, settings_fresh, monkeypatch):
        monkeypatch.setattr(settings_fresh, "API_SECRET_KEY", "too-short")
        errors = settings_fresh.validate()
        assert any("32 Zeichen" in e for e in errors)

    def test_validate_fails_with_invalid_user_id(self, settings_fresh, monkeypatch):
        monkeypatch.setattr(settings_fresh, "TELEGRAM_USER_ID_TAAKE", -1)
        errors = settings_fresh.validate()
        assert any("TELEGRAM_USER_ID_TAAKE" in e for e in errors)


class TestBotConfig:
    """Prüft BotConfig und get_bot_configs()."""

    def test_get_bot_configs_returns_both(self, settings_fresh):
        configs = settings_fresh.get_bot_configs()
        assert "taake" in configs
        assert "nina" in configs

    def test_bot_config_has_name(self, settings_fresh):
        configs = settings_fresh.get_bot_configs()
        assert configs["taake"].name == "Taake"
        assert configs["nina"].name == "Nina"

    def test_get_allowed_user_ids(self, settings_fresh):
        ids = settings_fresh.get_allowed_user_ids()
        assert 12345 in ids
        assert 67890 in ids

    def test_get_allowed_user_ids_excludes_invalid(self, settings_fresh, monkeypatch):
        monkeypatch.setattr(settings_fresh, "TELEGRAM_USER_ID_NINA", -1)
        ids = settings_fresh.get_allowed_user_ids()
        assert 12345 in ids
        assert -1 not in ids


class TestSystemPrompt:
    """Prüft get_system_prompt()."""

    def test_prompt_for_taake(self, settings_fresh):
        s = settings_fresh()
        prompt = s.get_system_prompt("taake")
        assert "Taake" in prompt

    def test_prompt_for_nina(self, settings_fresh):
        s = settings_fresh()
        prompt = s.get_system_prompt("nina")
        assert "Nina" in prompt

    def test_prompt_default(self, settings_fresh):
        s = settings_fresh()
        prompt = s.get_system_prompt(None)
        assert "hilfreicher" in prompt or "Assistent" in prompt

    def test_prompt_unknown_user(self, settings_fresh):
        s = settings_fresh()
        prompt = s.get_system_prompt("unknown")
        assert "Assistent" in prompt
