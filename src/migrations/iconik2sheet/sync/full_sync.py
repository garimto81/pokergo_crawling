"""Full sync implementation."""

import uuid
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from iconik import IconikClient
from sheets import SheetsWriter

from .state import SyncState


class FullSync:
    """Full sync from Iconik to Sheets."""

    def __init__(self) -> None:
        self.iconik = IconikClient()
        self.sheets = SheetsWriter()
        self.state = SyncState()
        self.console = Console()

    def run(self) -> dict:
        """Run full sync.

        Returns:
            Sync result summary
        """
        sync_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        self.console.print(f"[bold blue]Starting full sync[/bold blue] (ID: {sync_id})")

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

            self.console.print(f"[bold green]Sync complete![/bold green]")
            self.console.print(f"  Assets: {len(assets)}")
            self.console.print(f"  Collections: {len(collections)}")

        except Exception as e:
            result["status"] = "failed"
            result["completed_at"] = datetime.now()
            self.sheets.write_sync_log(result)

            self.console.print(f"[bold red]Sync failed:[/bold red] {e}")
            raise

        finally:
            self.iconik.close()

        return result

    def _sync_assets(self) -> list[dict]:
        """Sync all assets."""
        self.console.print("[blue]Fetching assets...[/blue]")

        assets = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Assets", total=None)

            for asset in self.iconik.get_all_assets(progress=progress, task_id=task):
                assets.append(asset.model_dump())

        self.console.print(f"  Fetched {len(assets)} assets")

        # Write to sheet
        self.console.print("[blue]Writing to Iconik_Assets sheet...[/blue]")
        self.sheets.write_assets(assets)

        return assets

    def _sync_collections(self) -> list[dict]:
        """Sync all collections."""
        self.console.print("[blue]Fetching collections...[/blue]")

        collections = []

        for collection in self.iconik.get_all_collections():
            collections.append(collection.model_dump())

        self.console.print(f"  Fetched {len(collections)} collections")

        # Write to sheet
        self.console.print("[blue]Writing to Iconik_Collections sheet...[/blue]")
        self.sheets.write_collections(collections)

        return collections
