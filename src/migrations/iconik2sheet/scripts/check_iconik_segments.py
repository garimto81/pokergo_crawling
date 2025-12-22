"""Check Iconik Segment API directly for specific asset IDs.

GG 시트에서 얻은 ID로 Iconik API를 직접 조회하여 Segment 상태를 확인합니다.
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from iconik import IconikClient


# Assets from GG sheet search results
ASSETS_TO_CHECK = [
    {
        "title": "serock vs griff  start from flop",
        "id": "8ddb35e6-007e-11f0-8c20-aad6eb65bf32",
        "gg_start": 136600,
        "gg_end": 513088,
        "user_iconik": "347300~347300",
    },
    {
        "title": "WSOP_2005_18_subclip_Phil Hellmuth Set over Set",
        "id": "712e6a98-5ca5-11f0-bc74-aa6aabd2c9a2",
        "gg_start": 1241725,
        "gg_end": 1446513,
        "user_iconik": "1241725~1241725",
    },
    {
        "title": "WSOP_2008_23_subclip_hellmuth tilted",
        "id": "32725c7e-5caa-11f0-8166-ce6143467bb9",
        "gg_start": 1986920,
        "gg_end": 2230030,
        "user_iconik": "2038555~2038555",
    },
    {
        "title": "WSOP - 1973 (1)_subclip_Amarillo Slim_Hero Call_Win the Pot",
        "id": "b88deba2-63a3-11f0-967e-820d87a649a9",
        "gg_start": 267567,
        "gg_end": 299833,
        "user_iconik": "267567~267567",
    },
]


def check_segments():
    """Check Iconik Segment API for each asset."""
    print("=" * 80)
    print("Iconik Segment API 직접 조회")
    print("=" * 80)

    with IconikClient() as client:
        for asset_info in ASSETS_TO_CHECK:
            print(f"\n[{asset_info['title'][:50]}...]")
            print("-" * 60)
            print(f"  Asset ID: {asset_info['id']}")
            print(f"  GG 시트: {asset_info['gg_start']} ~ {asset_info['gg_end']}")
            print(f"  사용자 Iconik 값: {asset_info['user_iconik']}")

            # Get asset info
            try:
                asset = client.get_asset(asset_info["id"])
                print(f"  Asset Type: {asset.type}")
                print(f"  Asset Title: {asset.title}")

                # Check if subclip (timecode in asset itself)
                if asset.type == "SUBCLIP":
                    print(f"  [Subclip 타임코드]")
                    print(f"    time_start_milliseconds: {asset.time_start_milliseconds}")
                    print(f"    time_end_milliseconds: {asset.time_end_milliseconds}")
            except Exception as e:
                print(f"  Asset 조회 실패: {e}")
                continue

            # Get segments
            try:
                segments = client.get_asset_segments(asset_info["id"], raise_for_404=False)
                if segments:
                    print(f"  [Segment API 결과] ({len(segments)}개)")
                    for i, seg in enumerate(segments[:3]):  # 최대 3개만
                        print(f"    Segment {i+1}:")
                        print(f"      time_start_milliseconds: {seg.get('time_start_milliseconds')}")
                        print(f"      time_end_milliseconds: {seg.get('time_end_milliseconds')}")
                        print(f"      segment_type: {seg.get('segment_type')}")
                        # metadata_values 확인
                        mv = seg.get("metadata_values", {})
                        if mv:
                            print(f"      metadata_values keys: {list(mv.keys())[:5]}...")
                else:
                    print("  [Segment API 결과] 없음 (빈 리스트)")
            except Exception as e:
                print(f"  Segment 조회 실패: {e}")

            # Comparison
            print(f"\n  [비교 결과]")
            if asset.type == "SUBCLIP":
                iconik_start = asset.time_start_milliseconds
                iconik_end = asset.time_end_milliseconds
            elif segments:
                iconik_start = segments[0].get("time_start_milliseconds")
                iconik_end = segments[0].get("time_end_milliseconds")
            else:
                iconik_start = None
                iconik_end = None

            if iconik_start and iconik_end:
                gg_match_start = iconik_start == asset_info["gg_start"]
                gg_match_end = iconik_end == asset_info["gg_end"]
                print(f"    Iconik 실제: {iconik_start} ~ {iconik_end}")
                print(f"    GG 시트: {asset_info['gg_start']} ~ {asset_info['gg_end']}")
                if gg_match_start and gg_match_end:
                    print(f"    상태: ✓ 일치")
                else:
                    print(f"    상태: ✗ 불일치")
                    print(f"      Start diff: {iconik_start - asset_info['gg_start']}")
                    print(f"      End diff: {iconik_end - asset_info['gg_end']}")
            else:
                print(f"    상태: Iconik에 타임코드 없음")


if __name__ == "__main__":
    check_segments()
