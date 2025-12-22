"""Unit tests for IconikClient with mocking."""

from unittest.mock import MagicMock, patch

import pytest


class TestIconikClientInit:
    """Test client initialization."""

    @patch("iconik.client.get_settings")
    def test_headers_set(self, mock_get_settings, mock_settings):
        """Test auth headers are set correctly."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        client = IconikClient()

        assert client.headers["App-ID"] == "test-app-id"
        assert client.headers["Auth-Token"] == "test-auth-token"
        assert client.headers["Content-Type"] == "application/json"

    @patch("iconik.client.get_settings")
    def test_base_url_set(self, mock_get_settings, mock_settings):
        """Test base URL is set correctly."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        client = IconikClient()

        assert client.base_url == "https://app.iconik.io/API"

    @patch("iconik.client.get_settings")
    def test_lazy_client_init(self, mock_get_settings, mock_settings):
        """Test HTTP client is lazily initialized."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        client = IconikClient()

        # Client should be None initially (lazy init)
        assert client._client is None


class TestIconikClientContextManager:
    """Test context manager protocol."""

    @patch("iconik.client.get_settings")
    def test_enter_returns_self(self, mock_get_settings, mock_settings):
        """Test __enter__ returns self."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        client = IconikClient()
        result = client.__enter__()

        assert result is client

    @patch("iconik.client.get_settings")
    def test_exit_closes_client(self, mock_get_settings, mock_settings):
        """Test __exit__ closes client."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with IconikClient() as client:
            # Force client creation
            _ = client.client

        # After exit, _client should be None (closed)
        assert client._client is None


class TestIconikClientAssetsMethods:
    """Test Assets API methods."""

    @patch("iconik.client.get_settings")
    def test_get_assets_page(self, mock_get_settings, mock_settings, sample_paginated_assets):
        """Test get_assets_page returns paginated response."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get") as mock_get:
            mock_get.return_value = sample_paginated_assets

            client = IconikClient()
            response = client.get_assets_page(page=1)

            assert response.total == 1
            assert len(response.objects) == 1
            mock_get.assert_called_once()

    @patch("iconik.client.get_settings")
    def test_get_asset(self, mock_get_settings, mock_settings, sample_asset):
        """Test get_asset returns single asset."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get") as mock_get:
            mock_get.return_value = sample_asset

            client = IconikClient()
            asset = client.get_asset("12345678-1234-1234-1234-123456789abc")

            assert asset.id == "12345678-1234-1234-1234-123456789abc"
            assert asset.title == "WSOP 2024 Main Event Hand 42"


class TestIconikClientMetadataMethods:
    """Test Metadata API methods."""

    @patch("iconik.client.get_settings")
    def test_get_asset_metadata(self, mock_get_settings, mock_settings, sample_metadata):
        """Test get_asset_metadata returns metadata dict."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get") as mock_get:
            mock_get.return_value = sample_metadata

            client = IconikClient()
            metadata = client.get_asset_metadata("asset-123", "view-456")

            assert "metadata_values" in metadata
            assert metadata["metadata_values"]["project_name"] == "WSOP 2024"
            mock_get.assert_called_with(
                "/metadata/v1/assets/asset-123/views/view-456/",
                raise_for_404=True,
            )

    @patch("iconik.client.get_settings")
    def test_get_metadata_views(self, mock_get_settings, mock_settings, sample_metadata_views):
        """Test get_metadata_views returns list of views."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get") as mock_get:
            mock_get.return_value = sample_metadata_views

            client = IconikClient()
            views = client.get_metadata_views()

            assert len(views) == 2
            assert views[0]["name"] == "Poker Hand Metadata"
            mock_get.assert_called_with("/metadata/v1/views/")

    @patch("iconik.client.get_settings")
    def test_get_metadata_view(self, mock_get_settings, mock_settings):
        """Test get_metadata_view returns single view."""
        mock_get_settings.return_value = mock_settings
        view_response = {
            "id": "view-001",
            "name": "Poker Hand Metadata",
            "description": "WSOP clips",
            "view_fields": [{"name": "project_name"}, {"name": "game_type"}],
        }

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get") as mock_get:
            mock_get.return_value = view_response

            client = IconikClient()
            view = client.get_metadata_view("view-001")

            assert view["id"] == "view-001"
            assert len(view["view_fields"]) == 2
            mock_get.assert_called_with("/metadata/v1/views/view-001/")


class TestIconikClientSegmentsMethods:
    """Test Segments API methods."""

    @patch("iconik.client.get_settings")
    def test_get_asset_segments(self, mock_get_settings, mock_settings, sample_segments):
        """Test get_asset_segments returns list of segments."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get") as mock_get:
            mock_get.return_value = sample_segments

            client = IconikClient()
            segments = client.get_asset_segments("asset-123")

            assert len(segments) == 1
            assert segments[0]["time_base"] == 125000
            assert segments[0]["time_end"] == 180000
            mock_get.assert_called_with(
                "/assets/v1/assets/asset-123/segments/",
                raise_for_404=True,
            )

    @patch("iconik.client.get_settings")
    def test_create_asset_segment(self, mock_get_settings, mock_settings):
        """Test create_asset_segment creates a new segment."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_post") as mock_post:
            mock_post.return_value = {
                "id": "segment-new-123",
                "time_start_milliseconds": 100000,
                "time_end_milliseconds": 200000,
                "segment_type": "GENERIC",
            }

            client = IconikClient()
            result = client.create_asset_segment(
                asset_id="asset-123",
                time_start_ms=100000,
                time_end_ms=200000,
            )

            assert result["id"] == "segment-new-123"
            mock_post.assert_called_with(
                "/assets/v1/assets/asset-123/segments/",
                {
                    "time_start_milliseconds": 100000,
                    "time_end_milliseconds": 200000,
                    "segment_type": "GENERIC",
                },
            )

    @patch("iconik.client.get_settings")
    def test_update_asset_segment(self, mock_get_settings, mock_settings):
        """Test update_asset_segment updates an existing segment."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_put") as mock_put:
            mock_put.return_value = {
                "id": "segment-123",
                "time_start_milliseconds": 150000,
                "time_end_milliseconds": 250000,
                "segment_type": "GENERIC",
            }

            client = IconikClient()
            result = client.update_asset_segment(
                asset_id="asset-123",
                segment_id="segment-123",
                time_start_ms=150000,
                time_end_ms=250000,
            )

            assert result["time_start_milliseconds"] == 150000
            assert result["time_end_milliseconds"] == 250000
            mock_put.assert_called_with(
                "/assets/v1/assets/asset-123/segments/segment-123/",
                {
                    "time_start_milliseconds": 150000,
                    "time_end_milliseconds": 250000,
                },
            )

    @patch("iconik.client.get_settings")
    def test_update_asset_segment_with_type_and_title(self, mock_get_settings, mock_settings):
        """Test update_asset_segment with optional type and title."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_put") as mock_put:
            mock_put.return_value = {
                "id": "segment-123",
                "time_start_milliseconds": 150000,
                "time_end_milliseconds": 250000,
                "segment_type": "MARKER",
                "title": "Key moment",
            }

            client = IconikClient()
            result = client.update_asset_segment(
                asset_id="asset-123",
                segment_id="segment-123",
                time_start_ms=150000,
                time_end_ms=250000,
                segment_type="MARKER",
                title="Key moment",
            )

            assert result["segment_type"] == "MARKER"
            assert result["title"] == "Key moment"
            mock_put.assert_called_with(
                "/assets/v1/assets/asset-123/segments/segment-123/",
                {
                    "time_start_milliseconds": 150000,
                    "time_end_milliseconds": 250000,
                    "segment_type": "MARKER",
                    "title": "Key moment",
                },
            )

    @patch("iconik.client.get_settings")
    def test_delete_asset_segment(self, mock_get_settings, mock_settings):
        """Test delete_asset_segment deletes a segment."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        client = IconikClient()

        # Mock the underlying httpx client
        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_http_client = MagicMock()
        mock_http_client.delete.return_value = mock_response

        # Replace _client directly
        client._client = mock_http_client

        # Should not raise
        client.delete_asset_segment("asset-123", "segment-123")

        mock_http_client.delete.assert_called_with(
            "/assets/v1/assets/asset-123/segments/segment-123/"
        )

    @patch("iconik.client.get_settings")
    def test_delete_asset_segment_not_found(self, mock_get_settings, mock_settings):
        """Test delete_asset_segment raises on 404."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient
        from iconik.exceptions import IconikNotFoundError

        client = IconikClient()

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_http_client = MagicMock()
        mock_http_client.delete.return_value = mock_response

        # Replace _client directly
        client._client = mock_http_client

        with pytest.raises(IconikNotFoundError):
            client.delete_asset_segment("asset-123", "nonexistent-segment")


class TestIconikClientHealthCheck:
    """Test health check method."""

    @patch("iconik.client.get_settings")
    def test_health_check_success(self, mock_get_settings, mock_settings):
        """Test health_check returns True on success."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get") as mock_get:
            mock_get.return_value = {"objects": []}

            client = IconikClient()
            result = client.health_check()

            assert result is True

    @patch("iconik.client.get_settings")
    def test_health_check_failure(self, mock_get_settings, mock_settings):
        """Test health_check returns False on error."""
        mock_get_settings.return_value = mock_settings

        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            client = IconikClient()
            result = client.health_check()

            assert result is False
