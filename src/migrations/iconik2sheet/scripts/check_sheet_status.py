"""Check Subclip_Validation_Report sheet status and data validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sheets.writer import SheetsWriter

writer = SheetsWriter()

print("=" * 80)
print("Subclip_Validation_Report 시트 상태 확인")
print("=" * 80)

# 1. Get spreadsheet metadata including data validation
spreadsheet = writer.service.spreadsheets().get(
    spreadsheetId=writer.spreadsheet_id,
    includeGridData=True,
    ranges=["Subclip_Validation_Report!A1:L10"],  # First 10 rows
).execute()

# Find sheet
target_sheet = None
for sheet in spreadsheet.get("sheets", []):
    if sheet["properties"]["title"] == "Subclip_Validation_Report":
        target_sheet = sheet
        break

if not target_sheet:
    print("시트를 찾을 수 없습니다!")
    sys.exit(1)

print(f"\n[시트 정보]")
print(f"  Sheet ID: {target_sheet['properties']['sheetId']}")
print(f"  Row Count: {target_sheet['properties']['gridProperties']['rowCount']}")
print(f"  Column Count: {target_sheet['properties']['gridProperties']['columnCount']}")

# 2. Check grid data
grid_data = target_sheet.get("data", [])
if grid_data:
    row_data = grid_data[0].get("rowData", [])

    print(f"\n[셀 데이터 분석 (처음 10행)]")

    # Column headers
    headers = []
    if row_data:
        for cell in row_data[0].get("values", []):
            headers.append(cell.get("formattedValue", ""))
    print(f"  헤더: {headers}")

    # Check checkbox columns (G=6, H=7, I=8, J=9, K=10, L=11)
    checkbox_cols = {"G": 6, "H": 7, "I": 8, "J": 9, "K": 10, "L": 11}

    print(f"\n[Checkbox 컬럼 분석]")
    for row_idx, row in enumerate(row_data[1:6], start=2):  # Rows 2-6 (skip header)
        values = row.get("values", [])
        print(f"\n  행 {row_idx}:")

        for col_name, col_idx in checkbox_cols.items():
            if col_idx < len(values):
                cell = values[col_idx]

                # Check various cell properties
                formatted = cell.get("formattedValue", "")
                effective = cell.get("effectiveValue", {})
                user_entered = cell.get("userEnteredValue", {})
                data_validation = cell.get("dataValidation", {})

                print(f"    {col_name} ({headers[col_idx] if col_idx < len(headers) else '?'}):")
                print(f"      formattedValue: {repr(formatted)}")
                print(f"      effectiveValue: {effective}")
                print(f"      userEnteredValue: {user_entered}")
                if data_validation:
                    print(f"      dataValidation: {data_validation}")
                else:
                    print(f"      dataValidation: 없음")

# 3. Check data validation rules separately
print("\n" + "=" * 80)
print("[Data Validation 규칙 조회]")
print("=" * 80)

try:
    # Get data validation for checkbox columns
    for col in ["G", "H", "I", "J", "K", "L"]:
        range_str = f"Subclip_Validation_Report!{col}2:{col}5"
        result = writer.service.spreadsheets().get(
            spreadsheetId=writer.spreadsheet_id,
            ranges=[range_str],
            includeGridData=True,
        ).execute()

        for sheet in result.get("sheets", []):
            data = sheet.get("data", [])
            if data:
                for row_data in data[0].get("rowData", [])[:1]:  # Just first row
                    for cell in row_data.get("values", []):
                        dv = cell.get("dataValidation")
                        if dv:
                            print(f"\n  컬럼 {col} Data Validation:")
                            print(f"    condition type: {dv.get('condition', {}).get('type')}")
                            print(f"    showCustomUi: {dv.get('showCustomUi')}")
                            break
except Exception as e:
    print(f"  Error: {e}")

# 4. Summary
print("\n" + "=" * 80)
print("[문제 분석]")
print("=" * 80)

# Read actual data
headers, data = writer.get_sheet_data("Subclip_Validation_Report")

# Check value types
sample_values = set()
for row in data[:20]:
    for col in ["orphan_subclip", "missing_parent", "self_reference",
                "missing_timecode", "round_timecode", "invalid_range"]:
        val = row.get(col, "")
        sample_values.add((col, repr(val), type(val).__name__))

print("\n값 타입 샘플:")
for col, val, typ in sorted(sample_values):
    print(f"  {col}: {val} (type={typ})")
