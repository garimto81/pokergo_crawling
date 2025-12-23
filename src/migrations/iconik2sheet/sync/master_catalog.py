"""Master_Catalog based asset classification.

Loads filenames from Master_Catalog sheet and provides classification logic.
Assets matching Master_Catalog filenames are classified as General (parent assets).
Assets not matching are classified as Subclips.
"""

from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import get_settings

# UDM metadata 스프레드시트 (Master_Catalog 포함)
UDM_SPREADSHEET_ID = "1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4"


class MasterCatalogClassifier:
    """Classifier based on Master_Catalog filenames.

    Loads filenames from Master_Catalog sheet and caches them for fast lookup.
    Used to distinguish General (parent) assets from Subclips.
    """

    def __init__(self) -> None:
        self._filenames: set[str] | None = None
        self._service = None

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

    def load_filenames(self) -> set[str]:
        """Load all filenames from Master_Catalog (without extension).

        Returns:
            Set of unique filenames (stem only, no extension)
        """
        if self._filenames is not None:
            return self._filenames

        print("[MasterCatalog] Loading filenames from Master_Catalog...")

        result = self.service.spreadsheets().values().get(
            spreadsheetId=UDM_SPREADSHEET_ID,
            range="Master_Catalog!A:Z",
        ).execute()

        values = result.get("values", [])
        if not values:
            print("[MasterCatalog] Warning: Master_Catalog is empty")
            self._filenames = set()
            return self._filenames

        headers = values[0]

        # Find Filename column index
        filename_idx = None
        for i, h in enumerate(headers):
            if h.lower() == "filename":
                filename_idx = i
                break

        if filename_idx is None:
            print("[MasterCatalog] Warning: Filename column not found")
            self._filenames = set()
            return self._filenames

        # Collect filenames (without extension)
        filenames = set()
        for row in values[1:]:
            if len(row) > filename_idx and row[filename_idx]:
                filename = row[filename_idx]
                # Remove extension
                name_without_ext = Path(filename).stem
                filenames.add(name_without_ext)

        self._filenames = filenames
        print(f"[MasterCatalog] Loaded {len(filenames)} unique filenames")

        return self._filenames

    def is_general_asset(self, title: str) -> bool:
        """Check if asset title matches Master_Catalog (→ General).

        Args:
            title: Iconik asset title

        Returns:
            True if matches Master_Catalog (General asset)
            False if not (Subclip)
        """
        filenames = self.load_filenames()
        return title in filenames

    def is_subclip(self, title: str) -> bool:
        """Check if asset is a Subclip (not in Master_Catalog).

        Args:
            title: Iconik asset title

        Returns:
            True if NOT in Master_Catalog (Subclip)
            False if in Master_Catalog (General)
        """
        return not self.is_general_asset(title)


# Singleton instance
_classifier: MasterCatalogClassifier | None = None


def get_classifier() -> MasterCatalogClassifier:
    """Get singleton classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = MasterCatalogClassifier()
    return _classifier
