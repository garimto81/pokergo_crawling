"""Google Sheets Writer with batch support."""

from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings
from mapping.column_mapper import TARGET_COLUMNS


class SheetsWriter:
    """Google Sheets writer with batch and incremental support."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self) -> None:
        self.settings = get_settings()
        self._service = None

    def _get_service(self) -> Any:
        """Get or create Sheets API service."""
        if self._service is None:
            creds = service_account.Credentials.from_service_account_file(
                str(self.settings.service_account_path),
                scopes=self.SCOPES,
            )
            self._service = build("sheets", "v4", credentials=creds)
        return self._service

    def create_sheet_if_not_exists(self, sheet_name: str) -> bool:
        """Create sheet if it doesn't exist.

        Returns:
            True if created, False if already exists
        """
        service = self._get_service()
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=self.settings.target_spreadsheet_id
        ).execute()

        existing_sheets = [
            s["properties"]["title"]
            for s in spreadsheet.get("sheets", [])
        ]

        if sheet_name in existing_sheets:
            return False

        service.spreadsheets().batchUpdate(
            spreadsheetId=self.settings.target_spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {"title": sheet_name}
                        }
                    }
                ]
            },
        ).execute()

        return True

    def clear_sheet(self, sheet_name: str) -> None:
        """Clear all data from a sheet."""
        self._get_service().spreadsheets().values().clear(
            spreadsheetId=self.settings.target_spreadsheet_id,
            range=sheet_name,
        ).execute()

    def write_rows(
        self,
        sheet_name: str,
        rows: list[list[Any]],
        start_row: int = 1,
    ) -> int:
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

        range_str = f"'{sheet_name}'!A{start_row}"

        self._get_service().spreadsheets().values().update(
            spreadsheetId=self.settings.target_spreadsheet_id,
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

        self._get_service().spreadsheets().values().append(
            spreadsheetId=self.settings.target_spreadsheet_id,
            range=sheet_name,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()

        return len(rows)

    def get_existing_row_count(self, sheet_name: str) -> int:
        """Get the number of existing rows in a sheet.

        Args:
            sheet_name: Sheet name

        Returns:
            Number of rows (including header)
        """
        try:
            result = self._get_service().spreadsheets().values().get(
                spreadsheetId=self.settings.target_spreadsheet_id,
                range=f"'{sheet_name}'!A:A",
            ).execute()
            return len(result.get("values", []))
        except Exception:
            return 0

    def write_full_metadata(
        self,
        data: list[dict[str, Any]],
        mode: str = "append",
    ) -> int:
        """Write data to Iconik_Full_Metadata sheet (35 columns).

        Args:
            data: List of dicts with mapped data
            mode: 'append' or 'overwrite'

        Returns:
            Number of rows written
        """
        sheet_name = self.settings.target_sheet_name
        self.create_sheet_if_not_exists(sheet_name)

        # Build rows
        rows = []

        if mode == "overwrite":
            self.clear_sheet(sheet_name)
            # Add header row
            rows.append(TARGET_COLUMNS)

        # Add data rows
        for item in data:
            row = [str(item.get(col, "")) for col in TARGET_COLUMNS]
            rows.append(row)

        if mode == "overwrite":
            return self.write_rows(sheet_name, rows)
        else:
            return self.append_rows(sheet_name, rows)

    def health_check(self) -> bool:
        """Check API connection."""
        try:
            self._get_service().spreadsheets().get(
                spreadsheetId=self.settings.target_spreadsheet_id
            ).execute()
            return True
        except Exception:
            return False
