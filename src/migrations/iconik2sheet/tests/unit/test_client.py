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
            mock_get.assert_called_with("/metadata/v1/assets/asset-123/views/view-456/")

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
            mock_get.assert_called_with("/assets/v1/assets/asset-123/segments/")


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
