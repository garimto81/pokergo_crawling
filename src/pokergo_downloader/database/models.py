"""
Database models for PokerGO content management.

Supports two sources:
1. PokerGO Website (pokergo.com) - Premium streaming content
2. YouTube Channel (@PokerGO) - Free promotional content

Phase 1: Metadata collection (DB Parsing)
Phase 2: Video download
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models"""

    pass


class Source(str, Enum):
    """Content source types"""

    POKERGO_WEB = "pokergo_web"  # pokergo.com (subscription required)
    YOUTUBE = "youtube"  # youtube.com/@PokerGO (free)
    ARCHIVE = "archive"  # PokerGO archive files (직접 받은 파일)


class DownloadStatus(str, Enum):
    """Download status states"""

    PENDING = "pending"  # Not yet downloaded
    QUEUED = "queued"  # In download queue
    DOWNLOADING = "downloading"  # Currently downloading
    COMPLETED = "completed"  # Successfully downloaded
    FAILED = "failed"  # Download failed
    SKIPPED = "skipped"  # Skipped (e.g., already exists)


class Channel(Base):
    """
    Channel/Source information.

    Examples:
    - PokerGO Website: channel_id = "pokergo_web", name = "PokerGO"
    - YouTube: channel_id = "UC...", name = "PokerGO"
    """

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    source: Mapped[Source] = mapped_column(SQLEnum(Source))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    subscriber_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    playlists: Mapped[list["Playlist"]] = relationship(back_populates="channel")
    videos: Mapped[list["Video"]] = relationship(back_populates="channel")

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, name='{self.name}', source={self.source.value})>"


class Playlist(Base):
    """
    Playlist/Series/Show information.

    Maps to:
    - PokerGO: Shows/Series (e.g., "High Stakes Poker", "WSOP 2023")
    - YouTube: Playlists
    """

    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    playlist_id: Mapped[str] = mapped_column(String(100), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    source: Mapped[Source] = mapped_column(SQLEnum(Source))

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # PokerGO specific
    season_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    channel: Mapped["Channel"] = relationship(back_populates="playlists")
    videos: Mapped[list["Video"]] = relationship(
        back_populates="playlist", secondary="playlist_videos"
    )

    __table_args__ = (UniqueConstraint("playlist_id", "source", name="uq_playlist_source"),)

    def __repr__(self) -> str:
        return f"<Playlist(id={self.id}, title='{self.title}', source={self.source.value})>"


class Video(Base):
    """
    Video/Episode information.

    Core entity that stores metadata for both PokerGO and YouTube videos.
    """

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[str] = mapped_column(String(100), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    source: Mapped[Source] = mapped_column(SQLEnum(Source))

    # Basic metadata
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds

    # YouTube specific
    view_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    like_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    upload_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # PokerGO specific
    episode_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    season_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    air_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    jwplayer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Download tracking (Phase 2)
    download_status: Mapped[DownloadStatus] = mapped_column(
        SQLEnum(DownloadStatus), default=DownloadStatus.PENDING
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # bytes

    # Quality info
    available_qualities: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array
    downloaded_quality: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    channel: Mapped["Channel"] = relationship(back_populates="videos")
    playlist: Mapped[Optional["Playlist"]] = relationship(
        back_populates="videos", secondary="playlist_videos"
    )
    download_tasks: Mapped[list["DownloadTask"]] = relationship(back_populates="video")

    __table_args__ = (UniqueConstraint("video_id", "source", name="uq_video_source"),)

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, title='{self.title[:30]}...', source={self.source.value})>"

    @property
    def url(self) -> str:
        """Generate URL based on source"""
        if self.source == Source.YOUTUBE:
            return f"https://www.youtube.com/watch?v={self.video_id}"
        elif self.source == Source.POKERGO_WEB:
            return f"https://www.pokergo.com/videos/{self.video_id}"
        return ""


class PlaylistVideo(Base):
    """Many-to-many relationship between playlists and videos"""

    __tablename__ = "playlist_videos"

    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"), primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), primary_key=True)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Order in playlist


class DownloadTask(Base):
    """
    Download task history and queue (Phase 2).

    Tracks download attempts, progress, and errors.
    """

    __tablename__ = "download_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))

    # Task info
    status: Mapped[DownloadStatus] = mapped_column(
        SQLEnum(DownloadStatus), default=DownloadStatus.PENDING
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Higher = more urgent
    requested_quality: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Progress tracking
    progress_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    downloaded_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    speed_bps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # bytes per second
    eta_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    video: Mapped["Video"] = relationship(back_populates="download_tasks")

    def __repr__(self) -> str:
        return f"<DownloadTask(id={self.id}, video_id={self.video_id}, status={self.status.value})>"


class CrawlHistory(Base):
    """Track crawling history for incremental updates"""

    __tablename__ = "crawl_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[Source] = mapped_column(SQLEnum(Source))
    target_type: Mapped[str] = mapped_column(String(50))  # "channel", "playlist", "video"
    target_id: Mapped[str] = mapped_column(String(100))

    # Stats
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ArchiveFileStatus(str, Enum):
    """Archive file processing status"""

    PENDING = "pending"  # Not yet parsed
    PARSED = "parsed"  # Metadata extracted from filename
    MATCHED = "matched"  # Matched with other source
    VERIFIED = "verified"  # Manually verified match


class ArchiveFile(Base):
    """
    Archive file information.

    Stores metadata for files received directly from PokerGO.
    Parses show/season/episode info from filename patterns.
    """

    __tablename__ = "archive_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # File info
    file_path: Mapped[str] = mapped_column(String(1000))
    file_name: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA256

    # Parsed metadata from filename
    parsed_show: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    parsed_season: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parsed_episode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parsed_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    parsed_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Media info (extracted from file)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds
    resolution: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "1080p"
    codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Matching with other sources
    matched_youtube_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    matched_pokergo_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    match_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)  # 0.0 ~ 1.0

    # Status
    status: Mapped[ArchiveFileStatus] = mapped_column(
        SQLEnum(ArchiveFileStatus), default=ArchiveFileStatus.PENDING
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ArchiveFile(id={self.id}, file_name='{self.file_name}', status={self.status.value})>"


class MatchType(str, Enum):
    """Content match types"""

    EXACT = "exact"  # Exact ID match
    FUZZY = "fuzzy"  # Fuzzy title match
    MANUAL = "manual"  # Manually assigned


class ContentMapping(Base):
    """
    Cross-source content mapping.

    Links content across YouTube, PokerGO.com, and Archive sources.
    """

    __tablename__ = "content_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Source IDs (at least two should be non-null)
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pokergo_episode_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    archive_file_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Match info
    match_type: Mapped[MatchType] = mapped_column(
        SQLEnum(MatchType), default=MatchType.FUZZY
    )
    confidence: Mapped[Optional[float]] = mapped_column(nullable=True)  # 0.0 ~ 1.0
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        sources = []
        if self.youtube_video_id:
            sources.append("YT")
        if self.pokergo_episode_id:
            sources.append("PG")
        if self.archive_file_id:
            sources.append("AR")
        return f"<ContentMapping(id={self.id}, sources={'+'.join(sources)}, verified={self.verified})>"
