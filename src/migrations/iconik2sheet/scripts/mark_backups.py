"""Mark Iconik Backup Assets with BACKUP_HIDDEN metadata.

Instead of deleting backup assets (which get re-registered by ISG on rescan),
this script marks them with BackupStatus=backup_hidden metadata.

Usage:
    # Dry run (default)
    python -m scripts.mark_backups

    # Execute marking (safe mode - skip assets with subclips)
    python -m scripts.mark_backups --execute --skip-with-subclips

    # Execute marking (all matching assets)
    python -m scripts.mark_backups --execute

    # Skip confirmation prompt
    python -m scripts.mark_backups --execute --yes

    # Output results to CSV
    python -m scripts.mark_backups --execute -o data/marking_report.csv
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync.backup_marker import BackupMarkerService, MarkingResult


def save_report(result: MarkingResult, output_path: str) -> None:
    """Save marking result to CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Asset ID", "Title", "Status", "Error"])

        for asset_id, title in result.marked:
            writer.writerow([asset_id, title, "MARKED", ""])

        for asset_id, title, error in result.failed:
            writer.writerow([asset_id, title, "FAILED", error])

    print(f"\nReport saved to: {path}")


def save_markdown_report(result: MarkingResult, output_path: str) -> None:
    """Save marking result to Markdown file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write("# Iconik Backup Marking Report\n\n")
        f.write(f"**Executed**: {result.start_time.strftime('%Y-%m-%d %H:%M:%S') if result.start_time else 'N/A'}\n")
        f.write(f"**Duration**: {result.duration_seconds:.1f} seconds\n\n")

        f.write("## Summary\n\n")
        f.write("| Item | Count |\n")
        f.write("|------|-------|\n")
        f.write(f"| Master_Catalog Backup Rows | {result.total_backup_rows} |\n")
        f.write(f"| Unique Backup Stems | {result.unique_backup_stems} |\n")
        f.write(f"| Matched Iconik Assets | {result.matched_assets} |\n")
        f.write(f"| Skipped (already marked) | {result.skipped_already_marked} |\n")
        f.write(f"| Skipped (has subclips) | {result.skipped_with_subclips} |\n")
        f.write(f"| **Marked** | **{result.marked_count}** |\n")
        f.write(f"| Failed | {result.failed_count} |\n\n")

        if result.marked:
            f.write("## Marked Assets\n\n")
            f.write("| # | Asset ID | Title |\n")
            f.write("|---|----------|-------|\n")
            for i, (asset_id, title) in enumerate(result.marked, 1):
                safe_title = title.replace("|", "\\|")
                f.write(f"| {i} | {asset_id} | {safe_title} |\n")

        if result.failed:
            f.write("\n## Failed Assets\n\n")
            f.write("| Asset ID | Title | Error |\n")
            f.write("|----------|-------|-------|\n")
            for asset_id, title, error in result.failed:
                safe_title = title.replace("|", "\\|")
                f.write(f"| {asset_id} | {safe_title} | {error} |\n")

    print(f"\nMarkdown report saved to: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mark Iconik Backup Assets with BACKUP_HIDDEN metadata"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute marking (default: dry run)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--skip-with-subclips",
        action="store_true",
        help="Skip assets that have linked subclips (safe mode)",
    )
    parser.add_argument(
        "--include-already-marked",
        action="store_true",
        help="Re-mark assets that are already marked (default: skip)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output CSV file path for results",
    )
    parser.add_argument(
        "--markdown", "-m",
        type=str,
        help="Output Markdown file path for report",
    )
    args = parser.parse_args()

    service = BackupMarkerService()

    result = service.run(
        dry_run=not args.execute,
        skip_confirmation=args.yes,
        skip_with_subclips=args.skip_with_subclips,
        skip_already_marked=not args.include_already_marked,
    )

    service.print_summary(result)

    # Save reports if requested
    if args.output and result.marked_count > 0:
        save_report(result, args.output)

    if args.markdown and result.marked_count > 0:
        save_markdown_report(result, args.markdown)

    # Generate default report on execute
    if args.execute and result.marked_count > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_md = f"docs/reports/iconik-backup-marked-{timestamp[:8]}.md"
        save_markdown_report(result, default_md)


if __name__ == "__main__":
    main()
