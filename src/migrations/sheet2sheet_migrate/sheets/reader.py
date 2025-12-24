"""Google Sheets Reader with multi-tab support."""

from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings


class SheetsReader:
    """Google Sheets reader supporting multiple tabs."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

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

    def get_tab_names(self, spreadsheet_id: str) -> list[str]:
        """Get all tab names from a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID

        Returns:
            List of tab names
        """
        service = self._get_service()
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        return [
            sheet["properties"]["title"]
            for sheet in spreadsheet.get("sheets", [])
        ]

    def read_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        header_row: int = 1,
    ) -> list[dict]:
        """Read a single sheet and return as list of dicts.

        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_name: Name of the sheet/tab
            header_row: Row number containing headers (1-indexed)

        Returns:
            List of dicts with headers as keys
        """
        service = self._get_service()

        # Read all data
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'",
        ).execute()

        rows = result.get("values", [])
        if not rows or len(rows) < header_row:
            return []

        # Get headers from specified row
        headers = rows[header_row - 1]  # Convert to 0-indexed
        data = []

        # Process data rows after header
        for row in rows[header_row:]:
            if not any(cell.strip() for cell in row if isinstance(cell, str)):
                continue  # Skip empty rows

            # Pad row to match header length
            padded_row = row + [""] * (len(headers) - len(row))
            row_dict = {}

            for i, header in enumerate(headers):
                if header and i < len(padded_row):
                    row_dict[header] = padded_row[i]

            if row_dict:  # Only add non-empty rows
                data.append(row_dict)

        return data

    def read_all_tabs(
        self,
        spreadsheet_id: str | None = None,
        header_row: int | None = None,
    ) -> dict[str, list[dict]]:
        """Read all tabs from a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID (defaults to source_spreadsheet_id)
            header_row: Row number containing headers (defaults to settings.header_row)

        Returns:
            Dict mapping tab name to list of row dicts
        """
        if spreadsheet_id is None:
            spreadsheet_id = self.settings.source_spreadsheet_id
        if header_row is None:
            header_row = self.settings.header_row

        tab_names = self.get_tab_names(spreadsheet_id)
        result = {}

        for tab_name in tab_names:
            data = self.read_sheet(spreadsheet_id, tab_name, header_row)
            if data:
                result[tab_name] = data

        return result

    def read_source(self) -> dict[str, list[dict]]:
        """Read all tabs from source spreadsheet."""
        return self.read_all_tabs(
            self.settings.source_spreadsheet_id,
            self.settings.header_row,
        )

    def health_check(self) -> bool:
        """Check API connection."""
        try:
            self._get_service().spreadsheets().get(
                spreadsheetId=self.settings.source_spreadsheet_id
            ).execute()
            return True
        except Exception:
            return False
