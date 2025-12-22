"""Verify newly created segment exists."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from iconik import IconikClient

asset_id = "fbb7e94e-4127-11f0-bf53-7216fc2efa1a"
new_segment_id = "c53db29e-de6c-11f0-a546-3ec466ad579c"

print(f"=== Verifying Segment ===\n")
print(f"Asset: {asset_id}")
print(f"Expected Segment: {new_segment_id}")
print()

with IconikClient() as client:
    # 1. List all segments on this asset
    print("1. All segments on asset:")
    response = client.client.get(f"/assets/v1/assets/{asset_id}/segments/")
    data = response.json()

    segments = data.get("objects", [])
    print(f"   Total: {len(segments)}")

    found = False
    for seg in segments:
        seg_id = seg.get("id", "")
        start = seg.get("time_start_milliseconds", 0)
        end = seg.get("time_end_milliseconds", 0)
        created = seg.get("date_created", "")[:19]

        start_sec = start / 1000
        end_sec = end / 1000

        # Check if this is our new segment
        is_new = seg_id == new_segment_id
        marker = " <-- NEW (1:30-2:30)" if is_new else ""
        if is_new:
            found = True

        print(f"   - {start_sec:.1f}s - {end_sec:.1f}s | ID: {seg_id[:12]}... | {created}{marker}")

    print()

    # 2. Try to get the specific segment directly
    print(f"2. Direct fetch of segment {new_segment_id[:12]}...")
    try:
        response2 = client.client.get(f"/assets/v1/assets/{asset_id}/segments/{new_segment_id}/")
        if response2.status_code == 200:
            seg = response2.json()
            print(f"   Status: EXISTS")
            print(f"   Start: {seg.get('time_start_milliseconds')}ms ({seg.get('time_start_milliseconds', 0)/1000}s)")
            print(f"   End: {seg.get('time_end_milliseconds')}ms ({seg.get('time_end_milliseconds', 0)/1000}s)")
            print(f"   Type: {seg.get('segment_type')}")
        else:
            print(f"   Status: {response2.status_code}")
            print(f"   Response: {response2.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # 3. Check asset info
    print("3. Asset info:")
    asset = client.get_asset(asset_id)
    print(f"   Title: {asset.title}")
    print(f"   Status: {asset.status}")

    print()
    print("=== iconik UI 확인 방법 ===")
    print(f"URL: https://app.iconik.io/asset/{asset_id}")
    print()
    print("확인 위치:")
    print("  1. Asset 열기")
    print("  2. 오른쪽 패널에서 'Segments' 탭 클릭")
    print("  3. 또는 Timeline 뷰에서 마커 확인")
    print("  4. 1분 30초 (90초) 위치로 이동")
