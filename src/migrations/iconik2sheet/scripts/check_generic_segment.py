"""Check GENERIC Segment metadata_values.

GENERIC Segment가 작업자가 만든 것인지, Iconik 기본 템플릿인지 확인합니다.
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


# 검증된 Asset ID 목록
ASSETS_TO_CHECK = [
    ("serock vs griff", "8ddb35e6-007e-11f0-8c20-aad6eb65bf32"),
    ("Phil Hellmuth Set over Set", "712e6a98-5ca5-11f0-bc74-aa6aabd2c9a2"),
    ("hellmuth tilted", "32725c7e-5caa-11f0-8166-ce6143467bb9"),
    ("Amarillo Slim", "b88deba2-63a3-11f0-967e-820d87a649a9"),
]


def check_generic_segments():
    """Check GENERIC Segment's metadata_values."""
    print("=" * 80)
    print("GENERIC Segment metadata_values 확인")
    print("=" * 80)

    with IconikClient() as client:
        for title, asset_id in ASSETS_TO_CHECK:
            print(f"\n[{title}]")
            print(f"  Asset ID: {asset_id}")
            print("-" * 60)

            # Get segments
            segments = client.get_asset_segments(asset_id, raise_for_404=False)

            if not segments:
                print("  Segment 없음")
                continue

            for i, seg in enumerate(segments):
                seg_type = seg.get("segment_type", "UNKNOWN")
                time_start = seg.get("time_start_milliseconds")
                time_end = seg.get("time_end_milliseconds")
                metadata_values = seg.get("metadata_values", {})

                print(f"\n  Segment {i+1}:")
                print(f"    Type: {seg_type}")
                print(f"    Timecode: {time_start} ~ {time_end}")
                print(f"    metadata_values 키 개수: {len(metadata_values)}")

                if metadata_values:
                    print(f"    metadata_values 키: {list(metadata_values.keys())}")
                    # 실제 값 확인 (처음 3개만)
                    for j, (key, value) in enumerate(metadata_values.items()):
                        if j >= 3:
                            print(f"    ... (총 {len(metadata_values)}개)")
                            break
                        field_values = value.get("field_values", [])
                        if field_values:
                            actual_values = [fv.get("value") for fv in field_values]
                            print(f"    {key}: {actual_values}")
                        else:
                            print(f"    {key}: (빈 값)")
                else:
                    print(f"    metadata_values: 비어있음 (빈 객체)")

    print("\n" + "=" * 80)
    print("분석 결과:")
    print("- GENERIC Segment에 metadata_values가 비어있다면 → Iconik 기본 템플릿")
    print("- GENERIC Segment에 metadata_values가 있다면 → 작업자가 입력한 데이터")
    print("=" * 80)


if __name__ == "__main__":
    check_generic_segments()
