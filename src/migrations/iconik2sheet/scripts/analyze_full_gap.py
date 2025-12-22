"""Analyze full data gap between GG sheet and Iconik Segments.

GG 시트(GGmetadata_and_timestamps)와 Iconik Segment API 간의
타임코드 데이터 갭을 분석합니다.

시나리오 분류:
- A: GG 시트에만 타임코드 있음 (Reverse Sync 필요)
- B: Iconik에만 Segment 있음 (Forward Sync 가능)
- C: 양쪽 모두 있음 (값 비교 필요)
- D: 양쪽 모두 없음 (액션 없음)
"""

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
class GapAnalysisResult:
    """Gap analysis result."""

    # Counts
    gg_total: int = 0
    iconik_total: int = 0
    title_matched: int = 0

    # Scenarios
    scenario_a: list = field(default_factory=list)  # GG only
    scenario_b: list = field(default_factory=list)  # Iconik only
    scenario_c_match: list = field(default_factory=list)  # Both, values match
    scenario_c_diff: list = field(default_factory=list)  # Both, values differ
    scenario_d: list = field(default_factory=list)  # Neither

    # Unmatched
    gg_not_in_iconik: list = field(default_factory=list)
    iconik_not_in_gg: list = field(default_factory=list)


def analyze_gap() -> GapAnalysisResult:
    """Analyze data gap between GG sheet and Iconik."""
    print("=" * 70)
    print("전체 데이터 갭 분석")
    print("GGmetadata_and_timestamps vs Iconik Segments")
    print("=" * 70)
    print()

    result = GapAnalysisResult()
    writer = SheetsWriter()
    client = IconikClient()

    # Step 1: Load GG sheet
    print("[1/4] GG 시트 로드 중...")
    _, gg_data = writer.get_sheet_data("GGmetadata_and_timestamps")
    result.gg_total = len(gg_data)
    print(f"  → {result.gg_total}건 로드")

    # Build GG title -> data map
    gg_by_title = {}
    for row in gg_data:
        title = row.get("title", "").strip()
        if title:
            gg_by_title[title] = {
                "time_start_ms": row.get("time_start_ms", ""),
                "time_end_ms": row.get("time_end_ms", ""),
                "has_timecode": bool(
                    row.get("time_start_ms") or row.get("time_end_ms")
                ),
            }

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

        if segments:
            first_seg = segments[0]
            time_start = first_seg.get("time_start_milliseconds")
            time_end = first_seg.get("time_end_milliseconds")

        iconik_by_title[title] = {
            "asset_id": asset.id,
            "time_start_ms": time_start,
            "time_end_ms": time_end,
            "has_segment": has_segment,
        }

        if asset_count % 100 == 0:
            print(f"  → {asset_count}개 처리됨...")

    result.iconik_total = asset_count
    print(f"  → 총 {result.iconik_total}개 Asset 조회 완료")

    client.close()

    # Step 3: Compare and classify
    print("\n[3/4] 데이터 비교 및 시나리오 분류 중...")

    all_titles = set(gg_by_title.keys()) | set(iconik_by_title.keys())

    for title in all_titles:
        gg_info = gg_by_title.get(title)
        iconik_info = iconik_by_title.get(title)

        # Title matching
        if gg_info and iconik_info:
            result.title_matched += 1

            gg_has_tc = gg_info["has_timecode"]
            iconik_has_seg = iconik_info["has_segment"]

            if gg_has_tc and not iconik_has_seg:
                # Scenario A: GG only
                result.scenario_a.append({
                    "title": title,
                    "gg_start": gg_info["time_start_ms"],
                    "gg_end": gg_info["time_end_ms"],
                })
            elif not gg_has_tc and iconik_has_seg:
                # Scenario B: Iconik only
                result.scenario_b.append({
                    "title": title,
                    "asset_id": iconik_info["asset_id"],
                    "iconik_start": iconik_info["time_start_ms"],
                    "iconik_end": iconik_info["time_end_ms"],
                })
            elif gg_has_tc and iconik_has_seg:
                # Scenario C: Both have timecode
                gg_start = str(gg_info["time_start_ms"]).strip()
                gg_end = str(gg_info["time_end_ms"]).strip()
                iconik_start = str(iconik_info["time_start_ms"] or "").strip()
                iconik_end = str(iconik_info["time_end_ms"] or "").strip()

                if gg_start == iconik_start and gg_end == iconik_end:
                    result.scenario_c_match.append({"title": title})
                else:
                    result.scenario_c_diff.append({
                        "title": title,
                        "gg_start": gg_info["time_start_ms"],
                        "gg_end": gg_info["time_end_ms"],
                        "iconik_start": iconik_info["time_start_ms"],
                        "iconik_end": iconik_info["time_end_ms"],
                    })
            else:
                # Scenario D: Neither has timecode
                result.scenario_d.append({"title": title})

        elif gg_info and not iconik_info:
            # GG에만 있음 (Iconik에 Asset 자체가 없음)
            result.gg_not_in_iconik.append({
                "title": title,
                "has_timecode": gg_info["has_timecode"],
            })

        elif iconik_info and not gg_info:
            # Iconik에만 있음 (GG 시트에 없음)
            result.iconik_not_in_gg.append({
                "title": title,
                "asset_id": iconik_info["asset_id"],
                "has_segment": iconik_info["has_segment"],
            })

    # Step 4: Print report
    print("\n[4/4] 분석 결과 리포트 생성...")
    print_report(result)

    return result


def print_report(result: GapAnalysisResult) -> None:
    """Print analysis report."""
    print()
    print("=" * 70)
    print("데이터 갭 분석 결과")
    print("=" * 70)

    # Summary
    print("\n[Summary]")
    print(f"  GG 시트 전체: {result.gg_total}건")
    print(f"  Iconik Asset 전체: {result.iconik_total}건")
    print(f"  Title 매칭: {result.title_matched}건")

    # Unmatched
    print(f"\n  GG에만 있음 (Iconik에 Asset 없음): {len(result.gg_not_in_iconik)}건")
    print(f"  Iconik에만 있음 (GG 시트에 없음): {len(result.iconik_not_in_gg)}건")

    # Scenarios
    print("\n[시나리오별 분류]")
    print(f"  A (GG 타임코드 O, Iconik Segment X): {len(result.scenario_a)}건")
    print(f"    → Reverse Sync 대상")
    print(f"  B (GG 타임코드 X, Iconik Segment O): {len(result.scenario_b)}건")
    print(f"    → Forward Sync 가능")
    print(f"  C-1 (양쪽 있음, 값 일치): {len(result.scenario_c_match)}건")
    print(f"    → 정상")
    print(f"  C-2 (양쪽 있음, 값 불일치): {len(result.scenario_c_diff)}건")
    print(f"    → 충돌 해결 필요")
    print(f"  D (양쪽 모두 없음): {len(result.scenario_d)}건")
    print(f"    → 액션 없음")

    # Action summary
    print("\n[액션 필요 요약]")
    total_action = len(result.scenario_a) + len(result.scenario_b) + len(result.scenario_c_diff)
    print(f"  Reverse Sync 필요: {len(result.scenario_a)}건")
    print(f"  Forward Sync 가능: {len(result.scenario_b)}건")
    print(f"  충돌 해결 필요: {len(result.scenario_c_diff)}건")
    print(f"  ────────────────────")
    print(f"  총 액션 필요: {total_action}건")

    # Samples
    if result.scenario_a:
        print("\n[시나리오 A 샘플] (최대 5건)")
        for item in result.scenario_a[:5]:
            print(f"  - {item['title'][:50]}")
            print(f"    GG: {item['gg_start']} ~ {item['gg_end']}")

    if result.scenario_c_diff:
        print("\n[시나리오 C-2 샘플 (값 불일치)] (최대 5건)")
        for item in result.scenario_c_diff[:5]:
            print(f"  - {item['title'][:50]}")
            print(f"    GG: {item['gg_start']} ~ {item['gg_end']}")
            print(f"    Iconik: {item['iconik_start']} ~ {item['iconik_end']}")

    if result.gg_not_in_iconik:
        print("\n[GG에만 있음 샘플] (최대 5건)")
        for item in result.gg_not_in_iconik[:5]:
            tc = "O" if item["has_timecode"] else "X"
            print(f"  - {item['title'][:50]} (타임코드: {tc})")


if __name__ == "__main__":
    analyze_gap()
