"""Unit tests for IconikClient error handling."""

from unittest.mock import MagicMock, patch

import pytest


class TestIconikExceptions:
    """Test custom exception classes."""

    def test_iconik_api_error_base(self):
        """Test base IconikAPIError."""
        from iconik.exceptions import IconikAPIError

        error = IconikAPIError("Something went wrong", status_code=500)
        assert str(error) == "Something went wrong"
        assert error.status_code == 500

    def test_iconik_not_found_error(self):
        """Test IconikNotFoundError (404)."""
        from iconik.exceptions import IconikNotFoundError

        error = IconikNotFoundError("Asset not found", status_code=404)
        assert error.status_code == 404
        assert "Asset not found" in str(error)

    def test_iconik_auth_error(self):
        """Test IconikAuthError (401/403)."""
        from iconik.exceptions import IconikAuthError

        error = IconikAuthError("Unauthorized", status_code=401)
        assert error.status_code == 401

    def test_iconik_rate_limit_error(self):
        """Test IconikRateLimitError (429)."""
        from iconik.exceptions import IconikRateLimitError

        error = IconikRateLimitError("Too many requests", status_code=429)
        assert error.status_code == 429


class TestClientGetMethod:
    """Test _get method error handling."""

    @pytest.fixture
    def mock_response(self):
        """Create mock httpx response."""
        response = MagicMock()
        response.json.return_value = {"data": "test"}
        return response

    def test_get_returns_none_on_404_when_disabled(self, mock_response):
        """Test _get returns None on 404 when raise_for_404=False."""
        from iconik.client import IconikClient

        mock_response.status_code = 404

        with patch.object(IconikClient, "client", new_callable=lambda: MagicMock()) as mock_client:
            mock_client.get.return_value = mock_response

            client = IconikClient.__new__(IconikClient)
            client._client = mock_client

            result = client._get("/test", raise_for_404=False)
            assert result is None

    def test_get_raises_not_found_on_404_by_default(self, mock_response):
        """Test _get raises IconikNotFoundError on 404 by default."""
        from iconik.client import IconikClient
        from iconik.exceptions import IconikNotFoundError

        mock_response.status_code = 404

        with patch.object(IconikClient, "client", new_callable=lambda: MagicMock()) as mock_client:
            mock_client.get.return_value = mock_response

            client = IconikClient.__new__(IconikClient)
            client._client = mock_client

            with pytest.raises(IconikNotFoundError) as exc_info:
                client._get("/test")

            assert exc_info.value.status_code == 404

    def test_get_raises_auth_error_on_401(self, mock_response):
        """Test _get raises IconikAuthError on 401."""
        from iconik.client import IconikClient
        from iconik.exceptions import IconikAuthError

        mock_response.status_code = 401

        with patch.object(IconikClient, "client", new_callable=lambda: MagicMock()) as mock_client:
            mock_client.get.return_value = mock_response

            client = IconikClient.__new__(IconikClient)
            client._client = mock_client

            with pytest.raises(IconikAuthError) as exc_info:
                client._get("/test")

            assert exc_info.value.status_code == 401

    def test_get_raises_auth_error_on_403(self, mock_response):
        """Test _get raises IconikAuthError on 403."""
        from iconik.client import IconikClient
        from iconik.exceptions import IconikAuthError

        mock_response.status_code = 403

        with patch.object(IconikClient, "client", new_callable=lambda: MagicMock()) as mock_client:
            mock_client.get.return_value = mock_response

            client = IconikClient.__new__(IconikClient)
            client._client = mock_client

            with pytest.raises(IconikAuthError) as exc_info:
                client._get("/test")

            assert exc_info.value.status_code == 403

    def test_get_raises_rate_limit_on_429(self, mock_response):
        """Test _get raises IconikRateLimitError on 429."""
        from iconik.client import IconikClient
        from iconik.exceptions import IconikRateLimitError

        mock_response.status_code = 429

        with patch.object(IconikClient, "client", new_callable=lambda: MagicMock()) as mock_client:
            mock_client.get.return_value = mock_response

            client = IconikClient.__new__(IconikClient)
            client._client = mock_client

            with pytest.raises(IconikRateLimitError) as exc_info:
                client._get("/test")

            assert exc_info.value.status_code == 429

    def test_get_raises_api_error_on_500(self, mock_response):
        """Test _get raises IconikAPIError on 500."""
        from iconik.client import IconikClient
        from iconik.exceptions import IconikAPIError

        mock_response.status_code = 500

        with patch.object(IconikClient, "client", new_callable=lambda: MagicMock()) as mock_client:
            mock_client.get.return_value = mock_response

            client = IconikClient.__new__(IconikClient)
            client._client = mock_client

            with pytest.raises(IconikAPIError) as exc_info:
                client._get("/test")

            assert exc_info.value.status_code == 500

    def test_get_returns_json_on_success(self, mock_response):
        """Test _get returns JSON on success."""
        from iconik.client import IconikClient

        mock_response.status_code = 200

        with patch.object(IconikClient, "client", new_callable=lambda: MagicMock()) as mock_client:
            mock_client.get.return_value = mock_response

            client = IconikClient.__new__(IconikClient)
            client._client = mock_client

            result = client._get("/test")
            assert result == {"data": "test"}


class TestGetAssetMetadata:
    """Test get_asset_metadata with raise_for_404 option."""

    def test_returns_none_on_404_when_disabled(self):
        """Test returns None on 404 when raise_for_404=False."""
        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get", return_value=None) as mock_get:
            client = IconikClient.__new__(IconikClient)
            result = client.get_asset_metadata("asset-123", "view-456", raise_for_404=False)

            mock_get.assert_called_once_with(
                "/metadata/v1/assets/asset-123/views/view-456/",
                raise_for_404=False,
            )
            assert result is None

    def test_returns_metadata_on_success(self):
        """Test returns metadata dict on success."""
        from iconik.client import IconikClient

        expected = {"metadata_values": {"field": "value"}}

        with patch.object(IconikClient, "_get", return_value=expected):
            client = IconikClient.__new__(IconikClient)
            result = client.get_asset_metadata("asset-123", "view-456")

            assert result == expected


class TestGetAssetSegments:
    """Test get_asset_segments with raise_for_404 option."""

    def test_returns_empty_list_on_404_when_disabled(self):
        """Test returns empty list on 404 when raise_for_404=False."""
        from iconik.client import IconikClient

        with patch.object(IconikClient, "_get", return_value=None):
            client = IconikClient.__new__(IconikClient)
            result = client.get_asset_segments("asset-123", raise_for_404=False)

            assert result == []

    def test_returns_segments_on_success(self):
        """Test returns segments list on success."""
        from iconik.client import IconikClient

        expected = {"objects": [{"time_base": 1000, "time_end": 2000}]}

        with patch.object(IconikClient, "_get", return_value=expected):
            client = IconikClient.__new__(IconikClient)
            result = client.get_asset_segments("asset-123")

            assert result == [{"time_base": 1000, "time_end": 2000}]
