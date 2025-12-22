"""Reverse Sync: GG Sheet → Iconik Segments.

GG 시트의 올바른 타임코드를 Iconik Segment에 동기화합니다.

대상:
- C-2 충돌 중 duration=0 패턴 (time_end = time_start)
- 시나리오 A (GG에만 타임코드 있음) - optional

Usage:
    python -m scripts.run_reverse_sync --dry-run          # 테스트 모드
    python -m scripts.run_reverse_sync --fix-duration-0   # duration=0만 수정
    python -m scripts.run_reverse_sync --all              # 전체 Reverse Sync
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from iconik import IconikClient
from sheets import SheetsWriter


@dataclass
class ReverseSyncResult:
    """Reverse sync result."""

    # Counts
    total_candidates: int = 0
    updated: int = 0
    created: int = 0
    skipped: int = 0
    errors: int = 0

    # Details
    updated_items: list = field(default_factory=list)
    created_items: list = field(default_factory=list)
    error_items: list = field(default_factory=list)


def find_duration_zero_cases(
    gg_by_title: dict, iconik_by_title: dict
) -> list[dict]:
    """Find C-2 conflicts where Iconik duration=0.

    Args:
        gg_by_title: GG sheet data by title
        iconik_by_title: Iconik data by title (with segment info)

    Returns:
        List of items with duration=0 pattern
    """
    cases = []

    for title, gg_info in gg_by_title.items():
        iconik_info = iconik_by_title.get(title)

        if not iconik_info:
            continue

        # Both have timecode
        if not gg_info["has_timecode"]:
            continue
        if not iconik_info["has_segment"]:
            continue

        # Check if Iconik has duration=0
        iconik_start = iconik_info["time_start_ms"]
        iconik_end = iconik_info["time_end_ms"]

        if iconik_start is not None and iconik_start == iconik_end:
            # Duration = 0 pattern
            cases.append({
                "title": title,
                "asset_id": iconik_info["asset_id"],
                "segment_id": iconik_info["segment_id"],
                "gg_start": gg_info["time_start_ms"],
                "gg_end": gg_info["time_end_ms"],
                "iconik_start": iconik_start,
                "iconik_end": iconik_end,
            })

    return cases


def run_reverse_sync(
    mode: str = "dry-run",
    fix_duration_0: bool = False,
) -> ReverseSyncResult:
    """Run reverse sync from GG sheet to Iconik.

    Args:
        mode: "dry-run" (preview) or "execute" (actually update)
        fix_duration_0: If True, only fix duration=0 cases

    Returns:
        ReverseSyncResult with counts and details
    """
    print("=" * 70)
    print("Reverse Sync: GG Sheet → Iconik Segments")
    print(f"Mode: {mode.upper()}")
    if fix_duration_0:
        print("Target: duration=0 cases only")
    print("=" * 70)
    print()

    result = ReverseSyncResult()
    writer = SheetsWriter()
    client = IconikClient()

    # Step 1: Load GG sheet
    print("[1/4] GG 시트 로드 중...")
    _, gg_data = writer.get_sheet_data("GGmetadata_and_timestamps")
    print(f"  → {len(gg_data)}건 로드")

    # Build GG title -> data map
    gg_by_title = {}
    for row in gg_data:
        title = row.get("title", "").strip()
        if title:
            try:
                time_start = row.get("time_start_ms")
                time_end = row.get("time_end_ms")

                # Convert to int if string
                if isinstance(time_start, str) and time_start:
                    time_start = int(float(time_start))
                if isinstance(time_end, str) and time_end:
                    time_end = int(float(time_end))

                gg_by_title[title] = {
                    "time_start_ms": time_start,
                    "time_end_ms": time_end,
                    "has_timecode": bool(time_start or time_end),
                }
            except (ValueError, TypeError):
                continue

    # Step 2: Load Iconik assets and segments
    print("\n[2/4] Iconik Asset 및 Segment 조회 중...")
    print("  (전체 Asset 조회 - 시간이 걸릴 수 있습니다)")

    iconik_by_title = {}
    asset_count = 0

    for asset in client.get_all_assets():
        asset_count += 1
        title = asset.title.strip() if asset.title else ""

        if not title:
            continue

        # Get segments for this asset
        segments = client.get_asset_segments(asset.id, raise_for_404=False)

        has_segment = bool(segments)
        time_start = None
        time_end = None
        segment_id = None

        if segments:
            first_seg = segments[0]
            time_start = first_seg.get("time_start_milliseconds")
            time_end = first_seg.get("time_end_milliseconds")
            segment_id = first_seg.get("id")

        iconik_by_title[title] = {
            "asset_id": asset.id,
            "segment_id": segment_id,
            "time_start_ms": time_start,
            "time_end_ms": time_end,
            "has_segment": has_segment,
        }

        if asset_count % 100 == 0:
            print(f"  → {asset_count}개 처리됨...")

    print(f"  → 총 {asset_count}개 Asset 조회 완료")

    # Step 3: Find candidates
    print("\n[3/4] 동기화 대상 검색 중...")

    if fix_duration_0:
        candidates = find_duration_zero_cases(gg_by_title, iconik_by_title)
        print(f"  → duration=0 케이스: {len(candidates)}건")
    else:
        # TODO: Implement full reverse sync (Scenario A + C-2)
        candidates = find_duration_zero_cases(gg_by_title, iconik_by_title)
        print(f"  → 대상: {len(candidates)}건")

    result.total_candidates = len(candidates)

    if not candidates:
        print("\n동기화 대상이 없습니다.")
        client.close()
        return result

    # Step 4: Execute or preview
    print(f"\n[4/4] {'미리보기' if mode == 'dry-run' else '동기화 실행'} 중...")

    for i, item in enumerate(candidates, 1):
        title = item["title"][:50]
        asset_id = item["asset_id"]
        segment_id = item["segment_id"]
        gg_start = item["gg_start"]
        gg_end = item["gg_end"]

        print(f"\n[{i}/{len(candidates)}] {title}")
        print(f"  Asset: {asset_id}")
        print(f"  Segment: {segment_id}")
        print(f"  현재 Iconik: {item['iconik_start']} ~ {item['iconik_end']}")
        print(f"  변경 예정:   {gg_start} ~ {gg_end}")

        if mode == "dry-run":
            result.skipped += 1
            continue

        # Execute update
        try:
            if segment_id:
                # Update existing segment
                client.update_asset_segment(
                    asset_id=asset_id,
                    segment_id=segment_id,
                    time_start_ms=gg_start,
                    time_end_ms=gg_end,
                )
                result.updated += 1
                result.updated_items.append(item)
                print("  ✓ 업데이트 완료")
            else:
                # Create new segment (shouldn't happen for duration=0 cases)
                client.create_asset_segment(
                    asset_id=asset_id,
                    time_start_ms=gg_start,
                    time_end_ms=gg_end,
                )
                result.created += 1
                result.created_items.append(item)
                print("  ✓ 생성 완료")

        except Exception as e:
            result.errors += 1
            result.error_items.append({**item, "error": str(e)})
            print(f"  ✗ 오류: {e}")

    client.close()

    # Print summary
    print("\n" + "=" * 70)
    print("Reverse Sync 결과")
    print("=" * 70)
    print(f"  대상: {result.total_candidates}건")
    if mode == "dry-run":
        print("  (Dry-run 모드 - 실제 변경 없음)")
    else:
        print(f"  업데이트: {result.updated}건")
        print(f"  생성: {result.created}건")
        print(f"  오류: {result.errors}건")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Reverse Sync: GG Sheet → Iconik Segments"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview mode (no actual changes)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the sync",
    )
    parser.add_argument(
        "--fix-duration-0",
        action="store_true",
        default=True,
        help="Only fix duration=0 cases (default)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Full reverse sync (Scenario A + C-2)",
    )

    args = parser.parse_args()

    mode = "execute" if args.execute else "dry-run"
    fix_duration_0 = not args.all

    run_reverse_sync(mode=mode, fix_duration_0=fix_duration_0)


if __name__ == "__main__":
    main()
