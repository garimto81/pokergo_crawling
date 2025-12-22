"""Full segment test - create and verify."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient
import json
import time

# Different test asset
asset_id = "623b5a30-63b9-11f0-b2c5-9e2846c90c6f"  # WS11_ME03_NB_subclip_DN_interview

with IconikClient() as client:
    print(f"=== Testing on Asset: {asset_id} ===\n")

    # 1. Check current segments
    print("1. Current segments:")
    response = client.client.get(f"/assets/v1/assets/{asset_id}/segments/")
    data = response.json()
    print(f"   Total: {data.get('total', 0)}")

    # 2. Create segment
    print("\n2. Creating segment...")
    segment_data = {
        "time_start_milliseconds": 5000,  # 5초
        "time_end_milliseconds": 15000,   # 15초
        "segment_type": "GENERIC",
        "title": "Reverse Sync Test Segment",
    }

    response = client.client.post(f"/assets/v1/assets/{asset_id}/segments/", json=segment_data)
    print(f"   Status: {response.status_code}")
    result = response.json()
    print(f"   Response:\n{json.dumps(result, indent=2, default=str)}")

    # 3. Wait and verify
    print("\n3. Waiting 2 seconds and verifying...")
    time.sleep(2)

    response = client.client.get(f"/assets/v1/assets/{asset_id}/segments/")
    data = response.json()
    print(f"   Total segments now: {data.get('total', 0)}")

    if data.get("objects"):
        print("   Segments found:")
        for seg in data["objects"]:
            print(f"     - ID: {seg.get('id')}")
            print(f"       Start: {seg.get('time_start_milliseconds')}ms")
            print(f"       End: {seg.get('time_end_milliseconds')}ms")
    else:
        print("   No segments visible yet")

        # Try getting the created segment directly
        segment_id = result.get("id")
        if segment_id:
            print(f"\n4. Fetching segment directly: {segment_id}")
            try:
                response = client.client.get(f"/assets/v1/assets/{asset_id}/segments/{segment_id}/")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
            except Exception as e:
                print(f"   Error: {e}")
