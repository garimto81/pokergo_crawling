"""Bulk timecode upload from Google Sheets to iconik.

Usage:
    python -m scripts.bulk_timecode_upload --dry-run   # Preview only
    python -m scripts.bulk_timecode_upload             # Actual upload
"""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account
from googleapiclient.discovery import build
from config.settings import get_settings
from iconik import IconikClient


class BulkTimecodeUploader:
    """Bulk upload timecodes from Sheets to iconik."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.iconik = IconikClient()
        self._sheets_service = None

    @property
    def sheets_service(self):
        """Get Sheets service."""
        if self._sheets_service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.settings.sheets.service_account_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            self._sheets_service = build("sheets", "v4", credentials=credentials)
        return self._sheets_service

    def read_sheet_data(self) -> list[dict]:
        """Read Iconik_Full_Metadata sheet and parse timecode data."""
        print("1. Reading Iconik_Full_Metadata sheet...")

        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.settings.sheets.spreadsheet_id,
            range="Iconik_Full_Metadata!A:F",  # id, title, time columns
        ).execute()

        values = result.get("values", [])
        if not values:
            print("   No data found")
            return []

        headers = values[0]
        print(f"   Headers: {headers}")
        print(f"   Total rows: {len(values) - 1}")

        # Parse data
        data = []
        for row in values[1:]:
            if len(row) < 2:
                continue

            asset_id = row[0] if len(row) > 0 else ""
            title = row[1] if len(row) > 1 else ""
            time_start_ms = row[2] if len(row) > 2 else ""
            time_end_ms = row[3] if len(row) > 3 else ""

            data.append({
                "id": asset_id,
                "title": title,
                "time_start_ms": time_start_ms,
                "time_end_ms": time_end_ms,
            })

        return data

    def analyze_timecodes(self, data: list[dict]) -> dict:
        """Analyze timecode status."""
        print("\n2. Analyzing timecode status...")

        with_timecode = []
        without_timecode = []

        for item in data:
            has_start = item["time_start_ms"] and item["time_start_ms"].strip()
            has_end = item["time_end_ms"] and item["time_end_ms"].strip()

            if has_start and has_end:
                with_timecode.append(item)
            else:
                without_timecode.append(item)

        print(f"   With timecode: {len(with_timecode)}")
        print(f"   Without timecode: {len(without_timecode)}")

        return {
            "with_timecode": with_timecode,
            "without_timecode": without_timecode,
        }

    def check_iconik_segments(self, asset_id: str) -> list[dict]:
        """Check if asset already has segments in iconik."""
        try:
            return self.iconik.get_asset_segments(asset_id, raise_for_404=False)
        except Exception:
            return []

    def create_segment(self, asset_id: str, time_start_ms: int, time_end_ms: int) -> dict | None:
        """Create segment on iconik."""
        endpoint = f"/assets/v1/assets/{asset_id}/segments/"
        segment_data = {
            "time_start_milliseconds": time_start_ms,
            "time_end_milliseconds": time_end_ms,
            "segment_type": "GENERIC",
            "title": "Imported from Sheet",
        }

        try:
            response = self.iconik.client.post(endpoint, json=segment_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def run(self, dry_run: bool = True, limit: int | None = None) -> dict:
        """Run bulk upload.

        Args:
            dry_run: If True, only preview without uploading
            limit: Limit number of uploads (for testing)
        """
        print("\n=== Bulk Timecode Upload ===\n")
        print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE UPLOAD'}")

        # 1. Read sheet data
        data = self.read_sheet_data()
        if not data:
            return {"error": "No data"}

        # 2. Analyze
        analysis = self.analyze_timecodes(data)
        with_timecode = analysis["with_timecode"]

        if not with_timecode:
            print("\n   No assets with timecodes to upload")
            return {"uploaded": 0}

        # 3. Preview or Upload
        print(f"\n3. {'Preview' if dry_run else 'Uploading'} timecodes...")

        results = {
            "total": len(with_timecode),
            "uploaded": 0,
            "skipped": 0,
            "failed": 0,
            "details": [],
        }

        upload_list = with_timecode[:limit] if limit else with_timecode

        for i, item in enumerate(upload_list):
            asset_id = item["id"]
            title = item["title"][:40]

            try:
                time_start = int(float(item["time_start_ms"]))
                time_end = int(float(item["time_end_ms"]))
            except (ValueError, TypeError):
                print(f"   [{i+1}] SKIP - Invalid timecode: {asset_id}")
                results["skipped"] += 1
                continue

            # Check existing segments
            existing = self.check_iconik_segments(asset_id)

            if dry_run:
                status = "EXISTS" if existing else "WILL_CREATE"
                print(f"   [{i+1}] {status}: {asset_id[:8]}... | {time_start}ms-{time_end}ms | {title}")
                results["details"].append({
                    "asset_id": asset_id,
                    "status": status,
                    "existing_segments": len(existing),
                })
            else:
                if existing:
                    print(f"   [{i+1}] SKIP (has {len(existing)} segments): {asset_id[:8]}...")
                    results["skipped"] += 1
                else:
                    result = self.create_segment(asset_id, time_start, time_end)
                    if result and "error" not in result:
                        print(f"   [{i+1}] OK: {asset_id[:8]}... | {time_start}ms-{time_end}ms")
                        results["uploaded"] += 1
                    else:
                        print(f"   [{i+1}] FAIL: {asset_id[:8]}... | {result.get('error', 'Unknown')}")
                        results["failed"] += 1

            if (i + 1) % 50 == 0:
                print(f"   ... processed {i + 1}/{len(upload_list)}")

        # Summary
        print(f"\n=== Summary ===")
        print(f"Total with timecode: {results['total']}")
        if not dry_run:
            print(f"Uploaded: {results['uploaded']}")
            print(f"Skipped: {results['skipped']}")
            print(f"Failed: {results['failed']}")

        self.iconik.close()
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk timecode upload")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--limit", type=int, help="Limit number of uploads")
    args = parser.parse_args()

    uploader = BulkTimecodeUploader()
    uploader.run(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
