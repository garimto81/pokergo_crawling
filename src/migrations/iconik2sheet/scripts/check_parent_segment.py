"""Check segment on parent asset."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient
import json

# Parent asset ID (where segment was actually created)
parent_asset_id = "fbb7e94e-4127-11f0-bf53-7216fc2efa1a"

with IconikClient() as client:
    print(f"=== Checking Parent Asset: {parent_asset_id} ===\n")

    # 1. Get asset info
    print("1. Asset Info:")
    asset = client.get_asset(parent_asset_id)
    print(f"   Title: {asset.title}")

    # 2. Get segments
    print("\n2. Segments on parent asset:")
    response = client.client.get(f"/assets/v1/assets/{parent_asset_id}/segments/")
    data = response.json()
    print(f"   Total: {data.get('total', 0)}")

    if data.get("objects"):
        for seg in data["objects"]:
            print(f"\n   Segment ID: {seg.get('id')}")
            print(f"   Type: {seg.get('segment_type')}")
            print(f"   Start: {seg.get('time_start_milliseconds')}ms ({seg.get('time_start_milliseconds', 0) / 1000}s)")
            print(f"   End: {seg.get('time_end_milliseconds')}ms ({seg.get('time_end_milliseconds', 0) / 1000}s)")

    # 3. Also check both test segments (previously created)
    print("\n\n=== Summary: Created Segments ===")
    print("Test 1: d206796c... -> segment 8b65f646...")
    print("Test 2: 623b5a30... -> segment c161c306... (on parent fbb7e94e...)")
