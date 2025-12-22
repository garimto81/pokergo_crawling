"""List all segments created by bulk import."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient

# Sample of assets we created segments for
TEST_ASSETS = [
    "623b5a30-63b9-11f0-b2c5-9e2846c90c6f",
    "d206796c-4cf3-11f0-a812-fa75e68441df",
    "072972ae-fd60-11ef-8c40-ca3810e537de",
    "82f1c376-fd60-11ef-abc8-ca3810e537de",
    "8e45b61c-fd60-11ef-9e50-ca3810e537de",
]

print("=== Bulk Import Segments Verification ===\n")

with IconikClient() as client:
    for asset_id in TEST_ASSETS:
        # Get asset info
        try:
            asset = client.get_asset(asset_id)
            title = asset.title[:50]
        except Exception:
            title = "(Unknown)"

        # Get segments
        response = client.client.get(f"/assets/v1/assets/{asset_id}/segments/")
        data = response.json()

        print(f"Asset: {asset_id[:8]}...")
        print(f"Title: {title}")
        print(f"URL: https://app.iconik.io/asset/{asset_id}")

        segments = data.get("objects", [])
        if segments:
            print(f"Segments ({len(segments)}):")
            for seg in segments:
                title = seg.get("title", "")
                start = seg.get("time_start_milliseconds", 0)
                end = seg.get("time_end_milliseconds", 0)
                seg_type = seg.get("segment_type", "")

                # Highlight bulk import segments
                marker = " <-- BULK IMPORT" if "Bulk Import" in str(title) else ""
                print(f"  - {start}ms - {end}ms | {seg_type} | {title}{marker}")
        else:
            print("  No segments (might be on parent asset)")

        print()

print("\n=== Search in iconik ===")
print("1. Go to: https://app.iconik.io")
print("2. Use Search box")
print("3. Search for: 'Bulk Import'")
print("4. Or filter by segment_type: GENERIC")
