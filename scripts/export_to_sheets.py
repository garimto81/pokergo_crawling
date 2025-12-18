"""Export NAMS data to Google Sheets with new tab.

Usage:
    python scripts/export_to_sheets.py [sheet_name]
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nams.api.services.export import export_to_google_sheets


def main():
    # Default sheet name with timestamp
    default_name = f"NAMS_{datetime.now().strftime('%Y%m%d_%H%M')}"
    sheet_name = sys.argv[1] if len(sys.argv) > 1 else default_name

    print("=" * 60)
    print("NAMS Google Sheets Export")
    print("=" * 60)
    print(f"\nSheet Name: {sheet_name}")
    print("Exporting...")

    result = export_to_google_sheets(sheet_name)

    if result.get("success"):
        print(f"\n[OK] Export successful!")
        print(f"  Rows: {result.get('rows_updated', 0)}")
        print(f"  URL: {result.get('url')}")
    else:
        print(f"\n[ERROR] Export failed!")
        print(f"  Error: {result.get('error')}")
        if result.get('help'):
            print(f"  Help: {result.get('help')}")


if __name__ == "__main__":
    main()
