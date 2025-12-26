"""Analyze current checkbox data in Subclip_Validation_Report sheet."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sheets.writer import SheetsWriter

writer = SheetsWriter()

# Read current sheet data
headers, data = writer.get_sheet_data("Subclip_Validation_Report")

if data:
    print("시트 헤더:", headers)
    print("\n처음 5행 데이터 분석:")
    print("=" * 120)

    # Analyze first 5 rows
    for idx, row in enumerate(data[:5], 1):
        print(f"\n행 {idx}:")
        print(f"  ID: {row.get('id', '')}")
        print(f"  Title: {row.get('title', '')[:50]}")
        print(f"  orphan_subclip (G): {repr(row.get('orphan_subclip', ''))}")
        print(f"  missing_parent (H): {repr(row.get('missing_parent', ''))}")
        print(f"  self_reference (I): {repr(row.get('self_reference', ''))}")
        print(f"  missing_timecode (J): {repr(row.get('missing_timecode', ''))}")
        print(f"  round_timecode (K): {repr(row.get('round_timecode', ''))}")
        print(f"  invalid_range (L): {repr(row.get('invalid_range', ''))}")

    print("\n" + "=" * 120)
    print(f"총 행 수: {len(data)}")

    # Analyze checkbox column values
    checkbox_cols = [
        "orphan_subclip",
        "missing_parent",
        "self_reference",
        "missing_timecode",
        "round_timecode",
        "invalid_range",
    ]

    print("\n체크박스 컬럼 값 분포:")
    for col in checkbox_cols:
        true_count = sum(1 for row in data if row.get(col, "") == "TRUE")
        false_count = sum(1 for row in data if row.get(col, "") == "FALSE")
        empty_count = sum(1 for row in data if row.get(col, "") == "")
        other_count = len(data) - true_count - false_count - empty_count

        print(
            f"  {col}: TRUE={true_count}, FALSE={false_count}, 빈칸={empty_count}, 기타={other_count}"
        )

    # Sample of different values
    print("\n샘플 (기타 값이 있는 경우):")
    for col in checkbox_cols:
        other_values = set()
        for row in data:
            val = row.get(col, "")
            if val not in ("TRUE", "FALSE", ""):
                other_values.add(val)

        if other_values:
            print(f"  {col}: {other_values}")
else:
    print("시트 데이터 없음")
