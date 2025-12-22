"""Verify created segment."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient

asset_id = "d206796c-4cf3-11f0-a812-fa75e68441df"

with IconikClient() as client:
    segments = client.get_asset_segments(asset_id, raise_for_404=False)
    print(f"Asset: {asset_id}")
    print(f"Segments count: {len(segments)}")

    for seg in segments:
        print(f"\n  Segment ID: {seg.get('id')}")
        print(f"  Type: {seg.get('segment_type')}")
        print(f"  Start: {seg.get('time_start_milliseconds')}ms")
        print(f"  End: {seg.get('time_end_milliseconds')}ms")
        print(f"  Title: {seg.get('title')}")
