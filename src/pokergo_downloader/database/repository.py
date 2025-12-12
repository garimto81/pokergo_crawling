"""
Repository pattern for database operations.

Provides a clean interface for CRUD operations on all entities.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker

from pokergo_downloader.database.models import (
    Base,
    Channel,
    CrawlHistory,
    DownloadStatus,
    DownloadTask,
    Playlist,
    PlaylistVideo,
    Source,
    Video,
)


class Repository:
    """
    Database repository for PokerGO content.

    Usage:
        repo = Repository("data/pokergo.db")
        repo.init_db()

        # Add channel
        channel = repo.upsert_channel(...)

        # Add videos
        for video_data in videos:
            repo.upsert_video(...)

        # Query
        pending = repo.get_pending_downloads()
    """

    def __init__(self, db_path: str = "data/pokergo.db"):
        """Initialize repository with SQLite database."""
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_db(self) -> None:
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    # ==================== Channel Operations ====================

    def upsert_channel(
        self,
        channel_id: str,
        source: Source,
        name: str,
        url: str,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        subscriber_count: Optional[int] = None,
        video_count: Optional[int] = None,
    ) -> Channel:
        """Insert or update a channel."""
        with self.get_session() as session:
            channel = session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            ).scalar_one_or_none()

            if channel:
                # Update existing
                channel.name = name
                channel.url = url
                channel.description = description
                channel.thumbnail_url = thumbnail_url
                channel.subscriber_count = subscriber_count
                channel.video_count = video_count
                channel.updated_at = datetime.now()
            else:
                # Create new
                channel = Channel(
                    channel_id=channel_id,
                    source=source,
                    name=name,
                    url=url,
                    description=description,
                    thumbnail_url=thumbnail_url,
                    subscriber_count=subscriber_count,
                    video_count=video_count,
                )
                session.add(channel)

            session.commit()
            session.refresh(channel)
            return channel

    def get_channel(self, channel_id: str) -> Optional[Channel]:
        """Get channel by ID."""
        with self.get_session() as session:
            return session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            ).scalar_one_or_none()

    def get_channels_by_source(self, source: Source) -> Sequence[Channel]:
        """Get all channels for a source."""
        with self.get_session() as session:
            return session.execute(select(Channel).where(Channel.source == source)).scalars().all()

    # ==================== Playlist Operations ====================

    def upsert_playlist(
        self,
        playlist_id: str,
        channel_id: int,
        source: Source,
        title: str,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        video_count: Optional[int] = None,
        season_number: Optional[int] = None,
    ) -> Playlist:
        """Insert or update a playlist."""
        with self.get_session() as session:
            playlist = session.execute(
                select(Playlist).where(
                    Playlist.playlist_id == playlist_id, Playlist.source == source
                )
            ).scalar_one_or_none()

            if playlist:
                playlist.title = title
                playlist.description = description
                playlist.thumbnail_url = thumbnail_url
                playlist.video_count = video_count
                playlist.season_number = season_number
                playlist.updated_at = datetime.now()
            else:
                playlist = Playlist(
                    playlist_id=playlist_id,
                    channel_id=channel_id,
                    source=source,
                    title=title,
                    description=description,
                    thumbnail_url=thumbnail_url,
                    video_count=video_count,
                    season_number=season_number,
                )
                session.add(playlist)

            session.commit()
            session.refresh(playlist)
            return playlist

    def get_playlists(
        self, channel_id: Optional[int] = None, source: Optional[Source] = None
    ) -> Sequence[Playlist]:
        """Get playlists, optionally filtered by channel or source."""
        with self.get_session() as session:
            query = select(Playlist)
            if channel_id:
                query = query.where(Playlist.channel_id == channel_id)
            if source:
                query = query.where(Playlist.source == source)
            return session.execute(query).scalars().all()

    # ==================== Video Operations ====================

    def upsert_video(
        self,
        video_id: str,
        channel_id: int,
        source: Source,
        title: str,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration: Optional[int] = None,
        view_count: Optional[int] = None,
        like_count: Optional[int] = None,
        comment_count: Optional[int] = None,
        upload_date: Optional[datetime] = None,
        tags: Optional[str] = None,
        episode_number: Optional[int] = None,
        season_number: Optional[int] = None,
        air_date: Optional[datetime] = None,
        jwplayer_id: Optional[str] = None,
        available_qualities: Optional[str] = None,
    ) -> Video:
        """Insert or update a video."""
        with self.get_session() as session:
            video = session.execute(
                select(Video).where(Video.video_id == video_id, Video.source == source)
            ).scalar_one_or_none()

            if video:
                # Update existing
                video.title = title
                video.description = description
                video.thumbnail_url = thumbnail_url
                video.duration = duration
                video.view_count = view_count
                video.like_count = like_count
                video.comment_count = comment_count
                video.upload_date = upload_date
                video.tags = tags
                video.episode_number = episode_number
                video.season_number = season_number
                video.air_date = air_date
                video.jwplayer_id = jwplayer_id
                video.available_qualities = available_qualities
                video.updated_at = datetime.now()
            else:
                # Create new
                video = Video(
                    video_id=video_id,
                    channel_id=channel_id,
                    source=source,
                    title=title,
                    description=description,
                    thumbnail_url=thumbnail_url,
                    duration=duration,
                    view_count=view_count,
                    like_count=like_count,
                    comment_count=comment_count,
                    upload_date=upload_date,
                    tags=tags,
                    episode_number=episode_number,
                    season_number=season_number,
                    air_date=air_date,
                    jwplayer_id=jwplayer_id,
                    available_qualities=available_qualities,
                )
                session.add(video)

            session.commit()
            session.refresh(video)
            return video

    def get_video(self, video_id: str, source: Source) -> Optional[Video]:
        """Get video by ID and source."""
        with self.get_session() as session:
            return session.execute(
                select(Video).where(Video.video_id == video_id, Video.source == source)
            ).scalar_one_or_none()

    def get_videos(
        self,
        source: Optional[Source] = None,
        channel_id: Optional[int] = None,
        download_status: Optional[DownloadStatus] = None,
        limit: Optional[int] = None,
    ) -> Sequence[Video]:
        """Get videos with optional filters."""
        with self.get_session() as session:
            query = select(Video)

            if source:
                query = query.where(Video.source == source)
            if channel_id:
                query = query.where(Video.channel_id == channel_id)
            if download_status:
                query = query.where(Video.download_status == download_status)
            if limit:
                query = query.limit(limit)

            return session.execute(query).scalars().all()

    def get_pending_downloads(self, limit: int = 100) -> Sequence[Video]:
        """Get videos pending download."""
        return self.get_videos(download_status=DownloadStatus.PENDING, limit=limit)

    def update_download_status(
        self,
        video_id: str,
        source: Source,
        status: DownloadStatus,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        downloaded_quality: Optional[str] = None,
    ) -> Optional[Video]:
        """Update video download status."""
        with self.get_session() as session:
            video = session.execute(
                select(Video).where(Video.video_id == video_id, Video.source == source)
            ).scalar_one_or_none()

            if video:
                video.download_status = status
                if file_path:
                    video.file_path = file_path
                if file_size:
                    video.file_size = file_size
                if downloaded_quality:
                    video.downloaded_quality = downloaded_quality
                video.updated_at = datetime.now()
                session.commit()
                session.refresh(video)

            return video

    def link_video_to_playlist(
        self, video_db_id: int, playlist_db_id: int, position: Optional[int] = None
    ) -> None:
        """Link a video to a playlist."""
        with self.get_session() as session:
            # Check if link exists
            existing = session.execute(
                select(PlaylistVideo).where(
                    PlaylistVideo.playlist_id == playlist_db_id,
                    PlaylistVideo.video_id == video_db_id,
                )
            ).scalar_one_or_none()

            if not existing:
                link = PlaylistVideo(
                    playlist_id=playlist_db_id, video_id=video_db_id, position=position
                )
                session.add(link)
                session.commit()

    # ==================== Statistics ====================

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self.get_session() as session:
            stats = {
                "channels": session.execute(select(func.count(Channel.id))).scalar() or 0,
                "playlists": session.execute(select(func.count(Playlist.id))).scalar() or 0,
                "videos": {
                    "total": session.execute(select(func.count(Video.id))).scalar() or 0,
                    "youtube": session.execute(
                        select(func.count(Video.id)).where(Video.source == Source.YOUTUBE)
                    ).scalar()
                    or 0,
                    "pokergo": session.execute(
                        select(func.count(Video.id)).where(Video.source == Source.POKERGO_WEB)
                    ).scalar()
                    or 0,
                },
                "downloads": {
                    "pending": session.execute(
                        select(func.count(Video.id)).where(
                            Video.download_status == DownloadStatus.PENDING
                        )
                    ).scalar()
                    or 0,
                    "completed": session.execute(
                        select(func.count(Video.id)).where(
                            Video.download_status == DownloadStatus.COMPLETED
                        )
                    ).scalar()
                    or 0,
                    "failed": session.execute(
                        select(func.count(Video.id)).where(
                            Video.download_status == DownloadStatus.FAILED
                        )
                    ).scalar()
                    or 0,
                },
            }
            return stats

    # ==================== Crawl History ====================

    def add_crawl_history(
        self,
        source: Source,
        target_type: str,
        target_id: str,
        items_found: int = 0,
        items_new: int = 0,
        items_updated: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> CrawlHistory:
        """Add a crawl history entry."""
        with self.get_session() as session:
            history = CrawlHistory(
                source=source,
                target_type=target_type,
                target_id=target_id,
                items_found=items_found,
                items_new=items_new,
                items_updated=items_updated,
                success=success,
                error_message=error_message,
                completed_at=datetime.now() if success else None,
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            return history
