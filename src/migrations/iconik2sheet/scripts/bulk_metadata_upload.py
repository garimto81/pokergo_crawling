"""Bulk metadata upload from Google Sheets to iconik.

Uploads metadata from Iconik_Full_Metadata sheet to iconik MAM system.

Usage:
    python -m scripts.bulk_metadata_upload --dry-run          # Preview only
    python -m scripts.bulk_metadata_upload --limit 10         # Upload 10 assets
    python -m scripts.bulk_metadata_upload                    # Full upload
"""

import sys
from pathlib import Path
import argparse
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings
from iconik import IconikClient
from iconik.exceptions import IconikAPIError


# Metadata field mapping: Sheet column -> iconik API field
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


class BulkMetadataUploader:
    """Upload metadata from Sheets to iconik."""

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
        """Read Iconik_Full_Metadata sheet.

        Returns:
            Tuple of (headers, data_rows)
        """
        print("1. Reading Iconik_Full_Metadata sheet...")

        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.settings.sheets.spreadsheet_id,
            range="Iconik_Full_Metadata",
        ).execute()

        values = result.get("values", [])
        if not values:
            print("   No data found")
            return [], []

        headers = values[0]
        print(f"   Headers: {len(headers)} columns")
        print(f"   Total rows: {len(values) - 1}")

        # Parse data into dicts
        data = []
        for row in values[1:]:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ""
            data.append(row_dict)

        return headers, data

    def build_metadata_payload(self, row: dict) -> dict[str, Any]:
        """Build iconik metadata payload from sheet row.

        Args:
            row: Sheet row as dict

        Returns:
            Dict of field_name -> field_values for iconik API
        """
        metadata_values = {}

        for sheet_col, api_field in METADATA_FIELD_MAP.items():
            value = row.get(sheet_col, "").strip()
            if value:
                # Handle multi-value fields (comma-separated)
                if "," in value:
                    field_values = [{"value": v.strip()} for v in value.split(",")]
                else:
                    field_values = [{"value": value}]

                metadata_values[api_field] = {"field_values": field_values}

        return metadata_values

    def upload_metadata(self, asset_id: str, metadata_values: dict) -> dict:
        """Upload metadata to iconik.

        Args:
            asset_id: Asset UUID
            metadata_values: Metadata payload

        Returns:
            Result dict with success/error info
        """
        try:
            result = self.iconik.update_asset_metadata(
                asset_id, self.view_id, metadata_values
            )
            return {"success": True, "result": result}
        except IconikAPIError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run(self, dry_run: bool = True, limit: int | None = None) -> dict:
        """Run bulk metadata upload.

        Args:
            dry_run: Preview only without uploading
            limit: Limit number of uploads

        Returns:
            Summary dict
        """
        print("\n=== Bulk Metadata Upload ===\n")
        print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE UPLOAD'}")
        print(f"Metadata View ID: {self.view_id}")

        if not self.view_id:
            print("\nERROR: ICONIK_METADATA_VIEW_ID not set in .env")
            return {"error": "Missing view_id"}

        # Read sheet data
        headers, data = self.read_sheet_data()
        if not data:
            return {"error": "No data"}

        # Filter rows with metadata
        rows_with_metadata = []
        for row in data:
            metadata = self.build_metadata_payload(row)
            if metadata:
                rows_with_metadata.append((row, metadata))

        print(f"\n2. Rows with metadata: {len(rows_with_metadata)}")

        # Process
        print(f"\n3. {'Preview' if dry_run else 'Uploading'} metadata...")

        results = {
            "total": len(rows_with_metadata),
            "uploaded": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }

        process_list = rows_with_metadata[:limit] if limit else rows_with_metadata

        for i, (row, metadata) in enumerate(process_list):
            asset_id = row.get("id", "")
            title = row.get("title", "")[:40]
            field_count = len(metadata)

            if not asset_id:
                results["skipped"] += 1
                continue

            if dry_run:
                print(f"   [{i+1}] WILL UPLOAD: {asset_id[:8]}... | {field_count} fields | {title}")
            else:
                result = self.upload_metadata(asset_id, metadata)

                if result.get("success"):
                    print(f"   [{i+1}] OK: {asset_id[:8]}... | {field_count} fields")
                    results["uploaded"] += 1
                else:
                    error = result.get("error", "Unknown error")
                    print(f"   [{i+1}] FAIL: {asset_id[:8]}... | {error[:50]}")
                    results["failed"] += 1
                    results["errors"].append({"asset_id": asset_id, "error": error})

            if (i + 1) % 50 == 0:
                print(f"   ... processed {i + 1}/{len(process_list)}")

        # Summary
        print(f"\n=== Summary ===")
        print(f"Total with metadata: {results['total']}")
        if not dry_run:
            print(f"Uploaded: {results['uploaded']}")
            print(f"Skipped: {results['skipped']}")
            print(f"Failed: {results['failed']}")

        self.iconik.close()
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk metadata upload to iconik")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--limit", type=int, help="Limit number of uploads")
    args = parser.parse_args()

    uploader = BulkMetadataUploader()
    uploader.run(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
