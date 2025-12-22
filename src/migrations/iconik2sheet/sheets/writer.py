"""Google Sheets Writer."""

from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings


class SheetsWriter:
    """Google Sheets writer with batch support."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self) -> None:
        settings = get_settings()
        self.service_account_path = Path(settings.sheets.service_account_path)
        self.spreadsheet_id = settings.sheets.spreadsheet_id
        self._service: Any = None

    @property
    def service(self) -> Any:
        """Get or create Sheets service."""
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                str(self.service_account_path),
                scopes=self.SCOPES,
            )
            self._service = build("sheets", "v4", credentials=credentials)
        return self._service

    def clear_sheet(self, sheet_name: str) -> None:
        """Clear all data from a sheet."""
        self.service.spreadsheets().values().clear(
            spreadsheetId=self.spreadsheet_id,
            range=sheet_name,
        ).execute()

    def write_rows(self, sheet_name: str, rows: list[list[Any]], start_row: int = 1) -> int:
        """Write rows to sheet.

        Args:
            sheet_name: Target sheet name
            rows: 2D list of values
            start_row: Starting row (1-indexed)

        Returns:
            Number of rows written
        """
        if not rows:
            return 0

        range_str = f"{sheet_name}!A{start_row}"

        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_str,
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()

        return len(rows)

    def append_rows(self, sheet_name: str, rows: list[list[Any]]) -> int:
        """Append rows to sheet.

        Args:
            sheet_name: Target sheet name
            rows: 2D list of values

        Returns:
            Number of rows appended
        """
        if not rows:
            return 0

        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=sheet_name,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()

        return len(rows)

    def create_sheet_if_not_exists(self, sheet_name: str) -> bool:
        """Create sheet if it doesn't exist.

        Returns:
            True if created, False if already exists
        """
        # Get existing sheets
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        existing_sheets = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]

        if sheet_name in existing_sheets:
            return False

        # Create new sheet
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": sheet_name,
                            }
                        }
                    }
                ]
            },
        ).execute()

        return True

    def write_assets(self, assets: list[dict[str, Any]]) -> int:
        """Write assets to Iconik_Assets sheet."""
        sheet_name = "Iconik_Assets"
        self.create_sheet_if_not_exists(sheet_name)
        self.clear_sheet(sheet_name)

        # Headers
        headers = ["ID", "Title", "External_ID", "Status", "Is_Online", "Created_At", "Updated_At"]
        rows = [headers]

        # Data rows
        for asset in assets:
            rows.append([
                asset.get("id", ""),
                asset.get("title", ""),
                asset.get("external_id", ""),
                asset.get("status", ""),
                str(asset.get("is_online", "")),
                str(asset.get("created_at", "")),
                str(asset.get("updated_at", "")),
            ])

        return self.write_rows(sheet_name, rows)

    def write_collections(self, collections: list[dict[str, Any]]) -> int:
        """Write collections to Iconik_Collections sheet."""
        sheet_name = "Iconik_Collections"
        self.create_sheet_if_not_exists(sheet_name)
        self.clear_sheet(sheet_name)

        # Headers
        headers = ["Collection_ID", "Title", "Parent_ID", "Is_Root", "Created_At"]
        rows = [headers]

        # Data rows
        for col in collections:
            rows.append([
                col.get("id", ""),
                col.get("title", ""),
                col.get("parent_id", ""),
                str(col.get("is_root", "")),
                str(col.get("created_at", "")),
            ])

        return self.write_rows(sheet_name, rows)

    def write_sync_log(self, log_entry: dict[str, Any]) -> int:
        """Append sync log entry."""
        sheet_name = "Sync_Log"
        self.create_sheet_if_not_exists(sheet_name)

        # Check if headers exist
        try:
            existing = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1:G1",
            ).execute()

            if not existing.get("values"):
                headers = [["Sync_ID", "Sync_Type", "Started_At", "Completed_At", "Assets_New", "Assets_Updated", "Status"]]
                self.write_rows(sheet_name, headers)
        except Exception:
            headers = [["Sync_ID", "Sync_Type", "Started_At", "Completed_At", "Assets_New", "Assets_Updated", "Status"]]
            self.write_rows(sheet_name, headers)

        # Append log entry
        row = [[
            log_entry.get("sync_id", ""),
            log_entry.get("sync_type", ""),
            str(log_entry.get("started_at", "")),
            str(log_entry.get("completed_at", "")),
            str(log_entry.get("assets_new", 0)),
            str(log_entry.get("assets_updated", 0)),
            log_entry.get("status", ""),
        ]]

        return self.append_rows(sheet_name, row)

    def health_check(self) -> bool:
        """Check API connection."""
        try:
            self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            return True
        except Exception:
            return False

    def write_full_metadata(self, exports: list[dict[str, Any]]) -> int:
        """Write full metadata to Iconik_Full_Metadata sheet (35 columns).

        Matches GGmetadata_and_timestamps structure exactly.
        """
        sheet_name = "Iconik_Full_Metadata"
        self.create_sheet_if_not_exists(sheet_name)
        self.clear_sheet(sheet_name)

        # Headers (35 columns - matching GGmetadata_and_timestamps)
        headers = [
            "id", "title",
            "time_start_ms", "time_end_ms", "time_start_S", "time_end_S",
            "Description", "ProjectName", "ProjectNameTag", "SearchTag",
            "Year_", "Location", "Venue", "EpisodeEvent",
            "Source", "Scene", "GameType", "PlayersTags",
            "HandGrade", "HANDTag", "EPICHAND", "Tournament",
            "PokerPlayTags", "Adjective", "Emotion", "AppearanceOutfit",
            "SceneryObject", "_gcvi_tags", "Badbeat", "Bluff",
            "Suckout", "Cooler", "RUNOUTTag", "PostFlop", "All-in",
        ]
        rows = [headers]

        # Data rows
        for export in exports:
            row = [
                export.get("id", ""),
                export.get("title", ""),
                str(export.get("time_start_ms", "")),
                str(export.get("time_end_ms", "")),
                str(export.get("time_start_S", "")),
                str(export.get("time_end_S", "")),
                export.get("Description", ""),
                export.get("ProjectName", ""),
                export.get("ProjectNameTag", ""),
                export.get("SearchTag", ""),
                str(export.get("Year_", "")),
                export.get("Location", ""),
                export.get("Venue", ""),
                export.get("EpisodeEvent", ""),
                export.get("Source", ""),
                export.get("Scene", ""),
                export.get("GameType", ""),
                export.get("PlayersTags", ""),
                export.get("HandGrade", ""),
                export.get("HANDTag", ""),
                str(export.get("EPICHAND", "")),
                export.get("Tournament", ""),
                export.get("PokerPlayTags", ""),
                export.get("Adjective", ""),
                export.get("Emotion", ""),
                export.get("AppearanceOutfit", ""),
                export.get("SceneryObject", ""),
                export.get("_gcvi_tags", ""),
                export.get("Badbeat", ""),
                export.get("Bluff", ""),
                export.get("Suckout", ""),
                export.get("Cooler", ""),
                export.get("RUNOUTTag", ""),
                export.get("PostFlop", ""),
                export.get("All_in", ""),  # Note: All-in → All_in in Python
            ]
            rows.append(row)

        return self.write_rows(sheet_name, rows)

    def get_sheet_data(self, sheet_name: str) -> tuple[list[str], list[dict]]:
        """Read all data from a sheet.

        Args:
            sheet_name: Sheet name to read

        Returns:
            Tuple of (headers, data_rows as dicts)
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_name,
            ).execute()

            values = result.get("values", [])
            if not values:
                return [], []

            headers = values[0]
            data = []

            for row in values[1:]:
                # Pad row to match headers length
                padded_row = row + [""] * (len(headers) - len(row))
                data.append(dict(zip(headers, padded_row)))

            return headers, data

        except Exception:
            return [], []

    def update_rows_by_id(
        self,
        sheet_name: str,
        updates: list[dict[str, Any]],
        id_column: str = "id",
    ) -> dict[str, int]:
        """Update specific rows by ID (incremental update).

        Args:
            sheet_name: Target sheet name
            updates: List of dicts with data to update (must include id_column)
            id_column: Column name to use as row identifier

        Returns:
            Dict with updated, inserted, skipped counts
        """
        result = {"updated": 0, "inserted": 0, "skipped": 0}

        if not updates:
            return result

        # Get current data
        headers, existing_data = self.get_sheet_data(sheet_name)

        if not headers:
            # Sheet is empty, just write all
            return {"updated": 0, "inserted": len(updates), "skipped": 0}

        # Build ID to row index map (1-indexed, +1 for header)
        id_to_row = {}
        for i, row in enumerate(existing_data):
            row_id = row.get(id_column)
            if row_id:
                id_to_row[row_id] = i + 2  # +2: 1 for 0-index, 1 for header

        # Prepare batch updates
        batch_data = []
        new_rows = []

        for update in updates:
            update_id = update.get(id_column)
            if not update_id:
                result["skipped"] += 1
                continue

            # Build row values in header order
            row_values = [str(update.get(h, "")) for h in headers]

            if update_id in id_to_row:
                # Update existing row
                row_num = id_to_row[update_id]
                batch_data.append({
                    "range": f"{sheet_name}!A{row_num}",
                    "values": [row_values],
                })
                result["updated"] += 1
            else:
                # New row to append
                new_rows.append(row_values)
                result["inserted"] += 1

        # Execute batch update for existing rows
        if batch_data:
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    "valueInputOption": "RAW",
                    "data": batch_data,
                },
            ).execute()

        # Append new rows
        if new_rows:
            self.append_rows(sheet_name, new_rows)

        return result
