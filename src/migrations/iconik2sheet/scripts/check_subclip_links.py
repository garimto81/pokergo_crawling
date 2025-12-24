"""Check Subclip links for deletion targets.

Checks if any assets scheduled for deletion have linked subclips.
If a parent asset is deleted, its subclips will become orphaned.

Usage:
    python -m scripts.check_subclip_links
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from iconik import IconikClient
from sync.backup_loader import get_backup_loader


def main() -> None:
    """Main entry point."""
    console = Console()

    console.print("\n[bold]Subclip Link Check[/bold]")
    console.print("삭제 대상 Asset에 연결된 Subclip 확인\n")

    # 1. Load backup filenames
    console.print("[bold]Step 1: Loading backup files[/bold]")
    loader = get_backup_loader()
    backup_stems = loader.load_backup_filenames()
    console.print(f"  Backup stems: {len(backup_stems)}\n")

    # 2. Get all Iconik assets
    console.print("[bold]Step 2: Scanning Iconik assets[/bold]")

    all_assets = []
    deletion_targets = {}  # asset_id -> title
    subclips_by_parent = {}  # parent_asset_id -> list of subclips

    with IconikClient() as client:
        if not client.health_check():
            console.print("[red]Iconik API connection failed![/red]")
            return

        with Progress() as progress:
            task = progress.add_task("Scanning assets...", total=None)

            for asset in client.get_all_assets():
                all_assets.append(asset)
                progress.update(task, advance=1)

                # Check if this is a deletion target
                if asset.title in backup_stems and asset.type == "ASSET":
                    deletion_targets[asset.id] = asset.title

                # Track subclips by parent
                if asset.original_asset_id:
                    if asset.original_asset_id not in subclips_by_parent:
                        subclips_by_parent[asset.original_asset_id] = []
                    subclips_by_parent[asset.original_asset_id].append({
                        "id": asset.id,
                        "title": asset.title,
                        "time_start": asset.time_start_milliseconds,
                        "time_end": asset.time_end_milliseconds,
                    })

    console.print(f"  Total assets: {len(all_assets)}")
    console.print(f"  Deletion targets: {len(deletion_targets)}")
    console.print(f"  Assets with subclips: {len(subclips_by_parent)}\n")

    # 3. Find affected subclips
    console.print("[bold]Step 3: Finding affected subclips[/bold]")

    affected_targets = {}  # target_id -> list of subclips

    for target_id, target_title in deletion_targets.items():
        if target_id in subclips_by_parent:
            affected_targets[target_id] = {
                "title": target_title,
                "subclips": subclips_by_parent[target_id],
            }

    if not affected_targets:
        console.print("\n[green]No subclips linked to deletion targets.[/green]")
        console.print("삭제 대상에 연결된 Subclip이 없습니다. 안전하게 삭제 가능합니다.\n")
        return

    # 4. Report affected assets
    console.print(f"\n[bold red]WARNING: {len(affected_targets)} deletion targets have linked subclips![/bold red]\n")

    total_subclips = 0

    for target_id, data in affected_targets.items():
        console.print(f"[bold]Parent: {data['title']}[/bold]")
        console.print(f"  Asset ID: {target_id}")
        console.print(f"  Subclips: {len(data['subclips'])}")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Subclip ID", width=40)
        table.add_column("Title", width=50)
        table.add_column("Timecode", width=20)

        for sub in data["subclips"][:10]:  # Show first 10
            start_sec = sub["time_start"] / 1000 if sub["time_start"] else 0
            end_sec = sub["time_end"] / 1000 if sub["time_end"] else 0
            timecode = f"{start_sec:.1f}s - {end_sec:.1f}s"
            table.add_row(sub["id"], sub["title"][:50], timecode)

        console.print(table)

        if len(data["subclips"]) > 10:
            console.print(f"  ... and {len(data['subclips']) - 10} more subclips\n")
        else:
            console.print()

        total_subclips += len(data["subclips"])

    # 5. Summary
    console.print("=" * 60)
    console.print("[bold]Summary[/bold]")
    console.print("=" * 60)
    console.print(f"  Deletion targets with subclips: {len(affected_targets)}")
    console.print(f"  Total affected subclips: {total_subclips}")
    console.print()
    console.print("[yellow]These subclips will become orphaned if parent is deleted.[/yellow]")
    console.print("Consider:")
    console.print("  1. Keep the parent asset (remove from deletion list)")
    console.print("  2. Delete subclips first, then delete parent")
    console.print("  3. Accept orphaned subclips\n")


if __name__ == "__main__":
    main()
