"""
Chunked Exporter for PokerGO Crawler.

5MB 단위로 파일을 분할 저장하고 인덱스 생성.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pokergo_downloader.config import settings
from pokergo_downloader.database.models import Source
from pokergo_downloader.database.repository import Repository

logger = logging.getLogger(__name__)


class ChunkedExporter:
    """Export videos to chunked JSON files with index."""

    def __init__(self, repo: Repository, max_size_bytes: int | None = None):
        self.repo = repo
        self.max_size_bytes = max_size_bytes or settings.max_file_size_bytes

    def export_all(self, source: Source | None = None) -> dict[str, Any]:
        """
        Export all data with chunking.

        Returns export summary.
        """
        settings.ensure_directories()

        result = {
            "channel": self._export_channel(source),
            "videos": self._export_videos_chunked(source),
            "playlists": self._export_playlists(source),
            "urls": self._export_urls(source),
        }

        # Create index
        self._create_index(result, source)

        return result

    def _export_channel(self, source: Source | None) -> dict[str, Any] | None:
        """Export channel info to channel.json."""
        source_filter = source or Source.YOUTUBE
        channels = self.repo.get_channels_by_source(source_filter)

        if not channels:
            return None

        ch = channels[0]
        channel_data = {
            "channel_id": ch.channel_id,
            "name": ch.name,
            "description": ch.description,
            "url": ch.url,
            "subscriber_count": ch.subscriber_count,
            "video_count": ch.video_count,
            "thumbnail_url": ch.thumbnail_url,
            "exported_at": datetime.now().isoformat(),
        }

        with open(settings.channel_path, "w", encoding="utf-8") as f:
            json.dump(channel_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported channel: {settings.channel_path}")
        return channel_data

    def _export_videos_chunked(self, source: Source | None) -> dict[str, Any]:
        """Export videos to multiple chunked files."""
        videos = self.repo.get_videos(source=source)

        if not videos:
            return {"total": 0, "files": []}

        # Convert to exportable format
        video_list = []
        for video in videos:
            duration_formatted = None
            if video.duration:
                hours, remainder = divmod(video.duration, 3600)
                mins, secs = divmod(remainder, 60)
                if hours > 0:
                    duration_formatted = f"{hours}:{mins:02d}:{secs:02d}"
                else:
                    duration_formatted = f"{mins}:{secs:02d}"

            video_list.append({
                "video_id": video.video_id,
                "title": video.title,
                "description": video.description,
                "source": video.source.value,
                "url": video.url,
                "duration": video.duration,
                "duration_formatted": duration_formatted,
                "upload_date": video.upload_date.strftime("%Y-%m-%d") if video.upload_date else None,
                "view_count": video.view_count,
                "like_count": video.like_count,
                "comment_count": video.comment_count,
                "thumbnail_url": video.thumbnail_url,
                "tags": json.loads(video.tags) if video.tags else [],
            })

        # Chunk by size
        chunks = self._split_by_size(video_list)

        # Write chunks
        file_info = []
        for i, chunk in enumerate(chunks, 1):
            filename = f"videos_{i:03d}.json"
            filepath = settings.videos_path / filename

            chunk_data = {
                "chunk": i,
                "total_chunks": len(chunks),
                "count": len(chunk),
                "videos": chunk,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)

            file_size = filepath.stat().st_size
            file_info.append({
                "file": f"videos/{filename}",
                "chunk": i,
                "count": len(chunk),
                "size_bytes": file_size,
                "first_id": chunk[0]["video_id"] if chunk else None,
                "last_id": chunk[-1]["video_id"] if chunk else None,
            })

            logger.info(f"Exported chunk {i}/{len(chunks)}: {filename} ({len(chunk)} videos, {file_size / 1024:.1f}KB)")

        return {
            "total": len(video_list),
            "files": file_info,
        }

    def _split_by_size(self, items: list[dict]) -> list[list[dict]]:
        """Split items into chunks based on JSON size."""
        chunks = []
        current_chunk = []
        current_size = 0

        # Overhead for chunk wrapper
        overhead = 100

        for item in items:
            item_size = len(json.dumps(item, ensure_ascii=False).encode("utf-8"))

            # If adding this item exceeds limit, start new chunk
            if current_size + item_size > self.max_size_bytes - overhead and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0

            current_chunk.append(item)
            current_size += item_size

        # Add remaining
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _export_playlists(self, source: Source | None) -> dict[str, Any]:
        """Export playlists to playlists.json."""
        playlists = self.repo.get_playlists(source=source) if source else self.repo.get_playlists()

        if not playlists:
            return {"total": 0, "file": None}

        playlist_list = []
        for playlist in playlists:
            playlist_list.append({
                "playlist_id": playlist.playlist_id,
                "title": playlist.title,
                "description": playlist.description,
                "video_count": playlist.video_count,
                "thumbnail_url": playlist.thumbnail_url,
            })

        filepath = settings.playlists_path / "playlists.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "count": len(playlist_list),
                "playlists": playlist_list,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported playlists: {filepath}")
        return {
            "total": len(playlist_list),
            "file": "playlists/playlists.json",
        }

    def _export_urls(self, source: Source | None) -> dict[str, Any]:
        """Export video URLs for 4K Downloader."""
        videos = self.repo.get_videos(source=source)

        if not videos:
            return {"total": 0, "file": None}

        urls = [video.url for video in videos]

        filepath = settings.urls_path / "youtube_urls.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(urls))

        logger.info(f"Exported URLs: {filepath}")
        return {
            "total": len(urls),
            "file": "urls/youtube_urls.txt",
        }

    def _create_index(self, export_result: dict, source: Source | None) -> None:
        """Create searchable index.json."""
        videos = self.repo.get_videos(source=source)

        # Build video index (video_id → title, file mapping)
        video_index = {}
        video_files = export_result.get("videos", {}).get("files", [])

        # Map videos to their chunk files
        file_mapping = {}
        for file_info in video_files:
            file_mapping[file_info["chunk"]] = file_info["file"]

        # Assign each video to its file
        chunk_idx = 0
        current_count = 0
        chunk_sizes = [f["count"] for f in video_files]

        for video in videos:
            # Find which chunk this video is in
            while chunk_idx < len(chunk_sizes) and current_count >= chunk_sizes[chunk_idx]:
                current_count = 0
                chunk_idx += 1

            if chunk_idx < len(video_files):
                video_index[video.video_id] = {
                    "title": video.title,
                    "file": video_files[chunk_idx]["file"],
                }
                current_count += 1

        index_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "source": (source.value if source else "youtube"),
                "total_videos": export_result.get("videos", {}).get("total", 0),
                "total_playlists": export_result.get("playlists", {}).get("total", 0),
                "total_files": len(video_files),
                "max_file_size_mb": settings.max_file_size_mb,
            },
            "channel": export_result.get("channel"),
            "files": video_files,
            "playlists_file": export_result.get("playlists", {}).get("file"),
            "urls_file": export_result.get("urls", {}).get("file"),
            "videos": video_index,
        }

        with open(settings.index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Created index: {settings.index_path}")

    def create_snapshot(self, source: Source | None = None) -> Path:
        """Create timestamped snapshot of current exports."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        snapshot_dir = settings.snapshots_path / timestamp

        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Copy current exports to snapshot
        import shutil

        if settings.index_path.exists():
            shutil.copy(settings.index_path, snapshot_dir / "index.json")

        if settings.channel_path.exists():
            shutil.copy(settings.channel_path, snapshot_dir / "channel.json")

        # Copy videos directory
        if settings.videos_path.exists():
            shutil.copytree(settings.videos_path, snapshot_dir / "videos", dirs_exist_ok=True)

        # Copy playlists
        if settings.playlists_path.exists():
            shutil.copytree(settings.playlists_path, snapshot_dir / "playlists", dirs_exist_ok=True)

        logger.info(f"Created snapshot: {snapshot_dir}")
        return snapshot_dir
