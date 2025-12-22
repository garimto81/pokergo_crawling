"""Find where user-created metadata is stored.

작업자가 입력한 메타데이터가 어디에 저장되어 있는지 확인합니다.
1. Asset 메타데이터 API
2. Parent Asset의 Segment
3. Subclip 자체 필드
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from iconik import IconikClient


# 검증할 Asset
ASSET_TO_CHECK = {
    "title": "serock vs griff start from flop",
    "id": "8ddb35e6-007e-11f0-8c20-aad6eb65bf32",
}


def find_metadata():
    """Find where metadata is stored."""
    print("=" * 80)
    print(f"메타데이터 위치 탐색: {ASSET_TO_CHECK['title']}")
    print(f"Asset ID: {ASSET_TO_CHECK['id']}")
    print("=" * 80)

    settings = get_settings()

    with IconikClient() as client:
        asset_id = ASSET_TO_CHECK["id"]

        # 1. Asset 기본 정보 조회
        print("\n[1] Asset 기본 정보")
        print("-" * 60)
        asset = client.get_asset(asset_id)
        print(f"  Type: {asset.type}")
        print(f"  Title: {asset.title}")
        print(f"  time_start_milliseconds: {asset.time_start_milliseconds}")
        print(f"  time_end_milliseconds: {asset.time_end_milliseconds}")

        # original_asset_id 확인 (Parent Asset)
        original_asset_id = getattr(asset, "original_asset_id", None)
        original_segment_id = getattr(asset, "original_segment_id", None)
        print(f"  original_asset_id: {original_asset_id}")
        print(f"  original_segment_id: {original_segment_id}")

        # 2. Subclip의 Segment 조회
        print("\n[2] Subclip의 Segment")
        print("-" * 60)
        segments = client.get_asset_segments(asset_id, raise_for_404=False)
        print(f"  Segment 개수: {len(segments) if segments else 0}")
        if segments:
            for seg in segments:
                print(f"    - Type: {seg.get('segment_type')}, metadata_values: {len(seg.get('metadata_values', {}))}")

        # 3. Asset 메타데이터 API 조회
        print("\n[3] Asset 메타데이터 API")
        print("-" * 60)
        view_id = settings.iconik.metadata_view_id if settings.iconik else None
        print(f"  View ID: {view_id or '(미설정)'}")

        if not view_id:
            print("  메타데이터 조회 건너뜀 (view_id 없음)")
            metadata = None
        else:
            metadata = client.get_asset_metadata(asset_id, view_id, raise_for_404=False)

        if metadata:
            print(f"  메타데이터 필드 개수: {len(metadata)}")
            # 실제 값이 있는 필드만 표시
            non_empty = {k: v for k, v in metadata.items() if v}
            print(f"  값이 있는 필드: {len(non_empty)}")
            for key, value in list(non_empty.items())[:10]:
                print(f"    {key}: {value}")
            if len(non_empty) > 10:
                print(f"    ... (총 {len(non_empty)}개)")
        else:
            print("  메타데이터 없음 (None)")

        # 4. Parent Asset 조회 (있는 경우)
        if original_asset_id:
            print("\n[4] Parent Asset 정보")
            print("-" * 60)
            print(f"  Parent Asset ID: {original_asset_id}")

            try:
                parent_asset = client.get_asset(original_asset_id)
                print(f"  Parent Title: {parent_asset.title}")
                print(f"  Parent Type: {parent_asset.type}")
            except Exception as e:
                print(f"  Parent Asset 조회 실패: {e}")

            # Parent Asset의 Segment 조회
            print("\n[5] Parent Asset의 Segment")
            print("-" * 60)
            parent_segments = client.get_asset_segments(original_asset_id, raise_for_404=False)
            print(f"  Segment 개수: {len(parent_segments) if parent_segments else 0}")

            if parent_segments:
                for i, seg in enumerate(parent_segments[:5]):  # 처음 5개만
                    seg_type = seg.get("segment_type")
                    seg_id = seg.get("id")
                    metadata_values = seg.get("metadata_values", {})
                    time_start = seg.get("time_start_milliseconds")
                    time_end = seg.get("time_end_milliseconds")

                    print(f"\n  Segment {i+1}:")
                    print(f"    ID: {seg_id}")
                    print(f"    Type: {seg_type}")
                    print(f"    Timecode: {time_start} ~ {time_end}")
                    print(f"    metadata_values 개수: {len(metadata_values)}")

                    # original_segment_id와 일치하는지 확인
                    if seg_id == original_segment_id:
                        print(f"    ★ original_segment_id와 일치!")

                    if metadata_values:
                        print(f"    metadata_values 키: {list(metadata_values.keys())[:5]}")
                        # 실제 값 확인
                        for key, value in list(metadata_values.items())[:3]:
                            field_values = value.get("field_values", [])
                            if field_values:
                                actual_values = [fv.get("value") for fv in field_values]
                                print(f"      {key}: {actual_values}")

                if len(parent_segments) > 5:
                    print(f"\n  ... (총 {len(parent_segments)}개)")

            # Parent Asset 메타데이터 조회
            print("\n[6] Parent Asset 메타데이터 API")
            print("-" * 60)
            if view_id:
                parent_metadata = client.get_asset_metadata(original_asset_id, view_id, raise_for_404=False)
            else:
                parent_metadata = None
                print("  메타데이터 조회 건너뜀 (view_id 없음)")

            if parent_metadata:
                non_empty = {k: v for k, v in parent_metadata.items() if v}
                print(f"  값이 있는 필드: {len(non_empty)}")
                for key, value in list(non_empty.items())[:5]:
                    print(f"    {key}: {value}")
            else:
                print("  메타데이터 없음 (None)")


if __name__ == "__main__":
    find_metadata()
