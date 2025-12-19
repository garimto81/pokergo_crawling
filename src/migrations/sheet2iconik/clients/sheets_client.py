"""Google Sheets API Client."""

from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings


class SheetsClient:
    """Google Sheets API client."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

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

    def get_sheet_data(self, sheet_name: str, range_notation: str = "") -> list[list[Any]]:
        """Get data from a sheet.

        Args:
            sheet_name: Name of the sheet
            range_notation: Optional range (e.g., "A1:Z100")

        Returns:
            2D list of values
        """
        range_str = f"{sheet_name}!{range_notation}" if range_notation else sheet_name

        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=range_str)
            .execute()
        )

        return result.get("values", [])

    def get_all_sheets(self) -> list[dict[str, Any]]:
        """Get all sheet names and metadata."""
        result = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()

        sheets = []
        for sheet in result.get("sheets", []):
            props = sheet.get("properties", {})
            sheets.append(
                {
                    "name": props.get("title"),
                    "index": props.get("index"),
                    "row_count": props.get("gridProperties", {}).get("rowCount"),
                    "column_count": props.get("gridProperties", {}).get("columnCount"),
                }
            )

        return sheets

    def get_matching_integrated(self) -> list[dict[str, Any]]:
        """Get Matching_Integrated sheet data as list of dicts."""
        data = self.get_sheet_data("Matching_Integrated")

        if not data:
            return []

        headers = data[0]
        rows = []

        for row in data[1:]:
            # Pad row to match headers length
            padded_row = row + [""] * (len(headers) - len(row))
            rows.append(dict(zip(headers, padded_row)))

        return rows

    def health_check(self) -> bool:
        """Check API connection."""
        try:
            self.get_all_sheets()
            return True
        except Exception:
            return False
