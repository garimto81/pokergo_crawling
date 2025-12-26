"""Fix checkbox values: convert string TRUE/FALSE to boolean."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sheets.writer import SheetsWriter

writer = SheetsWriter()

print("=" * 80)
print("Checkbox 값 수정: 문자열 → Boolean 변환")
print("=" * 80)

# 1. Read current data
headers, data = writer.get_sheet_data("Subclip_Validation_Report")
print(f"\n총 {len(data)}행 데이터 로드")

# 2. Checkbox columns (G=6, H=7, I=8, J=9, K=10, L=11 - 0-indexed)
checkbox_cols = [
    "orphan_subclip",     # G (index 6)
    "missing_parent",     # H (index 7)
    "self_reference",     # I (index 8)
    "missing_timecode",   # J (index 9)
    "round_timecode",     # K (index 10)
    "invalid_range",      # L (index 11)
]

# 3. Prepare checkbox column data only (G:L = columns 7-12 in 1-indexed)
# We need to update just the checkbox columns using USER_ENTERED
checkbox_values = []

for row in data:
    row_values = []
    for col in checkbox_cols:
        val = row.get(col, "FALSE")
        # Keep as string - USER_ENTERED will convert to boolean
        row_values.append(val)
    checkbox_values.append(row_values)

print(f"Checkbox 컬럼 데이터 준비 완료: {len(checkbox_values)}행 x {len(checkbox_cols)}열")

# 4. Update using USER_ENTERED to convert to boolean
range_str = f"Subclip_Validation_Report!G2:L{len(data) + 1}"
print(f"\n범위 업데이트: {range_str}")

result = writer.service.spreadsheets().values().update(
    spreadsheetId=writer.spreadsheet_id,
    range=range_str,
    valueInputOption="USER_ENTERED",  # ← 핵심! TRUE/FALSE를 boolean으로 변환
    body={"values": checkbox_values},
).execute()

print(f"\n업데이트 완료:")
print(f"  updatedCells: {result.get('updatedCells')}")
print(f"  updatedRows: {result.get('updatedRows')}")
print(f"  updatedColumns: {result.get('updatedColumns')}")

# 5. Verify the fix
print("\n" + "=" * 80)
print("수정 결과 확인")
print("=" * 80)

# Check first few cells
verify_result = writer.service.spreadsheets().get(
    spreadsheetId=writer.spreadsheet_id,
    ranges=["Subclip_Validation_Report!G2:L3"],
    includeGridData=True,
).execute()

for sheet in verify_result.get("sheets", []):
    for grid_data in sheet.get("data", []):
        for row_idx, row in enumerate(grid_data.get("rowData", []), start=2):
            print(f"\n행 {row_idx}:")
            for col_idx, cell in enumerate(row.get("values", [])):
                col_letter = chr(ord("G") + col_idx)
                effective = cell.get("effectiveValue", {})
                formatted = cell.get("formattedValue", "")

                if "boolValue" in effective:
                    status = "✓ Boolean"
                elif "stringValue" in effective:
                    status = "✗ 여전히 String"
                else:
                    status = "? Unknown"

                print(f"  {col_letter}: {formatted} → {effective} [{status}]")

print("\n완료!")
