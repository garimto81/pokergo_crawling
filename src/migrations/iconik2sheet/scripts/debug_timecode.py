"""Debug timecode extraction - 타임코드가 왜 안 나오는지 확인."""

import json
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from iconik import IconikClient
from sheets import SheetsWriter


def debug_timecode() -> None:
    """Debug timecode extraction for matched assets."""
    print("=" * 70)
    print("Debug Timecode Extraction")
    print("=" * 70)
    print()

    # Get Iconik_Full_Metadata 시트에서 title과 id 가져오기
    writer = SheetsWriter()
    _, iconik_data = writer.get_sheet_data("Iconik_Full_Metadata")

    if not iconik_data:
        print("ERROR: Iconik_Full_Metadata is empty!")
        return

    # GG 시트에서 타임코드가 있는 title 가져오기
    _, gg_data = writer.get_sheet_data("GGmetadata_and_timestamps")
    gg_with_timecode = {}
    for row in gg_data:
        title = row.get("title", "").strip()
        time_start = row.get("time_start_ms", "")
        time_end = row.get("time_end_ms", "")
        if title and (time_start or time_end):
            gg_with_timecode[title] = {
                "time_start_ms": time_start,
                "time_end_ms": time_end,
            }

    print(f"GG 시트에서 타임코드 있는 Asset: {len(gg_with_timecode)}개")
    print()

    # Iconik API로 직접 확인
    client = IconikClient()

    for row in iconik_data:
        asset_id = row.get("id", "")
        title = row.get("title", "")[:60]

        if not asset_id:
            continue

        print("-" * 70)
        print(f"Title: {title}")
        print(f"Asset ID: {asset_id}")

        # GG 시트의 타임코드
        if title in gg_with_timecode:
            gg_tc = gg_with_timecode[title]
            print(f"GG Timecode: {gg_tc['time_start_ms']} ~ {gg_tc['time_end_ms']}")
        else:
            print("GG Timecode: (없음)")

        # Iconik API에서 세그먼트 조회
        try:
            segments = client.get_asset_segments(asset_id, raise_for_404=False)

            if not segments:
                print("Segments: (없음 - 빈 리스트)")
            else:
                print(f"Segments: {len(segments)}개 발견")

                for i, seg in enumerate(segments[:3]):  # 최대 3개만 출력
                    print(f"\n  [Segment {i+1}]")
                    print(f"    id: {seg.get('id', 'N/A')}")
                    print(f"    segment_type: {seg.get('segment_type', 'N/A')}")
                    print(f"    time_start_milliseconds: {seg.get('time_start_milliseconds', 'N/A')}")
                    print(f"    time_end_milliseconds: {seg.get('time_end_milliseconds', 'N/A')}")

                    # 다른 타임코드 관련 필드 확인
                    for key in seg.keys():
                        if 'time' in key.lower() or 'start' in key.lower() or 'end' in key.lower():
                            if key not in ['time_start_milliseconds', 'time_end_milliseconds']:
                                print(f"    {key}: {seg.get(key, 'N/A')}")

                    # metadata_values 확인
                    metadata = seg.get("metadata_values", {})
                    if metadata:
                        print(f"    metadata_values: {len(metadata)} fields")
                    else:
                        print(f"    metadata_values: (없음)")

        except Exception as e:
            print(f"Segments ERROR: {e}")

        print()

    client.close()


if __name__ == "__main__":
    debug_timecode()
