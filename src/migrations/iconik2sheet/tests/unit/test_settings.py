"""Unit tests for settings module."""

import os
from functools import lru_cache
from unittest.mock import patch

import pytest


class TestIconikSettings:
    """Test IconikSettings class."""

    def test_default_values(self):
        """Test default setting values when env vars are not set."""
        # Clear ICONIK_ env vars to test true defaults
        with patch.dict(
            os.environ,
            {
                "ICONIK_APP_ID": "",
                "ICONIK_AUTH_TOKEN": "",
                "ICONIK_METADATA_VIEW_ID": "",
            },
            clear=False,
        ):
            from config.settings import IconikSettings

            settings = IconikSettings(_env_file=None)
            assert settings.base_url == "https://app.iconik.io"
            assert settings.timeout == 30
            assert settings.max_retries == 3
            assert settings.metadata_view_id == ""

    def test_env_prefix(self):
        """Test environment variable prefix ICONIK_."""
        with patch.dict(
            os.environ,
            {
                "ICONIK_APP_ID": "test-app",
                "ICONIK_AUTH_TOKEN": "test-token",
                "ICONIK_METADATA_VIEW_ID": "view-123",
            },
            clear=False,
        ):
            from config.settings import IconikSettings

            settings = IconikSettings()
            assert settings.app_id == "test-app"
            assert settings.auth_token == "test-token"
            assert settings.metadata_view_id == "view-123"

    def test_custom_base_url(self):
        """Test custom base URL."""
        with patch.dict(
            os.environ,
            {"ICONIK_BASE_URL": "https://custom.iconik.io"},
            clear=False,
        ):
            from config.settings import IconikSettings

            settings = IconikSettings()
            assert settings.base_url == "https://custom.iconik.io"


class TestGoogleSheetsSettings:
    """Test GoogleSheetsSettings class."""

    def test_default_values(self):
        """Test default empty values when env vars are not set."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_SERVICE_ACCOUNT_PATH": "",
                "GOOGLE_SPREADSHEET_ID": "",
            },
            clear=False,
        ):
            from config.settings import GoogleSheetsSettings

            settings = GoogleSheetsSettings(_env_file=None)  # Skip .env file loading
            assert settings.service_account_path == ""
            assert settings.spreadsheet_id == ""

    def test_env_prefix(self):
        """Test GOOGLE_ prefix works."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_SERVICE_ACCOUNT_PATH": "/path/to/key.json",
                "GOOGLE_SPREADSHEET_ID": "sheet-123",
            },
            clear=False,
        ):
            from config.settings import GoogleSheetsSettings

            settings = GoogleSheetsSettings()
            assert settings.service_account_path == "/path/to/key.json"
            assert settings.spreadsheet_id == "sheet-123"


class TestSettings:
    """Test main Settings class."""

    def test_nested_settings(self):
        """Test nested IconikSettings and GoogleSheetsSettings."""
        from config.settings import Settings

        settings = Settings()
        assert hasattr(settings, "iconik")
        assert hasattr(settings, "sheets")
        assert hasattr(settings.iconik, "app_id")
        assert hasattr(settings.sheets, "spreadsheet_id")

    def test_sync_defaults(self):
        """Test sync setting defaults."""
        from config.settings import Settings

        settings = Settings()
        assert settings.state_file == "data/sync_state.json"
        assert settings.batch_size == 100
        assert settings.rate_limit_per_sec == 50


class TestGetSettings:
    """Test get_settings function."""

    def test_returns_settings_instance(self):
        """Test returns Settings instance."""
        # Clear cache first
        from config.settings import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        from config.settings import Settings

        assert isinstance(settings, Settings)

    def test_cached_instance(self):
        """Test settings are cached (same instance returned)."""
        from config.settings import get_settings

        get_settings.cache_clear()

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2  # Same cached instance
