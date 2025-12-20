"""Application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root for .env file loading
PROJECT_ROOT = Path(__file__).parent.parent


class IconikSettings(BaseSettings):
    """Iconik API settings."""

    model_config = SettingsConfigDict(
        env_prefix="ICONIK_",
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_id: str = ""
    auth_token: str = ""
    base_url: str = "https://app.iconik.io"
    timeout: int = 30
    max_retries: int = 3
    metadata_view_id: str = ""  # Metadata View ID for 26-column export


class GoogleSheetsSettings(BaseSettings):
    """Google Sheets settings."""

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_",
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_account_path: str = ""
    spreadsheet_id: str = ""


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Lazy initialization - will be set in __init__
    iconik: IconikSettings | None = None
    sheets: GoogleSheetsSettings | None = None

    # Sync settings
    state_file: str = "data/sync_state.json"
    batch_size: int = 100
    rate_limit_per_sec: int = 50

    def model_post_init(self, __context) -> None:
        """Initialize nested settings after env files are loaded."""
        if self.iconik is None:
            object.__setattr__(self, "iconik", IconikSettings())
        if self.sheets is None:
            object.__setattr__(self, "sheets", GoogleSheetsSettings())


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
