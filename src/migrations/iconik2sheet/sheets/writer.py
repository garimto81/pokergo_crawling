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
