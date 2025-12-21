"""Bulk create timecodes for assets without segments.

Creates test timecodes (0-10s) for assets that don't have segments.

Usage:
    python -m scripts.bulk_create_timecodes --dry-run --limit 10
    python -m scripts.bulk_create_timecodes --limit 50
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


class BulkTimecodeCreator:
    """Create timecodes for assets without segments."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.iconik = IconikClient()
        self._sheets_service = None

    @property
    def sheets_service(self):
        if self._sheets_service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.settings.sheets.service_account_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            self._sheets_service = build("sheets", "v4", credentials=credentials)
        return self._sheets_service

    def get_assets_without_timecode(self) -> list[dict]:
        """Get assets without timecode from sheet."""
        print("1. Reading sheet for assets without timecode...")

        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.settings.sheets.spreadsheet_id,
            range="Iconik_Full_Metadata!A:F",
        ).execute()

        values = result.get("values", [])
        assets = []

        for row in values[1:]:
            if len(row) < 2:
                continue

            asset_id = row[0] if len(row) > 0 else ""
            title = row[1] if len(row) > 1 else ""
            time_start = row[2] if len(row) > 2 else ""
            time_end = row[3] if len(row) > 3 else ""

            # Only assets WITHOUT timecode in sheet
            if not (time_start.strip() and time_end.strip()):
                assets.append({
                    "id": asset_id,
                    "title": title[:50] if title else "Untitled",
                })

        print(f"   Found {len(assets)} assets without timecode in sheet")
        return assets

    def create_segment(self, asset_id: str, time_start_ms: int, time_end_ms: int, title: str = "") -> dict:
        """Create segment on iconik."""
        endpoint = f"/assets/v1/assets/{asset_id}/segments/"
        segment_data = {
            "time_start_milliseconds": time_start_ms,
            "time_end_milliseconds": time_end_ms,
            "segment_type": "GENERIC",
            "title": f"Bulk Import: {title}" if title else "Bulk Import",
        }

        try:
            response = self.iconik.client.post(endpoint, json=segment_data)
            if response.status_code == 201:
                data = response.json()
                return {"success": True, "segment_id": data.get("id"), "parent_asset": data.get("asset_id")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}", "detail": response.text[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run(self, dry_run: bool = True, limit: int = 10) -> dict:
        """Run bulk creation.

        Args:
            dry_run: Preview only
            limit: Number of assets to process
        """
        print("\n=== Bulk Timecode Creation ===\n")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE CREATE'}")
        print(f"Limit: {limit} assets\n")

        # Get assets
        assets = self.get_assets_without_timecode()
        if not assets:
            return {"error": "No assets without timecode"}

        # Verify they don't have segments in iconik
        print("\n2. Verifying assets have no segments in iconik...")

        candidates = []
        for i, asset in enumerate(assets[:limit * 2]):  # Check more to find enough
            if len(candidates) >= limit:
                break

            segments = self.iconik.get_asset_segments(asset["id"], raise_for_404=False)
            if not segments:
                candidates.append(asset)

            if (i + 1) % 20 == 0:
                print(f"   ... checked {i + 1}, found {len(candidates)} candidates")

        print(f"   Found {len(candidates)} assets ready for timecode creation")

        if not candidates:
            print("   No assets without segments found")
            return {"created": 0}

        # Create timecodes
        print(f"\n3. {'Preview' if dry_run else 'Creating'} timecodes...")

        results = {
            "total": len(candidates),
            "created": 0,
            "failed": 0,
            "details": [],
        }

        # Generate different timecodes for each asset
        for i, asset in enumerate(candidates[:limit]):
            asset_id = asset["id"]
            title = asset["title"]

            # Generate test timecode: 0-10s, 10-20s, 20-30s, etc.
            time_start_ms = (i % 10) * 10000
            time_end_ms = time_start_ms + 10000

            if dry_run:
                print(f"   [{i+1}] WILL CREATE: {asset_id[:8]}... | {time_start_ms}ms-{time_end_ms}ms | {title}")
                results["details"].append({
                    "asset_id": asset_id,
                    "time_start_ms": time_start_ms,
                    "time_end_ms": time_end_ms,
                })
            else:
                result = self.create_segment(asset_id, time_start_ms, time_end_ms, title)

                if result.get("success"):
                    print(f"   [{i+1}] OK: {asset_id[:8]}... | {time_start_ms}ms-{time_end_ms}ms")
                    print(f"         Segment ID: {result.get('segment_id', 'N/A')[:8]}...")
                    if result.get("parent_asset") != asset_id:
                        print(f"         (Created on parent: {result.get('parent_asset', 'N/A')[:8]}...)")
                    results["created"] += 1
                else:
                    print(f"   [{i+1}] FAIL: {asset_id[:8]}... | {result.get('error')}")
                    results["failed"] += 1

        # Summary
        print(f"\n=== Summary ===")
        print(f"Total candidates: {results['total']}")
        if not dry_run:
            print(f"Created: {results['created']}")
            print(f"Failed: {results['failed']}")

        self.iconik.close()
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk create timecodes")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--limit", type=int, default=10, help="Number of assets to process")
    args = parser.parse_args()

    creator = BulkTimecodeCreator()
    creator.run(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
