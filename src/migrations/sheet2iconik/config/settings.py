"""Application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class IconikSettings(BaseSettings):
    """Iconik API settings."""

    app_id: str = ""
    auth_token: str = ""
    base_url: str = "https://app.iconik.io"
    timeout: int = 30
    max_retries: int = 3

    class Config:
        env_prefix = "ICONIK_"


class GoogleSheetsSettings(BaseSettings):
    """Google Sheets settings."""

    service_account_path: str = ""
    spreadsheet_id: str = ""

    class Config:
        env_prefix = "GOOGLE_"


class Settings(BaseSettings):
    """Application settings."""

    iconik: IconikSettings = IconikSettings()
    sheets: GoogleSheetsSettings = GoogleSheetsSettings()

    # Database
    database_url: str = "sqlite:///data/migration.db"

    # Batch processing
    batch_size: int = 100
    rate_limit_per_sec: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
