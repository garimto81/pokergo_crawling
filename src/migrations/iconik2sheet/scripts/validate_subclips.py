"""Validate Iconik_Subclips_Metadata quality.

Checks:
1. Parent relationship: original_asset_id must exist in Iconik_General_Metadata
2. Self-reference: id != original_asset_id
3. Missing parent: original_asset_id should not be empty
4. Timecode quality: not round numbers (10s multiples), valid range

Usage:
    python -m scripts.validate_subclips              # Full validation + Sheets export
    python -m scripts.validate_subclips --dry-run    # Validation only (no Sheets write)
"""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from sheets.writer import SheetsWriter
from sync.subclip_validator import SubclipValidator


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate Iconik_Subclips_Metadata")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validation only, no Sheets write",
    )
    args = parser.parse_args()

    console = Console()

    console.print("\n[bold]Iconik Subclips Metadata Validator[/bold]")
    console.print("=" * 60)

    # Run validation
    console.print("\n[bold]Step 1: Loading data from Sheets[/bold]")
    validator = SubclipValidator()

    console.print("  - Loading Iconik_General_Metadata...")
    console.print("  - Loading Iconik_Subclips_Metadata...")

    console.print("\n[bold]Step 2: Running validations[/bold]")
    result = validator.validate()

    # Print summary
    report = result.to_report()
    summary = report["summary"]
    breakdown = report["issues_breakdown"]

    console.print(f"\n[bold]Summary[/bold]")
    console.print(f"  Total Subclips: {summary['total_subclips']}")
    console.print(f"  Valid: {summary['valid']} ({summary['valid_percentage']})")
    console.print(f"  Issues Found: {summary['issues']}")

    # Issues breakdown table
    console.print("\n[bold]Issues Breakdown[/bold]")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Issue Type", width=25)
    table.add_column("Count", justify="right", width=10)

    for issue_type, count in breakdown.items():
        if count > 0:
            table.add_row(issue_type, str(count))

    console.print(table)

    # Sample issues
    if result.orphan_subclips:
        console.print("\n[bold]Sample: Orphan Subclips[/bold] (first 5)")
        for item in result.orphan_subclips[:5]:
            console.print(f"  - {item['id'][:8]}... : {item['title'][:50]}")
            console.print(f"    parent: {item['original_asset_id'][:8]}...")

    if result.missing_parent:
        console.print("\n[bold]Sample: Missing Parent[/bold] (first 5)")
        for item in result.missing_parent[:5]:
            console.print(f"  - {item['id'][:8]}... : {item['title'][:50]}")

    if result.round_timecode:
        console.print("\n[bold]Sample: Round Timecode[/bold] (first 5)")
        for item in result.round_timecode[:5]:
            console.print(
                f"  - {item['id'][:8]}... : {item['time_start_ms']}ms - {item['time_end_ms']}ms"
            )

    # Write to Sheets (all subclips with issue flags)
    if args.dry_run:
        console.print("\n[yellow]Dry run mode - skipping Sheets write[/yellow]")
    else:
        console.print("\n[bold]Step 3: Writing to Sheets (all subclips with flags)[/bold]")

        # Use new validator instance to get all subclips with flags
        validator2 = SubclipValidator()
        all_with_flags = validator2.validate_all_with_flags()

        sheets = SheetsWriter()
        written = sheets.write_validation_report(all_with_flags)
        console.print(f"  Written {written} rows to Subclip_Validation_Report")
        console.print("  Format: All subclips with checkbox columns (G-L)")
        console.print("[green]Done![/green]")


if __name__ == "__main__":
    main()
