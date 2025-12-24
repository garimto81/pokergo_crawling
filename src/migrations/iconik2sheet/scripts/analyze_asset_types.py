"""Analyze ASSET vs SUBCLIP patterns."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from iconik import IconikClient


def main():
    c = IconikClient()

    # 샘플 수집
    subclips = []  # type=SUBCLIP
    assets_with_segment = []  # type=ASSET + GENERIC segment
    normal_assets = []  # type=ASSET, no segment

    print("Scanning 500 assets...")

    for i, a in enumerate(c.get_all_assets()):
        if i >= 500:
            break

        if i % 100 == 0:
            print(f"  ... {i} scanned")

        has_segment = False
        seg_count = 0
        try:
            segs = c.get_asset_segments(a.id, raise_for_404=False)
            generic_segs = [s for s in segs if s.get("segment_type") == "GENERIC"]
            seg_count = len(generic_segs)
            has_segment = seg_count > 0
        except Exception:
            pass

        info = {
            "id": a.id[:8],
            "title": a.title[:60] if a.title else "",
            "type": a.type,
            "has_orig": bool(a.original_asset_id),
            "has_seg": has_segment,
            "seg_count": seg_count,
            "time_start": a.time_start_milliseconds,
            "time_end": a.time_end_milliseconds,
        }

        if a.type == "SUBCLIP":
            subclips.append(info)
        elif has_segment:
            assets_with_segment.append(info)
        else:
            normal_assets.append(info)

    print("\n" + "=" * 80)
    print("SUBCLIP (type=SUBCLIP) - first 15")
    print("=" * 80)
    for x in subclips[:15]:
        title = x["title"][:45]
        print(f"{title:45} | orig:{x['has_orig']} time:{x['time_start']}-{x['time_end']}")

    print("\n" + "=" * 80)
    print("ASSET with GENERIC Segment - first 15")
    print("=" * 80)
    for x in assets_with_segment[:15]:
        title = x["title"][:45]
        print(f"{title:45} | seg_cnt:{x['seg_count']}")

    print("\n" + "=" * 80)
    print("Normal ASSET (no segment) - first 10")
    print("=" * 80)
    for x in normal_assets[:10]:
        title = x["title"][:45]
        print(f"{title:45}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"SUBCLIP (type=SUBCLIP):        {len(subclips)}")
    print(f"ASSET with GENERIC Segment:   {len(assets_with_segment)}")
    print(f"Normal ASSET (no segment):    {len(normal_assets)}")

    # 타이틀 패턴 분석
    print("\n" + "=" * 80)
    print("TITLE PATTERN ANALYSIS")
    print("=" * 80)

    # Subclip 타이틀 패턴
    subclip_patterns = {"Hand_": 0, "Clean": 0, "Dirty": 0, "_v": 0}
    for x in subclips:
        for p in subclip_patterns:
            if p in x["title"]:
                subclip_patterns[p] += 1

    print(f"\nSUBCLIP title patterns (n={len(subclips)}):")
    for p, cnt in subclip_patterns.items():
        pct = cnt / len(subclips) * 100 if subclips else 0
        print(f"  '{p}': {cnt} ({pct:.1f}%)")

    # Asset+Segment 타이틀 패턴
    asset_seg_patterns = {"Hand_": 0, "Clean": 0, "Dirty": 0, "_v": 0}
    for x in assets_with_segment:
        for p in asset_seg_patterns:
            if p in x["title"]:
                asset_seg_patterns[p] += 1

    print(f"\nASSET+Segment title patterns (n={len(assets_with_segment)}):")
    for p, cnt in asset_seg_patterns.items():
        pct = cnt / len(assets_with_segment) * 100 if assets_with_segment else 0
        print(f"  '{p}': {cnt} ({pct:.1f}%)")

    # Normal Asset 타이틀 패턴
    normal_patterns = {"Hand_": 0, "Clean": 0, "Dirty": 0, "_v": 0}
    for x in normal_assets:
        for p in normal_patterns:
            if p in x["title"]:
                normal_patterns[p] += 1

    print(f"\nNormal ASSET title patterns (n={len(normal_assets)}):")
    for p, cnt in normal_patterns.items():
        pct = cnt / len(normal_assets) * 100 if normal_assets else 0
        print(f"  '{p}': {cnt} ({pct:.1f}%)")

    c.close()


if __name__ == "__main__":
    main()
