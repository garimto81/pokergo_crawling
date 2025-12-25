"""Backup marker service for Iconik.

Marks backup assets with BACKUP_HIDDEN metadata instead of deleting.
This prevents ISG from re-registering deleted assets on rescan.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from config.settings import get_settings
from iconik import IconikClient
from iconik.exceptions import IconikAPIError, IconikNotFoundError

from .backup_loader import get_backup_loader


@dataclass
class MarkingResult:
    """Result of backup marking operation."""

    # Counts from Master_Catalog
    total_backup_rows: int = 0
    unique_backup_stems: int = 0

    # Matching results
    matched_assets: int = 0
    skipped_subclips: int = 0
    skipped_with_subclips: int = 0
    skipped_already_marked: int = 0

    # Target list (for dry-run report)
    targets: list[tuple[str, str]] = field(default_factory=list)  # (asset_id, title)

    # Marking results
    marked: list[tuple[str, str]] = field(default_factory=list)  # (asset_id, title)
    failed: list[tuple[str, str, str]] = field(default_factory=list)  # (asset_id, title, error)

    # Timing
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def marked_count(self) -> int:
        return len(self.marked)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class BackupMarkerService:
    """Service to mark backup assets in Iconik with BACKUP_HIDDEN status.

    Reads backup filenames from Master_Catalog sheet and marks
    matching assets with BackupStatus=backup_hidden metadata.
    Only marks General Assets (type=ASSET), preserves Subclips.
    """

    BACKUP_STATUS_FIELD = "BackupStatus"
    BACKUP_HIDDEN_VALUE = "backup_hidden"
    BATCH_SIZE = 50
    DELAY_BETWEEN_BATCHES = 1  # seconds

    def __init__(self, view_id: str | None = None) -> None:
        self.loader = get_backup_loader()
        self.console = Console()
        self.view_id = view_id or get_settings().iconik.metadata_view_id

    def run(
        self,
        dry_run: bool = True,
        skip_confirmation: bool = False,
        skip_with_subclips: bool = False,
        skip_already_marked: bool = True,
    ) -> MarkingResult:
        """Run backup marking.

        Args:
            dry_run: If True, only report what would be marked (default)
            skip_confirmation: If True, skip confirmation prompt
            skip_with_subclips: If True, skip assets that have linked subclips (safe mode)
            skip_already_marked: If True, skip assets already marked as BACKUP_HIDDEN

        Returns:
            MarkingResult with statistics
        """
        result = MarkingResult()
        result.start_time = datetime.now()

        # 1. Load backup filenames from Master_Catalog
        self.console.print("\n[bold]Step 1: Loading backup files from Master_Catalog[/bold]")
        backup_stems = self.loader.load_backup_filenames()
        stats = self.loader.get_stats()

        result.total_backup_rows = stats["total_backup_rows"]
        result.unique_backup_stems = stats["unique_stems"]

        self.console.print(f"  Backup rows: {result.total_backup_rows}")
        self.console.print(f"  Unique stems: {result.unique_backup_stems}")

        if not backup_stems:
            self.console.print("[yellow]No backup files found. Nothing to mark.[/yellow]")
            result.end_time = datetime.now()
            return result

        # 2. Get all Iconik assets and find matches
        self.console.print("\n[bold]Step 2: Matching with Iconik assets[/bold]")

        to_mark: list[tuple[str, str]] = []  # (asset_id, title)
        subclips_by_parent: dict[str, list[str]] = {}  # parent_id -> [subclip_ids]
        matched_candidates: list[tuple[str, str]] = []  # (asset_id, title)
        already_marked_ids: set[str] = set()

        with IconikClient() as client:
            # Health check
            if not client.health_check():
                self.console.print("[red]Iconik API connection failed![/red]")
                result.end_time = datetime.now()
                return result

            # Get all assets with progress
            with Progress() as progress:
                task = progress.add_task("Scanning Iconik assets...", total=None)

                asset_count = 0
                for asset in client.get_all_assets():
                    asset_count += 1
                    progress.update(task, advance=1, description=f"Scanned {asset_count} assets...")

                    # Track subclips by parent
                    if asset.original_asset_id:
                        if asset.original_asset_id not in subclips_by_parent:
                            subclips_by_parent[asset.original_asset_id] = []
                        subclips_by_parent[asset.original_asset_id].append(asset.id)

                    # Check if asset title matches backup stem
                    if asset.title in backup_stems:
                        if asset.type == "ASSET":
                            matched_candidates.append((asset.id, asset.title))
                            result.matched_assets += 1
                        else:
                            result.skipped_subclips += 1

            # Check already marked status (if enabled)
            if skip_already_marked and matched_candidates:
                self.console.print("\n  Checking already marked assets...")
                with Progress() as progress:
                    task = progress.add_task("Checking metadata...", total=len(matched_candidates))
                    for asset_id, _ in matched_candidates:
                        if self._is_already_marked(client, asset_id):
                            already_marked_ids.add(asset_id)
                            result.skipped_already_marked += 1
                        progress.update(task, advance=1)

            # Apply filters
            for asset_id, title in matched_candidates:
                # Skip already marked
                if asset_id in already_marked_ids:
                    continue
                # Skip with subclips
                if skip_with_subclips and asset_id in subclips_by_parent:
                    result.skipped_with_subclips += 1
                    continue
                to_mark.append((asset_id, title))

        self.console.print(f"  Total assets scanned: {asset_count}")
        self.console.print(f"  Matched backup assets: {result.matched_assets}")
        self.console.print(f"  Skipped (type=SUBCLIP): {result.skipped_subclips}")
        if skip_already_marked:
            self.console.print(f"  Skipped (already marked): {result.skipped_already_marked}")
        if skip_with_subclips:
            self.console.print(f"  Skipped (has linked subclips): {result.skipped_with_subclips}")
        self.console.print(f"  [green]To be marked: {len(to_mark)}[/green]")

        if not to_mark:
            self.console.print("[yellow]No assets to mark.[/yellow]")
            result.end_time = datetime.now()
            return result

        # Save targets list for reporting
        result.targets = to_mark

        # 3. Show marking preview
        self.console.print("\n[bold]Step 3: Marking preview[/bold]")
        self._show_marking_preview(to_mark[:20])

        if len(to_mark) > 20:
            self.console.print(f"  ... and {len(to_mark) - 20} more")

        # 4. Dry run or execute
        if dry_run:
            self.console.print("\n[yellow]DRY RUN mode - no assets marked[/yellow]")
            self.console.print(f"Would mark {len(to_mark)} assets as BACKUP_HIDDEN")
            self.console.print("\nTo execute marking, run with --execute flag")
            result.end_time = datetime.now()
            return result

        # 5. Confirmation prompt
        if not skip_confirmation:
            self.console.print(f"\n[bold cyan]About to mark {len(to_mark)} assets as BACKUP_HIDDEN[/bold cyan]")
            confirm = input("\nType 'MARK' to confirm: ")
            if confirm != "MARK":
                self.console.print("[yellow]Aborted.[/yellow]")
                result.end_time = datetime.now()
                return result

        # 6. Execute marking
        self.console.print("\n[bold]Step 4: Marking assets[/bold]")
        result = self._execute_marking(to_mark, result)

        result.end_time = datetime.now()
        return result

    def _is_already_marked(self, client: IconikClient, asset_id: str) -> bool:
        """Check if asset already has BACKUP_HIDDEN status."""
        try:
            metadata = client.get_asset_metadata(asset_id, self.view_id, raise_for_404=False)
            if not metadata:
                return False
            values = metadata.get("metadata_values", {})
            status = values.get(self.BACKUP_STATUS_FIELD, {})
            field_values = status.get("field_values", [])
            return any(v.get("value") == self.BACKUP_HIDDEN_VALUE for v in field_values)
        except Exception:
            return False

    def _mark_as_backup(self, client: IconikClient, asset_id: str) -> dict[str, Any]:
        """Mark asset with BACKUP_HIDDEN status."""
        metadata_values = {
            self.BACKUP_STATUS_FIELD: {
                "field_values": [{"value": self.BACKUP_HIDDEN_VALUE}]
            }
        }
        return client.update_asset_metadata(asset_id, self.view_id, metadata_values)

    def _show_marking_preview(self, items: list[tuple[str, str]]) -> None:
        """Show preview of assets to be marked."""
        self.console.print("\nAssets to be marked as BACKUP_HIDDEN:")
        self.console.print("-" * 80)

        for i, (asset_id, title) in enumerate(items, 1):
            safe_title = title[:50].encode('ascii', 'replace').decode('ascii')
            self.console.print(f"  {i:3}. {asset_id[:36]} | {safe_title}")

    def _execute_marking(
        self,
        to_mark: list[tuple[str, str]],
        result: MarkingResult,
    ) -> MarkingResult:
        """Execute asset marking with batch processing."""
        total = len(to_mark)

        with IconikClient() as client:
            with Progress() as progress:
                task = progress.add_task("Marking assets...", total=total)

                for i, (asset_id, title) in enumerate(to_mark):
                    try:
                        self._mark_as_backup(client, asset_id)
                        result.marked.append((asset_id, title))
                        progress.update(task, advance=1)

                    except IconikNotFoundError:
                        result.failed.append((asset_id, title, "Asset not found"))
                        progress.update(task, advance=1)

                    except IconikAPIError as e:
                        result.failed.append((asset_id, title, str(e)))
                        progress.update(task, advance=1)

                    # Batch delay
                    if (i + 1) % self.BATCH_SIZE == 0 and i + 1 < total:
                        time.sleep(self.DELAY_BETWEEN_BATCHES)

        self.console.print(f"\n[green]Marked: {result.marked_count}[/green]")
        if result.failed:
            self.console.print(f"[red]Failed: {result.failed_count}[/red]")

        return result

    def print_summary(self, result: MarkingResult) -> None:
        """Print summary of marking operation."""
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold]Backup Marking Summary[/bold]")
        self.console.print("=" * 60)

        table = Table(show_header=False, box=None)
        table.add_column("Label", width=30)
        table.add_column("Value", width=20)

        table.add_row("Master_Catalog Backup Rows", str(result.total_backup_rows))
        table.add_row("Unique Backup Stems", str(result.unique_backup_stems))
        table.add_row("Matched Iconik Assets", str(result.matched_assets))
        table.add_row("Skipped (type=SUBCLIP)", str(result.skipped_subclips))
        if result.skipped_already_marked > 0:
            table.add_row("Skipped (already marked)", f"[dim]{result.skipped_already_marked}[/dim]")
        if result.skipped_with_subclips > 0:
            table.add_row("Skipped (has linked subclips)", f"[yellow]{result.skipped_with_subclips}[/yellow]")
        table.add_row("", "")
        table.add_row("Marked as BACKUP_HIDDEN", f"[green]{result.marked_count}[/green]")
        table.add_row("Failed", f"[red]{result.failed_count}[/red]")
        table.add_row("", "")
        table.add_row("Duration", f"{result.duration_seconds:.1f} seconds")

        self.console.print(table)
        self.console.print("=" * 60)
