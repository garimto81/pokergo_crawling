"""
Configuration management for PokerGO Crawler.

DB 파싱 전용 - 다운로드는 4K Downloader 사용
3가지 소스 분리 관리: YouTube, PokerGO.com, Archive
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SourceType(str, Enum):
    """Data source types."""
    YOUTUBE = "youtube"
    POKERGO_WEB = "pokergo_web"
    ARCHIVE = "archive"


@dataclass
class Settings:
    """Application settings."""

    # Base data directory
    data_dir: str = field(default="data")

    # Database (under data_dir)
    db_dir: str = field(default="db")
    db_name: str = field(default="pokergo.db")

    # Sources directory (under data_dir)
    sources_dir: str = field(default="sources")

    # Analysis directory (under data_dir)
    analysis_dir: str = field(default="analysis")

    # Subdirectories for each source
    exports_subdir: str = field(default="exports")
    videos_subdir: str = field(default="videos")
    playlists_subdir: str = field(default="playlists")
    urls_subdir: str = field(default="urls")
    snapshots_subdir: str = field(default="snapshots")

    # Archive specific
    files_subdir: str = field(default="files")
    parsed_subdir: str = field(default="parsed")

    # File size settings
    max_file_size_mb: int = field(default=5)  # 5MB per file

    # Crawler settings
    verbose: bool = field(default=False)

    def __post_init__(self) -> None:
        """Load from environment variables."""
        self.data_dir = os.getenv("POKERGO_DATA_DIR", self.data_dir)
        self.max_file_size_mb = int(os.getenv("POKERGO_MAX_FILE_SIZE_MB", str(self.max_file_size_mb)))
        self.verbose = os.getenv("POKERGO_VERBOSE", "").lower() in ("true", "1", "yes")

    # ==================== Base Paths ====================

    @property
    def db_path(self) -> Path:
        """Full path to database file."""
        return Path(self.data_dir) / self.db_dir / self.db_name

    @property
    def sources_path(self) -> Path:
        """Full path to sources directory."""
        return Path(self.data_dir) / self.sources_dir

    @property
    def analysis_path(self) -> Path:
        """Full path to analysis directory."""
        return Path(self.data_dir) / self.analysis_dir

    # ==================== Source-specific Paths ====================

    def get_source_path(self, source: SourceType) -> Path:
        """Get base path for a specific source."""
        return self.sources_path / source.value

    def get_exports_path(self, source: SourceType) -> Path:
        """Get exports path for a specific source."""
        return self.get_source_path(source) / self.exports_subdir

    def get_videos_path(self, source: SourceType) -> Path:
        """Get videos path for a specific source."""
        return self.get_exports_path(source) / self.videos_subdir

    def get_playlists_path(self, source: SourceType) -> Path:
        """Get playlists path for a specific source."""
        return self.get_exports_path(source) / self.playlists_subdir

    def get_urls_path(self, source: SourceType) -> Path:
        """Get URLs path for a specific source."""
        return self.get_exports_path(source) / self.urls_subdir

    def get_snapshots_path(self, source: SourceType) -> Path:
        """Get snapshots path for a specific source."""
        return self.get_source_path(source) / self.snapshots_subdir

    def get_index_path(self, source: SourceType) -> Path:
        """Get index.json path for a specific source."""
        return self.get_exports_path(source) / "index.json"

    def get_channel_path(self, source: SourceType) -> Path:
        """Get channel.json path for a specific source (YouTube only)."""
        return self.get_exports_path(source) / "channel.json"

    # ==================== Archive-specific Paths ====================

    @property
    def archive_files_path(self) -> Path:
        """Get files path for archive source."""
        return self.get_exports_path(SourceType.ARCHIVE) / self.files_subdir

    @property
    def archive_parsed_path(self) -> Path:
        """Get parsed path for archive source."""
        return self.get_source_path(SourceType.ARCHIVE) / self.parsed_subdir

    # ==================== Legacy Compatibility ====================
    # (Keep old properties for backward compatibility)

    @property
    def exports_path(self) -> Path:
        """Legacy: Full path to exports directory (YouTube)."""
        return self.get_exports_path(SourceType.YOUTUBE)

    @property
    def videos_path(self) -> Path:
        """Legacy: Full path to videos export directory (YouTube)."""
        return self.get_videos_path(SourceType.YOUTUBE)

    @property
    def playlists_path(self) -> Path:
        """Legacy: Full path to playlists export directory (YouTube)."""
        return self.get_playlists_path(SourceType.YOUTUBE)

    @property
    def urls_path(self) -> Path:
        """Legacy: Full path to URLs export directory (YouTube)."""
        return self.get_urls_path(SourceType.YOUTUBE)

    @property
    def snapshots_path(self) -> Path:
        """Legacy: Full path to snapshots directory (YouTube)."""
        return self.get_snapshots_path(SourceType.YOUTUBE)

    @property
    def index_path(self) -> Path:
        """Legacy: Full path to index.json (YouTube)."""
        return self.get_index_path(SourceType.YOUTUBE)

    @property
    def channel_path(self) -> Path:
        """Legacy: Full path to channel.json (YouTube)."""
        return self.get_channel_path(SourceType.YOUTUBE)

    @property
    def max_file_size_bytes(self) -> int:
        """Max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    # ==================== Directory Creation ====================

    def ensure_directories(self, source: SourceType | None = None) -> None:
        """Create all necessary directories for specified source or all sources."""
        # Always create DB directory
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Analysis directory
        self.analysis_path.mkdir(parents=True, exist_ok=True)

        sources = [source] if source else list(SourceType)

        for src in sources:
            self.get_exports_path(src).mkdir(parents=True, exist_ok=True)
            self.get_videos_path(src).mkdir(parents=True, exist_ok=True)
            self.get_snapshots_path(src).mkdir(parents=True, exist_ok=True)

            if src == SourceType.YOUTUBE:
                self.get_playlists_path(src).mkdir(parents=True, exist_ok=True)
                self.get_urls_path(src).mkdir(parents=True, exist_ok=True)
            elif src == SourceType.ARCHIVE:
                self.archive_files_path.mkdir(parents=True, exist_ok=True)
                self.archive_parsed_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
