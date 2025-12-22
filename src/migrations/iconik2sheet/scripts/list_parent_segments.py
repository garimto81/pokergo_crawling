"""List segments on parent assets where bulk import created them."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient

# Parent assets from the bulk create output
PARENT_ASSETS = [
    ("fbb7e94e-4127-11f0-bf53-7216fc2efa1a", "WS11_ME03_NB"),
    ("ea200c74-4cf3-11f0-b006-fa75e68441df", "WSOP 2025 Event #37"),
    ("2c241e64-fd5a-11ef-8b68-ca3810e537de", "E01_GOG_final_edit"),
    ("d395f362-63af-11f0-a69b-ce32bb00c45e", "2009 WSOP ME09"),
]

print("=== Parent Asset Segments (Bulk Import) ===\n")

with IconikClient() as client:
    for asset_id, name in PARENT_ASSETS:
        print(f"Parent: {name}")
        print(f"URL: https://app.iconik.io/asset/{asset_id}")

        response = client.client.get(f"/assets/v1/assets/{asset_id}/segments/")
        data = response.json()

        segments = data.get("objects", [])
        bulk_count = 0

        if segments:
            print(f"Total segments: {len(segments)}")
            for seg in segments:
                title = seg.get("title", "")
                start = seg.get("time_start_milliseconds", 0)
                end = seg.get("time_end_milliseconds", 0)

                if "Bulk Import" in str(title):
                    bulk_count += 1
                    start_sec = start / 1000
                    end_sec = end / 1000
                    print(f"  * {start_sec:.1f}s - {end_sec:.1f}s | {title}")

            print(f"Bulk Import segments: {bulk_count}")
        else:
            print("  No segments")

        print()

print("\n" + "=" * 60)
print("HOW TO FIND IN ICONIK WEB UI:")
print("=" * 60)
print("""
1. Direct URL Access:
   https://app.iconik.io/asset/fbb7e94e-4127-11f0-bf53-7216fc2efa1a

2. Search by Segment Title:
   - Go to iconik.io
   - Open any asset with segments
   - Look for 'Bulk Import:' in segment panel

3. Search by Asset Title:
   - Search: "WS11_ME03_NB"
   - Open the asset
   - Check Timeline/Segments panel for 'Bulk Import' entries

4. Filter Recently Modified:
   - Sort by 'Date Modified'
   - Look for assets modified today
""")
