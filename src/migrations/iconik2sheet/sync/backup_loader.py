"""Backup file loader from Master_Catalog sheet.

Loads filenames with Role="Backup" from Master_Catalog sheet.
Used to identify Iconik assets that should be deleted.
"""

from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings

# UDM metadata 스프레드시트 (Master_Catalog 포함)
UDM_SPREADSHEET_ID = "1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4"

# Column indices (0-based)
# E열 = Role (index 4)
# Q열 = Filename (index 16)
# R열 = Full Path (index 17)
ROLE_COL_IDX = 4
FILENAME_COL_IDX = 16
FULLPATH_COL_IDX = 17


class BackupLoader:
    """Load backup filenames from Master_Catalog sheet.

    Reads Master_Catalog sheet and extracts filenames where Role="Backup".
    Returns filename stems (without extension) for matching with Iconik asset titles.
    """

    def __init__(self) -> None:
        self._service = None
        self._backup_data: list[dict] | None = None

    @property
    def service(self):
        """Get Google Sheets service (lazy init)."""
        if self._service is None:
            settings = get_settings()
            credentials = service_account.Credentials.from_service_account_file(
                str(settings.sheets.service_account_path),
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            self._service = build("sheets", "v4", credentials=credentials)
        return self._service

    def load_backup_filenames(self) -> set[str]:
        """Load backup file stems (without extension) from Master_Catalog.

        Returns:
            Set of unique filename stems where Role="Backup"
        """
        backup_data = self.load_backup_data()
        return {item["stem"] for item in backup_data}

    def load_backup_data(self) -> list[dict]:
        """Load full backup data including filename and path.

        Returns:
            List of dicts with keys: stem, filename, full_path
        """
        if self._backup_data is not None:
            return self._backup_data

        print("[BackupLoader] Loading backup files from Master_Catalog...")

        result = self.service.spreadsheets().values().get(
            spreadsheetId=UDM_SPREADSHEET_ID,
            range="Master_Catalog!A:Z",
        ).execute()

        values = result.get("values", [])
        if not values:
            print("[BackupLoader] Warning: Master_Catalog is empty")
            self._backup_data = []
            return self._backup_data

        headers = values[0]

        # Verify column indices
        role_idx = ROLE_COL_IDX
        filename_idx = FILENAME_COL_IDX
        fullpath_idx = FULLPATH_COL_IDX

        # Try to find columns by header name as fallback
        for i, h in enumerate(headers):
            h_lower = h.lower().strip()
            if h_lower == "role":
                role_idx = i
            elif h_lower == "filename":
                filename_idx = i
            elif h_lower in ("full path", "fullpath", "full_path"):
                fullpath_idx = i

        # Collect backup entries
        backup_data = []
        backup_count = 0
        primary_count = 0

        for row_num, row in enumerate(values[1:], start=2):
            # Ensure row has enough columns
            if len(row) <= max(role_idx, filename_idx):
                continue

            role = row[role_idx].strip() if len(row) > role_idx else ""
            filename = row[filename_idx].strip() if len(row) > filename_idx else ""
            full_path = row[fullpath_idx].strip() if len(row) > fullpath_idx else ""

            if not role or not filename:
                continue

            if role.upper() == "BACKUP":
                backup_count += 1
                stem = Path(filename).stem
                backup_data.append({
                    "stem": stem,
                    "filename": filename,
                    "full_path": full_path,
                    "row_num": row_num,
                })
            elif role.upper() == "PRIMARY":
                primary_count += 1

        self._backup_data = backup_data
        print(f"[BackupLoader] Found {backup_count} Backup files, {primary_count} Primary files")
        print(f"[BackupLoader] Unique backup stems: {len(set(item['stem'] for item in backup_data))}")

        return self._backup_data

    def get_stats(self) -> dict:
        """Get statistics about loaded data.

        Returns:
            Dict with counts for backup, unique stems, etc.
        """
        backup_data = self.load_backup_data()
        stems = {item["stem"] for item in backup_data}

        return {
            "total_backup_rows": len(backup_data),
            "unique_stems": len(stems),
        }


# Singleton instance
_loader: BackupLoader | None = None


def get_backup_loader() -> BackupLoader:
    """Get singleton loader instance."""
    global _loader
    if _loader is None:
        _loader = BackupLoader()
    return _loader
