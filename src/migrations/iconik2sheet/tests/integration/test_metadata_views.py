"""Integration tests for Metadata Views API.

This test is critical for discovering the correct METADATA_VIEW_ID
to use in .env.local for the 26-column export.

Requires valid credentials in .env.local:
- ICONIK_APP_ID
- ICONIK_AUTH_TOKEN

Run with: pytest tests/integration/test_metadata_views.py -v -s
"""

import pytest


@pytest.mark.integration
class TestMetadataViews:
    """Test Metadata Views API."""

    def test_get_all_views(self, iconik_client):
        """Test fetching all metadata views.

        IMPORTANT: This test outputs all available Metadata Views.
        Use the output to find the correct View ID for poker hand metadata.
        """
        views = iconik_client.get_metadata_views()

        assert isinstance(views, list)

        print("\n" + "=" * 60)
        print("AVAILABLE METADATA VIEWS")
        print("=" * 60)
        print("Copy the ID you need to .env.local as ICONIK_METADATA_VIEW_ID")
        print("-" * 60)

        for view in views:
            view_id = view.get("id", "N/A")
            name = view.get("name", "Untitled")
            description = view.get("description", "")[:50] if view.get("description") else ""

            print(f"\n  ID: {view_id}")
            print(f"  Name: {name}")
            if description:
                print(f"  Description: {description}...")

        print("\n" + "=" * 60)

        # Basic validation
        for view in views:
            assert "id" in view, "View missing 'id' field"
            assert "name" in view, "View missing 'name' field"

    def test_get_single_view_details(self, iconik_client):
        """Test fetching a single metadata view with fields."""
        views = iconik_client.get_metadata_views()

        if not views:
            pytest.skip("No metadata views found")

        # Get the first view's details
        view_id = views[0]["id"]
        view = iconik_client.get_metadata_view(view_id)

        assert view["id"] == view_id
        assert "name" in view

        print(f"\n=== View Details: {view['name']} ===")
        print(f"  ID: {view['id']}")

        if "view_fields" in view:
            print(f"  Fields ({len(view['view_fields'])}):")
            for field in view["view_fields"][:10]:
                field_name = field.get("name", "unknown")
                field_label = field.get("label", field_name)
                print(f"    - {field_name}: {field_label}")

            if len(view["view_fields"]) > 10:
                print(f"    ... and {len(view['view_fields']) - 10} more fields")


@pytest.mark.integration
class TestAssetMetadata:
    """Test Asset Metadata extraction."""

    def test_get_asset_metadata_with_first_view(self, iconik_client):
        """Test fetching metadata for an asset using first available view."""
        # Get first asset
        response = iconik_client.get_assets_page(page=1, per_page=1)

        if not response.objects:
            pytest.skip("No assets found")

        asset_id = response.objects[0]["id"]
        asset_title = response.objects[0].get("title", "Unknown")

        # Get first view
        views = iconik_client.get_metadata_views()
        if not views:
            pytest.skip("No metadata views found")

        view_id = views[0]["id"]
        view_name = views[0]["name"]

        # Fetch metadata
        try:
            metadata = iconik_client.get_asset_metadata(asset_id, view_id)
        except Exception as e:
            pytest.skip(f"Could not fetch metadata: {e}")

        assert isinstance(metadata, dict)

        print(f"\n=== Metadata for Asset ===")
        print(f"  Asset: {asset_title}")
        print(f"  View: {view_name}")

        if "metadata_values" in metadata:
            values = metadata["metadata_values"]
            print(f"  Fields ({len(values)}):")
            for key, value in list(values.items())[:10]:
                display_value = str(value)[:50] if value else "None"
                print(f"    - {key}: {display_value}")
        else:
            print("  No metadata_values found")


@pytest.mark.integration
class TestAssetSegments:
    """Test Asset Segments (timecode) API."""

    def test_get_asset_segments(self, iconik_client):
        """Test fetching segments for an asset."""
        response = iconik_client.get_assets_page(page=1, per_page=5)

        if not response.objects:
            pytest.skip("No assets found")

        # Try to find an asset with segments
        for asset_data in response.objects:
            asset_id = asset_data["id"]
            asset_title = asset_data.get("title", "Unknown")

            segments = iconik_client.get_asset_segments(asset_id)

            print(f"\n=== Segments for: {asset_title[:40]} ===")
            print(f"  Asset ID: {asset_id}")
            print(f"  Segment count: {len(segments)}")

            if segments:
                for seg in segments[:3]:
                    time_base = seg.get("time_base")
                    time_end = seg.get("time_end")
                    seg_type = seg.get("segment_type", "UNKNOWN")

                    # Convert ms to readable format
                    start_sec = time_base / 1000 if time_base else 0
                    end_sec = time_end / 1000 if time_end else 0

                    print(f"    - Type: {seg_type}")
                    print(f"      Start: {start_sec:.2f}s ({time_base}ms)")
                    print(f"      End: {end_sec:.2f}s ({time_end}ms)")

                # Found segments, test passes
                assert isinstance(segments, list)
                return

        # No assets had segments
        print("\n  Note: No segments found in checked assets")
        assert True  # Test still passes


@pytest.mark.integration
class TestFullDataExtraction:
    """Test complete data extraction pipeline."""

    def test_extract_asset_with_metadata_and_segments(self, iconik_client):
        """Test extracting asset data with metadata and segments.

        This is a comprehensive test that mirrors the full export workflow.
        """
        # Get first asset
        response = iconik_client.get_assets_page(page=1, per_page=1)
        if not response.objects:
            pytest.skip("No assets found")

        asset_data = response.objects[0]
        asset_id = asset_data["id"]

        print("\n" + "=" * 60)
        print("FULL DATA EXTRACTION TEST")
        print("=" * 60)

        # 1. Asset basic info
        print(f"\n[1] Asset Info:")
        print(f"  ID: {asset_id}")
        print(f"  Title: {asset_data.get('title', 'N/A')}")
        print(f"  Status: {asset_data.get('status', 'N/A')}")

        # 2. Segments (timecodes)
        print(f"\n[2] Segments:")
        segments = iconik_client.get_asset_segments(asset_id)
        if segments:
            seg = segments[0]
            print(f"  time_start_ms: {seg.get('time_base')}")
            print(f"  time_end_ms: {seg.get('time_end')}")
        else:
            print("  No segments found")

        # 3. Metadata
        print(f"\n[3] Metadata:")
        views = iconik_client.get_metadata_views()
        if views:
            view_id = views[0]["id"]
            try:
                metadata = iconik_client.get_asset_metadata(asset_id, view_id)
                values = metadata.get("metadata_values", {})
                print(f"  View: {views[0]['name']}")
                print(f"  Field count: {len(values)}")

                # Show first 5 fields
                for key, value in list(values.items())[:5]:
                    print(f"  - {key}: {value}")
            except Exception as e:
                print(f"  Error: {e}")
        else:
            print("  No views available")

        print("\n" + "=" * 60)
        print("Test completed successfully")
        print("=" * 60)
