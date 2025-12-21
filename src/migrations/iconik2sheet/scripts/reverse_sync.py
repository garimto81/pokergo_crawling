"""Reverse sync from Google Sheets to iconik.

Synchronizes metadata and timecodes from Iconik_Full_Metadata sheet to iconik MAM.

Usage:
    python -m scripts.reverse_sync --dry-run          # Preview only
    python -m scripts.reverse_sync --limit 10         # Sync 10 assets
    python -m scripts.reverse_sync --metadata-only    # Metadata only (no timecodes)
    python -m scripts.reverse_sync --timecode-only    # Timecodes only
    python -m scripts.reverse_sync                    # Full sync
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings
from iconik import IconikClient
from iconik.exceptions import IconikAPIError


# Metadata field mapping
METADATA_FIELD_MAP = {
    "Description": "Description",
    "ProjectName": "ProjectName",
    "ProjectNameTag": "ProjectNameTag",
    "SearchTag": "SearchTag",
    "Year_": "Year_",
    "Location": "Location",
    "Venue": "Venue",
    "EpisodeEvent": "EpisodeEvent",
    "Source": "Source",
    "Scene": "Scene",
    "GameType": "GameType",
    "PlayersTags": "PlayersTags",
    "HandGrade": "HandGrade",
    "HANDTag": "HANDTag",
    "EPICHAND": "EPICHAND",
    "Tournament": "Tournament",
    "PokerPlayTags": "PokerPlayTags",
    "Adjective": "Adjective",
    "Emotion": "Emotion",
    "AppearanceOutfit": "AppearanceOutfit",
    "SceneryObject": "SceneryObject",
    "_gcvi_tags": "_gcvi_tags",
    "Badbeat": "Badbeat",
    "Bluff": "Bluff",
    "Suckout": "Suckout",
    "Cooler": "Cooler",
    "RUNOUTTag": "RUNOUTTag",
    "PostFlop": "PostFlop",
    "All-in": "All-in",
}


class ReverseSync:
    """Reverse sync from Sheets to iconik."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.iconik = IconikClient()
        self._sheets_service = None
        self.view_id = self.settings.iconik.metadata_view_id

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

    def read_sheet_data(self) -> tuple[list[str], list[dict]]:
        """Read Iconik_Full_Metadata sheet."""
        print("1. Reading Iconik_Full_Metadata sheet...")

        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.settings.sheets.spreadsheet_id,
            range="Iconik_Full_Metadata",
        ).execute()

        values = result.get("values", [])
        if not values:
            return [], []

        headers = values[0]
        print(f"   Columns: {len(headers)}")
        print(f"   Rows: {len(values) - 1}")

        data = []
        for row in values[1:]:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ""
            data.append(row_dict)

        return headers, data

    def build_metadata_payload(self, row: dict) -> dict[str, Any]:
        """Build iconik metadata payload."""
        metadata_values = {}

        for sheet_col, api_field in METADATA_FIELD_MAP.items():
            value = row.get(sheet_col, "").strip()
            if value:
                if "," in value:
                    field_values = [{"value": v.strip()} for v in value.split(",")]
                else:
                    field_values = [{"value": value}]
                metadata_values[api_field] = {"field_values": field_values}

        return metadata_values

    def get_timecode(self, row: dict) -> tuple[int, int] | None:
        """Extract timecode from row."""
        time_start = row.get("time_start_ms", "").strip()
        time_end = row.get("time_end_ms", "").strip()

        if not time_start or not time_end:
            return None

        try:
            return int(float(time_start)), int(float(time_end))
        except (ValueError, TypeError):
            return None

    def sync_metadata(self, asset_id: str, metadata: dict, dry_run: bool) -> dict:
        """Sync metadata to iconik."""
        if dry_run:
            return {"success": True, "action": "would_update"}

        try:
            self.iconik.update_asset_metadata(asset_id, self.view_id, metadata)
            return {"success": True, "action": "updated"}
        except IconikAPIError as e:
            return {"success": False, "error": str(e)}

    def sync_timecode(
        self, asset_id: str, time_start_ms: int, time_end_ms: int, dry_run: bool
    ) -> dict:
        """Sync timecode to iconik."""
        # Check if segment already exists
        existing = self.iconik.get_asset_segments(asset_id, raise_for_404=False)

        # Skip if already has segments with same timecode
        for seg in existing:
            if (
                seg.get("time_start_milliseconds") == time_start_ms
                and seg.get("time_end_milliseconds") == time_end_ms
            ):
                return {"success": True, "action": "skipped", "reason": "exists"}

        if dry_run:
            return {"success": True, "action": "would_create"}

        try:
            self.iconik.create_asset_segment(asset_id, time_start_ms, time_end_ms)
            return {"success": True, "action": "created"}
        except IconikAPIError as e:
            return {"success": False, "error": str(e)}

    def run(
        self,
        dry_run: bool = True,
        limit: int | None = None,
        metadata_only: bool = False,
        timecode_only: bool = False,
    ) -> dict:
        """Run reverse sync.

        Args:
            dry_run: Preview without actual changes
            limit: Limit number of assets to process
            metadata_only: Only sync metadata
            timecode_only: Only sync timecodes
        """
        sync_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        print("\n" + "=" * 60)
        print("REVERSE SYNC: Sheets -> iconik")
        print("=" * 60)
        print(f"\nSync ID: {sync_id}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"Scope: {'metadata only' if metadata_only else 'timecode only' if timecode_only else 'full (metadata + timecode)'}")

        if not self.view_id:
            print("\nERROR: ICONIK_METADATA_VIEW_ID not set")
            return {"error": "Missing view_id"}

        # Read data
        headers, data = self.read_sheet_data()
        if not data:
            return {"error": "No data"}

        # Process
        results = {
            "sync_id": sync_id,
            "total": len(data),
            "metadata": {"updated": 0, "skipped": 0, "failed": 0},
            "timecode": {"created": 0, "skipped": 0, "failed": 0},
        }

        process_list = data[:limit] if limit else data
        print(f"\n2. Processing {len(process_list)} assets...")

        for i, row in enumerate(process_list):
            asset_id = row.get("id", "").strip()
            title = row.get("title", "")[:35]

            if not asset_id:
                continue

            status_parts = []

            # Metadata sync
            if not timecode_only:
                metadata = self.build_metadata_payload(row)
                if metadata:
                    result = self.sync_metadata(asset_id, metadata, dry_run)
                    if result.get("success"):
                        action = result.get("action", "ok")
                        status_parts.append(f"meta:{action}")
                        if action in ("updated", "would_update"):
                            results["metadata"]["updated"] += 1
                        else:
                            results["metadata"]["skipped"] += 1
                    else:
                        status_parts.append(f"meta:FAIL")
                        results["metadata"]["failed"] += 1

            # Timecode sync
            if not metadata_only:
                timecode = self.get_timecode(row)
                if timecode:
                    time_start_ms, time_end_ms = timecode
                    result = self.sync_timecode(asset_id, time_start_ms, time_end_ms, dry_run)
                    if result.get("success"):
                        action = result.get("action", "ok")
                        status_parts.append(f"tc:{action}")
                        if action in ("created", "would_create"):
                            results["timecode"]["created"] += 1
                        else:
                            results["timecode"]["skipped"] += 1
                    else:
                        status_parts.append(f"tc:FAIL")
                        results["timecode"]["failed"] += 1

            if status_parts:
                status = " | ".join(status_parts)
                print(f"   [{i+1}] {asset_id[:8]}... | {status} | {title}")

            if (i + 1) % 100 == 0:
                print(f"   ... {i + 1}/{len(process_list)} processed")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"\nSync ID: {sync_id}")
        print(f"Total assets: {results['total']}")

        if not timecode_only:
            m = results["metadata"]
            print(f"\nMetadata:")
            print(f"  Updated: {m['updated']}")
            print(f"  Skipped: {m['skipped']}")
            print(f"  Failed: {m['failed']}")

        if not metadata_only:
            t = results["timecode"]
            print(f"\nTimecode:")
            print(f"  Created: {t['created']}")
            print(f"  Skipped: {t['skipped']}")
            print(f"  Failed: {t['failed']}")

        self.iconik.close()
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Reverse sync from Sheets to iconik")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--limit", type=int, help="Limit number of assets")
    parser.add_argument("--metadata-only", action="store_true", help="Sync metadata only")
    parser.add_argument("--timecode-only", action="store_true", help="Sync timecodes only")
    args = parser.parse_args()

    if args.metadata_only and args.timecode_only:
        print("ERROR: Cannot use both --metadata-only and --timecode-only")
        return

    sync = ReverseSync()
    sync.run(
        dry_run=args.dry_run,
        limit=args.limit,
        metadata_only=args.metadata_only,
        timecode_only=args.timecode_only,
    )


if __name__ == "__main__":
    main()
