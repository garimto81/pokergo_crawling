"""
YouTube channel crawler using yt-dlp.

Phase 1: Metadata extraction from YouTube PokerGO channel.
Extracts channel info, playlists, and video metadata without downloading.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from yt_dlp import YoutubeDL

from pokergo_downloader.database.models import Source
from pokergo_downloader.database.repository import Repository

logger = logging.getLogger(__name__)

# PokerGO YouTube channel URL
POKERGO_YOUTUBE_CHANNEL = "https://www.youtube.com/@PokerGO"
POKERGO_YOUTUBE_VIDEOS = "https://www.youtube.com/@PokerGO/videos"
POKERGO_YOUTUBE_PLAYLISTS = "https://www.youtube.com/@PokerGO/playlists"


class YouTubeCrawler:
    """
    YouTube metadata crawler using yt-dlp.

    Extracts metadata without downloading videos.
    Stores results in the database for Phase 2 download.

    Usage:
        crawler = YouTubeCrawler(repo)
        await crawler.crawl_channel()
    """

    def __init__(self, repo: Repository, verbose: bool = False, use_cookies: str | None = None):
        self.repo = repo
        self.verbose = verbose
        self.use_cookies = use_cookies  # "edge", "chrome", "firefox", or None
        self._ydl_opts = self._get_ydl_options()

    def _get_ydl_options(self) -> dict[str, Any]:
        """Get yt-dlp options for metadata extraction only."""
        opts = {
            "quiet": not self.verbose,
            "no_warnings": not self.verbose,
            "extract_flat": False,  # Get full metadata
            "skip_download": True,  # Don't download, just extract info
            "ignoreerrors": True,  # Continue on errors
            "no_color": True,
            # Extract additional metadata
            "writeinfojson": False,
            "writethumbnail": False,
            "writesubtitles": False,
        }
        # Add browser cookies for authentication
        if self.use_cookies:
            opts["cookiesfrombrowser"] = (self.use_cookies,)
        return opts

    def _get_flat_options(self) -> dict[str, Any]:
        """Get yt-dlp options for flat playlist extraction (faster)."""
        opts = {
            "quiet": not self.verbose,
            "no_warnings": not self.verbose,
            "extract_flat": True,  # Only get basic info, no full extraction
            "skip_download": True,
            "ignoreerrors": True,
            "no_color": True,
        }
        # Add browser cookies for authentication
        if self.use_cookies:
            opts["cookiesfrombrowser"] = (self.use_cookies,)
        return opts

    def _parse_upload_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse yt-dlp date string (YYYYMMDD) to datetime."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            return None

    def crawl_channel_info(self) -> Optional[dict[str, Any]]:
        """
        Extract channel metadata.

        Returns channel info dict with:
        - id, title, description, thumbnail, subscriber_count, etc.
        """
        logger.info(f"Crawling channel info: {POKERGO_YOUTUBE_CHANNEL}")

        with YoutubeDL(self._get_flat_options()) as ydl:
            try:
                info = ydl.extract_info(POKERGO_YOUTUBE_CHANNEL, download=False)
                if info:
                    return {
                        "channel_id": info.get("channel_id") or info.get("id"),
                        "name": info.get("channel") or info.get("uploader") or "PokerGO",
                        "description": info.get("description"),
                        "thumbnail_url": info.get("thumbnail"),
                        "subscriber_count": info.get("subscriber_count"),
                        "url": info.get("channel_url") or POKERGO_YOUTUBE_CHANNEL,
                    }
            except Exception as e:
                logger.error(f"Failed to extract channel info: {e}")
                return None
        return None

    def crawl_playlists(self) -> list[dict[str, Any]]:
        """
        Extract all playlists from the channel.

        Returns list of playlist info dicts.
        """
        logger.info(f"Crawling playlists: {POKERGO_YOUTUBE_PLAYLISTS}")
        playlists = []

        with YoutubeDL(self._get_flat_options()) as ydl:
            try:
                info = ydl.extract_info(POKERGO_YOUTUBE_PLAYLISTS, download=False)
                if info and "entries" in info:
                    for entry in info["entries"]:
                        if entry:
                            playlists.append(
                                {
                                    "playlist_id": entry.get("id"),
                                    "title": entry.get("title"),
                                    "url": entry.get("url"),
                                    "video_count": entry.get("playlist_count"),
                                    "thumbnail_url": entry.get("thumbnail"),
                                }
                            )
            except Exception as e:
                logger.error(f"Failed to extract playlists: {e}")

        logger.info(f"Found {len(playlists)} playlists")
        return playlists

    def crawl_channel_videos(
        self, limit: Optional[int] = None, full_metadata: bool = False
    ) -> list[dict[str, Any]]:
        """
        Extract video list from channel.

        Args:
            limit: Maximum number of videos to extract (None = all)
            full_metadata: If True, extract full metadata (slower)

        Returns list of video info dicts.
        """
        logger.info(f"Crawling channel videos: {POKERGO_YOUTUBE_VIDEOS}")
        videos = []

        opts = self._ydl_opts if full_metadata else self._get_flat_options()
        if limit:
            opts["playlistend"] = limit

        with YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(POKERGO_YOUTUBE_VIDEOS, download=False)
                if info and "entries" in info:
                    for entry in info["entries"]:
                        if entry:
                            video_data = self._parse_video_info(entry, full_metadata)
                            if video_data:
                                videos.append(video_data)
            except Exception as e:
                logger.error(f"Failed to extract channel videos: {e}")

        logger.info(f"Found {len(videos)} videos")
        return videos

    def crawl_playlist_videos(
        self, playlist_url: str, full_metadata: bool = False
    ) -> list[dict[str, Any]]:
        """
        Extract videos from a specific playlist.

        Args:
            playlist_url: YouTube playlist URL
            full_metadata: If True, extract full metadata (slower)

        Returns list of video info dicts.
        """
        logger.info(f"Crawling playlist: {playlist_url}")
        videos = []

        opts = self._ydl_opts if full_metadata else self._get_flat_options()

        with YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(playlist_url, download=False)
                if info and "entries" in info:
                    for i, entry in enumerate(info["entries"]):
                        if entry:
                            video_data = self._parse_video_info(entry, full_metadata)
                            if video_data:
                                video_data["playlist_position"] = i + 1
                                videos.append(video_data)
            except Exception as e:
                logger.error(f"Failed to extract playlist videos: {e}")

        logger.info(f"Found {len(videos)} videos in playlist")
        return videos

    def crawl_video_metadata(self, video_url: str) -> Optional[dict[str, Any]]:
        """
        Extract full metadata for a single video.

        Args:
            video_url: YouTube video URL or ID

        Returns video info dict or None.
        """
        # Handle video ID
        if not video_url.startswith("http"):
            video_url = f"https://www.youtube.com/watch?v={video_url}"

        logger.debug(f"Crawling video: {video_url}")

        with YoutubeDL(self._ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                if info:
                    return self._parse_video_info(info, full_metadata=True)
            except Exception as e:
                logger.error(f"Failed to extract video info: {e}")
                return None
        return None

    def _parse_video_info(
        self, info: dict[str, Any], full_metadata: bool = False
    ) -> Optional[dict[str, Any]]:
        """Parse yt-dlp info dict to our format."""
        if not info:
            return None

        video_id = info.get("id")
        if not video_id:
            return None

        data = {
            "video_id": video_id,
            "title": info.get("title"),
            "description": info.get("description"),
            "thumbnail_url": info.get("thumbnail"),
            "duration": info.get("duration"),
            "upload_date": self._parse_upload_date(info.get("upload_date")),
            "url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}",
        }

        if full_metadata:
            data.update(
                {
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "comment_count": info.get("comment_count"),
                    "tags": json.dumps(info.get("tags", [])) if info.get("tags") else None,
                    "available_qualities": self._extract_qualities(info),
                }
            )

        return data

    def _extract_qualities(self, info: dict[str, Any]) -> Optional[str]:
        """Extract available video qualities."""
        formats = info.get("formats", [])
        qualities = set()

        for fmt in formats:
            height = fmt.get("height")
            if height:
                qualities.add(f"{height}p")

        if qualities:
            return json.dumps(sorted(qualities, key=lambda x: int(x[:-1]), reverse=True))
        return None

    # ==================== Database Integration ====================

    def sync_channel_to_db(self) -> Optional[int]:
        """
        Crawl channel and save to database.

        Returns channel database ID or None on failure.
        """
        channel_info = self.crawl_channel_info()
        if not channel_info:
            logger.error("Failed to get channel info")
            return None

        channel = self.repo.upsert_channel(
            channel_id=channel_info["channel_id"],
            source=Source.YOUTUBE,
            name=channel_info["name"],
            url=channel_info["url"],
            description=channel_info.get("description"),
            thumbnail_url=channel_info.get("thumbnail_url"),
            subscriber_count=channel_info.get("subscriber_count"),
        )

        logger.info(f"Saved channel: {channel.name} (ID: {channel.id})")
        return channel.id

    def sync_videos_to_db(
        self,
        channel_db_id: int,
        limit: Optional[int] = None,
        full_metadata: bool = False,
    ) -> tuple[int, int, int]:
        """
        Crawl videos and save to database.

        Returns (total, new, updated) counts.
        """
        videos = self.crawl_channel_videos(limit=limit, full_metadata=full_metadata)

        total = len(videos)
        new_count = 0
        updated_count = 0

        for video_data in videos:
            existing = self.repo.get_video(video_data["video_id"], Source.YOUTUBE)

            self.repo.upsert_video(
                video_id=video_data["video_id"],
                channel_id=channel_db_id,
                source=Source.YOUTUBE,
                title=video_data["title"],
                description=video_data.get("description"),
                thumbnail_url=video_data.get("thumbnail_url"),
                duration=video_data.get("duration"),
                view_count=video_data.get("view_count"),
                like_count=video_data.get("like_count"),
                comment_count=video_data.get("comment_count"),
                upload_date=video_data.get("upload_date"),
                tags=video_data.get("tags"),
                available_qualities=video_data.get("available_qualities"),
            )

            if existing:
                updated_count += 1
            else:
                new_count += 1

        logger.info(f"Synced {total} videos: {new_count} new, {updated_count} updated")

        # Record crawl history
        self.repo.add_crawl_history(
            source=Source.YOUTUBE,
            target_type="channel_videos",
            target_id=str(channel_db_id),
            items_found=total,
            items_new=new_count,
            items_updated=updated_count,
        )

        return total, new_count, updated_count

    def sync_playlists_to_db(self, channel_db_id: int) -> int:
        """
        Crawl playlists and save to database.

        Returns number of playlists synced.
        """
        playlists = self.crawl_playlists()

        for playlist_data in playlists:
            self.repo.upsert_playlist(
                playlist_id=playlist_data["playlist_id"],
                channel_id=channel_db_id,
                source=Source.YOUTUBE,
                title=playlist_data["title"],
                thumbnail_url=playlist_data.get("thumbnail_url"),
                video_count=playlist_data.get("video_count"),
            )

        logger.info(f"Synced {len(playlists)} playlists")
        return len(playlists)

    def full_sync(
        self,
        video_limit: Optional[int] = None,
        full_metadata: bool = False,
        include_playlists: bool = True,
    ) -> dict[str, Any]:
        """
        Perform full sync of YouTube channel.

        Args:
            video_limit: Max videos to sync (None = all)
            full_metadata: Extract detailed video metadata
            include_playlists: Also sync playlists

        Returns dict with sync statistics.
        """
        logger.info("Starting full YouTube sync...")

        # Sync channel
        channel_db_id = self.sync_channel_to_db()
        if not channel_db_id:
            return {"success": False, "error": "Failed to sync channel"}

        # Sync videos
        total, new, updated = self.sync_videos_to_db(
            channel_db_id, limit=video_limit, full_metadata=full_metadata
        )

        result = {
            "success": True,
            "channel_id": channel_db_id,
            "videos": {"total": total, "new": new, "updated": updated},
        }

        # Sync playlists
        if include_playlists:
            playlist_count = self.sync_playlists_to_db(channel_db_id)
            result["playlists"] = playlist_count

        logger.info(f"Full sync complete: {result}")
        return result
