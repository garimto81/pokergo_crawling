"""Sample 10 random assets from Iconik.

무작위 10개 Asset의 메타데이터 구조를 확인합니다.
"""

import sys
import random
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from iconik import IconikClient


def sample_assets():
    """Sample 10 random assets."""
    print("=" * 80)
    print("무작위 10개 Asset 샘플링")
    print("=" * 80)

    settings = get_settings()
    view_id = settings.iconik.metadata_view_id if settings.iconik else None

    with IconikClient() as client:
        # 먼저 일부 Asset 수집 (처음 100개 중 10개 선택)
        print("\nAsset 수집 중...")
        all_assets = []
        count = 0
        for asset in client.get_all_assets():
            all_assets.append(asset)
            count += 1
            if count >= 100:
                break

        print(f"  {len(all_assets)}개 중 10개 무작위 선택\n")

        # 무작위 10개 선택
        samples = random.sample(all_assets, min(10, len(all_assets)))

        for i, asset in enumerate(samples, 1):
            print(f"\n[{i}/10] {asset.title[:60]}...")
            print("-" * 70)
            print(f"  ID: {asset.id}")
            print(f"  Type: {asset.type}")

            # Subclip인 경우 타임코드
            if asset.type == "SUBCLIP":
                print(f"  Timecode: {asset.time_start_milliseconds} ~ {asset.time_end_milliseconds}")
                print(f"  Parent: {getattr(asset, 'original_asset_id', 'N/A')}")

            # Segment 조회
            segments = client.get_asset_segments(asset.id, raise_for_404=False)
            if segments:
                print(f"\n  [Segments] ({len(segments)}개)")
                for seg in segments[:3]:
                    seg_type = seg.get("segment_type")
                    mv_count = len(seg.get("metadata_values", {}))
                    ts = seg.get("time_start_milliseconds")
                    te = seg.get("time_end_milliseconds")
                    print(f"    - {seg_type}: {ts}~{te}, metadata_values: {mv_count}")
            else:
                print(f"\n  [Segments] 없음")

            # Asset Metadata API
            if view_id:
                metadata = client.get_asset_metadata(asset.id, view_id, raise_for_404=False)
                if metadata:
                    mv = metadata.get("metadata_values", {})
                    if mv:
                        # 값이 있는 필드만 카운트
                        non_empty = {k: v for k, v in mv.items()
                                    if v.get("field_values")}
                        print(f"\n  [Asset Metadata] ({len(non_empty)}개 필드)")
                        for key, val in list(non_empty.items())[:5]:
                            fv = val.get("field_values", [])
                            values = [f.get("value") for f in fv[:2]]
                            print(f"    {key}: {values}")
                        if len(non_empty) > 5:
                            print(f"    ... (+{len(non_empty)-5}개)")
                    else:
                        print(f"\n  [Asset Metadata] metadata_values 없음")
                else:
                    print(f"\n  [Asset Metadata] None")
            else:
                print(f"\n  [Asset Metadata] view_id 미설정")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    sample_assets()
