"""Integration tests for Iconik API connection.

Requires valid credentials in .env.local:
- ICONIK_APP_ID
- ICONIK_AUTH_TOKEN

Run with: pytest tests/integration/test_iconik_connection.py -v -s
"""

import pytest


@pytest.mark.integration
class TestIconikConnection:
    """Test real Iconik API connection."""

    def test_health_check(self, iconik_client):
        """Test API health check passes."""
        result = iconik_client.health_check()
        assert result is True, "Iconik API health check failed"

    def test_get_first_page(self, iconik_client):
        """Test fetching first page of assets."""
        response = iconik_client.get_assets_page(page=1, per_page=10)

        assert response.page == 1
        assert response.per_page == 10
        assert response.total >= 0

        print(f"\n=== Assets Page 1 ===")
        print(f"  Total assets: {response.total}")
        print(f"  Pages: {response.pages}")
        print(f"  Assets on this page: {len(response.objects)}")

    def test_get_single_asset(self, iconik_client):
        """Test fetching a single asset by ID."""
        # First get an asset ID from page 1
        response = iconik_client.get_assets_page(page=1, per_page=1)

        if not response.objects:
            pytest.skip("No assets found in Iconik")

        asset_id = response.objects[0]["id"]
        asset = iconik_client.get_asset(asset_id)

        assert asset.id == asset_id
        assert asset.title is not None

        print(f"\n=== Single Asset ===")
        print(f"  ID: {asset.id}")
        print(f"  Title: {asset.title}")
        print(f"  Status: {asset.status}")
        print(f"  Created: {asset.created_at}")


@pytest.mark.integration
class TestIconikCollections:
    """Test Collections API."""

    def test_get_collections_page(self, iconik_client):
        """Test fetching collections."""
        response = iconik_client.get_collections_page(page=1, per_page=10)

        assert response.page == 1
        assert response.total >= 0

        print(f"\n=== Collections ===")
        print(f"  Total: {response.total}")
        for col in response.objects[:5]:
            print(f"  - {col.get('title', 'Untitled')}")
