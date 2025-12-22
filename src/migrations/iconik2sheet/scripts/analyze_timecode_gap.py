"""Analyze timecode gap between Sheet and iconik."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account
from googleapiclient.discovery import build
from config.settings import get_settings
from iconik import IconikClient


def main():
    settings = get_settings()

    # Read sheet
    print("1. Reading Iconik_Full_Metadata sheet...")
    credentials = service_account.Credentials.from_service_account_file(
        settings.sheets.service_account_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=credentials)

    result = service.spreadsheets().values().get(
        spreadsheetId=settings.sheets.spreadsheet_id,
        range="Iconik_Full_Metadata!A:F",
    ).execute()

    values = result.get("values", [])
    print(f"   Total rows: {len(values) - 1}")

    # Parse and categorize
    sheet_with_timecode = []
    sheet_without_timecode = []

    for row in values[1:]:
        if len(row) < 2:
            continue

        asset_id = row[0] if len(row) > 0 else ""
        time_start = row[2] if len(row) > 2 else ""
        time_end = row[3] if len(row) > 3 else ""

        has_timecode = time_start.strip() and time_end.strip()

        if has_timecode:
            sheet_with_timecode.append(asset_id)
        else:
            sheet_without_timecode.append(asset_id)

    print(f"   Sheet with timecode: {len(sheet_with_timecode)}")
    print(f"   Sheet without timecode: {len(sheet_without_timecode)}")

    # Check iconik for assets WITHOUT timecode in sheet
    print("\n2. Checking iconik for assets WITHOUT timecode in sheet...")
    print("   (These might need timecode from another source)")

    with IconikClient() as client:
        # Sample check
        sample_size = 50
        iconik_has_segment = 0
        iconik_no_segment = 0

        for i, asset_id in enumerate(sheet_without_timecode[:sample_size]):
            segments = client.get_asset_segments(asset_id, raise_for_404=False)
            if segments:
                iconik_has_segment += 1
            else:
                iconik_no_segment += 1

            if (i + 1) % 10 == 0:
                print(f"   ... checked {i + 1}/{sample_size}")

        print(f"\n   Sample of {sample_size} assets without timecode in sheet:")
        print(f"   - iconik HAS segments: {iconik_has_segment}")
        print(f"   - iconik NO segments: {iconik_no_segment}")

        # Check iconik for assets WITH timecode in sheet (to find new uploads needed)
        print("\n3. Checking if sheet timecodes need upload to iconik...")

        need_upload = []
        already_exists = 0

        for i, asset_id in enumerate(sheet_with_timecode[:100]):
            segments = client.get_asset_segments(asset_id, raise_for_404=False)
            if not segments:
                need_upload.append(asset_id)
            else:
                already_exists += 1

            if (i + 1) % 20 == 0:
                print(f"   ... checked {i + 1}/100")

        print(f"\n   Sample of 100 assets WITH timecode in sheet:")
        print(f"   - Already has segments: {already_exists}")
        print(f"   - Need upload: {len(need_upload)}")

        if need_upload:
            print(f"\n   Assets needing upload:")
            for aid in need_upload[:10]:
                print(f"     - {aid}")


if __name__ == "__main__":
    main()
