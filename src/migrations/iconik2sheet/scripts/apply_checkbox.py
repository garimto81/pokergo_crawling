"""Apply checkbox data validation to Subclip_Validation_Report sheet."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sheets.writer import SheetsWriter

writer = SheetsWriter()

# Checkbox columns: G, H, I, J, K, L (orphan_subclip ~ invalid_range)
checkbox_columns = ["G", "H", "I", "J", "K", "L"]

print("Subclip_Validation_Report 시트에 checkbox 적용 중...")
print(f"대상 컬럼: {checkbox_columns}")

result = writer.apply_checkboxes(
    sheet_name="Subclip_Validation_Report",
    checkbox_columns=checkbox_columns,
    start_row=2,  # Skip header row
)

if result["success"]:
    print(f"\n성공!")
    print(f"  시트: {result['sheet']}")
    print(f"  컬럼: {result['columns']}")
    print(f"  행: {result['rows']}")
else:
    print(f"\n실패: {result['error']}")
