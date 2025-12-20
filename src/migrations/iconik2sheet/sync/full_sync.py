"""Full sync implementation."""

import uuid
from datetime import datetime

from iconik import IconikClient
from sheets import SheetsWriter

from .state import SyncState


class FullSync:
    """Full sync from Iconik to Sheets."""

    def __init__(self) -> None:
        self.iconik = IconikClient()
        self.sheets = SheetsWriter()
        self.state = SyncState()

    def run(self) -> dict:
        """Run full sync.

        Returns:
            Sync result summary
        """
        sync_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        print(f"Starting full sync (ID: {sync_id})")

        result = {
            "sync_id": sync_id,
            "sync_type": "full",
            "started_at": started_at,
            "completed_at": None,
            "assets_new": 0,
            "assets_updated": 0,
            "status": "running",
        }

        try:
            # Sync assets
            assets = self._sync_assets()
            result["assets_new"] = len(assets)

            # Sync collections
            collections = self._sync_collections()

            # Update state
            self.state.mark_sync_complete(
                sync_type="full",
                total_assets=len(assets),
                total_collections=len(collections),
            )

            result["completed_at"] = datetime.now()
            result["status"] = "success"

            # Write sync log
            self.sheets.write_sync_log(result)

            print("Sync complete!")
            print(f"  Assets: {len(assets)}")
            print(f"  Collections: {len(collections)}")

        except Exception as e:
            result["status"] = "failed"
            result["completed_at"] = datetime.now()
            self.sheets.write_sync_log(result)

            print(f"Sync failed: {e}")
            raise

        finally:
            self.iconik.close()

        return result

    def _sync_assets(self) -> list[dict]:
        """Sync all assets."""
        print("Fetching assets...")

        assets = []
        count = 0

        for asset in self.iconik.get_all_assets():
            assets.append(asset.model_dump())
            count += 1
            if count % 100 == 0:
                print(f"  ... {count} assets fetched")

        print(f"  Fetched {len(assets)} assets")

        # Write to sheet
        print("Writing to Iconik_Assets sheet...")
        self.sheets.write_assets(assets)

        return assets

    def _sync_collections(self) -> list[dict]:
        """Sync all collections."""
        print("Fetching collections...")

        collections = []

        for collection in self.iconik.get_all_collections():
            collections.append(collection.model_dump())

        print(f"  Fetched {len(collections)} collections")

        # Write to sheet
        print("Writing to Iconik_Collections sheet...")
        self.sheets.write_collections(collections)

        return collections
