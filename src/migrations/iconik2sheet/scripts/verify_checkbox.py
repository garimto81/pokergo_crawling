"""Verify checkbox values are now boolean."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sheets.writer import SheetsWriter

writer = SheetsWriter()

print("=" * 80)
print("Checkbox Boolean 변환 결과 확인")
print("=" * 80)

# Check first few cells
verify_result = writer.service.spreadsheets().get(
    spreadsheetId=writer.spreadsheet_id,
    ranges=["Subclip_Validation_Report!G2:L6"],
    includeGridData=True,
).execute()

bool_count = 0
string_count = 0

for sheet in verify_result.get("sheets", []):
    for grid_data in sheet.get("data", []):
        for row_idx, row in enumerate(grid_data.get("rowData", []), start=2):
            print(f"\nRow {row_idx}:")
            for col_idx, cell in enumerate(row.get("values", [])):
                col_letter = chr(ord("G") + col_idx)
                effective = cell.get("effectiveValue", {})
                formatted = cell.get("formattedValue", "")

                if "boolValue" in effective:
                    status = "OK (Boolean)"
                    bool_count += 1
                elif "stringValue" in effective:
                    status = "FAIL (String)"
                    string_count += 1
                else:
                    status = "UNKNOWN"

                print(f"  {col_letter}: {formatted:5} | effectiveValue={effective} | {status}")

print("\n" + "=" * 80)
print("Summary:")
print(f"  Boolean: {bool_count}")
print(f"  String: {string_count}")
print("=" * 80)

if bool_count > 0 and string_count == 0:
    print("\nSUCCESS! Checkbox columns are now boolean values.")
    print("Google Sheets will display them as actual checkboxes.")
else:
    print("\nWARNING: Some values may still be strings.")
