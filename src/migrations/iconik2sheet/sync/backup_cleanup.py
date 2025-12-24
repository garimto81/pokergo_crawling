"""Backup cleanup service for Iconik.

Deletes Backup assets from Iconik based on Master_Catalog Role column.
Only deletes General Assets (type=ASSET), preserves Subclips.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

from iconik import IconikClient
from iconik.exceptions import IconikAPIError, IconikNotFoundError

from .backup_loader import get_backup_loader


@dataclass
class CleanupResult:
    """Result of backup cleanup operation."""

    # Counts from Master_Catalog
    total_backup_rows: int = 0
    unique_backup_stems: int = 0

    # Matching results
    matched_assets: int = 0
    skipped_subclips: int = 0
    skipped_with_subclips: int = 0  # Assets skipped because they have linked subclips

    # Target list (for dry-run report)
    targets: list[tuple[str, str]] = field(default_factory=list)  # (asset_id, title)

    # Deletion results
    deleted: list[str] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    # Timing
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def deleted_count(self) -> int:
        return len(self.deleted)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class BackupCleanupService:
    """Service to cleanup backup assets from Iconik.

    Reads backup filenames from Master_Catalog sheet and deletes
    matching assets from Iconik. Only deletes General Assets (type=ASSET),
    preserves Subclips.
    """

    BATCH_SIZE = 50
    DELAY_BETWEEN_BATCHES = 2  # seconds

    def __init__(self) -> None:
        self.loader = get_backup_loader()
        self.console = Console()

    def run(
        self,
        dry_run: bool = True,
        skip_confirmation: bool = False,
        skip_with_subclips: bool = False,
    ) -> CleanupResult:
        """Run backup cleanup.

        Args:
            dry_run: If True, only report what would be deleted (default)
            skip_confirmation: If True, skip DELETE confirmation prompt
            skip_with_subclips: If True, skip assets that have linked subclips (safe mode)

        Returns:
            CleanupResult with statistics
        """
        result = CleanupResult()
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
            self.console.print("[yellow]No backup files found. Nothing to delete.[/yellow]")
            result.end_time = datetime.now()
            return result

        # 2. Get all Iconik assets and find matches
        self.console.print("\n[bold]Step 2: Matching with Iconik assets[/bold]")

        to_delete: list[tuple[str, str]] = []  # (asset_id, title)
        subclips_by_parent: dict[str, list[str]] = {}  # parent_id -> [subclip_ids]
        matched_candidates: list[tuple[str, str]] = []  # (asset_id, title) - before subclip filter

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

                    # Track subclips by parent (for skip_with_subclips filter)
                    if asset.original_asset_id:
                        if asset.original_asset_id not in subclips_by_parent:
                            subclips_by_parent[asset.original_asset_id] = []
                        subclips_by_parent[asset.original_asset_id].append(asset.id)

                    # Check if asset title matches backup stem
                    if asset.title in backup_stems:
                        # Only delete ASSET type (not SUBCLIP)
                        if asset.type == "ASSET":
                            matched_candidates.append((asset.id, asset.title))
                            result.matched_assets += 1
                        else:
                            result.skipped_subclips += 1

            # Apply skip_with_subclips filter
            if skip_with_subclips:
                for asset_id, title in matched_candidates:
                    if asset_id in subclips_by_parent:
                        result.skipped_with_subclips += 1
                    else:
                        to_delete.append((asset_id, title))
            else:
                to_delete = matched_candidates

        self.console.print(f"  Total assets scanned: {asset_count}")
        self.console.print(f"  Matched backup assets: {result.matched_assets}")
        self.console.print(f"  Skipped (type=SUBCLIP): {result.skipped_subclips}")
        if skip_with_subclips:
            self.console.print(f"  Skipped (has linked subclips): {result.skipped_with_subclips}")
            self.console.print(f"  [green]Safe to delete (no subclips): {len(to_delete)}[/green]")

        if not to_delete:
            self.console.print("[yellow]No matching assets found in Iconik.[/yellow]")
            result.end_time = datetime.now()
            return result

        # Save targets list for reporting
        result.targets = to_delete

        # 3. Show deletion preview
        self.console.print("\n[bold]Step 3: Deletion preview[/bold]")
        self._show_deletion_preview(to_delete[:20])  # Show first 20

        if len(to_delete) > 20:
            self.console.print(f"  ... and {len(to_delete) - 20} more")

        # 4. Dry run or execute
        if dry_run:
            self.console.print("\n[yellow]DRY RUN mode - no assets deleted[/yellow]")
            self.console.print(f"Would delete {len(to_delete)} assets from Iconik")
            self.console.print("\nTo execute deletion, run with --execute flag")
            result.end_time = datetime.now()
            return result

        # 5. Confirmation prompt
        if not skip_confirmation:
            self.console.print(f"\n[bold red]WARNING: About to delete {len(to_delete)} assets from Iconik![/bold red]")
            self.console.print("[red]This action is IRREVERSIBLE.[/red]")
            confirm = input("\nType 'DELETE' to confirm: ")
            if confirm != "DELETE":
                self.console.print("[yellow]Aborted.[/yellow]")
                result.end_time = datetime.now()
                return result

        # 6. Execute deletion
        self.console.print("\n[bold]Step 4: Deleting assets[/bold]")
        result = self._execute_deletion(to_delete, result)

        result.end_time = datetime.now()
        return result

    def _show_deletion_preview(self, items: list[tuple[str, str]]) -> None:
        """Show preview of assets to be deleted."""
        # Print simple text format to avoid unicode issues
        self.console.print("\nAssets to be deleted:")
        self.console.print("-" * 80)

        for i, (asset_id, title) in enumerate(items, 1):
            # Sanitize title for safe printing
            safe_title = title[:50].encode('ascii', 'replace').decode('ascii')
            self.console.print(f"  {i:3}. {asset_id[:36]} | {safe_title}")

    def _execute_deletion(
        self,
        to_delete: list[tuple[str, str]],
        result: CleanupResult,
    ) -> CleanupResult:
        """Execute asset deletion with batch processing."""
        total = len(to_delete)

        with IconikClient() as client:
            with Progress() as progress:
                task = progress.add_task("Deleting assets...", total=total)

                for i, (asset_id, title) in enumerate(to_delete):
                    try:
                        client.delete_asset(asset_id)
                        result.deleted.append(asset_id)
                        progress.update(task, advance=1)

                    except IconikNotFoundError:
                        # Already deleted
                        result.not_found.append(asset_id)
                        progress.update(task, advance=1)

                    except IconikAPIError as e:
                        result.failed.append((asset_id, str(e)))
                        progress.update(task, advance=1)

                    # Batch delay
                    if (i + 1) % self.BATCH_SIZE == 0 and i + 1 < total:
                        time.sleep(self.DELAY_BETWEEN_BATCHES)

        self.console.print(f"\n[green]Deleted: {result.deleted_count}[/green]")
        if result.not_found:
            self.console.print(f"[yellow]Already deleted (404): {len(result.not_found)}[/yellow]")
        if result.failed:
            self.console.print(f"[red]Failed: {result.failed_count}[/red]")

        return result

    def print_summary(self, result: CleanupResult) -> None:
        """Print summary of cleanup operation."""
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold]Backup Cleanup Summary[/bold]")
        self.console.print("=" * 60)

        table = Table(show_header=False, box=None)
        table.add_column("Label", width=30)
        table.add_column("Value", width=20)

        table.add_row("Master_Catalog Backup Rows", str(result.total_backup_rows))
        table.add_row("Unique Backup Stems", str(result.unique_backup_stems))
        table.add_row("Matched Iconik Assets", str(result.matched_assets))
        table.add_row("Skipped (type=SUBCLIP)", str(result.skipped_subclips))
        if result.skipped_with_subclips > 0:
            table.add_row("Skipped (has linked subclips)", f"[yellow]{result.skipped_with_subclips}[/yellow]")
        table.add_row("", "")
        table.add_row("Deleted", f"[green]{result.deleted_count}[/green]")
        table.add_row("Already Deleted (404)", f"[yellow]{len(result.not_found)}[/yellow]")
        table.add_row("Failed", f"[red]{result.failed_count}[/red]")
        table.add_row("", "")
        table.add_row("Duration", f"{result.duration_seconds:.1f} seconds")

        self.console.print(table)
        self.console.print("=" * 60)
