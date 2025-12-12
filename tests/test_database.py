"""
Tests for database models and repository.
"""

import tempfile
from pathlib import Path

import pytest

from pokergo_downloader.database.models import DownloadStatus, Source
from pokergo_downloader.database.repository import Repository


@pytest.fixture
def repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repository = Repository(str(db_path))
        repository.init_db()
        yield repository


class TestChannel:
    """Tests for Channel operations."""

    def test_create_channel(self, repo: Repository):
        """Test creating a new channel."""
        channel = repo.upsert_channel(
            channel_id="UC123456",
            source=Source.YOUTUBE,
            name="Test Channel",
            url="https://youtube.com/@test",
            description="A test channel",
        )

        assert channel.id is not None
        assert channel.channel_id == "UC123456"
        assert channel.source == Source.YOUTUBE
        assert channel.name == "Test Channel"

    def test_update_channel(self, repo: Repository):
        """Test updating an existing channel."""
        # Create
        channel1 = repo.upsert_channel(
            channel_id="UC123456",
            source=Source.YOUTUBE,
            name="Original Name",
            url="https://youtube.com/@test",
        )

        # Update
        channel2 = repo.upsert_channel(
            channel_id="UC123456",
            source=Source.YOUTUBE,
            name="Updated Name",
            url="https://youtube.com/@test",
        )

        assert channel1.id == channel2.id
        assert channel2.name == "Updated Name"

    def test_get_channels_by_source(self, repo: Repository):
        """Test getting channels filtered by source."""
        repo.upsert_channel(
            channel_id="UC111",
            source=Source.YOUTUBE,
            name="YouTube Channel",
            url="https://youtube.com/@yt",
        )
        repo.upsert_channel(
            channel_id="PG222",
            source=Source.POKERGO_WEB,
            name="PokerGO Channel",
            url="https://pokergo.com",
        )

        youtube_channels = repo.get_channels_by_source(Source.YOUTUBE)
        pokergo_channels = repo.get_channels_by_source(Source.POKERGO_WEB)

        assert len(youtube_channels) == 1
        assert len(pokergo_channels) == 1
        assert youtube_channels[0].name == "YouTube Channel"


class TestVideo:
    """Tests for Video operations."""

    def test_create_video(self, repo: Repository):
        """Test creating a new video."""
        channel = repo.upsert_channel(
            channel_id="UC123",
            source=Source.YOUTUBE,
            name="Test",
            url="https://youtube.com/@test",
        )

        video = repo.upsert_video(
            video_id="abc123",
            channel_id=channel.id,
            source=Source.YOUTUBE,
            title="Test Video",
            description="A test video",
            duration=300,
        )

        assert video.id is not None
        assert video.video_id == "abc123"
        assert video.title == "Test Video"
        assert video.duration == 300
        assert video.download_status == DownloadStatus.PENDING

    def test_update_download_status(self, repo: Repository):
        """Test updating video download status."""
        channel = repo.upsert_channel(
            channel_id="UC123",
            source=Source.YOUTUBE,
            name="Test",
            url="https://youtube.com/@test",
        )

        repo.upsert_video(
            video_id="abc123",
            channel_id=channel.id,
            source=Source.YOUTUBE,
            title="Test Video",
        )

        updated = repo.update_download_status(
            video_id="abc123",
            source=Source.YOUTUBE,
            status=DownloadStatus.COMPLETED,
            file_path="/path/to/video.mp4",
            file_size=1024000,
        )

        assert updated is not None
        assert updated.download_status == DownloadStatus.COMPLETED
        assert updated.file_path == "/path/to/video.mp4"
        assert updated.file_size == 1024000

    def test_get_pending_downloads(self, repo: Repository):
        """Test getting videos pending download."""
        channel = repo.upsert_channel(
            channel_id="UC123",
            source=Source.YOUTUBE,
            name="Test",
            url="https://youtube.com/@test",
        )

        # Create videos with different statuses
        repo.upsert_video(
            video_id="v1",
            channel_id=channel.id,
            source=Source.YOUTUBE,
            title="Pending Video",
        )

        repo.upsert_video(
            video_id="v2",
            channel_id=channel.id,
            source=Source.YOUTUBE,
            title="Another Video",
        )

        repo.update_download_status(
            video_id="v2",
            source=Source.YOUTUBE,
            status=DownloadStatus.COMPLETED,
        )

        pending = repo.get_pending_downloads()
        assert len(pending) == 1
        assert pending[0].video_id == "v1"


class TestStats:
    """Tests for statistics."""

    def test_get_stats(self, repo: Repository):
        """Test getting database statistics."""
        # Create test data
        channel = repo.upsert_channel(
            channel_id="UC123",
            source=Source.YOUTUBE,
            name="Test",
            url="https://youtube.com/@test",
        )

        repo.upsert_video(
            video_id="v1",
            channel_id=channel.id,
            source=Source.YOUTUBE,
            title="Video 1",
        )

        repo.upsert_video(
            video_id="v2",
            channel_id=channel.id,
            source=Source.YOUTUBE,
            title="Video 2",
        )

        stats = repo.get_stats()

        assert stats["channels"] == 1
        assert stats["videos"]["total"] == 2
        assert stats["videos"]["youtube"] == 2
        assert stats["downloads"]["pending"] == 2
