"""Configuration settings for Sheet-to-Sheet migration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Migration settings."""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Service Account
    google_service_account_path: str = Field(
        default=r"D:\AI\claude01\json\service_account_key.json",
        alias="GOOGLE_SERVICE_ACCOUNT_PATH",
    )

    # Source Sheet (Archive Metadata)
    source_spreadsheet_id: str = Field(
        default="1_RN_W_ZQclSZA0Iez6XniCXVtjkkd5HNZwiT6l-z6d4",
        alias="SOURCE_SPREADSHEET_ID",
    )

    # Target Sheet (Iconik metadata)
    target_spreadsheet_id: str = Field(
        default="1pUMPKe-OsKc-Xd8lH1cP9ctJO4hj3keXY5RwNFp2Mtk",
        alias="TARGET_SPREADSHEET_ID",
    )
    target_sheet_name: str = Field(
        default="Archive_Metadata",
        alias="TARGET_SHEET_NAME",
    )

    # Migration options
    mode: str = Field(
        default="append",
        description="Migration mode: 'append' or 'overwrite'",
    )
    batch_size: int = Field(
        default=100,
        description="Number of rows to process per batch",
    )
    header_row: int = Field(
        default=3,
        description="Row number containing headers (1-indexed). Default 3 for Archive Metadata.",
    )
    dry_run: bool = Field(
        default=True,
        description="If True, only preview changes without writing",
    )

    @property
    def service_account_path(self) -> Path:
        """Return service account path as Path object."""
        return Path(self.google_service_account_path)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
