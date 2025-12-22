"""Show all segments on WS11_ME03_NB parent asset."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient

asset_id = "fbb7e94e-4127-11f0-bf53-7216fc2efa1a"

print(f"=== All Segments on {asset_id} ===\n")
print(f"URL: https://app.iconik.io/asset/{asset_id}\n")

with IconikClient() as client:
    response = client.client.get(f"/assets/v1/assets/{asset_id}/segments/")
    data = response.json()

    segments = data.get("objects", [])
    print(f"Total: {len(segments)} segments\n")

    for i, seg in enumerate(segments, 1):
        seg_id = seg.get("id", "")
        title = seg.get("title", "(no title)")
        start = seg.get("time_start_milliseconds", 0)
        end = seg.get("time_end_milliseconds", 0)
        seg_type = seg.get("segment_type", "")
        created = seg.get("date_created", "")[:19]

        start_sec = start / 1000
        end_sec = end / 1000

        print(f"[{i}] Segment ID: {seg_id[:12]}...")
        print(f"    Title: {title}")
        print(f"    Time: {start_sec:.1f}s - {end_sec:.1f}s ({start}ms - {end}ms)")
        print(f"    Type: {seg_type}")
        print(f"    Created: {created}")
        print()

    # Show recently created (today)
    print("\n=== Recently Created (likely our test data) ===")
    for seg in segments:
        created = seg.get("date_created", "")
        if "2025-12-21" in created:
            print(f"  - {seg.get('id', '')[:12]}... | {seg.get('title', '')} | Created: {created[:19]}")
